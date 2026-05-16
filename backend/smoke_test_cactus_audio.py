import asyncio
import json

from audio_loader import load_audio_clip
from cactus_gateway import analyze_candidate_with_cactus, get_cactus_model_label
from config import DEFAULT_CONFIG


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
        "candidateType": "fire_alarm",
        "candidateConfidence": 0.99,
    }

    print(f"Model: {get_cactus_model_label()}")
    print(f"Audio: {clip.path}")
    print(f"Window: 0 ms to {window_end_ms} ms")

    result = await analyze_candidate_with_cactus(candidate_window, metadata, "en")

    print("\nRaw Cactus envelope:")
    print(result.raw_result_json or "<none>")
    print("\nRaw model response:")
    print(result.raw_response or "<none>")
    print("\nParsed alert JSON:")
    print(
        json.dumps(result.parsed_json, indent=2, ensure_ascii=False)
        if result.parsed_json is not None
        else "<none>"
    )

    if result.error_message:
        print(f"\nFAIL: {result.error_message}")
        return 1

    print("\nPASS: Cactus returned valid SoundSight alert JSON.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
