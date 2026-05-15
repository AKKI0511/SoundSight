from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import miniaudio
import numpy as np
from numpy.typing import NDArray

from detectors import DetectorConfig, FloatArray, SimpleAudioDetector
from schemas import ErrorEvent, SessionDoneEvent, SessionStartedEvent, StreamEvent
from state_machine import AlertStateMachine


SAMPLE_RATE = 16_000
STEP_MS = 500
WINDOW_MS = 4000
SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIO_ROOT_CANDIDATES = (
    REPO_ROOT / "supporting-data-images-audio" / "audio-clips",
    REPO_ROOT / "supporting-data-images-audio",
    REPO_ROOT / "supporint-data-image-audio" / "audio-clips",
    REPO_ROOT / "supporint-data-image-audio",
)

CLIP_FILE_CANDIDATES: dict[str, tuple[str, ...]] = {
    "emergency_vehicle": (
        "spinopel-ambulance-siren-364900.mp3",
        "freesound_community-german-ambulance-29046.mp3",
    ),
    "emergency_siren": (
        "spinopel-ambulance-siren-364900.mp3",
        "freesound_community-german-ambulance-29046.mp3",
    ),
    "fire_alarm": ("fire-alarm-414915.mp3",),
    "attention": ("baby-crying-434113.mp3", "baby-crying-loud-100441.mp3"),
    "getting_attention": (
        "baby-crying-434113.mp3",
        "baby-crying-loud-100441.mp3",
    ),
    "attention_outdoors": (
        "baby-crying-434113.mp3",
        "baby-crying-loud-100441.mp3",
    ),
}

CLIP_SEARCH_PATTERNS: dict[str, tuple[str, ...]] = {
    "emergency_vehicle": ("*ambulance*.mp3", "*siren*.mp3", "*emergency*.mp3"),
    "emergency_siren": ("*ambulance*.mp3", "*siren*.mp3", "*emergency*.mp3"),
    "fire_alarm": ("*fire*alarm*.mp3", "*alarm*.mp3"),
    "attention": ("*attention*.mp3", "*baby*cry*.mp3", "*cry*.mp3"),
    "getting_attention": ("*attention*.mp3", "*baby*cry*.mp3", "*cry*.mp3"),
    "attention_outdoors": ("*attention*.mp3", "*baby*cry*.mp3", "*cry*.mp3"),
    "door_knock": ("*door*knock*.mp3", "*knock*.mp3", "*doorbell*.mp3"),
    "indoor_address": ("*indoor*.mp3", "*address*.mp3", "*speech*.mp3"),
    "addressing_user": ("*indoor*.mp3", "*address*.mp3", "*speech*.mp3"),
}


@dataclass(frozen=True)
class LoadedAudioClip:
    clip_id: str
    path: Path
    samples: FloatArray
    sample_rate: int = SAMPLE_RATE

    @property
    def duration_ms(self) -> int:
        return int(round((len(self.samples) / self.sample_rate) * 1000))


class AudioUnavailableError(RuntimeError):
    pass


def iter_streaming_detection_events(
    clip_id: str,
    session_id: str,
    *,
    audio_path: Path | None = None,
    step_ms: int = STEP_MS,
    window_ms: int = WINDOW_MS,
) -> Iterator[StreamEvent]:
    yield SessionStartedEvent(
        session_id=session_id,
        clip_id=clip_id,
        timestamp_ms=0,
    )

    try:
        clip = load_audio_clip(clip_id, audio_path=audio_path)
    except AudioUnavailableError as exc:
        yield ErrorEvent(
            session_id=session_id,
            clip_id=clip_id,
            timestamp_ms=0,
            code="audio_unavailable",
            message=str(exc),
        )
        yield SessionDoneEvent(session_id=session_id, timestamp_ms=0)
        return

    detector = SimpleAudioDetector(DetectorConfig())
    state_machine = AlertStateMachine(session_id=session_id, clip_id=clip.clip_id)

    step_samples = max(1, int(round((step_ms / 1000) * clip.sample_rate)))
    window_samples = max(step_samples, int(round((window_ms / 1000) * clip.sample_rate)))

    for frame_start in range(0, len(clip.samples), step_samples):
        frame_end = min(len(clip.samples), frame_start + step_samples)
        frame = clip.samples[frame_start:frame_end]
        window_start = max(0, frame_end - window_samples)
        window = clip.samples[window_start:frame_end]
        timestamp_ms = int(round((frame_end / clip.sample_rate) * 1000))
        window_start_ms = int(round((window_start / clip.sample_rate) * 1000))

        features = detector.process_frame(
            frame,
            timestamp_ms=timestamp_ms,
            window_start_ms=window_start_ms,
            window_end_ms=timestamp_ms,
        )

        yield from state_machine.process(features, window)

    yield from state_machine.finish(clip.duration_ms)
    yield SessionDoneEvent(session_id=session_id, timestamp_ms=clip.duration_ms)


def load_audio_clip(
    clip_id: str,
    *,
    audio_path: Path | None = None,
) -> LoadedAudioClip:
    path = audio_path or resolve_audio_path(clip_id)

    if path is None:
        raise AudioUnavailableError(f"No audio file found for clipId '{clip_id}'.")

    try:
        decoded = miniaudio.decode_file(
            str(path),
            output_format=miniaudio.SampleFormat.FLOAT32,
            nchannels=1,
            sample_rate=SAMPLE_RATE,
        )
    except Exception as exc:
        raise AudioUnavailableError(f"Could not decode '{path.name}': {exc}") from exc

    samples = np.asarray(decoded.samples, dtype=np.float32)
    samples = np.clip(samples, -1.0, 1.0).astype(np.float32, copy=False)

    if samples.size == 0:
        raise AudioUnavailableError(f"Audio file '{path.name}' decoded to 0 samples.")

    return LoadedAudioClip(
        clip_id=canonical_clip_id_for_path(path, fallback_clip_id=clip_id),
        path=path,
        samples=samples,
    )


def resolve_audio_path(clip_id: str) -> Path | None:
    normalized = _normalize_id(clip_id)
    audio_files = list_supported_audio_files()

    for file_name in CLIP_FILE_CANDIDATES.get(normalized, ()):
        for audio_file in audio_files:
            if audio_file.name.lower() == file_name.lower():
                return audio_file

    for audio_file in audio_files:
        if _normalize_id(audio_file.stem) == normalized:
            return audio_file

    for pattern in CLIP_SEARCH_PATTERNS.get(normalized, ()):
        for audio_dir in audio_directories():
            matches = sorted(audio_dir.glob(pattern))
            if matches:
                return matches[0]

    return None


def list_supported_audio_files() -> list[Path]:
    files: dict[Path, Path] = {}
    for audio_dir in audio_directories():
        for path in audio_dir.iterdir():
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                files[path.resolve()] = path

    return sorted(files.values(), key=lambda path: path.name.lower())


def audio_directories() -> list[Path]:
    return [path for path in AUDIO_ROOT_CANDIDATES if path.is_dir()]


def canonical_clip_id_for_path(path: Path, *, fallback_clip_id: str | None = None) -> str:
    normalized = _normalize_id(path.stem)

    if "fire" in normalized and "alarm" in normalized:
        return "fire_alarm"

    if "ambulance" in normalized or "siren" in normalized or "emergency" in normalized:
        return "emergency_vehicle"

    if "baby" in normalized or "cry" in normalized or "attention" in normalized:
        return "attention_outdoors"

    if "door" in normalized or "knock" in normalized:
        return "door_knock"

    if "indoor" in normalized or "address" in normalized or "speech" in normalized:
        return "indoor_address"

    return _normalize_id(fallback_clip_id or path.stem)


def _normalize_id(value: str) -> str:
    return value.lower().replace("-", "_").replace(" ", "_")
