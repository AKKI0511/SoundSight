import asyncio
import json
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.audio.loader import load_audio_clip
from app.config import DEFAULT_CONFIG
from app.model.cactus_gateway import analyze_candidate_with_gemma4, get_cactus_model_label


async def main() -> int:
    clip = load_audio_clip("fire_alarm")
    sample_count = min(
        len(clip.samples),
        int(DEFAULT_CONFIG.audio.sample_rate * (DEFAULT_CONFIG.audio.window_ms / 1000)),
    )
    candidate_window = clip.samples[:sample_count]
    window_end_ms = int(round((len(candidate_window) / clip.sample_rate) * 1000))
    metadata = {
        "clipId": clip.clip_id,
        "timestampMs": window_end_ms,
        "windowStartMs": 0,
        "windowEndMs": window_end_ms,
        "triggerMode": "detector",
        "candidateType": "audio_event",
        "candidateConfidence": 0.99,
        "rms": 0.1,
        "peak": 0.5,
        "onsetScore": 0.1,
        "silent": False,
        "reason": "smoke_test",
    }

    print(f"Model: {get_cactus_model_label()}")
    print(f"Audio: {clip.path}")
    print(f"Window: 0 ms to {window_end_ms} ms")

    result = await analyze_candidate_with_gemma4(candidate_window, metadata, "en")
    print("\nParsed SoundSight analysis:")
    print(json.dumps(result.model_dump(by_alias=True), indent=2, ensure_ascii=False))

    if result.model_error_message:
        print(f"\nFAIL: {result.model_error_message}")
        return 1

    if not result.should_alert:
        print("\nFAIL: Cactus returned a valid no-alert response for the fire alarm smoke clip.")
        return 1

    print("\nPASS: Cactus returned valid SoundSight alert JSON.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
