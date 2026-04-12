import asyncio
import logging

import numpy as np
import sounddevice as sd

from sasayaki.config import Config

logger = logging.getLogger(__name__)

OMNIVOICE_SAMPLE_RATE = 24000


class WhisperPlayback:
    """Plays TTS audio through a specific output device."""

    def __init__(self, config: Config):
        self.config = config
        self._playing = False
        self._device_index = self._resolve_device()
        self._omnivoice_model = None

    def _resolve_device(self) -> int | None:
        """Find output device index by name."""
        name = self.config.tts_output_device
        if not name:
            return None
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if (
                name.lower() in dev["name"].lower()
                and dev["max_output_channels"] > 0
            ):
                logger.info(
                    "TTS output device: %s (index %d)",
                    dev["name"], i,
                )
                return i
        logger.warning(
            "TTS output device not found: %r", name
        )
        return None

    def _get_omnivoice(self):
        """Lazy-load OmniVoice model."""
        if self._omnivoice_model is None:
            import torch
            from omnivoice import OmniVoice

            self._omnivoice_model = OmniVoice.from_pretrained(
                self.config.tts_omnivoice_model,
                device_map="cpu",
                dtype=torch.float32,
            )
            device = "cpu"
            logger.info(
                "OmniVoice loaded (device=%s)", device
            )
        return self._omnivoice_model

    async def speak(self, text: str) -> bool:
        """Convert text to speech and play it."""
        if self._playing or not text:
            return False
        self._playing = True
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, self._generate_and_play, text
            )
            return True
        except Exception:
            logger.exception("TTS playback failed")
            return False
        finally:
            self._playing = False

    def _generate_and_play(self, text: str):
        model = self._get_omnivoice()
        audio = model.generate(
            text=text,
            instruct=self.config.tts_omnivoice_instruct,
            speed=self.config.tts_omnivoice_speed,
        )
        # audio is a list of tensors, shape (1, T)
        waveform = audio[0].squeeze(0).cpu().numpy()
        waveform = np.asarray(
            waveform, dtype=np.float32
        )
        waveform = waveform * self.config.tts_volume

        # Resample to device native rate to avoid
        # crackling on headphones
        play_rate = OMNIVOICE_SAMPLE_RATE
        if self._device_index is not None:
            dev_info = sd.query_devices(
                self._device_index, "output"
            )
            native_rate = int(
                dev_info["default_samplerate"]
            )
            if native_rate != OMNIVOICE_SAMPLE_RATE:
                import resampy
                waveform = resampy.resample(
                    waveform,
                    OMNIVOICE_SAMPLE_RATE,
                    native_rate,
                )
                play_rate = native_rate

        sd.play(
            waveform,
            samplerate=play_rate,
            device=self._device_index,
        )
        sd.wait()
