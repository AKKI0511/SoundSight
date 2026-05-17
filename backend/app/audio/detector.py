from dataclasses import dataclass

import numpy as np

from app.audio.windowing import AudioWindow
from app.config import DEFAULT_CONFIG, DetectorConfig, TriggerMode


@dataclass(frozen=True)
class DetectorDecision:
    timestamp_ms: int
    window_start_ms: int
    window_end_ms: int
    rms: float
    peak: float
    onset_score: float
    silent: bool
    should_call_model: bool
    reason: str
    candidate_type: str
    candidate_confidence: float

    def metadata(self, clip_id: str, trigger_mode: TriggerMode) -> dict[str, object]:
        return {
            "clipId": clip_id,
            "timestampMs": self.timestamp_ms,
            "windowStartMs": self.window_start_ms,
            "windowEndMs": self.window_end_ms,
            "triggerMode": trigger_mode,
            "candidateType": self.candidate_type,
            "candidateConfidence": self.candidate_confidence,
            "rms": self.rms,
            "peak": self.peak,
            "onsetScore": self.onset_score,
            "silent": self.silent,
            "reason": self.reason,
        }


def analyze_window(
    window: AudioWindow,
    *,
    trigger_mode: TriggerMode,
    active_event: bool,
    config: DetectorConfig = DEFAULT_CONFIG.detector,
) -> DetectorDecision:
    rms = _rms(window.samples)
    peak = float(np.max(np.abs(window.samples))) if window.samples.size else 0.0
    onset_score = _onset_score(window.samples)
    silent = rms < config.silence_rms and peak < config.silence_peak

    if trigger_mode == "interval":
        should_call_model = True
        reason = "interval"
        confidence = max(0.05, _confidence(rms, peak, onset_score, config))
    elif active_event and silent:
        should_call_model = True
        reason = "active_quiet_check"
        confidence = 0.0
    else:
        candidate = (
            rms >= config.candidate_rms
            or peak >= config.candidate_peak
            or onset_score >= config.candidate_onset
        )
        should_call_model = candidate
        reason = "energy_or_onset" if candidate else "clear_silence"
        confidence = _confidence(rms, peak, onset_score, config) if candidate else 0.0

    return DetectorDecision(
        timestamp_ms=window.end_ms,
        window_start_ms=window.start_ms,
        window_end_ms=window.end_ms,
        rms=round(rms, 6),
        peak=round(peak, 6),
        onset_score=round(onset_score, 6),
        silent=silent,
        should_call_model=should_call_model,
        reason=reason,
        candidate_type="audio_event",
        candidate_confidence=round(confidence, 3),
    )


def _rms(samples: np.ndarray) -> float:
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(samples, dtype=np.float32))))


def _onset_score(samples: np.ndarray) -> float:
    if samples.size < 2:
        return 0.0
    frame_count = min(16, max(1, samples.size // 512))
    frames = np.array_split(samples, frame_count)
    frame_rms = np.asarray([_rms(frame) for frame in frames], dtype=np.float32)
    if frame_rms.size < 2:
        return 0.0
    return float(np.max(np.maximum(np.diff(frame_rms), 0.0)))


def _confidence(
    rms: float,
    peak: float,
    onset_score: float,
    config: DetectorConfig,
) -> float:
    return min(
        1.0,
        max(
            rms / max(config.candidate_rms * 3.0, 0.001),
            peak / max(config.candidate_peak * 2.0, 0.001),
            onset_score / max(config.candidate_onset * 2.0, 0.001),
        ),
    )
