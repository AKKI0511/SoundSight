from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Literal


ModelMode = Literal["dummy", "cactus"]
TriggerMode = Literal["detector", "interval"]


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent

MODEL_MODE_ENV = "SOUNDSIGHT_MODEL_MODE"
TRIGGER_MODE_ENV = "SOUNDSIGHT_TRIGGER_MODE"
INTERVAL_SECONDS_ENV = "SOUNDSIGHT_INTERVAL_SECONDS"


@dataclass(frozen=True)
class AudioConfig:
    sample_rate: int = 16_000
    window_ms: int = 4_000
    detector_step_ms: int = 2_000
    supported_extensions: frozenset[str] = frozenset(
        {".aac", ".flac", ".m4a", ".mp3", ".mp4", ".ogg", ".opus", ".wav", ".webm"}
    )


@dataclass(frozen=True)
class PathConfig:
    repo_root: Path = REPO_ROOT
    backend_root: Path = BACKEND_ROOT
    audio_root_candidates: tuple[Path, ...] = field(
        default_factory=lambda: (
            REPO_ROOT / "supporting-data-images-audio" / "audio-clips",
            REPO_ROOT / "supporting-data-images-audio",
        )
    )


@dataclass(frozen=True)
class DetectorConfig:
    silence_rms: float = 0.01
    silence_peak: float = 0.04
    candidate_rms: float = 0.025
    candidate_peak: float = 0.12
    candidate_onset: float = 0.08


@dataclass(frozen=True)
class EngineConfig:
    audio: AudioConfig = field(default_factory=AudioConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    detector: DetectorConfig = field(default_factory=DetectorConfig)


DEFAULT_CONFIG = EngineConfig()


def get_model_mode() -> ModelMode:
    mode = os.getenv(MODEL_MODE_ENV, "dummy").strip().lower()
    if mode not in {"dummy", "cactus"}:
        raise RuntimeError(
            f"{MODEL_MODE_ENV} must be 'dummy' or 'cactus', got {mode!r}."
        )
    return mode  # type: ignore[return-value]


def get_trigger_mode() -> TriggerMode:
    mode = os.getenv(TRIGGER_MODE_ENV, "detector").strip().lower()
    if mode not in {"detector", "interval"}:
        raise RuntimeError(
            f"{TRIGGER_MODE_ENV} must be 'detector' or 'interval', got {mode!r}."
        )
    return mode  # type: ignore[return-value]


def get_interval_seconds() -> float:
    raw_value = os.getenv(INTERVAL_SECONDS_ENV, "2.0").strip()
    try:
        interval_seconds = float(raw_value)
    except ValueError as exc:
        raise RuntimeError(
            f"{INTERVAL_SECONDS_ENV} must be a positive number, got {raw_value!r}."
        ) from exc

    if interval_seconds <= 0:
        raise RuntimeError(
            f"{INTERVAL_SECONDS_ENV} must be a positive number, got {raw_value!r}."
        )
    return interval_seconds
