from dataclasses import dataclass, field

from numpy.typing import NDArray

from detectors import DetectorFeatures
from mock_events import analyze_candidate_window
from schemas import (
    AlertEndEvent,
    AlertStartEvent,
    EngineLogEvent,
    EngineState,
    ModelCallEvent,
    StreamEvent,
)


@dataclass
class StateMachineConfig:
    model_context_ms: int = 1000
    candidate_timeout_ms: int = 1000
    min_active_ms: int = 2000
    quiet_cooldown_ms: int = 1500


@dataclass
class AlertStateMachine:
    session_id: str
    clip_id: str
    config: StateMachineConfig = field(default_factory=StateMachineConfig)
    state: EngineState = "IDLE"
    candidate_start_ms: int | None = None
    last_candidate_ms: int | None = None
    active_start_ms: int | None = None
    active_event_id: str | None = None
    quiet_start_ms: int | None = None
    event_count: int = 0
    emitted_sound_types: set[str] = field(default_factory=set)

    def process(
        self,
        features: DetectorFeatures,
        audio_window: NDArray,
    ) -> list[StreamEvent]:
        events: list[StreamEvent] = []

        if self.state == "IDLE" and features.candidate:
            self._enter_candidate(features.timestamp_ms)

        if self.state == "CANDIDATE" and features.candidate:
            self.last_candidate_ms = features.timestamp_ms

        events.append(self._engine_log(features))

        if self.state == "CANDIDATE":
            events.extend(self._process_candidate(features, audio_window))
        elif self.state == "ACTIVE":
            events.extend(self._process_active(features))
        elif self.state == "COOLDOWN":
            events.extend(self._process_cooldown(features))

        return events

    def finish(self, timestamp_ms: int) -> list[StreamEvent]:
        if self.active_event_id is None:
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

    def _process_candidate(
        self,
        features: DetectorFeatures,
        audio_window: NDArray,
    ) -> list[StreamEvent]:
        if self.candidate_start_ms is None:
            self._enter_candidate(features.timestamp_ms)

        assert self.candidate_start_ms is not None
        last_candidate_ms = self.last_candidate_ms or self.candidate_start_ms

        if (
            features.quiet
            and features.timestamp_ms - last_candidate_ms
            >= self.config.candidate_timeout_ms
        ):
            self._reset_to_idle()
            return []

        if (
            features.timestamp_ms - self.candidate_start_ms
            < self.config.model_context_ms
        ):
            return []

        analysis = analyze_candidate_window(
            audio_window,
            self.clip_id,
            features.timestamp_ms,
        )
        reason = "candidate_event_confirmed"
        model_call = ModelCallEvent(
            session_id=self.session_id,
            timestamp_ms=features.timestamp_ms,
            clip_id=self.clip_id,
            reason=reason,
            window_start_ms=features.window_start_ms,
            window_end_ms=features.window_end_ms,
            analysis=analysis,
        )

        if (
            not analysis.should_alert
            or analysis.detected_sound_type in self.emitted_sound_types
        ):
            self.state = "COOLDOWN"
            self.quiet_start_ms = features.timestamp_ms
            return [model_call]

        self.event_count += 1
        event_id = f"{analysis.detected_sound_type}_{self.event_count}"
        self.state = "ACTIVE"
        self.active_start_ms = features.timestamp_ms
        self.active_event_id = event_id
        self.quiet_start_ms = None
        self.emitted_sound_types.add(analysis.detected_sound_type)

        return [
            model_call,
            AlertStartEvent(
                session_id=self.session_id,
                event_id=event_id,
                timestamp_ms=features.timestamp_ms,
                alert=analysis.alert,
            ),
        ]

    def _process_active(self, features: DetectorFeatures) -> list[StreamEvent]:
        if self.active_start_ms is None:
            self.active_start_ms = features.timestamp_ms

        if (
            features.quiet
            and features.timestamp_ms - self.active_start_ms
            >= self.config.min_active_ms
        ):
            self.state = "COOLDOWN"
            self.quiet_start_ms = features.timestamp_ms

        return []

    def _process_cooldown(self, features: DetectorFeatures) -> list[StreamEvent]:
        if features.candidate:
            self.state = "ACTIVE"
            self.quiet_start_ms = None
            return []

        if self.quiet_start_ms is None:
            self.quiet_start_ms = features.timestamp_ms
            return []

        if (
            features.timestamp_ms - self.quiet_start_ms
            < self.config.quiet_cooldown_ms
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
                timestamp_ms=features.timestamp_ms,
            )
        ]

    def _engine_log(self, features: DetectorFeatures) -> EngineLogEvent:
        return EngineLogEvent(
            session_id=self.session_id,
            timestamp_ms=features.timestamp_ms,
            window_start_ms=features.window_start_ms,
            window_end_ms=features.window_end_ms,
            rms=features.rms,
            noise_floor=features.noise_floor,
            energy_ratio=features.energy_ratio,
            onset_score=features.onset_score,
            sustained_energy=features.sustained_energy,
            state=self.state,
            candidate=features.candidate,
        )

    def _enter_candidate(self, timestamp_ms: int) -> None:
        self.state = "CANDIDATE"
        self.candidate_start_ms = timestamp_ms
        self.last_candidate_ms = timestamp_ms

    def _reset_to_idle(self) -> None:
        self.state = "IDLE"
        self.candidate_start_ms = None
        self.last_candidate_ms = None
        self.active_start_ms = None
        self.active_event_id = None
        self.quiet_start_ms = None
