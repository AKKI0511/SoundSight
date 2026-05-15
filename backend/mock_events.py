from dataclasses import dataclass

from schemas import AlertPayload, AlertTranslation


@dataclass(frozen=True)
class ScheduledAlert:
    event_id: str
    start_ms: int
    end_ms: int
    alert: AlertPayload


@dataclass(frozen=True)
class ClipStreamPlan:
    clip_id: str
    done_ms: int
    alerts: tuple[ScheduledAlert, ...]


def _alert(
    *,
    sound_type: str,
    tier: str,
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


MOCK_STREAM_PLANS: dict[str, ClipStreamPlan] = {
    "emergency_vehicle": ClipStreamPlan(
        clip_id="emergency_vehicle",
        done_ms=12500,
        alerts=(
            ScheduledAlert(
                event_id="emergency_vehicle_1",
                start_ms=2800,
                end_ms=9700,
                alert=_alert(
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
            ),
        ),
    ),
    "fire_alarm": ClipStreamPlan(
        clip_id="fire_alarm",
        done_ms=12000,
        alerts=(
            ScheduledAlert(
                event_id="fire_alarm_1",
                start_ms=2800,
                end_ms=9300,
                alert=_alert(
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
            ),
        ),
    ),
    "attention_outdoors": ClipStreamPlan(
        clip_id="attention_outdoors",
        done_ms=9000,
        alerts=(
            ScheduledAlert(
                event_id="attention_outdoors_1",
                start_ms=2600,
                end_ms=7000,
                alert=_alert(
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
            ),
        ),
    ),
    "door_knock": ClipStreamPlan(
        clip_id="door_knock",
        done_ms=8500,
        alerts=(
            ScheduledAlert(
                event_id="door_knock_1",
                start_ms=2500,
                end_ms=6600,
                alert=_alert(
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
            ),
        ),
    ),
    "indoor_address": ClipStreamPlan(
        clip_id="indoor_address",
        done_ms=9000,
        alerts=(
            ScheduledAlert(
                event_id="indoor_address_1",
                start_ms=2600,
                end_ms=7000,
                alert=_alert(
                    sound_type="indoor_address",
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
            ),
        ),
    ),
}


def get_stream_plan(clip_id: str) -> ClipStreamPlan | None:
    return MOCK_STREAM_PLANS.get(clip_id)
