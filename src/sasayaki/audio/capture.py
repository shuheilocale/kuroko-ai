import asyncio
import logging
from typing import Literal

import numpy as np
import sounddevice as sd

from sasayaki.config import Config

logger = logging.getLogger(__name__)


def find_device_index(name: str) -> int | None:
    """Find audio device index by partial name match."""
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if name.lower() in dev["name"].lower() and dev["max_input_channels"] > 0:
            return i
    return None


class AudioCapture:
    """Captures audio from a named input device and pushes frames to a queue."""

    def __init__(
        self,
        config: Config,
        source: Literal["system", "mic"],
        queue: asyncio.Queue,
        loop: asyncio.AbstractEventLoop,
    ):
        self.config = config
        self.source = source
        self.queue = queue
        self.loop = loop

        device_name = (
            config.system_audio_device if source == "system" else config.mic_device
        )
        if device_name:
            self.device_index = find_device_index(device_name)
            if self.device_index is None:
                raise RuntimeError(
                    f"Audio device not found: {device_name!r}. "
                    f"Available: {[d['name'] for d in sd.query_devices() if d['max_input_channels'] > 0]}"
                )
        else:
            self.device_index = None  # Use system default

        self.stream: sd.InputStream | None = None
        self.resolved_device_name: str = ""

    def _callback(self, indata: np.ndarray, frames: int, time_info, status):
        if status:
            logger.warning("Audio callback status: %s", status)
        # Convert to mono float32, copy to avoid buffer reuse
        audio = indata[:, 0].copy().astype(np.float32)
        try:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, audio)
        except asyncio.QueueFull:
            pass  # Drop frame if consumer is behind

    def start(self):
        device_info = sd.query_devices(self.device_index, "input")
        self.resolved_device_name = device_info["name"]
        native_sr = int(device_info["default_samplerate"])
        logger.info(
            "Opening %s device: %s (native %dHz, target %dHz)",
            self.source,
            self.resolved_device_name,
            native_sr,
            self.config.sample_rate,
        )

        self.stream = sd.InputStream(
            device=self.device_index,
            samplerate=self.config.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=512,  # 32ms at 16kHz
            callback=self._callback,
        )
        self.stream.start()

    def stop(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
