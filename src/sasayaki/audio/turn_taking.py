import logging

import numpy as np

from sasayaki.config import Config

logger = logging.getLogger(__name__)

MAAI_CHUNK_SIZE = 160  # 10ms at 16kHz


class TurnTakingMonitor:
    """Wraps MaAI for real-time turn-taking prediction."""

    def __init__(self, config: Config):
        self.config = config
        self._mic_remainder = np.array([], dtype=np.float32)
        self._sys_remainder = np.array([], dtype=np.float32)
        self._maai = None
        self._mic_input = None
        self._sys_input = None
        self._last_result: dict = {}

    def start(self):
        from maai import Maai, MaaiInput

        self._mic_input = MaaiInput.Chunk()
        self._sys_input = MaaiInput.Chunk()
        self._maai = Maai(
            mode="vap",
            lang="jp",
            frame_rate=self.config.maai_frame_rate,
            audio_ch1=self._mic_input,
            audio_ch2=self._sys_input,
            device=self.config.maai_device,
        )
        self._maai.start()
        logger.info(
            "MaAI started (frame_rate=%d, device=%s)",
            self.config.maai_frame_rate,
            self.config.maai_device,
        )

    def feed_mic(self, frame: np.ndarray):
        """Feed a 512-sample mic frame."""
        self._feed_channel(frame, self._mic_input, is_mic=True)

    def feed_system(self, frame: np.ndarray):
        """Feed a 512-sample system frame."""
        self._feed_channel(
            frame, self._sys_input, is_mic=False
        )

    def _feed_channel(self, frame, maai_input, *, is_mic: bool):
        if maai_input is None:
            return
        remainder = (
            self._mic_remainder if is_mic
            else self._sys_remainder
        )
        if len(remainder) > 0:
            data = np.concatenate([remainder, frame])
        else:
            data = frame

        offset = 0
        while offset + MAAI_CHUNK_SIZE <= len(data):
            chunk = data[offset:offset + MAAI_CHUNK_SIZE]
            maai_input.put_chunk(chunk)
            offset += MAAI_CHUNK_SIZE

        new_remainder = data[offset:]
        if is_mic:
            self._mic_remainder = new_remainder
        else:
            self._sys_remainder = new_remainder

    def get_prediction(self) -> dict:
        """Return latest turn-taking prediction.

        Returns dict with 'p_now' and 'p_future' floats.
        """
        if self._maai is None:
            return {"p_now": 0.0, "p_future": 0.0}
        try:
            result = self._maai.get_result()
            if result is not None:
                self._last_result = result
        except Exception:
            logger.debug("MaAI get_result error", exc_info=True)

        return self._normalize(self._last_result)

    def _normalize(self, result: dict) -> dict:
        """Extract p_now/p_future as simple floats.

        MaAI returns [ch1_prob, ch2_prob] lists.
        ch1 = mic (self), ch2 = system (partner).
        We use ch1 (probability that self should speak next).
        """
        p_now = result.get("p_now", 0.0)
        p_future = result.get("p_future", 0.0)
        if isinstance(p_now, (list, tuple)):
            p_now = p_now[0] if p_now else 0.0
        if isinstance(p_future, (list, tuple)):
            p_future = p_future[0] if p_future else 0.0
        return {
            "p_now": float(p_now),
            "p_future": float(p_future),
        }

    def stop(self):
        if self._maai is not None:
            try:
                self._maai.stop()
            except Exception:
                logger.debug("MaAI stop error", exc_info=True)
            self._maai = None
        logger.info("MaAI stopped")
