from collections.abc import AsyncIterator
from pathlib import Path

from audio_loader import (
    AudioUnavailableError,
    LoadedAudioClip,
    canonical_clip_id_for_path,
    list_supported_audio_files,
    load_audio_clip,
)
from config import DEFAULT_CONFIG, EngineConfig
from feature_extractor import RollingFeatureExtractor
from fusion_engine import CandidateFusionEngine
from schemas import ErrorEvent, LanguageCode, SessionDoneEvent, SessionStartedEvent, StreamEvent
from signal_detector import SignalDetector
from state_machine import AlertStateMachine
from vad_detector import SpeechDetector


async def iter_streaming_detection_events(
    clip_id: str,
    session_id: str,
    *,
    language: LanguageCode = "en",
    audio_path: Path | None = None,
    config: EngineConfig = DEFAULT_CONFIG,
) -> AsyncIterator[StreamEvent]:
    yield SessionStartedEvent(
        session_id=session_id,
        clip_id=clip_id,
        timestamp_ms=0,
    )

    try:
        clip = load_audio_clip(
            clip_id,
            audio_path=audio_path,
            audio_config=config.audio,
        )
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

    last_timestamp_ms = 0
    try:
        async for event in _process_loaded_clip(
            clip,
            session_id,
            language=language,
            config=config,
        ):
            last_timestamp_ms = max(last_timestamp_ms, _event_timestamp(event))
            yield event
    except Exception as exc:
        yield ErrorEvent(
            session_id=session_id,
            clip_id=clip.clip_id,
            timestamp_ms=last_timestamp_ms,
            code="engine_error",
            message=str(exc),
        )

    yield SessionDoneEvent(session_id=session_id, timestamp_ms=clip.duration_ms)


async def collect_streaming_detection_events(
    clip_id: str,
    session_id: str,
    *,
    language: LanguageCode = "en",
    audio_path: Path | None = None,
    config: EngineConfig = DEFAULT_CONFIG,
) -> list[StreamEvent]:
    events: list[StreamEvent] = []
    async for event in iter_streaming_detection_events(
        clip_id,
        session_id,
        language=language,
        audio_path=audio_path,
        config=config,
    ):
        events.append(event)
    return events


async def _process_loaded_clip(
    clip: LoadedAudioClip,
    session_id: str,
    *,
    language: LanguageCode,
    config: EngineConfig,
) -> AsyncIterator[StreamEvent]:
    feature_extractor = RollingFeatureExtractor(
        sample_rate=clip.sample_rate,
        config=config.features,
    )
    signal_detector = SignalDetector(config=config.signal)
    speech_detector = SpeechDetector(
        sample_rate=clip.sample_rate,
        config=config.vad,
    )
    fusion_engine = CandidateFusionEngine(
        clip_id=clip.clip_id,
        config=config.fusion,
    )
    state_machine = AlertStateMachine(
        session_id=session_id,
        clip_id=clip.clip_id,
        language=language,
        config=config.state_machine,
    )

    step_samples = max(1, int(round((config.audio.step_ms / 1000) * clip.sample_rate)))
    window_samples = max(
        step_samples,
        int(round((config.audio.window_ms / 1000) * clip.sample_rate)),
    )

    for frame_start in range(0, len(clip.samples), step_samples):
        frame_end = min(len(clip.samples), frame_start + step_samples)
        frame = clip.samples[frame_start:frame_end]
        window_start = max(0, frame_end - window_samples)
        window = clip.samples[window_start:frame_end]
        timestamp_ms = int(round((frame_end / clip.sample_rate) * 1000))
        window_start_ms = int(round((window_start / clip.sample_rate) * 1000))

        features = feature_extractor.process(
            frame,
            window,
            timestamp_ms=timestamp_ms,
            window_start_ms=window_start_ms,
            window_end_ms=timestamp_ms,
        )
        signal = signal_detector.process(features)
        speech = speech_detector.process(features, frame, window)
        decision = fusion_engine.process(features, signal, speech)

        for event in await state_machine.process(decision, window):
            yield event

    for event in state_machine.finish(clip.duration_ms):
        yield event


def _event_timestamp(event: StreamEvent) -> int:
    return int(getattr(event, "timestamp_ms", 0))
