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
class PipelineState:
    """Shared mutable state polled by the UI."""

    transcripts: list[TranscriptEvent] = field(default_factory=list)
    entities: list[EntityEvent] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    suggesting: bool = False
    is_running: bool = False
    error: str | None = None
    system_device: str = ""
    mic_device: str = ""
    ollama_ok: bool = False
