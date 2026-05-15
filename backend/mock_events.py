from typing import Any

from model_gateway import ALERT_PAYLOADS, deterministic_dummy_alert
from schemas import AlertAnalysis, AlertPayload


def normalize_alert_key(clip_id: str) -> str:
    normalized = clip_id.lower().replace("-", "_").replace(" ", "_")

    if "fire" in normalized and "alarm" in normalized:
        return "fire_alarm"

    if "emergency" in normalized or "siren" in normalized or "ambulance" in normalized:
        return "emergency_vehicle"

    if "door" in normalized or "knock" in normalized:
        return "door_knock"

    if (
        "attention" in normalized
        or "getting" in normalized
        or "baby" in normalized
        or "cry" in normalized
    ):
        return "attention_outdoors"

    if "address" in normalized or "indoor" in normalized or "speech" in normalized:
        return "indoor_address"

    return normalized


def get_dummy_alert_payload(clip_id: str) -> AlertPayload:
    return ALERT_PAYLOADS.get(
        normalize_alert_key(clip_id),
        ALERT_PAYLOADS["attention_outdoors"],
    )


def analyze_candidate_window(
    audio_window: object,
    clip_id: str,
    timestamp_ms: int,
) -> AlertAnalysis:
    del audio_window
    metadata: dict[str, Any] = {
        "clipId": clip_id,
        "timestampMs": timestamp_ms,
        "candidateType": _candidate_type_for_clip(clip_id),
        "candidateConfidence": 0.86,
    }
    return deterministic_dummy_alert(metadata)


def _candidate_type_for_clip(clip_id: str) -> str:
    alert_key = normalize_alert_key(clip_id)
    if alert_key == "attention_outdoors" or alert_key == "indoor_address":
        return "speech_attention"
    return alert_key if alert_key in {"fire_alarm", "emergency_vehicle", "door_knock"} else "unknown"
