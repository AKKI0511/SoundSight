from dataclasses import dataclass
from pathlib import Path

import librosa
import miniaudio
import numpy as np
import soundfile as sf
from numpy.typing import NDArray

from app.config import AudioConfig, DEFAULT_CONFIG, PathConfig


FloatArray = NDArray[np.float32]


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
    "getting_attention": ("baby-crying-434113.mp3", "baby-crying-loud-100441.mp3"),
    "attention_outdoors": ("baby-crying-434113.mp3", "baby-crying-loud-100441.mp3"),
    "baby_crying": ("baby-crying-434113.mp3", "baby-crying-loud-100441.mp3"),
}


CLIP_SEARCH_PATTERNS: dict[str, tuple[str, ...]] = {
    "emergency_vehicle": ("*ambulance*.mp3", "*siren*.mp3", "*emergency*.mp3"),
    "emergency_siren": ("*ambulance*.mp3", "*siren*.mp3", "*emergency*.mp3"),
    "fire_alarm": ("*fire*alarm*.mp3", "*alarm*.mp3"),
    "attention": ("*attention*.mp3", "*baby*cry*.mp3", "*cry*.mp3"),
    "getting_attention": ("*attention*.mp3", "*baby*cry*.mp3", "*cry*.mp3"),
    "attention_outdoors": ("*attention*.mp3", "*baby*cry*.mp3", "*cry*.mp3"),
    "baby_crying": ("*baby*cry*.mp3", "*cry*.mp3"),
    "door_knock": ("*door*knock*.mp3", "*knock*.mp3", "*doorbell*.mp3"),
    "indoor_address": ("*indoor*.mp3", "*address*.mp3", "*speech*.mp3"),
    "addressing_user": ("*indoor*.mp3", "*address*.mp3", "*speech*.mp3"),
}


@dataclass(frozen=True)
class LoadedAudioClip:
    clip_id: str
    path: Path
    samples: FloatArray
    sample_rate: int

    @property
    def duration_ms(self) -> int:
        return int(round((len(self.samples) / self.sample_rate) * 1000))


class AudioUnavailableError(RuntimeError):
    pass


def load_audio_clip(
    clip_id: str,
    *,
    audio_path: Path | None = None,
    audio_config: AudioConfig = DEFAULT_CONFIG.audio,
) -> LoadedAudioClip:
    path = audio_path or resolve_audio_path(clip_id, audio_config=audio_config)

    if path is None:
        raise AudioUnavailableError(f"No audio file found for clipId '{clip_id}'.")

    errors: list[str] = []
    samples = _decode_with_soundfile(path, audio_config.sample_rate, errors)
    if samples is None:
        samples = _decode_with_av(path, audio_config.sample_rate, errors)
    if samples is None:
        samples = _decode_with_miniaudio(path, audio_config.sample_rate, errors)
    if samples is None:
        samples = _decode_with_pydub(path, audio_config.sample_rate, errors)
    if samples is None:
        samples = _decode_with_librosa(path, audio_config.sample_rate, errors)

    if samples is None:
        detail = "; ".join(errors) if errors else "no decoder returned samples"
        raise AudioUnavailableError(f"Could not decode '{path.name}': {detail}")

    samples = np.nan_to_num(samples, copy=False)
    samples = np.clip(samples, -1.0, 1.0).astype(np.float32, copy=False)

    if samples.size == 0:
        raise AudioUnavailableError(f"Audio file '{path.name}' decoded to 0 samples.")

    return LoadedAudioClip(
        clip_id=canonical_clip_id_for_path(path, default_clip_id=clip_id),
        path=path,
        samples=samples,
        sample_rate=audio_config.sample_rate,
    )


def resolve_audio_path(
    clip_id: str,
    *,
    audio_config: AudioConfig = DEFAULT_CONFIG.audio,
    path_config: PathConfig = DEFAULT_CONFIG.paths,
) -> Path | None:
    normalized = normalize_id(clip_id)
    audio_files = list_supported_audio_files(
        audio_config=audio_config,
        path_config=path_config,
    )

    for file_name in CLIP_FILE_CANDIDATES.get(normalized, ()):
        for audio_file in audio_files:
            if audio_file.name.lower() == file_name.lower():
                return audio_file

    for audio_file in audio_files:
        if normalize_id(audio_file.stem) == normalized:
            return audio_file

    for pattern in CLIP_SEARCH_PATTERNS.get(normalized, ()):
        for audio_dir in audio_directories(path_config):
            matches = sorted(audio_dir.glob(pattern))
            if matches:
                return matches[0]

    return None


def list_supported_audio_files(
    *,
    audio_config: AudioConfig = DEFAULT_CONFIG.audio,
    path_config: PathConfig = DEFAULT_CONFIG.paths,
) -> list[Path]:
    files: dict[Path, Path] = {}
    for audio_dir in audio_directories(path_config):
        for path in audio_dir.iterdir():
            if path.is_file() and path.suffix.lower() in audio_config.supported_extensions:
                files[path.resolve()] = path

    return sorted(files.values(), key=lambda path: path.name.lower())


def audio_directories(path_config: PathConfig = DEFAULT_CONFIG.paths) -> list[Path]:
    return [path for path in path_config.audio_root_candidates if path.is_dir()]


def canonical_clip_id_for_path(
    path: Path,
    *,
    default_clip_id: str | None = None,
) -> str:
    normalized = normalize_id(path.stem)

    if "fire" in normalized and "alarm" in normalized:
        return "fire_alarm"
    if "ambulance" in normalized or "siren" in normalized or "emergency" in normalized:
        return "emergency_vehicle"
    if "baby" in normalized or "cry" in normalized:
        return "baby_crying"
    if "attention" in normalized:
        return "attention_outdoors"
    if "door" in normalized or "knock" in normalized:
        return "door_knock"
    if "indoor" in normalized or "address" in normalized or "speech" in normalized:
        return "addressing_user"

    return normalize_id(default_clip_id or path.stem)


def normalize_id(value: str) -> str:
    return value.lower().replace("-", "_").replace(" ", "_")


def _decode_with_soundfile(
    path: Path,
    sample_rate: int,
    errors: list[str],
) -> FloatArray | None:
    try:
        samples, source_rate = sf.read(str(path), dtype="float32", always_2d=False)
        if samples.ndim == 2:
            samples = np.mean(samples, axis=1, dtype=np.float32)
        samples = np.asarray(samples, dtype=np.float32)
        if source_rate != sample_rate:
            samples = librosa.resample(samples, orig_sr=source_rate, target_sr=sample_rate)
        return samples.astype(np.float32, copy=False)
    except Exception as exc:
        errors.append(f"soundfile: {exc}")
        return None


def _decode_with_librosa(
    path: Path,
    sample_rate: int,
    errors: list[str],
) -> FloatArray | None:
    try:
        samples, _ = librosa.load(str(path), sr=sample_rate, mono=True, dtype=np.float32)
        return np.asarray(samples, dtype=np.float32)
    except Exception as exc:
        errors.append(f"librosa: {exc}")
        return None


def _decode_with_av(path: Path, sample_rate: int, errors: list[str]) -> FloatArray | None:
    try:
        import av
        from av.audio.resampler import AudioResampler

        chunks: list[FloatArray] = []
        with av.open(str(path)) as container:
            audio_stream = next(
                (stream for stream in container.streams if stream.type == "audio"),
                None,
            )
            if audio_stream is None:
                raise ValueError("no audio stream found")

            resampler = AudioResampler(format="flt", layout="mono", rate=sample_rate)
            for frame in container.decode(audio_stream):
                for resampled_frame in _iter_av_frames(resampler.resample(frame)):
                    chunks.append(_av_frame_to_mono_float(resampled_frame))

            try:
                flushed_frames = resampler.resample(None)
            except Exception:
                flushed_frames = []

            for resampled_frame in _iter_av_frames(flushed_frames):
                chunks.append(_av_frame_to_mono_float(resampled_frame))

        if not chunks:
            raise ValueError("no decoded audio frames")
        return np.concatenate(chunks).astype(np.float32, copy=False)
    except Exception as exc:
        errors.append(f"av: {exc}")
        return None


def _iter_av_frames(frames: object) -> tuple[object, ...]:
    if frames is None:
        return ()
    if isinstance(frames, list):
        return tuple(frames)
    return (frames,)


def _av_frame_to_mono_float(frame: object) -> FloatArray:
    samples = np.asarray(frame.to_ndarray(), dtype=np.float32)
    if samples.ndim == 2:
        if samples.shape[0] == 1:
            samples = samples[0]
        else:
            samples = np.mean(samples, axis=0, dtype=np.float32)
    return samples.reshape(-1).astype(np.float32, copy=False)


def _decode_with_pydub(path: Path, sample_rate: int, errors: list[str]) -> FloatArray | None:
    try:
        from pydub import AudioSegment

        segment = AudioSegment.from_file(path)
        segment = segment.set_channels(1).set_frame_rate(sample_rate)
        raw = np.asarray(segment.get_array_of_samples())
        max_value = float(1 << (8 * segment.sample_width - 1))
        if max_value <= 0:
            raise ValueError("invalid sample width")
        return (raw.astype(np.float32) / max_value).astype(np.float32, copy=False)
    except Exception as exc:
        errors.append(f"pydub: {exc}")
        return None


def _decode_with_miniaudio(
    path: Path,
    sample_rate: int,
    errors: list[str],
) -> FloatArray | None:
    try:
        decoded = miniaudio.decode_file(
            str(path),
            output_format=miniaudio.SampleFormat.FLOAT32,
            nchannels=1,
            sample_rate=sample_rate,
        )
        return np.asarray(decoded.samples, dtype=np.float32)
    except Exception as exc:
        errors.append(f"miniaudio: {exc}")
        return None
