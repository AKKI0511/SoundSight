import asyncio
import json
from pathlib import Path
import sys
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.audio.loader import canonical_clip_id_for_path, list_supported_audio_files, load_audio_clip
from app.config import DEFAULT_CONFIG, get_trigger_mode
from app.model.gateway import get_model_name, get_model_source
from app.realtime.stream_runner import iter_demo_stream_events
from app.schemas import (
    AlertEndEvent,
    AlertStartEvent,
    EngineLogEvent,
    ErrorEvent,
    ModelCallEvent,
    ModelErrorEvent,
    ModelResultEvent,
    SessionDoneEvent,
)


REPORT_DIR = BACKEND_ROOT / "reports"
MARKDOWN_REPORT_PATH = REPORT_DIR / "audio_detection_report.md"
JSON_REPORT_PATH = REPORT_DIR / "audio_detection_report.json"


def main() -> None:
    summaries = asyncio.run(build_report())
    markdown = format_markdown_report(summaries)
    json_payload = {
        "generatedBy": "SoundSight backend audio trigger report",
        "modelSource": get_model_source(),
        "model": get_model_name(),
        "triggerMode": get_trigger_mode(),
        "audioDirectoryCandidates": [
            str(path) for path in DEFAULT_CONFIG.paths.audio_root_candidates
        ],
        "clips": summaries,
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    MARKDOWN_REPORT_PATH.write_text(markdown, encoding="utf-8")
    JSON_REPORT_PATH.write_text(
        json.dumps(json_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(markdown)
    print(f"Saved markdown report to {MARKDOWN_REPORT_PATH}")
    print(f"Saved JSON report to {JSON_REPORT_PATH}")


async def build_report() -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for audio_path in list_supported_audio_files():
        clip_id = canonical_clip_id_for_path(audio_path)
        summaries.append(await summarize_audio_file(audio_path, clip_id))
    return summaries


async def summarize_audio_file(audio_path: Path, clip_id: str) -> dict[str, Any]:
    session_id = f"report_{audio_path.stem}"
    duration_ms = 0
    errors: list[str] = []
    trigger_timeline: list[dict[str, Any]] = []
    model_calls: list[dict[str, Any]] = []
    model_results: list[dict[str, Any]] = []
    model_errors: list[dict[str, Any]] = []
    alert_starts: list[dict[str, Any]] = []
    alert_ends: list[dict[str, Any]] = []

    try:
        loaded_clip = load_audio_clip(clip_id, audio_path=audio_path)
        duration_ms = loaded_clip.duration_ms
    except Exception as exc:
        errors.append(str(exc))

    async for event in iter_demo_stream_events(
        clip_id,
        session_id,
        audio_path=audio_path,
    ):
        if isinstance(event, EngineLogEvent):
            trigger_timeline.append(
                {
                    "timestampMs": event.timestamp_ms,
                    "windowStartMs": event.window_start_ms,
                    "windowEndMs": event.window_end_ms,
                    "rms": event.rms,
                    "peak": event.peak,
                    "onsetScore": event.onset_score,
                    "silent": event.silent,
                    "shouldCallModel": event.should_call_model,
                    "reason": event.reason,
                }
            )
        elif isinstance(event, ModelCallEvent):
            model_calls.append(
                {
                    "timestampMs": event.timestamp_ms,
                    "candidateId": event.candidate_id,
                    "candidateType": event.candidate_type,
                    "confidence": event.candidate_confidence,
                    "windowStartMs": event.window_start_ms,
                    "windowEndMs": event.window_end_ms,
                    "reason": event.reason,
                }
            )
        elif isinstance(event, ModelResultEvent):
            model_results.append(
                {
                    "timestampMs": event.timestamp_ms,
                    "candidateId": event.candidate_id,
                    "source": event.source,
                    "model": event.model_name,
                    "soundType": event.analysis.sound_type,
                    "should_alert": event.analysis.should_alert,
                    "confidence": event.analysis.confidence,
                    "language": event.analysis.language,
                    "alert_text": event.analysis.alert_text,
                    "action": event.analysis.action,
                }
            )
        elif isinstance(event, ModelErrorEvent):
            model_errors.append(
                {
                    "timestampMs": event.timestamp_ms,
                    "candidateId": event.candidate_id,
                    "source": event.source,
                    "model": event.model_name,
                    "message": event.message,
                }
            )
        elif isinstance(event, AlertStartEvent):
            alert_starts.append(
                {
                    "timestampMs": event.timestamp_ms,
                    "eventId": event.event_id,
                    "soundType": event.alert.sound_type,
                    "confidence": event.alert.confidence,
                    "language": event.alert.language,
                }
            )
        elif isinstance(event, AlertEndEvent):
            alert_ends.append(
                {
                    "timestampMs": event.timestamp_ms,
                    "eventId": event.event_id,
                }
            )
        elif isinstance(event, ErrorEvent):
            errors.append(event.message)
        elif isinstance(event, SessionDoneEvent):
            duration_ms = event.timestamp_ms

    return {
        "fileName": audio_path.name,
        "clipId": clip_id,
        "durationMs": duration_ms,
        "triggerTimeline": trigger_timeline,
        "modelCalls": model_calls,
        "modelResults": model_results,
        "modelErrors": model_errors,
        "alertStarts": alert_starts,
        "alertEnds": alert_ends,
        "totalAlertsEmitted": len(alert_starts),
        "errors": errors,
    }


def format_markdown_report(summaries: list[dict[str, Any]]) -> str:
    lines: list[str] = ["# SoundSight Audio Trigger Report", ""]
    lines.extend(
        [
            f"- model source: {get_model_source()}",
            f"- model: {get_model_name()}",
            f"- trigger mode: {get_trigger_mode()}",
            "",
        ]
    )

    if not summaries:
        lines.extend(["No supported audio files found.", ""])

    for summary in summaries:
        lines.extend(format_summary(summary))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def format_summary(summary: dict[str, Any]) -> list[str]:
    return [
        f"## {summary['fileName']}",
        "",
        f"- clip id: {summary['clipId']}",
        f"- duration: {_format_ms(summary['durationMs'])}",
        f"- trigger timeline: {_format_timeline(summary['triggerTimeline'])}",
        f"- model_call timestamps: {_format_event_points(summary['modelCalls'])}",
        f"- model_result outputs: {_format_model_results(summary['modelResults'])}",
        f"- model_error outputs: {_format_model_errors(summary['modelErrors'])}",
        f"- alert_start timestamps: {_format_alert_starts(summary['alertStarts'])}",
        f"- alert_end timestamps: {_format_event_points(summary['alertEnds'])}",
        f"- total alerts emitted: {summary['totalAlertsEmitted']}",
        f"- errors: {_format_list(summary['errors'])}",
    ]


def _format_ms(value: int | float) -> str:
    value_int = int(value)
    return f"{value_int} ms ({value_int / 1000:.3f} s)"


def _format_timeline(timeline: list[dict[str, Any]]) -> str:
    if not timeline:
        return "none"

    return ", ".join(
        f"{_format_ms(item['timestampMs'])}:"
        f"rms={float(item.get('rms', 0.0)):.3f} "
        f"peak={float(item.get('peak', 0.0)):.3f} "
        f"call={item.get('shouldCallModel')} "
        f"reason={item.get('reason')}"
        for item in timeline
    )


def _format_event_points(events: list[dict[str, Any]]) -> str:
    if not events:
        return "none"
    return ", ".join(_format_ms(item["timestampMs"]) for item in events)


def _format_model_results(events: list[dict[str, Any]]) -> str:
    if not events:
        return "none"

    return ", ".join(
        f"{_format_ms(item['timestampMs'])}:"
        f"{item.get('source', 'dummy')}:{item['soundType']}"
        f" should_alert={item['should_alert']}"
        f" confidence={float(item['confidence']):.3f}"
        f" language={item['language']}"
        for item in events
    )


def _format_model_errors(events: list[dict[str, Any]]) -> str:
    if not events:
        return "none"

    return "; ".join(
        f"{_format_ms(item['timestampMs'])}:"
        f"{item.get('source', 'unknown')} {item['message']}"
        for item in events
    )


def _format_alert_starts(events: list[dict[str, Any]]) -> str:
    if not events:
        return "none"

    return ", ".join(
        f"{_format_ms(item['timestampMs'])}:{item['eventId']}"
        f" {item['soundType']} confidence={float(item['confidence']):.3f}"
        f" language={item['language']}"
        for item in events
    )


def _format_list(values: list[str]) -> str:
    if not values:
        return "none"
    return "; ".join(values)


if __name__ == "__main__":
    main()
