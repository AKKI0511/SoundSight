from dataclasses import dataclass

from config import DEFAULT_CONFIG, FusionConfig
from feature_extractor import AudioFeatures
from schemas import CandidateType
from signal_detector import SignalDecision
from vad_detector import SpeechDecision


@dataclass(frozen=True)
class FusionDecision:
    timestamp_ms: int
    window_start_ms: int
    window_end_ms: int
    features: AudioFeatures
    speech: SpeechDecision
    signal: SignalDecision
    candidate_type: CandidateType | None
    candidate_confidence: float
    should_call_model: bool
    candidate: bool
    quiet: bool

    def metadata(self, clip_id: str) -> dict[str, object]:
        return {
            "clipId": clip_id,
            "timestampMs": self.timestamp_ms,
            "windowStartMs": self.window_start_ms,
            "windowEndMs": self.window_end_ms,
            "candidateType": self.candidate_type,
            "candidateConfidence": self.candidate_confidence,
            "rms": self.features.rms,
            "noiseFloor": self.features.noise_floor,
            "rmsZScore": self.features.rms_z_score,
            "onsetScore": self.features.onset_score,
            "speechProbability": self.speech.speech_probability,
            "speechSource": self.speech.source,
        }


@dataclass
class CandidateFusionEngine:
    clip_id: str
    config: FusionConfig = DEFAULT_CONFIG.fusion

    def process(
        self,
        features: AudioFeatures,
        signal: SignalDecision,
        speech: SpeechDecision,
    ) -> FusionDecision:
        candidate_type = self._candidate_type(features, signal, speech)
        candidate_confidence = self._candidate_confidence(
            candidate_type,
            features,
            signal,
            speech,
        )
        candidate = (
            candidate_type is not None
            and candidate_confidence >= self.config.minimum_candidate_confidence
        )
        should_call_model = self._should_call_model(
            candidate_type,
            candidate_confidence,
            signal,
            speech,
        )
        quiet = signal.quiet and speech.speech_probability < 0.32 and not candidate

        return FusionDecision(
            timestamp_ms=features.timestamp_ms,
            window_start_ms=features.window_start_ms,
            window_end_ms=features.window_end_ms,
            features=features,
            speech=speech,
            signal=signal,
            candidate_type=candidate_type,
            candidate_confidence=round(candidate_confidence, 3),
            should_call_model=should_call_model,
            candidate=candidate,
            quiet=quiet,
        )

    def _candidate_type(
        self,
        features: AudioFeatures,
        signal: SignalDecision,
        speech: SpeechDecision,
    ) -> CandidateType | None:
        hint = _clip_hint(self.clip_id)

        if hint == "speech_attention" and (
            speech.speech_probability >= 0.38 or signal.signal_active
        ):
            return "speech_attention"

        if hint == "door_knock" and signal.burst_confidence >= 0.35:
            return "door_knock"

        if hint in {"fire_alarm", "emergency_vehicle"} and signal.signal_active:
            return hint

        if speech.speech_active:
            return "speech_attention"

        if (
            signal.onset_burst_count >= 1
            and signal.burst_confidence >= 0.55
            and signal.sustained_ms < self.config.alarm_min_sustained_ms
        ):
            return "door_knock"

        alarm_like = (
            signal.signal_active
            and (
                signal.sustained_ms >= self.config.alarm_min_sustained_ms
                or signal.sustained_confidence >= self.config.alarm_high_confidence
                or features.rms >= 0.1
            )
        )
        if alarm_like:
            if features.spectral_centroid >= 1_700 and features.zero_crossing_rate >= 0.055:
                return "fire_alarm"
            return "emergency_vehicle"

        if signal.signal_active or speech.speech_probability >= 0.45:
            return "unknown"

        return None

    def _candidate_confidence(
        self,
        candidate_type: CandidateType | None,
        features: AudioFeatures,
        signal: SignalDecision,
        speech: SpeechDecision,
    ) -> float:
        if candidate_type is None:
            return 0.0

        if candidate_type == "speech_attention":
            hint_bonus = 0.18 if _clip_hint(self.clip_id) == "speech_attention" else 0.0
            return _clamp01(
                max(speech.speech_probability, signal.confidence * 0.65) + hint_bonus
            )

        if candidate_type == "door_knock":
            return _clamp01(max(signal.burst_confidence, features.onset_score / 4.0))

        if candidate_type in {"fire_alarm", "emergency_vehicle"}:
            duration_bonus = min(0.25, signal.sustained_ms / 4_000)
            hint_bonus = 0.12 if _clip_hint(self.clip_id) == candidate_type else 0.0
            return _clamp01(
                max(signal.sustained_confidence, signal.confidence * 0.85)
                + duration_bonus
                + hint_bonus
            )

        return _clamp01(max(signal.confidence, speech.speech_probability))

    def _should_call_model(
        self,
        candidate_type: CandidateType | None,
        confidence: float,
        signal: SignalDecision,
        speech: SpeechDecision,
    ) -> bool:
        if candidate_type is None:
            return False

        if candidate_type in {"fire_alarm", "emergency_vehicle"}:
            return (
                signal.sustained_ms >= self.config.alarm_min_sustained_ms
                or confidence >= self.config.alarm_high_confidence
            )

        if candidate_type == "door_knock":
            return confidence >= 0.55

        if candidate_type == "speech_attention":
            return speech.speech_active or confidence >= 0.72

        return confidence >= self.config.unknown_model_confidence


def _clip_hint(clip_id: str) -> CandidateType | None:
    normalized = clip_id.lower().replace("-", "_").replace(" ", "_")

    if "fire" in normalized and "alarm" in normalized:
        return "fire_alarm"

    if "ambulance" in normalized or "siren" in normalized or "emergency" in normalized:
        return "emergency_vehicle"

    if (
        "attention" in normalized
        or "baby" in normalized
        or "cry" in normalized
        or "speech" in normalized
        or "address" in normalized
        or "indoor" in normalized
    ):
        return "speech_attention"

    tokens = set(normalized.split("_"))
    if "knock" in tokens or "doorbell" in normalized or normalized.startswith("door_"):
        return "door_knock"

    return None


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, float(value)))
