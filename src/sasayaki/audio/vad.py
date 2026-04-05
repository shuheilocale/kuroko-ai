import asyncio
import logging
import time
from typing import Literal

import numpy as np
import silero_vad
import torch

from sasayaki.config import Config
from sasayaki.types import SpeechSegment

logger = logging.getLogger(__name__)

# Silero VAD expects 16kHz, 512 samples (32ms) per frame
FRAME_SIZE = 512


class VadGate:
    """Detects speech segments using Silero VAD and outputs SpeechSegments."""

    def __init__(
        self,
        config: Config,
        source: Literal["system", "mic"],
        input_queue: asyncio.Queue,
        output_queue: asyncio.Queue,
    ):
        self.config = config
        self.source = source
        self.input_queue = input_queue
        self.output_queue = output_queue

        self.model = silero_vad.load_silero_vad()

        self._buffer = np.array([], dtype=np.float32)
        self._speech_buffer = np.array([], dtype=np.float32)
        self._is_speaking = False
        self._silence_start: float | None = None
        self._speech_start_time: float = 0.0
        self._last_partial_time: float = 0.0

    def _get_speech_prob(self, frame: np.ndarray) -> float:
        tensor = torch.from_numpy(frame)
        with torch.no_grad():
            prob = self.model(tensor, 16000).item()
        return prob

    async def run(self):
        logger.info("VadGate started for %s", self.source)
        while True:
            audio = await self.input_queue.get()
            self._buffer = np.concatenate([self._buffer, audio])

            while len(self._buffer) >= FRAME_SIZE:
                frame = self._buffer[:FRAME_SIZE]
                self._buffer = self._buffer[FRAME_SIZE:]
                await self._process_frame(frame)

    async def _process_frame(self, frame: np.ndarray):
        prob = self._get_speech_prob(frame)
        now = time.monotonic()

        if not self._is_speaking:
            if prob >= self.config.vad_threshold:
                self._is_speaking = True
                self._silence_start = None
                self._speech_start_time = now
                self._last_partial_time = now
                self._speech_buffer = frame.copy()
                logger.debug("[%s] Speech started", self.source)
        else:
            self._speech_buffer = np.concatenate([self._speech_buffer, frame])

            if prob < self.config.vad_threshold:
                if self._silence_start is None:
                    self._silence_start = now
                elif (now - self._silence_start) * 1000 >= self.config.vad_min_silence_ms:
                    # Speech ended
                    await self._emit_segment(is_partial=False)
                    self._is_speaking = False
                    self._silence_start = None
                    logger.debug("[%s] Speech ended", self.source)
            else:
                self._silence_start = None

                # Flush partial for long utterances
                if (
                    now - self._last_partial_time
                    >= self.config.vad_partial_flush_sec
                ):
                    await self._emit_segment(is_partial=True)
                    self._last_partial_time = now

    async def _emit_segment(self, is_partial: bool):
        if len(self._speech_buffer) < FRAME_SIZE:
            return
        segment = SpeechSegment(
            audio=self._speech_buffer.copy(),
            source=self.source,
            is_partial=is_partial,
            timestamp=time.monotonic(),
        )
        await self.output_queue.put(segment)
        if not is_partial:
            self._speech_buffer = np.array([], dtype=np.float32)
