from collections import deque
from dataclasses import dataclass, field

from config import DEFAULT_CONFIG, SignalDetectorConfig
from feature_extractor import AudioFeatures


@dataclass(frozen=True)
class SignalDecision:
    timestamp_ms: int
    signal_active: bool
    signal_started: bool
    quiet: bool
    confidence: float
    burst_confidence: float
    sustained_confidence: float
    sustained_ms: int
    onset_burst_count: int


@dataclass
class SignalDetector:
    config: SignalDetectorConfig = DEFAULT_CONFIG.signal
    _active: bool = False
    _active_start_ms: int | None = None
    _last_signal_ms: int | None = None
    _strong_start_ms: int | None = None
    _onset_times: deque[int] = field(default_factory=deque)

    def process(self, features: AudioFeatures) -> SignalDecision:
        timestamp_ms = features.timestamp_ms
        is_start_signal = self._is_start_signal(features)
        is_keep_signal = self._is_keep_signal(features)
        is_strong_signal = self._is_strong_signal(features)

        if features.onset_score >= self.config.knock_onset_threshold and (
            features.rms >= max(features.noise_floor * 1.5, 0.025)
        ):
            self._onset_times.append(timestamp_ms)

        while (
            self._onset_times
            and timestamp_ms - self._onset_times[0] > self.config.knock_window_ms
        ):
            self._onset_times.popleft()

        signal_started = False
        if not self._active and is_start_signal:
            self._active = True
            self._active_start_ms = timestamp_ms
            self._last_signal_ms = timestamp_ms
            signal_started = True
        elif self._active and is_keep_signal:
            self._last_signal_ms = timestamp_ms

        if is_strong_signal:
            if self._strong_start_ms is None:
                self._strong_start_ms = timestamp_ms
        else:
            self._strong_start_ms = None

        if self._active and not self._should_remain_active(features):
            self._active = False
            self._active_start_ms = None
            self._last_signal_ms = None

        sustained_ms = (
            0
            if self._strong_start_ms is None
            else max(0, timestamp_ms - self._strong_start_ms + 500)
        )
        burst_confidence = _clamp01(
            max(features.onset_score / 4.0, len(self._onset_times) / 3.0)
        )
        sustained_confidence = _clamp01(
            max(
                features.sustained_energy_score,
                (features.energy_ratio - 1.0) / 5.0,
                features.rms_z_score / 6.0,
            )
        )
        confidence = _clamp01(
            max(
                sustained_confidence,
                burst_confidence * 0.95,
                min(features.rms / max(features.noise_floor * 6.0, 0.18), 1.0),
            )
        )

        quiet = (
            features.silence_score >= 0.45
            and features.rms < max(features.noise_floor * 1.35, self.config.absolute_keep_rms)
        )

        return SignalDecision(
            timestamp_ms=timestamp_ms,
            signal_active=self._active,
            signal_started=signal_started,
            quiet=quiet,
            confidence=round(confidence, 3),
            burst_confidence=round(burst_confidence, 3),
            sustained_confidence=round(sustained_confidence, 3),
            sustained_ms=sustained_ms,
            onset_burst_count=len(self._onset_times),
        )

    def _is_start_signal(self, features: AudioFeatures) -> bool:
        return any(
            (
                features.rms_z_score >= self.config.start_rms_z,
                features.energy_ratio >= self.config.start_energy_ratio,
                features.rms >= self.config.absolute_start_rms,
                features.onset_score >= self.config.onset_start
                and features.rms >= self.config.absolute_keep_rms,
                features.sustained_energy_score >= self.config.sustained_start_score,
            )
        )

    def _is_keep_signal(self, features: AudioFeatures) -> bool:
        return any(
            (
                features.rms_z_score >= self.config.keep_rms_z,
                features.energy_ratio >= self.config.keep_energy_ratio,
                features.rms >= self.config.absolute_keep_rms,
                features.onset_score >= self.config.onset_keep
                and features.rms >= max(features.noise_floor * 1.2, 0.02),
                features.sustained_energy_score >= self.config.sustained_keep_score,
            )
        )

    def _is_strong_signal(self, features: AudioFeatures) -> bool:
        return any(
            (
                features.energy_ratio >= self.config.start_energy_ratio,
                features.rms_z_score >= self.config.start_rms_z,
                features.rms >= self.config.absolute_start_rms,
                features.sustained_energy_score >= self.config.sustained_start_score,
            )
        )

    def _should_remain_active(self, features: AudioFeatures) -> bool:
        if self._active_start_ms is None or self._last_signal_ms is None:
            return False

        if features.timestamp_ms - self._active_start_ms < self.config.min_alive_ms:
            return True

        return features.timestamp_ms - self._last_signal_ms <= self.config.grace_ms


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, float(value)))
