from collections.abc import Iterator
from dataclasses import dataclass

from app.audio.loader import FloatArray, LoadedAudioClip


@dataclass(frozen=True)
class AudioWindow:
    index: int
    samples: FloatArray
    sample_rate: int
    start_ms: int
    end_ms: int


def iter_audio_windows(
    clip: LoadedAudioClip,
    *,
    window_ms: int,
    step_ms: int,
) -> Iterator[AudioWindow]:
    sample_rate = clip.sample_rate
    window_samples = max(1, int(round((window_ms / 1000) * sample_rate)))
    step_samples = max(1, int(round((step_ms / 1000) * sample_rate)))

    if len(clip.samples) <= window_samples:
        yield AudioWindow(
            index=1,
            samples=clip.samples,
            sample_rate=sample_rate,
            start_ms=0,
            end_ms=clip.duration_ms,
        )
        return

    index = 1
    start = 0
    while start < len(clip.samples):
        end = min(len(clip.samples), start + window_samples)
        yield AudioWindow(
            index=index,
            samples=clip.samples[start:end],
            sample_rate=sample_rate,
            start_ms=int(round((start / sample_rate) * 1000)),
            end_ms=int(round((end / sample_rate) * 1000)),
        )
        if end == len(clip.samples):
            break
        start += step_samples
        index += 1
