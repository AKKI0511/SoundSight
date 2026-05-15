from collections import deque
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray
from scipy.signal import get_window

from audio_loader import FloatArray
from config import DEFAULT_CONFIG, FeatureConfig


@dataclass(frozen=True)
class AudioFeatures:
    timestamp_ms: int
    window_start_ms: int
    window_end_ms: int
    rms: float
    noise_floor: float
    rms_z_score: float
    energy_ratio: float
    onset_score: float
    spectral_flux: float
    zero_crossing_rate: float
    spectral_centroid: float
    sustained_energy_score: float
    silence_score: float


@dataclass
class RollingFeatureExtractor:
    sample_rate: int
    config: FeatureConfig = DEFAULT_CONFIG.features
    _rms_history: deque[float] = field(default_factory=deque)
    _recent_rms: deque[float] = field(default_factory=deque)
    _prev_rms: float | None = None
    _prev_spectrum: NDArray[np.float32] | None = None
    _noise_floor: float = 0.0

    def __post_init__(self) -> None:
        self._noise_floor = self.config.min_noise_floor

    def process(
        self,
        frame: FloatArray,
        window: FloatArray,
        *,
        timestamp_ms: int,
        window_start_ms: int,
        window_end_ms: int,
    ) -> AudioFeatures:
        rms = _rms(frame)
        history = np.asarray(self._rms_history or [self.config.min_noise_floor])
        median = float(np.median(history))
        mad = float(np.median(np.abs(history - median)))
        robust_std = max(mad * 1.4826, self.config.min_noise_floor * 0.5, 0.001)

        noise_floor = max(
            self.config.min_noise_floor,
            min(self._noise_floor, float(np.percentile(history, 35))),
        )
        rms_z_score = max(0.0, (rms - median) / robust_std)
        energy_ratio = rms / max(noise_floor, self.config.min_noise_floor)

        spectrum = self._magnitude_spectrum(window)
        spectral_flux = self._spectral_flux(spectrum)
        spectral_centroid = self._spectral_centroid(spectrum)
        zero_crossing_rate = _zero_crossing_rate(frame)

        onset_score = max(
            _energy_onset_score(rms, self._prev_rms, noise_floor),
            spectral_flux,
        )

        self._recent_rms.append(rms)
        while len(self._recent_rms) > 8:
            self._recent_rms.popleft()

        sustained_energy_score = self._sustained_energy_score(noise_floor)
        quiet_threshold = max(
            noise_floor * self.config.silence_rms_multiplier,
            self.config.silence_absolute_rms,
        )
        silence_score = 1.0 - min(1.0, rms / quiet_threshold)

        if self._should_update_noise(timestamp_ms, rms, noise_floor):
            self._rms_history.append(rms)
            while len(self._rms_history) > self.config.noise_history_frames:
                self._rms_history.popleft()
            self._noise_floor = max(
                self.config.min_noise_floor,
                (self._noise_floor * 0.95) + (rms * 0.05),
            )
        elif not self._rms_history:
            self._rms_history.append(rms)

        self._prev_rms = rms
        self._prev_spectrum = spectrum

        return AudioFeatures(
            timestamp_ms=timestamp_ms,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            rms=round(rms, 6),
            noise_floor=round(noise_floor, 6),
            rms_z_score=round(rms_z_score, 3),
            energy_ratio=round(energy_ratio, 3),
            onset_score=round(onset_score, 3),
            spectral_flux=round(spectral_flux, 3),
            zero_crossing_rate=round(zero_crossing_rate, 4),
            spectral_centroid=round(spectral_centroid, 1),
            sustained_energy_score=round(sustained_energy_score, 3),
            silence_score=round(max(0.0, silence_score), 3),
        )

    def _magnitude_spectrum(self, window_samples: FloatArray) -> NDArray[np.float32]:
        n_fft = min(self.config.spectral_n_fft, max(16, len(window_samples)))
        if n_fft <= 0:
            return np.zeros(1, dtype=np.float32)

        segment = window_samples[-n_fft:]
        if len(segment) < n_fft:
            segment = np.pad(segment, (n_fft - len(segment), 0))

        taper = get_window("hann", n_fft, fftbins=True).astype(np.float32)
        spectrum = np.abs(np.fft.rfft(segment * taper)).astype(np.float32)
        total = float(np.sum(spectrum))
        if total > 0:
            spectrum = spectrum / total
        return spectrum

    def _spectral_flux(self, spectrum: NDArray[np.float32]) -> float:
        if self._prev_spectrum is None:
            return 0.0

        size = min(len(spectrum), len(self._prev_spectrum))
        if size == 0:
            return 0.0

        diff = spectrum[:size] - self._prev_spectrum[:size]
        return float(np.sqrt(np.mean(np.square(np.maximum(diff, 0.0)))) * 100.0)

    def _spectral_centroid(self, spectrum: NDArray[np.float32]) -> float:
        if spectrum.size == 0:
            return 0.0

        freqs = np.fft.rfftfreq((spectrum.size - 1) * 2, d=1.0 / self.sample_rate)
        total = float(np.sum(spectrum))
        if total <= 0:
            return 0.0
        return float(np.sum(freqs * spectrum) / total)

    def _sustained_energy_score(self, noise_floor: float) -> float:
        if not self._recent_rms:
            return 0.0

        threshold = max(noise_floor * 1.6, 0.03)
        recent = np.asarray(self._recent_rms, dtype=np.float32)
        return float(np.mean(np.clip(recent / threshold, 0.0, 1.0)))

    def _should_update_noise(self, timestamp_ms: int, rms: float, noise_floor: float) -> bool:
        if timestamp_ms <= self.config.initial_noise_ms:
            return True

        return rms <= max(noise_floor * 1.35, self.config.silence_absolute_rms)


def _rms(samples: FloatArray) -> float:
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(samples, dtype=np.float32))))


def _zero_crossing_rate(samples: FloatArray) -> float:
    if samples.size < 2:
        return 0.0
    signs = np.signbit(samples)
    return float(np.mean(signs[1:] != signs[:-1]))


def _energy_onset_score(
    rms: float,
    previous_rms: float | None,
    noise_floor: float,
) -> float:
    if previous_rms is None:
        return 0.0

    rise = max(0.0, rms - previous_rms)
    return rise / max(noise_floor, 0.001)
