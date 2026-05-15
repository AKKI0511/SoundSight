from dataclasses import dataclass, field

from audio_loader import FloatArray
from config import DEFAULT_CONFIG
from feature_extractor import RollingFeatureExtractor
from signal_detector import SignalDetector


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


@dataclass(frozen=True)
class DetectorConfig:
    sample_rate: int = DEFAULT_CONFIG.audio.sample_rate


@dataclass
class SimpleAudioDetector:
    config: DetectorConfig = field(default_factory=DetectorConfig)
    _features: RollingFeatureExtractor = field(init=False)
    _signal: SignalDetector = field(init=False)

    def __post_init__(self) -> None:
        self._features = RollingFeatureExtractor(sample_rate=self.config.sample_rate)
        self._signal = SignalDetector()

    def process_frame(
        self,
        frame: FloatArray,
        *,
        timestamp_ms: int,
        window_start_ms: int,
        window_end_ms: int,
    ) -> DetectorFeatures:
        features = self._features.process(
            frame,
            frame,
            timestamp_ms=timestamp_ms,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
        )
        signal = self._signal.process(features)

        return DetectorFeatures(
            timestamp_ms=features.timestamp_ms,
            window_start_ms=features.window_start_ms,
            window_end_ms=features.window_end_ms,
            rms=features.rms,
            noise_floor=features.noise_floor,
            energy_ratio=features.energy_ratio,
            onset_score=features.onset_score,
            sustained_energy=features.sustained_energy_score >= 0.5,
            candidate=signal.signal_active,
            quiet=signal.quiet,
        )
