from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


LanguageCode = Literal["en", "hi", "es"]
AlertTier = Literal["emergency", "social", "ambient"]


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


StreamEvent = (
    SessionStartedEvent | AlertStartEvent | AlertEndEvent | SessionDoneEvent
)
