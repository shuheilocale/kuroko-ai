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
    """Consumes SpeechSegments and produces TranscriptEvents via mlx-whisper.

    For streaming mode: when a new partial segment arrives while a previous
    partial is still being transcribed, the old one is discarded in favor
    of the newer (longer) audio buffer.
    """

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

            # If this is a partial, drain the queue for newer partials
            # from the same source (use the latest one)
            if segment.is_partial:
                segment = self._drain_for_latest_partial(segment)

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
                timestamp=time.time(),
            )
            await self.output_queue.put(event)
            logger.info(
                "[%s] %s: %s",
                "partial" if event.is_partial else "final",
                event.source,
                text,
            )

    def _drain_for_latest_partial(self, current: SpeechSegment) -> SpeechSegment:
        """Drain queued partials from the same source, keeping only the latest."""
        latest = current
        requeue = []
        while not self.input_queue.empty():
            try:
                item = self.input_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            if item.is_partial and item.source == latest.source:
                # Newer partial from same source - use this one instead
                latest = item
            else:
                # Different source or final segment - keep it
                requeue.append(item)

        # Put back non-matching items
        for item in requeue:
            try:
                self.input_queue.put_nowait(item)
            except asyncio.QueueFull:
                pass

        if latest is not current:
            logger.debug(
                "Skipped stale partial(s), using latest (%d samples)",
                len(latest.audio),
            )
        return latest
