from collections.abc import AsyncIterator
from pathlib import Path

from app.audio.detector import analyze_window
from app.audio.loader import AudioUnavailableError, LoadedAudioClip, load_audio_clip
from app.audio.windowing import AudioWindow, iter_audio_windows
from app.config import DEFAULT_CONFIG, EngineConfig, get_interval_seconds, get_trigger_mode
from app.model.gateway import analyze_candidate_with_gemma4, get_model_name, get_model_source
from app.realtime.event_reconciler import EventReconciler
from app.schemas import (
    EngineLogEvent,
    ErrorEvent,
    LanguageCode,
    ModelCallEvent,
    ModelErrorEvent,
    ModelResultEvent,
    SessionDoneEvent,
    SessionStartedEvent,
    StreamEvent,
)


_LIVE_RECONCILERS: dict[str, EventReconciler] = {}


async def iter_demo_stream_events(
    clip_id: str,
    session_id: str,
    *,
    language: LanguageCode = "en",
    audio_path: Path | None = None,
    config: EngineConfig = DEFAULT_CONFIG,
) -> AsyncIterator[StreamEvent]:
    reconciler = EventReconciler(session_id=session_id)
    async for event in _iter_stream_events(
        clip_id,
        session_id,
        language=language,
        audio_path=audio_path,
        config=config,
        reconciler=reconciler,
        finish_active=False,
    ):
        yield event


async def iter_live_window_events(
    clip_id: str,
    session_id: str,
    *,
    language: LanguageCode = "en",
    audio_path: Path | None = None,
    config: EngineConfig = DEFAULT_CONFIG,
) -> AsyncIterator[StreamEvent]:
    reconciler = _LIVE_RECONCILERS.setdefault(
        session_id,
        EventReconciler(session_id=session_id),
    )
    async for event in _iter_stream_events(
        clip_id,
        session_id,
        language=language,
        audio_path=audio_path,
        config=config,
        reconciler=reconciler,
        finish_active=False,
    ):
        yield event


async def _iter_stream_events(
    clip_id: str,
    session_id: str,
    *,
    language: LanguageCode,
    audio_path: Path | None,
    config: EngineConfig,
    reconciler: EventReconciler,
    finish_active: bool,
) -> AsyncIterator[StreamEvent]:
    yield SessionStartedEvent(
        session_id=session_id,
        clip_id=clip_id,
        timestamp_ms=0,
    )

    try:
        trigger_mode = get_trigger_mode()
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
    except Exception as exc:
        yield ErrorEvent(
            session_id=session_id,
            clip_id=clip_id,
            timestamp_ms=0,
            code="configuration_error",
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
            trigger_mode=trigger_mode,
            config=config,
            reconciler=reconciler,
        ):
            last_timestamp_ms = max(last_timestamp_ms, _event_timestamp(event))
            yield event

        if finish_active:
            for event in reconciler.finish(timestamp_ms=clip.duration_ms):
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


async def _process_loaded_clip(
    clip: LoadedAudioClip,
    session_id: str,
    *,
    language: LanguageCode,
    trigger_mode: str,
    config: EngineConfig,
    reconciler: EventReconciler,
) -> AsyncIterator[StreamEvent]:
    step_ms = (
        int(round(get_interval_seconds() * 1000))
        if trigger_mode == "interval"
        else config.audio.detector_step_ms
    )

    for window in iter_audio_windows(
        clip,
        window_ms=config.audio.window_ms,
        step_ms=step_ms,
    ):
        decision = analyze_window(
            window,
            trigger_mode=trigger_mode,  # type: ignore[arg-type]
            active_event=reconciler.active_event_id is not None,
            config=config.detector,
        )

        yield EngineLogEvent(
            session_id=session_id,
            timestamp_ms=decision.timestamp_ms,
            window_start_ms=decision.window_start_ms,
            window_end_ms=decision.window_end_ms,
            trigger_mode=trigger_mode,
            rms=decision.rms,
            peak=decision.peak,
            onset_score=decision.onset_score,
            silent=decision.silent,
            should_call_model=decision.should_call_model,
            reason=decision.reason,
        )

        if not decision.should_call_model:
            continue

        async for event in _run_model_for_window(
            clip,
            session_id,
            language=language,
            window=window,
            decision=decision,
            trigger_mode=trigger_mode,
            reconciler=reconciler,
        ):
            yield event


async def _run_model_for_window(
    clip: LoadedAudioClip,
    session_id: str,
    *,
    language: LanguageCode,
    window: AudioWindow,
    decision: object,
    trigger_mode: str,
    reconciler: EventReconciler,
) -> AsyncIterator[StreamEvent]:
    candidate_id = f"candidate_{window.index}"
    model_source = get_model_source()
    model_name = get_model_name()

    yield ModelCallEvent(
        session_id=session_id,
        candidate_id=candidate_id,
        source=model_source,
        model_name=model_name,
        timestamp_ms=window.end_ms,
        clip_id=clip.clip_id,
        language=language,
        reason=decision.reason,
        window_start_ms=window.start_ms,
        window_end_ms=window.end_ms,
        candidate_type=decision.candidate_type,
        candidate_confidence=decision.candidate_confidence,
    )

    analysis = await analyze_candidate_with_gemma4(
        window.samples,
        decision.metadata(clip.clip_id, trigger_mode),  # type: ignore[arg-type]
        language,
    )

    if analysis.model_error_message:
        yield ModelErrorEvent(
            session_id=session_id,
            candidate_id=candidate_id,
            source=model_source,
            model_name=model_name,
            timestamp_ms=window.end_ms,
            clip_id=clip.clip_id,
            message=analysis.model_error_message,
        )

    yield ModelResultEvent(
        session_id=session_id,
        candidate_id=candidate_id,
        source=model_source,
        model_name=model_name,
        timestamp_ms=window.end_ms,
        clip_id=clip.clip_id,
        analysis=analysis,
    )

    for event in reconciler.reconcile(analysis, timestamp_ms=window.end_ms):
        yield event


def _event_timestamp(event: StreamEvent) -> int:
    return int(getattr(event, "timestamp_ms", 0))
