from typing import Any

from app.audio.loader import normalize_id
from app.model.no_alert import no_alert
from app.schemas import AlertAnalysis, LanguageCode


DUMMY_MODEL_NAME = "deterministic_dummy"


type LocalizedCopy = dict[LanguageCode, tuple[str, str]]


async def analyze_candidate(
    audio_window: object,
    metadata: dict[str, Any],
    language: LanguageCode,
) -> AlertAnalysis:
    del audio_window

    if metadata.get("reason") == "active_quiet_check" or metadata.get("silent") is True:
        return no_alert(language)

    sound_key = _sound_key(str(metadata.get("clipId", "")))
    if sound_key == "unknown":
        return no_alert(language)

    alert = DUMMY_ALERTS[sound_key]
    confidence = float(metadata.get("candidateConfidence", 0.0) or 0.0)
    confidence = round(min(max(confidence, alert["confidence"]), 0.99), 3)
    alert_text, action = _localized(alert["copy"], language)

    return AlertAnalysis(
        should_alert=True,
        sound_type=alert["sound_type"],
        tier=alert["tier"],
        alert_text=alert_text,
        action=action,
        image_key=alert["image_key"],
        haptic=alert["haptic"],
        confidence=confidence,
        language=language,
    )


def _sound_key(clip_id: str) -> str:
    normalized = normalize_id(clip_id)

    if "fire" in normalized and "alarm" in normalized:
        return "fire_alarm"
    if "ambulance" in normalized or "siren" in normalized or "emergency" in normalized:
        return "emergency_vehicle"
    if "door" in normalized or "knock" in normalized:
        return "door_knock"
    if "baby" in normalized or "cry" in normalized:
        return "baby_crying"
    if "attention" in normalized:
        return "attention_outdoors"
    if "indoor" in normalized or "address" in normalized or "speech" in normalized:
        return "addressing_user"
    if normalized == "live_window":
        return "live_sound"
    return "unknown"


def _localized(copy: LocalizedCopy, language: LanguageCode) -> tuple[str, str]:
    return copy.get(language) or copy["en"]


DUMMY_ALERTS: dict[str, dict[str, object]] = {
    "emergency_vehicle": {
        "sound_type": "emergency_vehicle",
        "tier": "emergency",
        "image_key": "emergency_vehicle",
        "haptic": "SOS vibration",
        "confidence": 0.95,
        "copy": {
            "en": ("Emergency vehicle nearby.", "Look around now."),
            "hi": ("Aapatkalin vahan paas hai.", "Abhi aaspaas dekhen."),
            "es": ("Vehiculo de emergencia cerca.", "Mira alrededor ahora."),
        },
    },
    "fire_alarm": {
        "sound_type": "fire_alarm",
        "tier": "emergency",
        "image_key": "fire_alarm",
        "haptic": "SOS vibration",
        "confidence": 0.94,
        "copy": {
            "en": ("Fire alarm detected.", "Move to safety now."),
            "hi": ("Aag ka alarm mila.", "Abhi surakshit jagah jayein."),
            "es": ("Alarma de incendio detectada.", "Ve a un lugar seguro ahora."),
        },
    },
    "attention_outdoors": {
        "sound_type": "attention_outdoors",
        "tier": "social",
        "image_key": "attention_outdoors",
        "haptic": "Two short pulses",
        "confidence": 0.88,
        "copy": {
            "en": ("Someone wants your attention.", "Look around safely."),
            "hi": ("Koi aapka dhyan chahta hai.", "Surakshit hokar dekhen."),
            "es": ("Alguien llama tu atencion.", "Mira con cuidado."),
        },
    },
    "baby_crying": {
        "sound_type": "baby_crying",
        "tier": "social",
        "image_key": "baby_crying",
        "haptic": "Two short pulses",
        "confidence": 0.87,
        "copy": {
            "en": ("Baby crying nearby.", "Check on the baby."),
            "hi": ("Baccha ro raha hai.", "Bacche ko dekhen."),
            "es": ("Bebe llorando cerca.", "Revisa al bebe."),
        },
    },
    "door_knock": {
        "sound_type": "door_knock",
        "tier": "social",
        "image_key": "door_knock",
        "haptic": "Two short pulses",
        "confidence": 0.9,
        "copy": {
            "en": ("Someone is at the door.", "Check the entrance."),
            "hi": ("Darwaze par koi hai.", "Darwaza dekhen."),
            "es": ("Hay alguien en la puerta.", "Revisa la entrada."),
        },
    },
    "addressing_user": {
        "sound_type": "addressing_user",
        "tier": "social",
        "image_key": "indoor_address",
        "haptic": "Two short pulses",
        "confidence": 0.86,
        "copy": {
            "en": ("Someone may be speaking to you.", "Look up safely."),
            "hi": ("Koi aapse baat kar raha hai.", "Surakshit hokar dekhen."),
            "es": ("Alguien puede hablarte.", "Mira con cuidado."),
        },
    },
    "live_sound": {
        "sound_type": "unknown",
        "tier": "ambient",
        "image_key": "attention_outdoors",
        "haptic": "One short pulse",
        "confidence": 0.75,
        "copy": {
            "en": ("Sound detected nearby.", "Check your surroundings."),
            "hi": ("Paas mein dhvani mili.", "Aaspaas dekhen."),
            "es": ("Sonido detectado cerca.", "Revisa tu entorno."),
        },
    },
}
