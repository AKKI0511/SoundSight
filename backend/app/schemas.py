from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


LanguageCode = Literal["en", "hi", "es"]
SoundType = Literal[
    "emergency_vehicle",
    "fire_alarm",
    "door_knock",
    "attention_outdoors",
    "addressing_user",
    "baby_crying",
    "background_noise",
    "unknown",
]
AlertTier = Literal["emergency", "social", "ambient", "none"]
ModelSource = Literal["dummy", "cactus"]


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class StreamEventsRequest(ApiModel):
    clip_id: str = Field(alias="clipId")
    language: LanguageCode = "en"


class AlertPayload(ApiModel):
    sound_type: SoundType
    tier: AlertTier
    alert_text: str
    action: str
    image_key: str
    haptic: str
    confidence: float = Field(ge=0.0, le=1.0)
    language: LanguageCode


class AlertAnalysis(AlertPayload):
    should_alert: bool
    model_error_message: str | None = Field(
        default=None,
        alias="modelErrorMessage",
        exclude=True,
    )

    def to_alert_payload(self) -> AlertPayload:
        return AlertPayload(
            sound_type=self.sound_type,
            tier=self.tier,
            alert_text=self.alert_text,
            action=self.action,
            image_key=self.image_key,
            haptic=self.haptic,
            confidence=self.confidence,
            language=self.language,
        )


class SessionStartedEvent(ApiModel):
    type: Literal["session_started"] = "session_started"
    session_id: str = Field(alias="sessionId")
    clip_id: str = Field(alias="clipId")
    timestamp_ms: int = Field(default=0, alias="timestampMs")


class EngineLogEvent(ApiModel):
    type: Literal["engine_log"] = "engine_log"
    session_id: str = Field(alias="sessionId")
    timestamp_ms: int = Field(alias="timestampMs")
    window_start_ms: int = Field(alias="windowStartMs")
    window_end_ms: int = Field(alias="windowEndMs")
    trigger_mode: str = Field(alias="triggerMode")
    rms: float
    peak: float
    onset_score: float = Field(alias="onsetScore")
    silent: bool
    should_call_model: bool = Field(alias="shouldCallModel")
    reason: str


class ModelCallEvent(ApiModel):
    type: Literal["model_call"] = "model_call"
    session_id: str = Field(alias="sessionId")
    candidate_id: str = Field(alias="candidateId")
    source: ModelSource = "dummy"
    model_name: str | None = Field(default=None, alias="model")
    timestamp_ms: int = Field(alias="timestampMs")
    clip_id: str = Field(alias="clipId")
    language: LanguageCode
    reason: str
    window_start_ms: int = Field(alias="windowStartMs")
    window_end_ms: int = Field(alias="windowEndMs")
    candidate_type: str = Field(alias="candidateType")
    candidate_confidence: float = Field(alias="candidateConfidence")


class ModelResultEvent(ApiModel):
    type: Literal["model_result"] = "model_result"
    session_id: str = Field(alias="sessionId")
    candidate_id: str = Field(alias="candidateId")
    source: ModelSource = "dummy"
    model_name: str | None = Field(default=None, alias="model")
    timestamp_ms: int = Field(alias="timestampMs")
    clip_id: str = Field(alias="clipId")
    analysis: AlertAnalysis


class ModelErrorEvent(ApiModel):
    type: Literal["model_error"] = "model_error"
    session_id: str = Field(alias="sessionId")
    candidate_id: str = Field(alias="candidateId")
    source: ModelSource = "cactus"
    model_name: str | None = Field(default=None, alias="model")
    timestamp_ms: int = Field(alias="timestampMs")
    clip_id: str = Field(alias="clipId")
    message: str


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
    | ModelResultEvent
    | ModelErrorEvent
    | AlertStartEvent
    | AlertEndEvent
    | SessionDoneEvent
    | ErrorEvent
)
