import asyncio
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from audio_engine import iter_streaming_detection_events
from schemas import StreamEvent, StreamEventsRequest


app = FastAPI(title="SoundSight Streaming API")

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
        _stream_events(request),
        media_type="application/x-ndjson",
    )


async def _stream_events(request: StreamEventsRequest) -> AsyncIterator[str]:
    session_id = f"demo_{uuid4().hex}"
    elapsed_ms = 0

    async for event in iter_streaming_detection_events(
        request.clip_id,
        session_id,
        language=request.language,
    ):
        timestamp_ms = _event_timestamp(event)
        await _wait_until(timestamp_ms, elapsed_ms)
        elapsed_ms = max(elapsed_ms, timestamp_ms)
        yield _to_ndjson(event)


async def _wait_until(target_ms: int, elapsed_ms: int) -> None:
    delay_ms = max(0, target_ms - elapsed_ms)
    if delay_ms:
        await asyncio.sleep(delay_ms / 1000)


def _to_ndjson(event: StreamEvent) -> str:
    return event.model_dump_json(by_alias=True) + "\n"


def _event_timestamp(event: StreamEvent) -> int:
    return int(getattr(event, "timestamp_ms", 0))
