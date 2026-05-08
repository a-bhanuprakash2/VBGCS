# ═══════════════════════════════════════════════════════════════════════════════
#  hand_detector.py  v4.0
# ═══════════════════════════════════════════════════════════════════════════════
import cv2
import mediapipe as mp
import numpy as np


class HandDetector:
    def __init__(self, max_hands=1, detection_confidence=0.82, tracking_confidence=0.82):
        self.mp_hands = mp.solutions.hands
        self.hands    = self.mp_hands.Hands(
            static_image_mode       = False,
            max_num_hands           = max_hands,
            model_complexity        = 1,
            min_detection_confidence= detection_confidence,
            min_tracking_confidence = tracking_confidence,
        )
        self.mp_draw = mp.solutions.drawing_utils
        # Stylised landmark drawing specs
        self._lm_spec = self.mp_draw.DrawingSpec(
            color=(0, 220, 255), thickness=2, circle_radius=4)
        self._cn_spec = self.mp_draw.DrawingSpec(
            color=(0, 170, 100), thickness=2)
        self.results  = None

    # ─────────────────────────────────────────────────────────────────────────
    def find_hands(self, frame, draw=True):
        """Detect hands and optionally draw stylised skeleton. Returns frame."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        self.results = self.hands.process(rgb)
        rgb.flags.writeable = True

        if self.results.multi_hand_landmarks:
            for hlm in self.results.multi_hand_landmarks:
                if draw:
                    self.mp_draw.draw_landmarks(
                        frame, hlm,
                        self.mp_hands.HAND_CONNECTIONS,
                        self._lm_spec, self._cn_spec)
        return frame

    # ─────────────────────────────────────────────────────────────────────────
    def get_landmark_positions(self, frame):
        """Returns list of 21 (x, y) pixel tuples for the first detected hand."""
        positions = []
        h, w, _ = frame.shape
        if self.results and self.results.multi_hand_landmarks:
            for hlm in self.results.multi_hand_landmarks:
                for lm in hlm.landmark:
                    positions.append((int(lm.x * w), int(lm.y * h)))
                break          # only first hand
        return positions

    # ─────────────────────────────────────────────────────────────────────────
    def get_palm_center(self, frame):
        """Returns (cx, cy) pixel centroid of wrist + four MCP joints, or None."""
        lm = self.get_landmark_positions(frame)
        if not lm:
            return None
        anchors = [lm[0], lm[5], lm[9], lm[13], lm[17]]   # WRIST + MCPs
        cx = int(sum(p[0] for p in anchors) / len(anchors))
        cy = int(sum(p[1] for p in anchors) / len(anchors))
        return cx, cy

    # ─────────────────────────────────────────────────────────────────────────
    def get_hand_bbox(self, frame):
        """Returns (x1, y1, x2, y2) bounding box with 20 px padding, or None."""
        lm = self.get_landmark_positions(frame)
        if not lm:
            return None
        xs = [p[0] for p in lm]
        ys = [p[1] for p in lm]
        pad = 20
        return (max(0, min(xs) - pad), max(0, min(ys) - pad),
                min(frame.shape[1], max(xs) + pad),
                min(frame.shape[0], max(ys) + pad))

    # ─────────────────────────────────────────────────────────────────────────
    def hand_present(self):
        return bool(self.results and self.results.multi_hand_landmarks)
