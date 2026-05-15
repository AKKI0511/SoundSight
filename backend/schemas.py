from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


LanguageCode = Literal["en", "hi", "es"]
AlertTier = Literal["emergency", "social", "ambient"]
EngineState = Literal["IDLE", "CANDIDATE", "ACTIVE", "COOLDOWN"]


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class StreamEventsRequest(ApiModel):
    clip_id: str = Field(alias="clipId")
    language: LanguageCode = "en"


class AlertTranslation(ApiModel):
    alert_text: str
    action: str


class AlertPayload(ApiModel):
    sound_type: str
    tier: AlertTier
    image_key: str
    alert_text: str
    action: str
    translations: dict[Literal["hi", "es"], AlertTranslation]
    haptic: str
    confidence: float


class AlertAnalysis(ApiModel):
    detected_sound_type: str = Field(alias="detectedSoundType")
    tier: AlertTier
    alert_text: str = Field(alias="alertText")
    action: str
    confidence: float
    should_alert: bool = Field(alias="shouldAlert")
    alert: AlertPayload


class SessionStartedEvent(ApiModel):
    type: Literal["session_started"] = "session_started"
    session_id: str = Field(alias="sessionId")
    clip_id: str = Field(alias="clipId")
    timestamp_ms: int = Field(default=0, alias="timestampMs")


class AlertStartEvent(ApiModel):
    type: Literal["alert_start"] = "alert_start"
    session_id: str = Field(alias="sessionId")
    event_id: str = Field(alias="eventId")
    timestamp_ms: int = Field(alias="timestampMs")
    alert: AlertPayload


class AlertEndEvent(ApiModel):
    type: Literal["alert_end"] = "alert_end"
    session_id: str = Field(alias="sessionId")
    event_id: str = Field(alias="eventId")
    timestamp_ms: int = Field(alias="timestampMs")


class SessionDoneEvent(ApiModel):
    type: Literal["session_done"] = "session_done"
    session_id: str = Field(alias="sessionId")
    timestamp_ms: int = Field(alias="timestampMs")


class EngineLogEvent(ApiModel):
    type: Literal["engine_log"] = "engine_log"
    session_id: str = Field(alias="sessionId")
    timestamp_ms: int = Field(alias="timestampMs")
    window_start_ms: int = Field(alias="windowStartMs")
    window_end_ms: int = Field(alias="windowEndMs")
    rms: float
    noise_floor: float = Field(alias="noiseFloor")
    energy_ratio: float = Field(alias="energyRatio")
    onset_score: float = Field(alias="onsetScore")
    sustained_energy: bool = Field(alias="sustainedEnergy")
    state: EngineState
    candidate: bool


class ModelCallEvent(ApiModel):
    type: Literal["model_call"] = "model_call"
    session_id: str = Field(alias="sessionId")
    timestamp_ms: int = Field(alias="timestampMs")
    clip_id: str = Field(alias="clipId")
    reason: str
    window_start_ms: int = Field(alias="windowStartMs")
    window_end_ms: int = Field(alias="windowEndMs")
    analysis: AlertAnalysis


class ErrorEvent(ApiModel):
    type: Literal["error"] = "error"
    session_id: str = Field(alias="sessionId")
    clip_id: str = Field(alias="clipId")
    timestamp_ms: int = Field(default=0, alias="timestampMs")
    code: str
    message: str


StreamEvent = (
    SessionStartedEvent
    | EngineLogEvent
    | ModelCallEvent
    | AlertStartEvent
    | AlertEndEvent
    | SessionDoneEvent
    | ErrorEvent
)
