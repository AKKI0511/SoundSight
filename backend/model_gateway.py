import os
from typing import Any

from audio_loader import normalize_id
from schemas import (
    AlertAnalysis,
    AlertPayload,
    AlertTier,
    AlertTranslation,
    ModelSource,
    SoundType,
)


MODEL_MODE_ENV = "SOUNDSIGHT_MODEL_MODE"
DUMMY_MODEL_NAME = "deterministic_dummy"


async def analyze_candidate_with_gemma4(
    candidate_window: object,
    candidate_metadata: dict[str, Any],
    language: str,
) -> AlertAnalysis:
    if get_model_source() == "cactus":
        try:
            from cactus_gateway import analyze_candidate_with_cactus

            result = await analyze_candidate_with_cactus(
                candidate_window,
                candidate_metadata,
                language,
            )
            return result.analysis
        except Exception as exc:
            return _safe_no_alert_analysis(
                "Cactus gateway failed before model execution: "
                f"{str(exc).replace(chr(10), ' ')}"
            )

    del candidate_window, language
    return deterministic_dummy_alert(candidate_metadata)


def get_model_source() -> ModelSource:
    mode = os.getenv(MODEL_MODE_ENV, "dummy").strip().lower()
    return "cactus" if mode == "cactus" else "dummy"


def get_model_name() -> str:
    if get_model_source() == "cactus":
        try:
            from cactus_gateway import get_cactus_model_label

            return get_cactus_model_label()
        except Exception:
            return os.getenv("SOUNDSIGHT_CACTUS_MODEL_PATH") or os.getenv(
                "SOUNDSIGHT_CACTUS_MODEL",
                "google/gemma-4-E2B-it",
            )

    return DUMMY_MODEL_NAME


def shutdown_model_gateway() -> None:
    try:
        from cactus_gateway import destroy_cactus_model
    except Exception:
        return

    destroy_cactus_model()


def deterministic_dummy_alert(candidate_metadata: dict[str, Any]) -> AlertAnalysis:
    candidate_type = candidate_metadata.get("candidateType")
    clip_id = str(candidate_metadata.get("clipId", ""))
    confidence = float(candidate_metadata.get("candidateConfidence", 0.0) or 0.0)

    sound_key = _sound_key(candidate_type, clip_id)
    if sound_key == "unknown":
        alert = _payload(
            sound_type="unknown",
            tier="ambient",
            image_key="indoor_address",
            alert_text="Unusual sound detected.",
            action="Check your surroundings.",
            hi_alert_text="\u0905\u0938\u093e\u092e\u093e\u0928\u094d\u092f \u0927\u094d\u0935\u0928\u093f \u092e\u093f\u0932\u0940\u0964",
            hi_action="\u0905\u092a\u0928\u0947 \u0906\u0938\u092a\u093e\u0938 \u0926\u0947\u0916\u0947\u0902\u0964",
            es_alert_text="Sonido inusual detectado.",
            es_action="Revisa tu entorno.",
            haptic="One short pulse",
            confidence=max(0.5, min(confidence, 0.72)),
        )
        return _analysis(alert, should_alert=False)

    alert = ALERT_PAYLOADS[sound_key]
    if confidence > 0:
        alert = alert.model_copy(update={"confidence": round(min(confidence, 0.99), 3)})
    return _analysis(alert, should_alert=True)


def _sound_key(candidate_type: object, clip_id: str) -> str:
    normalized = normalize_id(clip_id)

    if candidate_type == "fire_alarm":
        return "fire_alarm"

    if candidate_type == "emergency_vehicle":
        return "emergency_vehicle"

    if candidate_type == "door_knock":
        return "door_knock"

    if candidate_type == "speech_attention":
        if "indoor" in normalized or "address" in normalized or "speech" in normalized:
            return "indoor_address"
        return "attention_outdoors"

    return "unknown"


def _analysis(alert: AlertPayload, *, should_alert: bool) -> AlertAnalysis:
    return AlertAnalysis(
        detected_sound_type=alert.sound_type,
        tier=alert.tier,
        alert_text=alert.alert_text,
        action=alert.action,
        confidence=alert.confidence,
        should_alert=should_alert,
        alert=alert,
    )


def _payload(
    *,
    sound_type: SoundType,
    tier: AlertTier,
    image_key: str,
    alert_text: str,
    action: str,
    hi_alert_text: str,
    hi_action: str,
    es_alert_text: str,
    es_action: str,
    haptic: str,
    confidence: float,
) -> AlertPayload:
    return AlertPayload(
        sound_type=sound_type,
        tier=tier,
        image_key=image_key,
        alert_text=alert_text,
        action=action,
        translations={
            "hi": AlertTranslation(alert_text=hi_alert_text, action=hi_action),
            "es": AlertTranslation(alert_text=es_alert_text, action=es_action),
        },
        haptic=haptic,
        confidence=confidence,
    )


ALERT_PAYLOADS: dict[str, AlertPayload] = {
    "emergency_vehicle": _payload(
        sound_type="emergency_vehicle",
        tier="emergency",
        image_key="emergency_vehicle",
        alert_text="Emergency vehicle nearby.",
        action="Look around now.",
        hi_alert_text="\u0906\u092a\u093e\u0924\u0915\u093e\u0932\u0940\u0928 \u0935\u093e\u0939\u0928 \u092a\u093e\u0938 \u0939\u0948\u0964",
        hi_action="\u0905\u092d\u0940 \u0906\u0938\u092a\u093e\u0938 \u0926\u0947\u0916\u0947\u0902\u0964",
        es_alert_text="Veh\u00edculo de emergencia cerca.",
        es_action="Mira alrededor ahora.",
        haptic="SOS vibration",
        confidence=0.95,
    ),
    "fire_alarm": _payload(
        sound_type="fire_alarm",
        tier="emergency",
        image_key="fire_alarm",
        alert_text="Fire alarm detected.",
        action="Move to safety now.",
        hi_alert_text="\u0906\u0917 \u0915\u093e \u0905\u0932\u093e\u0930\u094d\u092e \u092e\u093f\u0932\u093e\u0964",
        hi_action="\u0905\u092d\u0940 \u0938\u0941\u0930\u0915\u094d\u0937\u093f\u0924 \u091c\u0917\u0939 \u091c\u093e\u090f\u0902\u0964",
        es_alert_text="Alarma de incendio detectada.",
        es_action="Ve a un lugar seguro ahora.",
        haptic="SOS vibration",
        confidence=0.94,
    ),
    "attention_outdoors": _payload(
        sound_type="attention_outdoors",
        tier="social",
        image_key="attention_outdoors",
        alert_text="Someone wants your attention.",
        action="Look around safely.",
        hi_alert_text="\u0915\u094b\u0908 \u0906\u092a\u0915\u093e \u0927\u094d\u092f\u093e\u0928 \u091a\u093e\u0939\u0924\u093e \u0939\u0948\u0964",
        hi_action="\u0938\u0941\u0930\u0915\u094d\u0937\u093f\u0924 \u0939\u094b\u0915\u0930 \u0926\u0947\u0916\u0947\u0902\u0964",
        es_alert_text="Alguien llama tu atenci\u00f3n.",
        es_action="Mira con cuidado.",
        haptic="Two short pulses",
        confidence=0.88,
    ),
    "door_knock": _payload(
        sound_type="door_knock",
        tier="social",
        image_key="door_knock",
        alert_text="Someone is at the door.",
        action="Check the entrance.",
        hi_alert_text="\u0926\u0930\u0935\u093e\u091c\u0947 \u092a\u0930 \u0915\u094b\u0908 \u0939\u0948\u0964",
        hi_action="\u0926\u0930\u0935\u093e\u091c\u093e \u0926\u0947\u0916\u0947\u0902\u0964",
        es_alert_text="Hay alguien en la puerta.",
        es_action="Revisa la entrada.",
        haptic="Two short pulses",
        confidence=0.9,
    ),
    "indoor_address": _payload(
        sound_type="addressing_user",
        tier="social",
        image_key="indoor_address",
        alert_text="Someone may be speaking to you.",
        action="Look up safely.",
        hi_alert_text="\u0915\u094b\u0908 \u0906\u092a\u0938\u0947 \u092c\u093e\u0924 \u0915\u0930 \u0930\u0939\u093e \u0939\u0948\u0964",
        hi_action="\u0938\u0941\u0930\u0915\u094d\u0937\u093f\u0924 \u0939\u094b\u0915\u0930 \u0926\u0947\u0916\u0947\u0902\u0964",
        es_alert_text="Alguien puede hablarte.",
        es_action="Mira con cuidado.",
        haptic="Two short pulses",
        confidence=0.86,
    ),
}


def _safe_no_alert_analysis(error_message: str) -> AlertAnalysis:
    alert = AlertPayload(
        sound_type="unknown",
        tier="none",
        image_key="unknown",
        alert_text="No important sound detected.",
        action="No action needed.",
        translations={
            "hi": AlertTranslation(
                alert_text="\u0915\u094b\u0908 \u092e\u0939\u0924\u094d\u0935\u092a\u0942\u0930\u094d\u0923 \u0927\u094d\u0935\u0928\u093f \u0928\u0939\u0940\u0902 \u092e\u093f\u0932\u0940\u0964",
                action="\u0915\u094b\u0908 \u0915\u093e\u0930\u094d\u0930\u0935\u093e\u0908 \u091c\u0930\u0942\u0930\u0940 \u0928\u0939\u0940\u0902\u0964",
            ),
            "es": AlertTranslation(
                alert_text="No se detecto sonido importante.",
                action="No se necesita accion.",
            ),
        },
        haptic="None",
        confidence=0.0,
    )
    return AlertAnalysis(
        detected_sound_type=alert.sound_type,
        tier=alert.tier,
        alert_text=alert.alert_text,
        action=alert.action,
        confidence=alert.confidence,
        should_alert=False,
        alert=alert,
        model_error_message=error_message,
    )
