import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
import tempfile
from uuid import uuid4

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.model.gateway import shutdown_model_gateway
from app.realtime.stream_runner import iter_demo_stream_events, iter_live_window_events
from app.schemas import LanguageCode, StreamEvent, StreamEventsRequest


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        yield
    finally:
        shutdown_model_gateway()


app = FastAPI(title="SoundSight Streaming API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/demo/stream-events")
def stream_demo_events(request: StreamEventsRequest) -> StreamingResponse:
    return StreamingResponse(
        _stream_demo_events(request),
        media_type="application/x-ndjson",
    )


@app.post("/api/live/process-window")
async def process_live_window(
    audio: UploadFile = File(...),
    language: LanguageCode = Form("en"),
    session_id: str | None = Form(default=None, alias="sessionId"),
) -> StreamingResponse:
    audio_path = await _save_upload_to_temp(audio)
    return StreamingResponse(
        _stream_live_window_events(
            audio_path,
            session_id=session_id or f"live_{uuid4().hex}",
            language=language,
        ),
        media_type="application/x-ndjson",
    )


async def _stream_demo_events(request: StreamEventsRequest) -> AsyncIterator[str]:
    session_id = f"demo_{uuid4().hex}"
    elapsed_ms = 0

    async for event in iter_demo_stream_events(
        request.clip_id,
        session_id,
        language=request.language,
    ):
        timestamp_ms = _event_timestamp(event)
        await _wait_until(timestamp_ms, elapsed_ms)
        elapsed_ms = max(elapsed_ms, timestamp_ms)
        yield _to_ndjson(event)


async def _stream_live_window_events(
    audio_path: Path,
    *,
    session_id: str,
    language: LanguageCode,
) -> AsyncIterator[str]:
    try:
        async for event in iter_live_window_events(
            "live_window",
            session_id,
            language=language,
            audio_path=audio_path,
        ):
            yield _to_ndjson(event)
    finally:
        audio_path.unlink(missing_ok=True)


async def _save_upload_to_temp(upload: UploadFile) -> Path:
    with tempfile.NamedTemporaryFile(
        suffix=_upload_suffix(upload),
        prefix="soundsight-live-",
        delete=False,
    ) as temp_file:
        path = Path(temp_file.name)
        while chunk := await upload.read(1024 * 1024):
            temp_file.write(chunk)

    await upload.close()
    return path


def _upload_suffix(upload: UploadFile) -> str:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix:
        return suffix

    content_type_suffixes = {
        "audio/webm": ".webm",
        "video/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/opus": ".opus",
        "audio/mp4": ".mp4",
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
    }
    return content_type_suffixes.get(upload.content_type or "", ".webm")


async def _wait_until(target_ms: int, elapsed_ms: int) -> None:
    delay_ms = max(0, target_ms - elapsed_ms)
    if delay_ms:
        await asyncio.sleep(delay_ms / 1000)


def _to_ndjson(event: StreamEvent) -> str:
    return event.model_dump_json(by_alias=True) + "\n"


def _event_timestamp(event: StreamEvent) -> int:
    return int(getattr(event, "timestamp_ms", 0))
