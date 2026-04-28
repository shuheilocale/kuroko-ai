from dataclasses import dataclass, field
from typing import Literal

import numpy as np


@dataclass
class SpeechSegment:
    audio: np.ndarray  # 16kHz mono float32
    source: Literal["system", "mic"]
    is_partial: bool
    timestamp: float


@dataclass
class TranscriptEvent:
    text: str
    source: Literal["system", "mic"]
    is_partial: bool
    timestamp: float


@dataclass
class EntityEvent:
    term: str
    definition: str
    timestamp: float
    loading: bool = False


@dataclass
class SuggestionEvent:
    suggestions: list[str]
    in_response_to: str
    timestamp: float


@dataclass
class ProfileFact:
    """A single discovered fact about the conversation partner."""
    category: str
    content: str
    timestamp: float


@dataclass
class PartnerProfile:
    """Dynamically built profile of the conversation partner."""
    name: str | None = None
    facts: list[ProfileFact] = field(default_factory=list)
    summary: str = ""


@dataclass
class ExpressionChangeEvent:
    """Records a moment when the partner's expression changed."""
    detail: str
    transcript_snippet: str
    timestamp: float


@dataclass
class FaceAnalysisState:
    """Face analysis results for the UI."""
    detected: bool = False
    joy: float = 0.0
    surprise: float = 0.0
    concern: float = 0.0
    neutral: float = 1.0
    dominant_emotion: str = "neutral"
    nodding: bool = False
    nod_count: int = 0
    expression_changes: list[ExpressionChangeEvent] = field(
        default_factory=list
    )
    fps: float = 0.0
    face_image_base64: str = ""


@dataclass
class TurnTakingState:
    """MaAI turn-taking prediction state."""
    p_now: float = 0.0
    p_future: float = 0.0
    is_turn_change: bool = False
    last_trigger_time: float = 0.0
    enabled: bool = False


@dataclass
class PipelineState:
    """Shared mutable state polled by the UI."""

    transcripts: list[TranscriptEvent] = field(default_factory=list)
    entities: list[EntityEvent] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    suggesting: bool = False
    suggestion_style: str = ""
    profile: PartnerProfile = field(default_factory=PartnerProfile)
    profiling: bool = False
    is_running: bool = False
    error: str | None = None
    system_device: str = ""
    mic_device: str = ""
    tts_output_device: str = ""
    tts_omnivoice_ref_audio: str = ""
    tts_omnivoice_ref_text: str = ""
    tts_loopback_suppress: bool = True
    ollama_ok: bool = False
    system_level: float = 0.0
    mic_level: float = 0.0
    face: FaceAnalysisState = field(default_factory=FaceAnalysisState)
    turn_taking: TurnTakingState = field(default_factory=TurnTakingState)
    tts_playing: bool = False
    auto_suggestion_pending: bool = False
    # Mirrors of Config so the UI can render the live backend wiring.
    llm_backend: str = "ollama"
    ollama_model: str = ""
    llamacpp_url: str = ""
    auto_suggest_style: str = ""
    turn_taking_threshold: float = 0.6
    turn_taking_cooldown_sec: float = 8.0
    turn_taking_min_transcripts: int = 3
    llm_context_mode: str = "fixed"
    llm_context_turns: int = 5
    # (x, y, w, h) — (0,0,0,0) means full monitor.
    screen_region: tuple[int, int, int, int] = (0, 0, 0, 0)
    screen_monitor: int = 1
    # Seconds since the most recent transcript arrived. Surfaced for the
    # header "沈黙 4.2s" indicator. 0 if no transcripts yet.
    silence_seconds: float = 0.0
    silence_rescue_enabled: bool = True
    silence_rescue_seconds: float = 6.0
    silence_rescue_style: str = "話題転換"
    speculative_pre_fire_enabled: bool = True
    # Most recently whispered suggestion. Used as the source for the
    # "replay last whisper" hotkey.
    last_whisper_text: str = ""
    meeting_context: str = ""
    adapt_style_to_emotion: bool = True
    concern_alert_enabled: bool = True
