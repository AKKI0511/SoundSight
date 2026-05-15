from collections import deque
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray


FloatArray = NDArray[np.float32]


@dataclass(frozen=True)
class DetectorFeatures:
    timestamp_ms: int
    window_start_ms: int
    window_end_ms: int
    rms: float
    noise_floor: float
    energy_ratio: float
    onset_score: float
    sustained_energy: bool
    candidate: bool
    quiet: bool


@dataclass
class DetectorConfig:
    initial_noise_ms: int = 2000
    min_noise_floor: float = 0.006
    absolute_rms_threshold: float = 0.09
    min_event_rms: float = 0.04
    energy_ratio_threshold: float = 1.75
    onset_score_threshold: float = 2.4
    sustained_ratio_threshold: float = 1.35
    sustained_frames: int = 3
    quiet_ratio_threshold: float = 1.25
    quiet_rms_threshold: float = 0.045
    history_frames: int = 8


@dataclass
class SimpleAudioDetector:
    config: DetectorConfig = field(default_factory=DetectorConfig)
    noise_floor: float = 0.006
    _prev_rms: float | None = None
    _background_rms: list[float] = field(default_factory=list)
    _rms_history: deque[float] = field(default_factory=deque)

    def process_frame(
        self,
        frame: FloatArray,
        *,
        timestamp_ms: int,
        window_start_ms: int,
        window_end_ms: int,
    ) -> DetectorFeatures:
        rms = _rms(frame)
        self._rms_history.append(rms)
        while len(self._rms_history) > self.config.history_frames:
            self._rms_history.popleft()

        if timestamp_ms <= self.config.initial_noise_ms:
            self._background_rms.append(rms)
            self.noise_floor = max(
                self.config.min_noise_floor,
                float(np.median(self._background_rms)),
            )

        noise_floor = max(self.noise_floor, self.config.min_noise_floor)
        energy_ratio = rms / noise_floor
        onset_score = self._onset_score(rms)
        sustained_energy = self._has_sustained_energy(noise_floor)

        dynamic_threshold = max(
            noise_floor * self.config.energy_ratio_threshold,
            noise_floor + 0.02,
            self.config.min_event_rms,
        )
        absolute_candidate = rms >= self.config.absolute_rms_threshold
        energy_candidate = rms >= dynamic_threshold
        onset_candidate = (
            onset_score >= self.config.onset_score_threshold
            and rms >= max(noise_floor + 0.015, self.config.min_event_rms)
        )
        candidate = (
            absolute_candidate
            or energy_candidate
            or onset_candidate
            or sustained_energy
        )

        quiet_threshold = max(
            noise_floor * self.config.quiet_ratio_threshold,
            self.config.quiet_rms_threshold,
        )
        quiet = rms < quiet_threshold and not absolute_candidate

        if timestamp_ms > self.config.initial_noise_ms and quiet:
            self.noise_floor = max(
                self.config.min_noise_floor,
                (self.noise_floor * 0.96) + (rms * 0.04),
            )

        self._prev_rms = rms

        return DetectorFeatures(
            timestamp_ms=timestamp_ms,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            rms=round(rms, 6),
            noise_floor=round(noise_floor, 6),
            energy_ratio=round(energy_ratio, 3),
            onset_score=round(onset_score, 3),
            sustained_energy=sustained_energy,
            candidate=candidate,
            quiet=quiet,
        )

    def _onset_score(self, rms: float) -> float:
        if self._prev_rms is None:
            return 0.0

        previous = max(self._prev_rms, self.config.min_noise_floor)
        return max(0.0, rms / previous)

    def _has_sustained_energy(self, noise_floor: float) -> bool:
        if len(self._rms_history) < self.config.sustained_frames:
            return False

        recent = list(self._rms_history)[-self.config.sustained_frames :]
        threshold = max(
            noise_floor * self.config.sustained_ratio_threshold,
            self.config.min_event_rms,
        )
        return all(value >= threshold for value in recent)


def _rms(frame: FloatArray) -> float:
    if frame.size == 0:
        return 0.0

    return float(np.sqrt(np.mean(np.square(frame, dtype=np.float32))))
