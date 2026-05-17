from __future__ import annotations

import asyncio
import atexit
import json
import os
import re
import sys
import tempfile
import threading
import wave
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.config import DEFAULT_CONFIG
from app.model.no_alert import no_alert
from app.schemas import AlertAnalysis, AlertTier, LanguageCode, SoundType


DEFAULT_CACTUS_MODEL = "google/gemma-4-E2B-it"
CACTUS_SAMPLE_RATE = DEFAULT_CONFIG.audio.sample_rate


class CactusAlertJson(BaseModel):
    should_alert: bool
    sound_type: SoundType
    tier: AlertTier
    alert_text: str
    action: str
    image_key: str
    haptic: str
    confidence: float = Field(ge=0.0, le=1.0)
    language: LanguageCode

    @field_validator("alert_text")
    @classmethod
    def _alert_text_max_words(cls, value: str) -> str:
        if len(value.split()) > 12:
            raise ValueError("alert_text must be 12 words or fewer")
        return value

    @field_validator("action")
    @classmethod
    def _action_max_words(cls, value: str) -> str:
        if len(value.split()) > 8:
            raise ValueError("action must be 8 words or fewer")
        return value


_MODEL_LOCK = threading.RLock()
_CACTUS_API: Any | None = None
_CACTUS_MODEL: Any | None = None
_CACTUS_MODEL_PATH: Path | None = None


async def analyze_candidate_with_gemma4(
    audio_window: object,
    metadata: dict[str, Any],
    language: LanguageCode,
) -> AlertAnalysis:
    return await asyncio.to_thread(
        _analyze_candidate_with_gemma4_sync,
        audio_window,
        metadata,
        language,
    )


def get_cactus_model_label() -> str:
    model_path = os.getenv("SOUNDSIGHT_CACTUS_MODEL_PATH")
    if model_path:
        return str(Path(model_path).expanduser())
    if _CACTUS_MODEL_PATH is not None:
        return str(_CACTUS_MODEL_PATH)
    return os.getenv("SOUNDSIGHT_CACTUS_MODEL", DEFAULT_CACTUS_MODEL)


def destroy_cactus_model() -> None:
    global _CACTUS_MODEL

    with _MODEL_LOCK:
        if _CACTUS_MODEL is None:
            return
        try:
            _load_cactus_api().cactus_destroy(_CACTUS_MODEL)
        finally:
            _CACTUS_MODEL = None


def _analyze_candidate_with_gemma4_sync(
    audio_window: object,
    metadata: dict[str, Any],
    language: LanguageCode,
) -> AlertAnalysis:
    audio_path: Path | None = None
    try:
        audio_path = _write_candidate_wav(audio_window)
        prompt = _build_prompt(metadata, language)
        raw_result_json = _complete_with_cactus(prompt, audio_path)
        return _analysis_from_cactus_completion(raw_result_json, language)
    except Exception as exc:
        return no_alert(language, model_error_message=_format_error(exc))
    finally:
        if audio_path is not None:
            try:
                audio_path.unlink(missing_ok=True)
            except OSError:
                pass


def _complete_with_cactus(prompt: str, audio_path: Path) -> str:
    messages = json.dumps(
        [
            {
                "role": "user",
                "content": prompt,
                "audio": [str(audio_path)],
            }
        ]
    )
    options = json.dumps(
        {
            "max_tokens": 256,
            "temperature": 0.0,
            "stop_sequences": ["```", "<|im_end|>"],
        }
    )

    with _MODEL_LOCK:
        api = _load_cactus_api()
        model = _ensure_cactus_model(api)
        return api.cactus_complete(model, messages, options, None, None)


def _load_cactus_api() -> Any:
    global _CACTUS_API

    if _CACTUS_API is not None:
        return _CACTUS_API

    cactus_repo = os.getenv("SOUNDSIGHT_CACTUS_REPO")
    if cactus_repo:
        cactus_python = Path(cactus_repo).expanduser() / "python"
        if str(cactus_python) not in sys.path:
            sys.path.insert(0, str(cactus_python))

    try:
        from src import cactus as cactus_api  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "Could not import Cactus Python bindings. Set SOUNDSIGHT_CACTUS_REPO "
            "to a Cactus checkout and run `source ./setup && cactus build --python`."
        ) from exc

    _CACTUS_API = cactus_api
    return _CACTUS_API


def _ensure_cactus_model(api: Any) -> Any:
    global _CACTUS_MODEL, _CACTUS_MODEL_PATH

    if _CACTUS_MODEL is not None:
        return _CACTUS_MODEL

    _CACTUS_MODEL_PATH = _resolve_model_path()
    _CACTUS_MODEL = api.cactus_init(str(_CACTUS_MODEL_PATH), None, False)
    return _CACTUS_MODEL


def _resolve_model_path() -> Path:
    configured_path = os.getenv("SOUNDSIGHT_CACTUS_MODEL_PATH")
    if configured_path:
        path = Path(configured_path).expanduser()
        if "gemma-4" not in str(path).lower():
            raise RuntimeError(
                "Cactus mode only supports Gemma 4. "
                "SOUNDSIGHT_CACTUS_MODEL_PATH must point to Gemma 4 weights."
            )
        if not path.exists():
            raise RuntimeError(f"SOUNDSIGHT_CACTUS_MODEL_PATH does not exist: {path}")
        return path

    model_id = os.getenv("SOUNDSIGHT_CACTUS_MODEL", DEFAULT_CACTUS_MODEL)
    if "gemma-4" not in model_id.lower():
        raise RuntimeError(
            "Cactus mode only supports Gemma 4. Set "
            f"SOUNDSIGHT_CACTUS_MODEL={DEFAULT_CACTUS_MODEL!r}."
        )

    try:
        from src.downloads import ensure_model  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "SOUNDSIGHT_CACTUS_MODEL_PATH is required when src.downloads is unavailable."
        ) from exc

    return Path(ensure_model(model_id))


def _write_candidate_wav(audio_window: object) -> Path:
    samples = np.asarray(audio_window, dtype=np.float32)
    if samples.ndim > 1:
        samples = np.mean(samples, axis=1, dtype=np.float32)

    samples = np.nan_to_num(samples, copy=False)
    samples = np.clip(samples, -1.0, 1.0)
    pcm = (samples * np.iinfo(np.int16).max).astype(np.int16, copy=False)

    with tempfile.NamedTemporaryFile(
        suffix=".wav",
        prefix="soundsight-candidate-",
        delete=False,
    ) as temp_file:
        wav_path = Path(temp_file.name)

    with wave.open(str(wav_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(CACTUS_SAMPLE_RATE)
        wav_file.writeframes(pcm.tobytes())

    return wav_path


def _build_prompt(metadata: dict[str, Any], language: LanguageCode) -> str:
    metadata_json = json.dumps(metadata, ensure_ascii=True, sort_keys=True)
    return f"""You are SoundSight, an accessibility assistant for Deaf and hard-of-hearing users. Analyze the attached audio directly with Gemma 4. Do not transcribe first. Return only one valid compact JSON object and no markdown.

Required JSON shape:
{{"should_alert":true,"sound_type":"fire_alarm","tier":"emergency","alert_text":"Fire alarm detected.","action":"Move to safety now.","image_key":"fire_alarm","haptic":"SOS vibration","confidence":0.91,"language":"{language}"}}

Allowed sound_type values: emergency_vehicle, fire_alarm, door_knock, attention_outdoors, addressing_user, baby_crying, background_noise, unknown.
Allowed tier values: emergency, social, ambient, none.
Rules:
- Use only the requested UI language for alert_text and action.
- Set language exactly to "{language}".
- Return selected-language fields only; do not include other language fields.
- If uncertain or only background noise, set should_alert=false, sound_type="unknown" or "background_noise", tier="none", haptic="None", confidence <= 0.30.
- alert_text max 12 words.
- action max 8 words.
- Use image_key matching sound_type when possible.

Detector metadata: {metadata_json}
"""


def _analysis_from_cactus_completion(
    raw_result_json: str,
    language: LanguageCode,
) -> AlertAnalysis:
    try:
        result = json.loads(raw_result_json)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Cactus returned non-JSON completion envelope: {exc}") from exc

    if result.get("success") is False:
        raise RuntimeError(f"Cactus completion failed: {result.get('error') or 'unknown error'}")

    if result.get("cloud_handoff"):
        raise RuntimeError("Cactus attempted cloud handoff; SoundSight cactus mode is local only.")

    raw_response = _string_or_none(result.get("response"))
    if not raw_response:
        raise RuntimeError("Cactus completion did not include a response field.")

    try:
        parsed_json = parse_alert_json(raw_response)
        parsed_alert = CactusAlertJson.model_validate(parsed_json)
    except (ValueError, ValidationError) as exc:
        raise RuntimeError(
            f"Cactus response did not validate as SoundSight alert JSON: {_format_error(exc)}"
        ) from exc

    if parsed_alert.language != language:
        raise RuntimeError(
            f"Cactus returned language {parsed_alert.language!r}, expected {language!r}."
        )

    return AlertAnalysis(
        should_alert=parsed_alert.should_alert,
        sound_type=parsed_alert.sound_type,
        tier=parsed_alert.tier,
        alert_text=parsed_alert.alert_text,
        action=parsed_alert.action,
        image_key=parsed_alert.image_key,
        haptic=parsed_alert.haptic,
        confidence=round(float(parsed_alert.confidence), 3),
        language=parsed_alert.language,
    )


def parse_alert_json(raw_response: str) -> dict[str, Any]:
    parse_attempts = [_strip_json_fence(raw_response.strip())]
    parse_attempts.extend(_balanced_json_candidates(raw_response))

    for candidate in parse_attempts:
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    raise ValueError("no valid JSON object found")


def _strip_json_fence(value: str) -> str:
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", value, flags=re.IGNORECASE).strip()


def _balanced_json_candidates(value: str) -> list[str]:
    candidates: list[str] = []
    starts = [index for index, char in enumerate(value) if char == "{"]

    for start in starts:
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(value)):
            char = value[index]
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(value[start : index + 1])
                    break

    return candidates


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _format_error(exc: BaseException) -> str:
    return str(exc).replace("\n", " ").strip() or exc.__class__.__name__


atexit.register(destroy_cactus_model)
