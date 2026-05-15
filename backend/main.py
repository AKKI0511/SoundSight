import asyncio
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from mock_events import get_stream_plan
from schemas import (
    AlertEndEvent,
    AlertStartEvent,
    SessionDoneEvent,
    SessionStartedEvent,
    StreamEvent,
    StreamEventsRequest,
)


app = FastAPI(title="SoundSight Mock Streaming API")

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
    plan = get_stream_plan(request.clip_id)

    if plan is None:
        raise HTTPException(status_code=404, detail="Unknown clipId")

    return StreamingResponse(
        _stream_events(request.clip_id),
        media_type="application/x-ndjson",
    )


async def _stream_events(clip_id: str) -> AsyncIterator[str]:
    plan = get_stream_plan(clip_id)

    if plan is None:
        return

    session_id = f"demo_{uuid4().hex}"

    yield _to_ndjson(
        SessionStartedEvent(
            session_id=session_id,
            clip_id=clip_id,
            timestamp_ms=0,
        )
    )

    elapsed_ms = 0
    for scheduled_alert in plan.alerts:
        await _wait_until(scheduled_alert.start_ms, elapsed_ms)
        elapsed_ms = scheduled_alert.start_ms
        yield _to_ndjson(
            AlertStartEvent(
                session_id=session_id,
                event_id=scheduled_alert.event_id,
                timestamp_ms=scheduled_alert.start_ms,
                alert=scheduled_alert.alert,
            )
        )

        await _wait_until(scheduled_alert.end_ms, elapsed_ms)
        elapsed_ms = scheduled_alert.end_ms
        yield _to_ndjson(
            AlertEndEvent(
                session_id=session_id,
                event_id=scheduled_alert.event_id,
                timestamp_ms=scheduled_alert.end_ms,
            )
        )

    await _wait_until(plan.done_ms, elapsed_ms)
    yield _to_ndjson(
        SessionDoneEvent(session_id=session_id, timestamp_ms=plan.done_ms)
    )


async def _wait_until(target_ms: int, elapsed_ms: int) -> None:
    delay_ms = max(0, target_ms - elapsed_ms)
    if delay_ms:
        await asyncio.sleep(delay_ms / 1000)


def _to_ndjson(event: StreamEvent) -> str:
    return event.model_dump_json(by_alias=True) + "\n"
