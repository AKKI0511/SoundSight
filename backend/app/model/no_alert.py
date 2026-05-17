from app.schemas import AlertAnalysis, LanguageCode


type LocalizedCopy = dict[LanguageCode, tuple[str, str]]


NO_ALERT_COPY: LocalizedCopy = {
    "en": ("No important sound detected.", "No action needed."),
    "hi": ("Koi mahatvapurn dhvani nahi mili.", "Koi karvai zaruri nahi."),
    "es": ("No se detecto sonido importante.", "No se necesita accion."),
}


def no_alert(
    language: LanguageCode,
    *,
    model_error_message: str | None = None,
) -> AlertAnalysis:
    alert_text, action = NO_ALERT_COPY.get(language) or NO_ALERT_COPY["en"]
    return AlertAnalysis(
        should_alert=False,
        sound_type="unknown",
        tier="none",
        alert_text=alert_text,
        action=action,
        image_key="unknown",
        haptic="None",
        confidence=0.0,
        language=language,
        model_error_message=model_error_message,
    )
