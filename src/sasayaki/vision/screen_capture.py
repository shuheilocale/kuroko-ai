import logging
import time

import cv2
import mss
import numpy as np

logger = logging.getLogger(__name__)

MAX_WIDTH = 1920


class ScreenCapture:
    """Captures a region of the screen at a target FPS."""

    def __init__(self, monitor: int = 1, fps: float = 2.0):
        self._monitor = monitor
        self._interval = 1.0 / fps
        self._sct = mss.mss()
        self._last_capture = 0.0
        # Region: (x, y, w, h) relative to monitor. (0,0,0,0) = full
        self._region: tuple[int, int, int, int] = (0, 0, 0, 0)

    @property
    def monitor_index(self) -> int:
        return self._monitor

    @monitor_index.setter
    def monitor_index(self, value: int):
        self._monitor = value

    @property
    def region(self) -> tuple[int, int, int, int]:
        return self._region

    @region.setter
    def region(self, value: tuple[int, int, int, int]):
        self._region = value

    @staticmethod
    def list_monitors() -> list[dict]:
        """Return available monitors with index and dimensions."""
        with mss.mss() as sct:
            return [
                {
                    "index": i,
                    "width": m["width"],
                    "height": m["height"],
                }
                for i, m in enumerate(sct.monitors)
                if i > 0
            ]

    def get_monitor_size(self) -> tuple[int, int]:
        """Return (width, height) of current monitor."""
        monitors = self._sct.monitors
        idx = self._monitor if self._monitor < len(monitors) else 1
        mon = monitors[idx]
        return mon["width"], mon["height"]

    def grab(self) -> np.ndarray | None:
        """Grab a frame. Returns RGB numpy array or None."""
        now = time.monotonic()
        if now - self._last_capture < self._interval:
            return None

        self._last_capture = now
        monitors = self._sct.monitors
        idx = self._monitor if self._monitor < len(monitors) else 1
        mon = monitors[idx]

        x, y, w, h = self._region
        if w > 0 and h > 0:
            # Capture specific region
            grab_area = {
                "left": mon["left"] + x,
                "top": mon["top"] + y,
                "width": min(w, mon["width"] - x),
                "height": min(h, mon["height"] - y),
            }
        else:
            grab_area = mon

        screenshot = self._sct.grab(grab_area)
        bgra = np.frombuffer(
            screenshot.raw, dtype=np.uint8
        ).reshape(screenshot.height, screenshot.width, 4)
        frame = cv2.cvtColor(bgra, cv2.COLOR_BGRA2RGB)

        # Resize if too large
        if frame.shape[1] > MAX_WIDTH:
            scale = MAX_WIDTH / frame.shape[1]
            frame = cv2.resize(frame, None, fx=scale, fy=scale)

        return frame

    def close(self):
        self._sct.close()
