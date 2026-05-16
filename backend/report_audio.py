import asyncio
import json
from pathlib import Path
from typing import Any

from audio_engine import iter_streaming_detection_events
from audio_loader import canonical_clip_id_for_path, list_supported_audio_files, load_audio_clip
from config import DEFAULT_CONFIG
from model_gateway import get_model_name, get_model_source
from schemas import (
    AlertEndEvent,
    AlertStartEvent,
    CandidateStartEvent,
    CandidateUpdateEvent,
    EngineLogEvent,
    ErrorEvent,
    ModelCallEvent,
    ModelErrorEvent,
    ModelResultEvent,
    SessionDoneEvent,
)


REPORT_DIR = Path(__file__).resolve().parent / "reports"
MARKDOWN_REPORT_PATH = REPORT_DIR / "audio_detection_report.md"
JSON_REPORT_PATH = REPORT_DIR / "audio_detection_report.json"


def main() -> None:
    summaries = asyncio.run(build_report())
    markdown = format_markdown_report(summaries)
    json_payload = {
        "generatedBy": "SoundSight backend audio detection report",
        "modelSource": get_model_source(),
        "model": get_model_name(),
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
    warnings: list[str] = []
    errors: list[str] = []
    candidate_intervals: list[dict[str, Any]] = []
    candidate_timeline: list[dict[str, Any]] = []
    speech_intervals: list[dict[str, Any]] = []
    model_calls: list[dict[str, Any]] = []
    model_results: list[dict[str, Any]] = []
    model_errors: list[dict[str, Any]] = []
    alert_starts: list[dict[str, Any]] = []
    alert_ends: list[dict[str, Any]] = []
    candidate_events: list[dict[str, Any]] = []

    try:
        loaded_clip = load_audio_clip(clip_id, audio_path=audio_path)
        duration_ms = loaded_clip.duration_ms
    except Exception as exc:
        errors.append(str(exc))

    candidate_open: dict[str, Any] | None = None
    speech_open: dict[str, Any] | None = None
    vad_sources: set[str] = set()

    async for event in iter_streaming_detection_events(
        clip_id,
        session_id,
        audio_path=audio_path,
    ):
        if isinstance(event, EngineLogEvent):
            vad_sources.add(event.speech_source)
            if event.speech_warning and event.speech_warning not in warnings:
                warnings.append(event.speech_warning)

            if event.candidate_type is not None or event.candidate_confidence > 0:
                candidate_timeline.append(
                    {
                        "timestampMs": event.timestamp_ms,
                        "candidateType": event.candidate_type,
                        "confidence": event.candidate_confidence,
                        "shouldCallModel": event.should_call_model,
                        "state": event.state,
                    }
                )

            if event.candidate:
                if candidate_open is None:
                    candidate_open = {
                        "startMs": event.timestamp_ms,
                        "endMs": event.timestamp_ms,
                        "candidateType": event.candidate_type,
                        "maxConfidence": event.candidate_confidence,
                    }
                else:
                    candidate_open["endMs"] = event.timestamp_ms
                    if event.candidate_confidence > candidate_open["maxConfidence"]:
                        candidate_open["maxConfidence"] = event.candidate_confidence
                        candidate_open["candidateType"] = event.candidate_type
            elif candidate_open is not None:
                candidate_intervals.append(candidate_open)
                candidate_open = None

            if (
                event.candidate_type == "speech_attention"
                and event.speech_probability
                >= DEFAULT_CONFIG.vad.speech_probability_threshold
            ):
                if speech_open is None:
                    speech_open = {
                        "startMs": event.timestamp_ms,
                        "endMs": event.timestamp_ms,
                        "source": event.speech_source,
                        "maxProbability": event.speech_probability,
                    }
                else:
                    speech_open["endMs"] = event.timestamp_ms
                    speech_open["maxProbability"] = max(
                        speech_open["maxProbability"],
                        event.speech_probability,
                    )
            elif speech_open is not None:
                speech_intervals.append(speech_open)
                speech_open = None

        elif isinstance(event, CandidateStartEvent):
            candidate_events.append(
                {
                    "type": event.type,
                    "timestampMs": event.timestamp_ms,
                    "candidateId": event.candidate_id,
                    "source": event.source,
                    "model": event.model_name,
                    "candidateType": event.candidate_type,
                    "confidence": event.candidate_confidence,
                }
            )
        elif isinstance(event, CandidateUpdateEvent):
            candidate_events.append(
                {
                    "type": event.type,
                    "timestampMs": event.timestamp_ms,
                    "candidateId": event.candidate_id,
                    "candidateType": event.candidate_type,
                    "confidence": event.candidate_confidence,
                    "shouldCallModel": event.should_call_model,
                    "state": event.state,
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
                }
            )
        elif isinstance(event, ModelResultEvent):
            model_results.append(
                {
                    "timestampMs": event.timestamp_ms,
                    "candidateId": event.candidate_id,
                    "source": event.source,
                    "model": event.model_name,
                    "detectedSoundType": event.analysis.detected_sound_type,
                    "shouldAlert": event.analysis.should_alert,
                    "confidence": event.analysis.confidence,
                    "alertText": event.analysis.alert_text,
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

    if candidate_open is not None:
        candidate_intervals.append(candidate_open)
    if speech_open is not None:
        speech_intervals.append(speech_open)

    return {
        "fileName": audio_path.name,
        "clipId": clip_id,
        "durationMs": duration_ms,
        "candidateIntervals": candidate_intervals,
        "candidateTimeline": candidate_timeline,
        "candidateEvents": candidate_events,
        "vad": {
            "sileroLoaded": "silero" in vad_sources,
            "sources": sorted(vad_sources),
            "speechIntervals": speech_intervals,
        },
        "modelCalls": model_calls,
        "modelResults": model_results,
        "modelErrors": model_errors,
        "alertStarts": alert_starts,
        "alertEnds": alert_ends,
        "totalAlertsEmitted": len(alert_starts),
        "warnings": warnings,
        "errors": errors,
    }


def format_markdown_report(summaries: list[dict[str, Any]]) -> str:
    lines: list[str] = ["# SoundSight Audio Detection Report", ""]
    lines.extend(
        [
            f"- model source: {get_model_source()}",
            f"- model: {get_model_name()}",
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
        f"- candidate intervals: {_format_intervals(summary['candidateIntervals'])}",
        f"- candidate timeline: {_format_timeline(summary['candidateTimeline'])}",
        f"- VAD/speech: {_format_vad(summary['vad'])}",
        f"- model_call timestamps: {_format_event_points(summary['modelCalls'])}",
        f"- model_result outputs: {_format_model_results(summary['modelResults'])}",
        f"- model_error outputs: {_format_model_errors(summary['modelErrors'])}",
        f"- alert_start timestamps: {_format_alert_starts(summary['alertStarts'])}",
        f"- alert_end timestamps: {_format_event_points(summary['alertEnds'])}",
        f"- total alerts emitted: {summary['totalAlertsEmitted']}",
        f"- warnings: {_format_list(summary['warnings'])}",
        f"- errors: {_format_list(summary['errors'])}",
    ]


def _format_ms(value: int | float) -> str:
    value_int = int(value)
    return f"{value_int} ms ({value_int / 1000:.3f} s)"


def _format_intervals(intervals: list[dict[str, Any]]) -> str:
    if not intervals:
        return "none"

    return ", ".join(
        f"{_format_ms(item['startMs'])} to {_format_ms(item['endMs'])}"
        f" {item.get('candidateType') or 'unknown'}"
        f" max={float(item.get('maxConfidence', 0.0)):.3f}"
        for item in intervals
    )


def _format_timeline(timeline: list[dict[str, Any]]) -> str:
    if not timeline:
        return "none"

    return ", ".join(
        f"{_format_ms(item['timestampMs'])}:{item.get('candidateType')}"
        f"({float(item.get('confidence', 0.0)):.3f})"
        for item in timeline
    )


def _format_vad(vad: dict[str, Any]) -> str:
    source = ",".join(vad.get("sources", [])) or "none"
    silero = "yes" if vad.get("sileroLoaded") else "no"
    intervals = vad.get("speechIntervals", [])
    if not intervals:
        return f"Silero loaded={silero}; sources={source}; speech intervals=none"

    formatted = ", ".join(
        f"{_format_ms(item['startMs'])} to {_format_ms(item['endMs'])}"
        f" max={float(item.get('maxProbability', 0.0)):.3f}"
        for item in intervals
    )
    return f"Silero loaded={silero}; sources={source}; speech intervals={formatted}"


def _format_event_points(events: list[dict[str, Any]]) -> str:
    if not events:
        return "none"

    return ", ".join(_format_ms(item["timestampMs"]) for item in events)


def _format_model_results(events: list[dict[str, Any]]) -> str:
    if not events:
        return "none"

    return ", ".join(
        f"{_format_ms(item['timestampMs'])}:"
        f"{item.get('source', 'dummy')}:{item['detectedSoundType']}"
        f" shouldAlert={item['shouldAlert']}"
        f" confidence={float(item['confidence']):.3f}"
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
        for item in events
    )


def _format_list(values: list[str]) -> str:
    if not values:
        return "none"

    return "; ".join(values)


if __name__ == "__main__":
    main()
