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
    tts_output_device: str = ""
    ollama_ok: bool = False
    system_level: float = 0.0
    mic_level: float = 0.0
    face: FaceAnalysisStateSchema = FaceAnalysisStateSchema()
    turn_taking: TurnTakingStateSchema = TurnTakingStateSchema()
    tts_playing: bool = False
    auto_suggestion_pending: bool = False
    llm_backend: str = "ollama"
    ollama_model: str = ""
    llamacpp_url: str = ""
    auto_suggest_style: str = ""
    turn_taking_threshold: float = 0.6
    turn_taking_cooldown_sec: float = 8.0
    turn_taking_min_transcripts: int = 3
    llm_context_mode: str = "fixed"
    llm_context_turns: int = 5
    screen_region: tuple[int, int, int, int] = (0, 0, 0, 0)
    screen_monitor: int = 1
    silence_seconds: float = 0.0
    silence_rescue_enabled: bool = True
    silence_rescue_seconds: float = 6.0
    silence_rescue_style: str = "話題転換"
    speculative_pre_fire_enabled: bool = True
    last_whisper_text: str = ""
    meeting_context: str = ""
    adapt_style_to_emotion: bool = True
    concern_alert_enabled: bool = True


class MonitorInfo(BaseModel):
    index: int
    width: int
    height: int


class MonitorsResponse(BaseModel):
    monitors: list[MonitorInfo]


class ScreenRegionResponse(BaseModel):
    region: tuple[int, int, int, int] | None


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
    turn_taking_threshold: float | None = None
    turn_taking_cooldown_sec: float | None = None
    turn_taking_min_transcripts: int | None = None
    llm_context_mode: Literal["fixed", "since_last_fire"] | None = None
    llm_context_turns: int | None = None
    silence_rescue_enabled: bool | None = None
    silence_rescue_seconds: float | None = None
    silence_rescue_style: str | None = None
    tts_chime_enabled: bool | None = None
    speculative_pre_fire_enabled: bool | None = None
    meeting_context: str | None = None
    adapt_style_to_emotion: bool | None = None
    concern_alert_enabled: bool | None = None


class DeviceInfo(BaseModel):
    name: str


class DevicesResponse(BaseModel):
    input_devices: list[DeviceInfo]
    output_devices: list[DeviceInfo]


class OkResponse(BaseModel):
    ok: bool = True
