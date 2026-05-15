from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from audio_loader import FloatArray
from config import DEFAULT_CONFIG, VadConfig
from feature_extractor import AudioFeatures


@dataclass(frozen=True)
class SpeechDecision:
    speech_probability: float
    speech_active: bool
    speech_duration_ms: int
    source: str
    warning: str | None = None


@dataclass
class SpeechDetector:
    sample_rate: int
    config: VadConfig = DEFAULT_CONFIG.vad
    silero_loaded: bool = False
    status_message: str = "Silero VAD not initialized."
    _model: Any | None = None
    _get_speech_timestamps: Callable[..., list[dict[str, int]]] | None = None
    _speech_run_ms: int = 0

    def __post_init__(self) -> None:
        self._try_load_silero()

    def process(
        self,
        features: AudioFeatures,
        frame: FloatArray,
        window: FloatArray,
    ) -> SpeechDecision:
        if self.silero_loaded:
            silero_decision = self._process_with_silero(window)
            if silero_decision is not None:
                return silero_decision

        probability = self._fallback_probability(features, frame)
        if probability >= self.config.speech_probability_threshold:
            self._speech_run_ms += 500
        else:
            self._speech_run_ms = 0

        return SpeechDecision(
            speech_probability=round(probability, 3),
            speech_active=self._speech_run_ms >= self.config.min_speech_ms,
            speech_duration_ms=self._speech_run_ms,
            source="fallback",
            warning=self.status_message,
        )

    def _try_load_silero(self) -> None:
        try:
            from silero_vad import get_speech_timestamps, load_silero_vad

            self._model = load_silero_vad()
            self._get_speech_timestamps = get_speech_timestamps
            self.silero_loaded = True
            self.status_message = "Silero VAD loaded successfully."
        except Exception as exc:
            self.silero_loaded = False
            self._model = None
            self._get_speech_timestamps = None
            self.status_message = f"Silero VAD unavailable: {exc}"

    def _process_with_silero(self, window: FloatArray) -> SpeechDecision | None:
        if self._model is None or self._get_speech_timestamps is None:
            return None

        try:
            speech_timestamps = self._get_speech_timestamps(
                window,
                self._model,
                sampling_rate=self.sample_rate,
            )
        except Exception as exc:
            self.silero_loaded = False
            self.status_message = f"Silero VAD disabled after runtime error: {exc}"
            return None

        speech_samples = 0
        for item in speech_timestamps:
            speech_samples += max(0, int(item.get("end", 0)) - int(item.get("start", 0)))

        speech_ms = int(round((speech_samples / self.sample_rate) * 1000))
        probability = min(1.0, speech_ms / max(self.config.min_speech_ms, 1))

        return SpeechDecision(
            speech_probability=round(probability, 3),
            speech_active=speech_ms >= self.config.min_speech_ms,
            speech_duration_ms=speech_ms,
            source="silero",
        )

    def _fallback_probability(self, features: AudioFeatures, frame: FloatArray) -> float:
        centroid_score = _range_score(
            features.spectral_centroid,
            self.config.fallback_min_centroid_hz,
            self.config.fallback_max_centroid_hz,
        )
        zcr_score = _range_score(
            features.zero_crossing_rate,
            self.config.fallback_min_zcr,
            self.config.fallback_max_zcr,
        )
        energy_score = min(1.0, max(features.rms_z_score / 4.0, features.energy_ratio / 5.0))
        modulation_score = _modulation_score(frame)

        return min(
            1.0,
            (centroid_score * 0.28)
            + (zcr_score * 0.24)
            + (energy_score * 0.28)
            + (features.sustained_energy_score * 0.12)
            + (modulation_score * 0.08),
        )


def _range_score(value: float, minimum: float, maximum: float) -> float:
    if minimum <= value <= maximum:
        return 1.0

    if value < minimum:
        return max(0.0, 1.0 - ((minimum - value) / max(minimum, 1.0)))

    return max(0.0, 1.0 - ((value - maximum) / max(maximum, 1.0)))


def _modulation_score(frame: FloatArray) -> float:
    if frame.size < 8:
        return 0.0

    chunks = np.array_split(frame, 8)
    rms_values = np.asarray(
        [np.sqrt(np.mean(np.square(chunk, dtype=np.float32))) for chunk in chunks],
        dtype=np.float32,
    )
    mean_rms = float(np.mean(rms_values))
    if mean_rms <= 0:
        return 0.0

    return min(1.0, float(np.std(rms_values) / mean_rms))
