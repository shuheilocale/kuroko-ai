from typing import Literal

from pydantic import BaseModel, ConfigDict


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TranscriptEventSchema(_Base):
    text: str
    source: Literal["system", "mic"]
    is_partial: bool
    timestamp: float


class EntityEventSchema(_Base):
    term: str
    definition: str
    timestamp: float
    loading: bool = False


class ProfileFactSchema(_Base):
    category: str
    content: str
    timestamp: float


class PartnerProfileSchema(_Base):
    name: str | None = None
    facts: list[ProfileFactSchema] = []
    summary: str = ""


class ExpressionChangeEventSchema(_Base):
    detail: str
    transcript_snippet: str
    timestamp: float


class FaceAnalysisStateSchema(_Base):
    detected: bool = False
    joy: float = 0.0
    surprise: float = 0.0
    concern: float = 0.0
    neutral: float = 1.0
    dominant_emotion: str = "neutral"
    nodding: bool = False
    nod_count: int = 0
    expression_changes: list[ExpressionChangeEventSchema] = []
    fps: float = 0.0
    face_image_base64: str = ""


class TurnTakingStateSchema(_Base):
    p_now: float = 0.0
    p_future: float = 0.0
    is_turn_change: bool = False
    last_trigger_time: float = 0.0
    enabled: bool = False


class PipelineStateSchema(_Base):
    transcripts: list[TranscriptEventSchema] = []
    entities: list[EntityEventSchema] = []
    suggestions: list[str] = []
    suggesting: bool = False
    suggestion_style: str = ""
    profile: PartnerProfileSchema = PartnerProfileSchema()
    profiling: bool = False
    is_running: bool = False
    error: str | None = None
    system_device: str = ""
    mic_device: str = ""
    ollama_ok: bool = False
    system_level: float = 0.0
    mic_level: float = 0.0
    face: FaceAnalysisStateSchema = FaceAnalysisStateSchema()
    turn_taking: TurnTakingStateSchema = TurnTakingStateSchema()
    tts_playing: bool = False
    auto_suggestion_pending: bool = False


class SuggestRequest(BaseModel):
    style: str


class KeywordRequest(BaseModel):
    term: str


class SettingsPatch(BaseModel):
    """Partial Config update. Only provided fields are modified."""

    model_config = ConfigDict(extra="allow")

    system_audio_device: str | None = None
    mic_device: str | None = None
    tts_output_device: str | None = None
    screen_monitor: int | None = None
    llm_backend: Literal["ollama", "llamacpp"] | None = None
    ollama_model: str | None = None
    llamacpp_url: str | None = None
    maai_enabled: bool | None = None
    tts_enabled: bool | None = None
    auto_suggest_style: str | None = None


class DeviceInfo(BaseModel):
    name: str


class DevicesResponse(BaseModel):
    input_devices: list[DeviceInfo]
    output_devices: list[DeviceInfo]


class OkResponse(BaseModel):
    ok: bool = True
