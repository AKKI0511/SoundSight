from pathlib import Path

from audio_engine import (
    canonical_clip_id_for_path,
    iter_streaming_detection_events,
    list_supported_audio_files,
    load_audio_clip,
)
from schemas import (
    AlertEndEvent,
    AlertStartEvent,
    EngineLogEvent,
    ErrorEvent,
    ModelCallEvent,
    SessionDoneEvent,
)


REPORT_PATH = Path(__file__).resolve().parent / "reports" / "audio_detection_report.md"


def main() -> None:
    audio_files = list_supported_audio_files()
    lines: list[str] = ["# SoundSight Audio Detection Report", ""]

    if not audio_files:
        lines.extend(["No supported audio files found.", ""])

    for audio_path in audio_files:
        clip_id = canonical_clip_id_for_path(audio_path)
        session_id = f"report_{audio_path.stem}"
        summary = summarize_audio_file(audio_path, clip_id, session_id)
        lines.extend(format_summary(summary))
        lines.append("")

    report = "\n".join(lines).rstrip() + "\n"
    print(report)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Saved report to {REPORT_PATH}")


def summarize_audio_file(
    audio_path: Path,
    clip_id: str,
    session_id: str,
) -> dict[str, object]:
    candidate_intervals: list[tuple[int, int]] = []
    model_calls: list[int] = []
    alert_starts: list[int] = []
    alert_ends: list[int] = []
    errors: list[str] = []
    duration_ms = 0

    try:
        loaded_clip = load_audio_clip(clip_id, audio_path=audio_path)
        duration_ms = loaded_clip.duration_ms
    except Exception as exc:
        errors.append(str(exc))

    candidate_start: int | None = None
    last_candidate_ts: int | None = None

    for event in iter_streaming_detection_events(
        clip_id,
        session_id,
        audio_path=audio_path,
    ):
        if isinstance(event, EngineLogEvent):
            if event.candidate:
                if candidate_start is None:
                    candidate_start = event.timestamp_ms
                last_candidate_ts = event.timestamp_ms
            elif candidate_start is not None:
                candidate_intervals.append(
                    (candidate_start, last_candidate_ts or event.timestamp_ms)
                )
                candidate_start = None
                last_candidate_ts = None
        elif isinstance(event, ModelCallEvent):
            model_calls.append(event.timestamp_ms)
        elif isinstance(event, AlertStartEvent):
            alert_starts.append(event.timestamp_ms)
        elif isinstance(event, AlertEndEvent):
            alert_ends.append(event.timestamp_ms)
        elif isinstance(event, ErrorEvent):
            errors.append(event.message)
        elif isinstance(event, SessionDoneEvent):
            duration_ms = event.timestamp_ms

    if candidate_start is not None:
        candidate_intervals.append((candidate_start, last_candidate_ts or duration_ms))

    return {
        "file_name": audio_path.name,
        "clip_id": clip_id,
        "duration_ms": duration_ms,
        "candidate_intervals": candidate_intervals,
        "model_calls": model_calls,
        "alert_starts": alert_starts,
        "alert_ends": alert_ends,
        "alert_count": len(alert_starts),
        "errors": errors,
    }


def format_summary(summary: dict[str, object]) -> list[str]:
    duration_ms = int(summary["duration_ms"])
    return [
        f"## {summary['file_name']}",
        "",
        f"- clip id: {summary['clip_id']}",
        f"- duration: {_format_ms(duration_ms)}",
        f"- detected candidate intervals: {_format_intervals(summary['candidate_intervals'])}",
        f"- model_call timestamps: {_format_points(summary['model_calls'])}",
        f"- alert_start timestamps: {_format_points(summary['alert_starts'])}",
        f"- alert_end timestamps: {_format_points(summary['alert_ends'])}",
        f"- final alerts emitted: {summary['alert_count']}",
        f"- errors: {_format_errors(summary['errors'])}",
    ]


def _format_ms(value: int) -> str:
    return f"{value} ms ({value / 1000:.3f} s)"


def _format_points(values: object) -> str:
    points = values if isinstance(values, list) else []
    if not points:
        return "none"

    return ", ".join(_format_ms(int(value)) for value in points)


def _format_intervals(values: object) -> str:
    intervals = values if isinstance(values, list) else []
    if not intervals:
        return "none"

    return ", ".join(
        f"{_format_ms(int(start))} to {_format_ms(int(end))}"
        for start, end in intervals
    )


def _format_errors(values: object) -> str:
    errors = values if isinstance(values, list) else []
    if not errors:
        return "none"

    return "; ".join(str(error) for error in errors)


if __name__ == "__main__":
    main()
