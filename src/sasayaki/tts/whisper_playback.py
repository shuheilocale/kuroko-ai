import asyncio
import logging

import numpy as np
import sounddevice as sd

from sasayaki.config import Config

logger = logging.getLogger(__name__)

OMNIVOICE_SAMPLE_RATE = 24000


def _make_chime(
    sample_rate: int,
    freq: float = 880.0,
    duration: float = 0.06,
    gain: float = 0.18,
) -> np.ndarray:
    """Short cosine-windowed sine 'ting' to alert the user before a
    whisper. Same sample rate as the speech that follows so we can
    concatenate without resampling glitches."""
    n = int(sample_rate * duration)
    t = np.arange(n, dtype=np.float32) / sample_rate
    wave = np.sin(2.0 * np.pi * freq * t)
    fade_n = max(1, int(sample_rate * 0.01))
    if 2 * fade_n < n:
        env = np.ones(n, dtype=np.float32)
        env[:fade_n] = np.linspace(0.0, 1.0, fade_n, dtype=np.float32)
        env[-fade_n:] = np.linspace(1.0, 0.0, fade_n, dtype=np.float32)
        wave *= env
    return (wave * gain).astype(np.float32)


class WhisperPlayback:
    """Plays TTS audio through a specific output device."""

    def __init__(self, config: Config):
        self.config = config
        self._playing = False
        self._device_index = self._resolve_device()
        self._omnivoice_model = None
        # Pre-encoded reference for voice cloning. Populated lazily after
        # the model is loaded; reused across syntheses so we don't pay
        # the encode cost per whisper.
        self._voice_clone_prompt = None

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

            requested = self.config.tts_omnivoice_device
            if requested == "auto":
                device = (
                    "mps" if torch.backends.mps.is_available() else "cpu"
                )
            else:
                device = requested
            self._omnivoice_model = OmniVoice.from_pretrained(
                self.config.tts_omnivoice_model,
                device_map=device,
                dtype=torch.float32,
            )
            logger.info(
                "OmniVoice loaded (device=%s)", device
            )
            self._build_voice_clone_prompt()
        return self._omnivoice_model

    def _build_voice_clone_prompt(self) -> None:
        """Encode the configured reference audio once so subsequent
        syntheses skip the per-call ref encode cost. Silently no-ops
        when the user hasn't configured a reference.

        Loads the audio via soundfile and hands OmniVoice a
        (waveform, sample_rate) tuple. Going through OmniVoice's
        string-path branch hits torchaudio, which now requires the
        optional torchcodec dependency we don't pull in.
        """
        ref_audio_path = self.config.tts_omnivoice_ref_audio
        if not ref_audio_path:
            return
        ref_text = self.config.tts_omnivoice_ref_text or None
        try:
            import soundfile as sf
            import torch

            wav_np, sr = sf.read(ref_audio_path, dtype="float32")
            if wav_np.ndim == 2:  # stereo → mono
                wav_np = wav_np.mean(axis=1)
            wav = torch.from_numpy(wav_np).unsqueeze(0)  # (1, T)
            self._voice_clone_prompt = (
                self._omnivoice_model.create_voice_clone_prompt(
                    ref_audio=(wav, sr),
                    ref_text=ref_text,
                )
            )
            logger.info(
                "Voice clone prompt ready (ref_audio=%s, %.1fs)",
                ref_audio_path,
                wav.shape[-1] / sr,
            )
        except Exception:
            logger.exception(
                "Voice clone prompt build failed, "
                "falling back to instruct mode"
            )
            self._voice_clone_prompt = None

    async def play_alert(
        self,
        freq: float = 660.0,
        duration: float = 0.10,
        gain: float = 0.20,
    ) -> None:
        """Play a one-shot chime through the same device the whisper
        uses. Non-blocking on the event loop (offloads to a thread).

        Used for emotion alerts and other ambient cues that should
        share the user's headphones, not leak through the Mac speaker.
        """
        if self._playing:
            # Don't talk over an active whisper.
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, self._play_alert_blocking, freq, duration, gain
        )

    def _play_alert_blocking(
        self, freq: float, duration: float, gain: float
    ) -> None:
        play_rate = OMNIVOICE_SAMPLE_RATE
        if self._device_index is not None:
            try:
                dev_info = sd.query_devices(
                    self._device_index, "output"
                )
                play_rate = int(dev_info["default_samplerate"])
            except Exception:
                pass
        chime = _make_chime(
            play_rate, freq=freq, duration=duration, gain=gain
        )
        sd.play(
            chime, samplerate=play_rate, device=self._device_index
        )
        sd.wait()

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
        if self._voice_clone_prompt is not None:
            audio = model.generate(
                text=text,
                voice_clone_prompt=self._voice_clone_prompt,
                speed=self.config.tts_omnivoice_speed,
                num_step=self.config.tts_omnivoice_clone_num_step,
            )
        else:
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

        if self.config.tts_chime_enabled:
            chime_in = _make_chime(play_rate, freq=880, duration=0.06)
            gap_pre = np.zeros(
                int(play_rate * 0.08), dtype=np.float32
            )
            # Lower-pitched, slightly quieter "done" cue so the user
            # can tell the whisper is finished without watching the UI.
            chime_out = _make_chime(
                play_rate, freq=523, duration=0.05, gain=0.13
            )
            gap_post = np.zeros(
                int(play_rate * 0.05), dtype=np.float32
            )
            waveform = np.concatenate(
                [chime_in, gap_pre, waveform, gap_post, chime_out]
            )

        sd.play(
            waveform,
            samplerate=play_rate,
            device=self._device_index,
        )
        sd.wait()
