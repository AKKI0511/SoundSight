from dataclasses import dataclass, field

from numpy.typing import NDArray

from audio_loader import FloatArray
from config import DEFAULT_CONFIG, StateMachineConfig
from fusion_engine import FusionDecision
from model_gateway import analyze_candidate_with_gemma4
from schemas import (
    AlertEndEvent,
    AlertStartEvent,
    CandidateStartEvent,
    CandidateUpdateEvent,
    EngineLogEvent,
    EngineState,
    LanguageCode,
    ModelCallEvent,
    ModelResultEvent,
    StreamEvent,
)


@dataclass
class AlertStateMachine:
    session_id: str
    clip_id: str
    language: LanguageCode = "en"
    config: StateMachineConfig = DEFAULT_CONFIG.state_machine
    state: EngineState = "IDLE"
    candidate_id: str | None = None
    candidate_start_ms: int | None = None
    last_candidate_ms: int | None = None
    candidate_type: str | None = None
    best_candidate_confidence: float = 0.0
    model_called: bool = False
    active_start_ms: int | None = None
    active_event_id: str | None = None
    quiet_start_ms: int | None = None
    candidate_count: int = 0
    alert_count: int = 0

    async def process(
        self,
        decision: FusionDecision,
        candidate_window: FloatArray | NDArray,
    ) -> list[StreamEvent]:
        events: list[StreamEvent] = []

        if self.state == "IDLE":
            events.extend(self._process_idle(decision))
        elif self.state == "CANDIDATE":
            events.extend(self._process_candidate_liveness(decision))
        elif self.state == "ACTIVE":
            events.extend(self._process_active_liveness(decision))
        elif self.state == "COOLDOWN":
            events.extend(self._process_cooldown_liveness(decision))

        events.append(self._engine_log(decision))

        if self.state in {"CANDIDATE", "ACTIVE"} and decision.candidate:
            events.append(self._candidate_update(decision))

        if (
            self.state == "CANDIDATE"
            and decision.candidate
            and decision.should_call_model
            and not self.model_called
            and self.candidate_id is not None
            and decision.candidate_type is not None
        ):
            events.extend(await self._call_model(decision, candidate_window))

        return events

    def finish(self, timestamp_ms: int) -> list[StreamEvent]:
        if self.active_event_id is None:
            self._reset_to_idle()
            return []

        event_id = self.active_event_id
        self._reset_to_idle()
        return [
            AlertEndEvent(
                session_id=self.session_id,
                event_id=event_id,
                timestamp_ms=timestamp_ms,
            )
        ]

    def _process_idle(self, decision: FusionDecision) -> list[StreamEvent]:
        if not decision.candidate or decision.candidate_type is None:
            return []

        self._enter_candidate(decision)
        assert self.candidate_id is not None
        return [
            CandidateStartEvent(
                session_id=self.session_id,
                candidate_id=self.candidate_id,
                timestamp_ms=decision.timestamp_ms,
                window_start_ms=decision.window_start_ms,
                window_end_ms=decision.window_end_ms,
                candidate_type=decision.candidate_type,
                candidate_confidence=decision.candidate_confidence,
            )
        ]

    def _process_candidate_liveness(self, decision: FusionDecision) -> list[StreamEvent]:
        if decision.candidate:
            self._update_candidate(decision)
            return []

        last_candidate_ms = self.last_candidate_ms or self.candidate_start_ms
        if last_candidate_ms is None:
            self._reset_to_idle()
            return []

        if decision.timestamp_ms - last_candidate_ms >= self.config.candidate_timeout_ms:
            self._reset_to_idle()

        return []

    def _process_active_liveness(self, decision: FusionDecision) -> list[StreamEvent]:
        if decision.candidate:
            self._update_candidate(decision)
            self.quiet_start_ms = None
            return []

        if self.quiet_start_ms is None:
            self.state = "COOLDOWN"
            self.quiet_start_ms = decision.timestamp_ms

        return []

    def _process_cooldown_liveness(self, decision: FusionDecision) -> list[StreamEvent]:
        if decision.candidate and self.active_event_id is not None:
            self.state = "ACTIVE"
            self.quiet_start_ms = None
            self._update_candidate(decision)
            return []

        if self.quiet_start_ms is None:
            self.quiet_start_ms = decision.timestamp_ms
            return []

        active_age_ms = (
            0
            if self.active_start_ms is None
            else decision.timestamp_ms - self.active_start_ms
        )
        cooldown_elapsed = decision.timestamp_ms - self.quiet_start_ms
        if (
            cooldown_elapsed < self.config.quiet_cooldown_ms
            or active_age_ms < self.config.min_active_ms
        ):
            return []

        if self.active_event_id is None:
            self._reset_to_idle()
            return []

        event_id = self.active_event_id
        self._reset_to_idle()
        return [
            AlertEndEvent(
                session_id=self.session_id,
                event_id=event_id,
                timestamp_ms=decision.timestamp_ms,
            )
        ]

    async def _call_model(
        self,
        decision: FusionDecision,
        candidate_window: FloatArray | NDArray,
    ) -> list[StreamEvent]:
        assert self.candidate_id is not None
        assert decision.candidate_type is not None

        self.model_called = True
        model_call = ModelCallEvent(
            session_id=self.session_id,
            candidate_id=self.candidate_id,
            timestamp_ms=decision.timestamp_ms,
            clip_id=self.clip_id,
            language=self.language,
            reason="candidate_event_confirmed",
            window_start_ms=decision.window_start_ms,
            window_end_ms=decision.window_end_ms,
            candidate_type=decision.candidate_type,
            candidate_confidence=decision.candidate_confidence,
        )
        analysis = await analyze_candidate_with_gemma4(
            candidate_window,
            decision.metadata(self.clip_id),
            self.language,
        )
        model_result = ModelResultEvent(
            session_id=self.session_id,
            candidate_id=self.candidate_id,
            timestamp_ms=decision.timestamp_ms,
            clip_id=self.clip_id,
            analysis=analysis,
        )

        events: list[StreamEvent] = [model_call, model_result]
        if not analysis.should_alert:
            self.state = "COOLDOWN"
            self.quiet_start_ms = decision.timestamp_ms
            return events

        self.alert_count += 1
        event_id = f"{analysis.detected_sound_type}_{self.alert_count}"
        self.state = "ACTIVE"
        self.active_start_ms = decision.timestamp_ms
        self.active_event_id = event_id
        self.quiet_start_ms = None
        events.append(
            AlertStartEvent(
                session_id=self.session_id,
                event_id=event_id,
                timestamp_ms=decision.timestamp_ms,
                alert=analysis.alert,
            )
        )
        return events

    def _engine_log(self, decision: FusionDecision) -> EngineLogEvent:
        return EngineLogEvent(
            session_id=self.session_id,
            timestamp_ms=decision.timestamp_ms,
            window_start_ms=decision.window_start_ms,
            window_end_ms=decision.window_end_ms,
            rms=decision.features.rms,
            noise_floor=decision.features.noise_floor,
            rms_z_score=decision.features.rms_z_score,
            onset_score=decision.features.onset_score,
            spectral_flux=decision.features.spectral_flux,
            zero_crossing_rate=decision.features.zero_crossing_rate,
            spectral_centroid=decision.features.spectral_centroid,
            sustained_energy_score=decision.features.sustained_energy_score,
            silence_score=decision.features.silence_score,
            speech_probability=decision.speech.speech_probability,
            speech_source=decision.speech.source,
            speech_warning=decision.speech.warning,
            candidate_type=decision.candidate_type,
            candidate_confidence=decision.candidate_confidence,
            should_call_model=decision.should_call_model,
            state=self.state,
            candidate=decision.candidate,
        )

    def _candidate_update(self, decision: FusionDecision) -> CandidateUpdateEvent:
        assert self.candidate_id is not None
        assert decision.candidate_type is not None
        return CandidateUpdateEvent(
            session_id=self.session_id,
            candidate_id=self.candidate_id,
            timestamp_ms=decision.timestamp_ms,
            window_start_ms=decision.window_start_ms,
            window_end_ms=decision.window_end_ms,
            candidate_type=decision.candidate_type,
            candidate_confidence=decision.candidate_confidence,
            should_call_model=decision.should_call_model,
            state=self.state,
        )

    def _enter_candidate(self, decision: FusionDecision) -> None:
        self.candidate_count += 1
        self.candidate_id = f"candidate_{self.candidate_count}"
        self.state = "CANDIDATE"
        self.candidate_start_ms = decision.timestamp_ms
        self.last_candidate_ms = decision.timestamp_ms
        self.candidate_type = decision.candidate_type
        self.best_candidate_confidence = decision.candidate_confidence
        self.model_called = False
        self.quiet_start_ms = None

    def _update_candidate(self, decision: FusionDecision) -> None:
        self.last_candidate_ms = decision.timestamp_ms
        if decision.candidate_confidence >= self.best_candidate_confidence:
            self.best_candidate_confidence = decision.candidate_confidence
            self.candidate_type = decision.candidate_type

    def _reset_to_idle(self) -> None:
        self.state = "IDLE"
        self.candidate_id = None
        self.candidate_start_ms = None
        self.last_candidate_ms = None
        self.candidate_type = None
        self.best_candidate_confidence = 0.0
        self.model_called = False
        self.active_start_ms = None
        self.active_event_id = None
        self.quiet_start_ms = None
