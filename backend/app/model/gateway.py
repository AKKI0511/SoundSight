from typing import Any

from app.config import get_model_mode
from app.model import dummy_gateway
from app.schemas import AlertAnalysis, LanguageCode, ModelSource


async def analyze_candidate_with_gemma4(
    audio_window: object,
    metadata: dict[str, Any],
    language: LanguageCode,
) -> AlertAnalysis:
    mode = get_model_mode()
    if mode == "dummy":
        return await dummy_gateway.analyze_candidate(audio_window, metadata, language)

    from app.model.cactus_gateway import analyze_candidate_with_gemma4 as cactus_analyze

    return await cactus_analyze(audio_window, metadata, language)


def get_model_source() -> ModelSource:
    return get_model_mode()


def get_model_name() -> str:
    if get_model_mode() == "dummy":
        return dummy_gateway.DUMMY_MODEL_NAME

    from app.model.cactus_gateway import get_cactus_model_label

    return get_cactus_model_label()


def shutdown_model_gateway() -> None:
    try:
        from app.model.cactus_gateway import destroy_cactus_model
    except Exception:
        return

    destroy_cactus_model()
