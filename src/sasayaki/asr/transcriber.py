import asyncio
import logging
import time

import numpy as np

from sasayaki.config import Config
from sasayaki.types import SpeechSegment, TranscriptEvent

logger = logging.getLogger(__name__)


def _transcribe_sync(audio: np.ndarray, model: str, language: str) -> str:
    """Synchronous transcription using mlx-whisper. Runs in executor."""
    import mlx_whisper

    result = mlx_whisper.transcribe(
        audio,
        path_or_hf_repo=model,
        language=language,
        word_timestamps=False,
    )
    text = result.get("text", "").strip()
    return text


class Transcriber:
    """Consumes SpeechSegments and produces TranscriptEvents via mlx-whisper."""

    def __init__(
        self,
        config: Config,
        input_queue: asyncio.Queue,
        output_queue: asyncio.Queue,
    ):
        self.config = config
        self.input_queue = input_queue
        self.output_queue = output_queue

    async def run(self):
        logger.info(
            "Transcriber started (model=%s)", self.config.whisper_model
        )
        loop = asyncio.get_event_loop()
        while True:
            segment: SpeechSegment = await self.input_queue.get()

            # Skip very short segments (< 0.3s) to avoid hallucinations
            if len(segment.audio) < self.config.sample_rate * 0.3:
                continue

            try:
                text = await loop.run_in_executor(
                    None,
                    _transcribe_sync,
                    segment.audio,
                    self.config.whisper_model,
                    self.config.whisper_language,
                )
            except Exception:
                logger.exception("Transcription failed")
                continue

            # Discard empty or punctuation-only results
            cleaned = text.replace(".", "").replace("。", "").replace("、", "").strip()
            if len(cleaned) < 2:
                continue

            event = TranscriptEvent(
                text=text,
                source=segment.source,
                is_partial=segment.is_partial,
                timestamp=time.monotonic(),
            )
            await self.output_queue.put(event)
            logger.info("[%s] %s: %s", "partial" if event.is_partial else "final", event.source, text)
