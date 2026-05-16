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
EngineState = Literal["IDLE", "CANDIDATE", "ACTIVE", "COOLDOWN"]
CandidateType = Literal[
    "fire_alarm",
    "emergency_vehicle",
    "door_knock",
    "speech_attention",
    "unknown",
]


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class StreamEventsRequest(ApiModel):
    clip_id: str = Field(alias="clipId")
    language: LanguageCode = "en"


class AlertTranslation(ApiModel):
    alert_text: str
    action: str


class AlertPayload(ApiModel):
    sound_type: SoundType
    tier: AlertTier
    image_key: str
    alert_text: str
    action: str
    translations: dict[Literal["hi", "es"], AlertTranslation]
    haptic: str
    confidence: float


class AlertAnalysis(ApiModel):
    detected_sound_type: SoundType = Field(alias="detectedSoundType")
    tier: AlertTier
    alert_text: str = Field(alias="alertText")
    action: str
    confidence: float
    should_alert: bool = Field(alias="shouldAlert")
    alert: AlertPayload
    model_error_message: str | None = Field(
        default=None,
        alias="modelErrorMessage",
        exclude=True,
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
    rms: float
    noise_floor: float = Field(alias="noiseFloor")
    rms_z_score: float = Field(alias="rmsZScore")
    onset_score: float = Field(alias="onsetScore")
    spectral_flux: float = Field(alias="spectralFlux")
    zero_crossing_rate: float = Field(alias="zeroCrossingRate")
    spectral_centroid: float = Field(alias="spectralCentroid")
    sustained_energy_score: float = Field(alias="sustainedEnergyScore")
    silence_score: float = Field(alias="silenceScore")
    speech_probability: float = Field(alias="speechProbability")
    speech_source: str = Field(alias="speechSource")
    speech_warning: str | None = Field(default=None, alias="speechWarning")
    candidate_type: CandidateType | None = Field(alias="candidateType")
    candidate_confidence: float = Field(alias="candidateConfidence")
    should_call_model: bool = Field(alias="shouldCallModel")
    state: EngineState
    candidate: bool


class CandidateStartEvent(ApiModel):
    type: Literal["candidate_start"] = "candidate_start"
    session_id: str = Field(alias="sessionId")
    candidate_id: str = Field(alias="candidateId")
    timestamp_ms: int = Field(alias="timestampMs")
    window_start_ms: int = Field(alias="windowStartMs")
    window_end_ms: int = Field(alias="windowEndMs")
    candidate_type: CandidateType = Field(alias="candidateType")
    candidate_confidence: float = Field(alias="candidateConfidence")


class CandidateUpdateEvent(ApiModel):
    type: Literal["candidate_update"] = "candidate_update"
    session_id: str = Field(alias="sessionId")
    candidate_id: str = Field(alias="candidateId")
    timestamp_ms: int = Field(alias="timestampMs")
    window_start_ms: int = Field(alias="windowStartMs")
    window_end_ms: int = Field(alias="windowEndMs")
    candidate_type: CandidateType = Field(alias="candidateType")
    candidate_confidence: float = Field(alias="candidateConfidence")
    should_call_model: bool = Field(alias="shouldCallModel")
    state: EngineState


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
    candidate_type: CandidateType = Field(alias="candidateType")
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
    | CandidateStartEvent
    | CandidateUpdateEvent
    | ModelCallEvent
    | ModelResultEvent
    | ModelErrorEvent
    | AlertStartEvent
    | AlertEndEvent
    | SessionDoneEvent
    | ErrorEvent
)
