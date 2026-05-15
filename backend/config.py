from dataclasses import dataclass, field
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class AudioConfig:
    sample_rate: int = 16_000
    step_ms: int = 500
    window_ms: int = 4_000
    supported_extensions: frozenset[str] = frozenset(
        {".mp3", ".wav", ".m4a", ".flac", ".ogg"}
    )


@dataclass(frozen=True)
class PathConfig:
    repo_root: Path = REPO_ROOT
    audio_root_candidates: tuple[Path, ...] = field(
        default_factory=lambda: (
            REPO_ROOT / "supporting-data-images-audio" / "audio-clips",
            REPO_ROOT / "supporting-data-images-audio",
            REPO_ROOT / "supporint-data-image-audio" / "audio-clips",
            REPO_ROOT / "supporint-data-image-audio",
            REPO_ROOT / "supporint-data-images-audio" / "audio-clips",
            REPO_ROOT / "supporint-data-images-audio",
        )
    )


@dataclass(frozen=True)
class FeatureConfig:
    min_noise_floor: float = 0.004
    initial_noise_ms: int = 2_000
    noise_history_frames: int = 40
    spectral_n_fft: int = 1024
    spectral_hop_length: int = 256
    silence_rms_multiplier: float = 1.25
    silence_absolute_rms: float = 0.018


@dataclass(frozen=True)
class SignalDetectorConfig:
    start_rms_z: float = 2.2
    keep_rms_z: float = 0.85
    start_energy_ratio: float = 2.15
    keep_energy_ratio: float = 1.35
    absolute_start_rms: float = 0.075
    absolute_keep_rms: float = 0.035
    onset_start: float = 1.25
    onset_keep: float = 0.65
    sustained_start_score: float = 0.62
    sustained_keep_score: float = 0.35
    min_alive_ms: int = 1_000
    grace_ms: int = 1_000
    knock_onset_threshold: float = 1.45
    knock_window_ms: int = 1_500


@dataclass(frozen=True)
class VadConfig:
    min_speech_ms: int = 800
    speech_probability_threshold: float = 0.48
    fallback_min_centroid_hz: float = 250.0
    fallback_max_centroid_hz: float = 4_800.0
    fallback_min_zcr: float = 0.018
    fallback_max_zcr: float = 0.28


@dataclass(frozen=True)
class FusionConfig:
    alarm_min_sustained_ms: int = 1_000
    alarm_high_confidence: float = 0.88
    unknown_model_confidence: float = 0.9
    minimum_candidate_confidence: float = 0.35


@dataclass(frozen=True)
class StateMachineConfig:
    candidate_timeout_ms: int = 1_000
    quiet_cooldown_ms: int = 1_500
    min_active_ms: int = 1_500


@dataclass(frozen=True)
class EngineConfig:
    audio: AudioConfig = field(default_factory=AudioConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    signal: SignalDetectorConfig = field(default_factory=SignalDetectorConfig)
    vad: VadConfig = field(default_factory=VadConfig)
    fusion: FusionConfig = field(default_factory=FusionConfig)
    state_machine: StateMachineConfig = field(default_factory=StateMachineConfig)


DEFAULT_CONFIG = EngineConfig()
