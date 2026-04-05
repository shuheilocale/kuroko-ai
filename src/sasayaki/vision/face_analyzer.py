"""Face analysis using MediaPipe FaceLandmarker (tasks API).

Detects emotions, nods, and expression changes using blendshapes
and face landmarks from the FaceLandmarker model.
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

logger = logging.getLogger(__name__)

NOSE_TIP = 1
MODEL_PATH = Path(__file__).resolve().parents[3] / "models" / "face_landmarker.task"


@dataclass
class EmotionScores:
    """Emotion estimation scores (0.0 - 1.0)."""
    joy: float = 0.0
    surprise: float = 0.0
    concern: float = 0.0
    neutral: float = 1.0

    @property
    def dominant(self) -> str:
        scores = {
            "joy": self.joy,
            "surprise": self.surprise,
            "concern": self.concern,
            "neutral": self.neutral,
        }
        return max(scores, key=scores.get)


@dataclass
class FaceState:
    """Current state of face analysis."""
    detected: bool = False
    emotions: EmotionScores = field(default_factory=EmotionScores)
    nodding: bool = False
    nod_count: int = 0
    expression_changed: bool = False
    expression_change_detail: str = ""
    timestamp: float = 0.0
    face_crop: np.ndarray | None = None  # Small RGB crop of face


class FaceAnalyzer:
    """Analyzes faces in video frames using MediaPipe FaceLandmarker."""

    def __init__(self):
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Face landmarker model not found: {MODEL_PATH}\n"
                "Download it with:\n"
                "  curl -L -o models/face_landmarker.task "
                "https://storage.googleapis.com/mediapipe-models/"
                "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
            )

        base_options = mp.tasks.BaseOptions(
            model_asset_path=str(MODEL_PATH)
        )
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_faces=1,
            output_face_blendshapes=True,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
        )
        self._landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(
            options
        )

        # Nod detection state
        self._nose_y_history: deque[float] = deque(maxlen=30)
        self._nod_count = 0
        self._last_nod_time = 0.0
        self._nod_state = "idle"

        # Expression change detection
        self._prev_dominant = "neutral"
        self._emotion_stable_since = 0.0

    def analyze(self, frame: np.ndarray) -> FaceState:
        """Analyze an RGB frame and return face state.

        Splits the frame into overlapping tiles to detect small faces
        in large screen captures.
        """
        now = time.monotonic()

        result, tile = self._detect_in_tiles(frame)

        if not result or not result.face_landmarks:
            return FaceState(timestamp=now)

        landmarks = result.face_landmarks[0]
        th, tw = tile.shape[:2]

        # Emotion from blendshapes
        emotions = EmotionScores()
        if result.face_blendshapes:
            emotions = self._emotions_from_blendshapes(
                result.face_blendshapes[0]
            )

        # Crop face from tile
        face_crop = self._crop_face(tile, landmarks)

        # Nod detection from nose tip
        nose_y = landmarks[NOSE_TIP].y * th
        nodding = self._detect_nod(nose_y, now)

        # Expression change
        expression_changed, change_detail = self._detect_expression_change(
            emotions, now
        )

        return FaceState(
            detected=True,
            emotions=emotions,
            nodding=nodding,
            nod_count=self._nod_count,
            expression_changed=expression_changed,
            expression_change_detail=change_detail,
            timestamp=now,
            face_crop=face_crop,
        )

    def _detect_in_tiles(self, frame: np.ndarray):
        """Split frame into 2x2 overlapping tiles and detect in each.

        Returns (result, tile_image) or (None, None).
        """
        h, w = frame.shape[:2]

        # First try full frame (works if face is large enough)
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=np.ascontiguousarray(frame),
        )
        result = self._landmarker.detect(mp_image)
        if result.face_landmarks:
            return result, frame

        # Split into 2x2 tiles with 25% overlap
        tile_h, tile_w = h // 2, w // 2
        overlap_h, overlap_w = tile_h // 4, tile_w // 4
        tiles = [
            (0, 0, tile_w + overlap_w, tile_h + overlap_h),
            (tile_w - overlap_w, 0, w, tile_h + overlap_h),
            (0, tile_h - overlap_h, tile_w + overlap_w, h),
            (tile_w - overlap_w, tile_h - overlap_h, w, h),
        ]

        for x1, y1, x2, y2 in tiles:
            x2 = min(x2, w)
            y2 = min(y2, h)
            tile = frame[y1:y2, x1:x2]
            mp_tile = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=np.ascontiguousarray(tile),
            )
            result = self._landmarker.detect(mp_tile)
            if result.face_landmarks:
                return result, tile

        return None, None

    def _crop_face(
        self, tile: np.ndarray, landmarks
    ) -> np.ndarray | None:
        """Crop a small region around the face from the tile."""
        h, w = tile.shape[:2]
        xs = [lm.x * w for lm in landmarks]
        ys = [lm.y * h for lm in landmarks]
        x_min, x_max = int(min(xs)), int(max(xs))
        y_min, y_max = int(min(ys)), int(max(ys))

        # Add margin
        margin_x = int((x_max - x_min) * 0.3)
        margin_y = int((y_max - y_min) * 0.3)
        x1 = max(0, x_min - margin_x)
        y1 = max(0, y_min - margin_y)
        x2 = min(w, x_max + margin_x)
        y2 = min(h, y_max + margin_y)

        crop = tile[y1:y2, x1:x2]
        if crop.size == 0:
            return None

        # Resize to small thumbnail (96px height)
        scale = 96 / max(crop.shape[0], 1)
        thumb = cv2.resize(crop, None, fx=scale, fy=scale)
        return thumb

    def _emotions_from_blendshapes(self, blendshapes) -> EmotionScores:
        """Map MediaPipe blendshapes to emotion scores."""
        bs = {}
        for b in blendshapes:
            bs[b.category_name] = b.score

        # Joy: mouth smile + cheek raise
        mouth_smile_l = bs.get("mouthSmileLeft", 0)
        mouth_smile_r = bs.get("mouthSmileRight", 0)
        cheek_squint_l = bs.get("cheekSquintLeft", 0)
        cheek_squint_r = bs.get("cheekSquintRight", 0)
        joy = min(1.0, (mouth_smile_l + mouth_smile_r) / 2
                  + (cheek_squint_l + cheek_squint_r) / 4)

        # Surprise: brow raise + eye wide + jaw open
        brow_inner_up = bs.get("browInnerUp", 0)
        brow_outer_up_l = bs.get("browOuterUpLeft", 0)
        brow_outer_up_r = bs.get("browOuterUpRight", 0)
        eye_wide_l = bs.get("eyeWideLeft", 0)
        eye_wide_r = bs.get("eyeWideRight", 0)
        jaw_open = bs.get("jawOpen", 0)
        surprise = min(1.0,
            (brow_inner_up + brow_outer_up_l + brow_outer_up_r) / 3
            + (eye_wide_l + eye_wide_r) / 4
            + jaw_open * 0.3
        )

        # Concern: brow down + mouth frown
        brow_down_l = bs.get("browDownLeft", 0)
        brow_down_r = bs.get("browDownRight", 0)
        mouth_frown_l = bs.get("mouthFrownLeft", 0)
        mouth_frown_r = bs.get("mouthFrownRight", 0)
        concern = min(1.0,
            (brow_down_l + brow_down_r) / 2
            + (mouth_frown_l + mouth_frown_r) / 4
        )

        max_emotion = max(joy, surprise, concern)
        neutral = max(0.0, 1.0 - max_emotion)

        return EmotionScores(
            joy=round(joy, 2),
            surprise=round(surprise, 2),
            concern=round(concern, 2),
            neutral=round(neutral, 2),
        )

    def _detect_nod(self, nose_y: float, now: float) -> bool:
        """Detect head nods from nose tip vertical movement."""
        self._nose_y_history.append(nose_y)

        if len(self._nose_y_history) < 5:
            return False

        recent = list(self._nose_y_history)
        velocities = [recent[i] - recent[i-1] for i in range(1, len(recent))]
        recent_vel = velocities[-3:]
        avg_vel = sum(recent_vel) / len(recent_vel)
        threshold = 1.5

        if self._nod_state == "idle" and avg_vel > threshold:
            self._nod_state = "down"
        elif self._nod_state == "down" and avg_vel < -threshold:
            self._nod_state = "up"
        elif self._nod_state == "up" and abs(avg_vel) < threshold:
            if now - self._last_nod_time > 0.3:
                self._nod_count += 1
                self._last_nod_time = now
                self._nod_state = "idle"
                logger.debug("Nod detected (count=%d)", self._nod_count)
                return True
            self._nod_state = "idle"

        return False

    def _detect_expression_change(
        self, emotions: EmotionScores, now: float
    ) -> tuple[bool, str]:
        """Detect sudden expression changes."""
        current_dominant = emotions.dominant
        changed = False
        detail = ""

        if current_dominant != self._prev_dominant:
            if self._emotion_stable_since == 0.0:
                self._emotion_stable_since = now
            elif now - self._emotion_stable_since > 0.5:
                LABEL_JP = {
                    "joy": "喜び",
                    "surprise": "驚き",
                    "concern": "困惑",
                    "neutral": "平常",
                }
                prev_jp = LABEL_JP.get(
                    self._prev_dominant, self._prev_dominant
                )
                curr_jp = LABEL_JP.get(current_dominant, current_dominant)
                detail = f"{prev_jp} → {curr_jp}"
                changed = True
                self._prev_dominant = current_dominant
                self._emotion_stable_since = 0.0
                logger.info("Expression change: %s", detail)
        else:
            self._emotion_stable_since = 0.0

        return changed, detail

    def close(self):
        self._landmarker.close()
