# ═══════════════════════════════════════════════════════════════════════════════
#  gesture_controller.py  v4.0  ─  Premium Gesture Engine
#  Fixes: volume thumb detection, mute gesture, smartboard erase/clear split
# ═══════════════════════════════════════════════════════════════════════════════
import pyautogui
import numpy as np
import subprocess, platform, time, math, os, datetime

# ── MediaPipe landmark indices ───────────────────────────────────────────────
WRIST = 0
THUMB_CMC, THUMB_MCP_J, THUMB_IP, THUMB_TIP       = 1, 2, 3, 4
INDEX_MCP,  INDEX_PIP,  INDEX_DIP,  INDEX_FINGER_TIP  = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_FINGER_TIP = 9, 10, 11, 12
RING_MCP,   RING_PIP,   RING_DIP,   RING_FINGER_TIP   = 13, 14, 15, 16
PINKY_MCP,  PINKY_PIP,  PINKY_DIP,  PINKY_TIP         = 17, 18, 19, 20


class GestureController:
    def __init__(self, screen_w, screen_h, cam_w, cam_h, smoothing=4):
        self.screen_w, self.screen_h = screen_w, screen_h
        self.cam_w, self.cam_h = cam_w, cam_h
        self.smoothing = smoothing
        self.prev_x, self.prev_y = 0, 0

        # ── App state ──────────────────────────────────────────────────────────
        self.smartboard_open   = False
        self.peace_start_time  = None
        self.palm_start_time   = None
        self.fist_start_time   = None
        self._screenshot_start = None

        self.PEACE_HOLD = 1.5
        self.PALM_HOLD  = 2.0
        self.FIST_HOLD  = 2.0
        self.SS_HOLD    = 1.5

        # ── Cooldown counters (frames) ─────────────────────────────────────────
        self.cd = dict(toggle=0, mute=0, clear=0, color=0, click=0)

        # ── Volume rate-limiting ───────────────────────────────────────────────
        self._vol_last    = 0.0
        self.VOL_INTERVAL = 0.10   # seconds between volume key presses

        pyautogui.FAILSAFE = False

    # ═══════════════════════════════════════════════════════════════════════════
    #  GEOMETRY HELPERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _dist(self, lm, a, b):
        return math.hypot(lm[a][0] - lm[b][0], lm[a][1] - lm[b][1])

    def _palm_len(self, lm):
        """Wrist → Middle MCP distance as normalisation reference."""
        return self._dist(lm, WRIST, MIDDLE_MCP) + 1e-6

    def _is_up(self, lm, tip, pip):
        """Finger is extended when its tip is farther from wrist than its PIP joint."""
        return self._dist(lm, WRIST, tip) > self._dist(lm, WRIST, pip) * 1.18

    def _get_thumb_dir(self, lm):
        """
        Returns 'up' / 'down' / 'neutral'.
        Uses palm-axis dot-product, requires thumb to be clearly abducted.
        """
        pl = self._palm_len(lm)
        # Thumb must be meaningfully separated from index base
        if self._dist(lm, THUMB_TIP, INDEX_MCP) < pl * 0.52:
            return "neutral"

        # Palm orientation vector (wrist → middle MCP)
        vx = lm[MIDDLE_MCP][0] - lm[WRIST][0]
        vy = lm[MIDDLE_MCP][1] - lm[WRIST][1]
        # Thumb direction vector (MCP → TIP for stability)
        tx = lm[THUMB_TIP][0] - lm[THUMB_MCP_J][0]
        ty = lm[THUMB_TIP][1] - lm[THUMB_MCP_J][1]

        denom = math.hypot(vx, vy) * math.hypot(tx, ty)
        if denom < 1e-6:
            return "neutral"
        dot = (vx * tx + vy * ty) / denom

        if dot > 0.40:   return "up"
        if dot < -0.48:  return "down"
        return "neutral"

    # ═══════════════════════════════════════════════════════════════════════════
    #  GESTURE CLASSIFIERS  (all return bool)
    # ═══════════════════════════════════════════════════════════════════════════

    def is_index_only(self, lm):
        """☝  Only index finger extended."""
        return (     self._is_up(lm, INDEX_FINGER_TIP,  INDEX_PIP)  and
                not  self._is_up(lm, MIDDLE_FINGER_TIP, MIDDLE_PIP) and
                not  self._is_up(lm, RING_FINGER_TIP,   RING_PIP)   and
                not  self._is_up(lm, PINKY_TIP,         PINKY_PIP))

    def is_peace(self, lm):
        """✌  Index + Middle extended, Ring + Pinky curled."""
        return (     self._is_up(lm, INDEX_FINGER_TIP,  INDEX_PIP)  and
                     self._is_up(lm, MIDDLE_FINGER_TIP, MIDDLE_PIP) and
                not  self._is_up(lm, RING_FINGER_TIP,   RING_PIP)   and
                not  self._is_up(lm, PINKY_TIP,         PINKY_PIP))

    def is_three_fingers(self, lm):
        """🤟  Index + Middle + Ring up, Pinky down."""
        return (     self._is_up(lm, INDEX_FINGER_TIP,  INDEX_PIP)  and
                     self._is_up(lm, MIDDLE_FINGER_TIP, MIDDLE_PIP) and
                     self._is_up(lm, RING_FINGER_TIP,   RING_PIP)   and
                not  self._is_up(lm, PINKY_TIP,         PINKY_PIP))

    def is_open_palm(self, lm):
        """🖐  All four fingers extended."""
        return all([self._is_up(lm, INDEX_FINGER_TIP,  INDEX_PIP),
                    self._is_up(lm, MIDDLE_FINGER_TIP, MIDDLE_PIP),
                    self._is_up(lm, RING_FINGER_TIP,   RING_PIP),
                    self._is_up(lm, PINKY_TIP,         PINKY_PIP)])

    def is_fist(self, lm):
        """✊  All four fingers curled."""
        return not any([self._is_up(lm, INDEX_FINGER_TIP,  INDEX_PIP),
                        self._is_up(lm, MIDDLE_FINGER_TIP, MIDDLE_PIP),
                        self._is_up(lm, RING_FINGER_TIP,   RING_PIP),
                        self._is_up(lm, PINKY_TIP,         PINKY_PIP)])

    def is_pinky_only(self, lm):
        """🤙  Only pinky extended — used for mute toggle."""
        return (     self._is_up(lm, PINKY_TIP,         PINKY_PIP)  and
                not  self._is_up(lm, INDEX_FINGER_TIP,  INDEX_PIP)  and
                not  self._is_up(lm, MIDDLE_FINGER_TIP, MIDDLE_PIP) and
                not  self._is_up(lm, RING_FINGER_TIP,   RING_PIP))

    def is_rock(self, lm):
        """🤘  Index + Pinky up, Middle + Ring down."""
        return (     self._is_up(lm, INDEX_FINGER_TIP,  INDEX_PIP)  and
                     self._is_up(lm, PINKY_TIP,         PINKY_PIP)  and
                not  self._is_up(lm, MIDDLE_FINGER_TIP, MIDDLE_PIP) and
                not  self._is_up(lm, RING_FINGER_TIP,   RING_PIP))

    def is_thumbs_up(self, lm):
        """👍  Fist with thumb pointing along palm axis."""
        return self.is_fist(lm) and self._get_thumb_dir(lm) == "up"

    def is_thumbs_down(self, lm):
        """👎  Fist with thumb pointing against palm axis."""
        return self.is_fist(lm) and self._get_thumb_dir(lm) == "down"

    def is_index_thumb_pinch(self, lm):
        """👌  Index tip and thumb tip within ~36 px of each other."""
        return self._dist(lm, THUMB_TIP, INDEX_FINGER_TIP) < 36

    def is_middle_thumb_pinch(self, lm):
        """🤏  Middle tip and thumb tip within ~36 px of each other."""
        return self._dist(lm, THUMB_TIP, MIDDLE_FINGER_TIP) < 36

    # ═══════════════════════════════════════════════════════════════════════════
    #  COOLDOWN TICK  (call once per frame)
    # ═══════════════════════════════════════════════════════════════════════════

    def tick(self):
        for k in self.cd:
            if self.cd[k] > 0:
                self.cd[k] -= 1

    # ═══════════════════════════════════════════════════════════════════════════
    #  ACTION HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════

    # ── Volume (continuous while holding thumbs up/down) ──────────────────────
    def check_volume(self, lm):
        """Returns 'up' / 'down' / None. No gesture check — caller must guard."""
        direction = self._get_thumb_dir(lm)
        now = time.time()
        if now - self._vol_last > self.VOL_INTERVAL:
            if direction == "up":
                pyautogui.press("volumeup");   self._vol_last = now; return "up"
            if direction == "down":
                pyautogui.press("volumedown"); self._vol_last = now; return "down"
        return None

    # ── Smartboard Toggle  ✌ hold ─────────────────────────────────────────────
    def check_smartboard_toggle(self, lm):
        """Returns (is_holding, progress 0→1, just_toggled)."""
        if self.cd["toggle"] > 0:
            return False, 0.0, False
        if self.is_peace(lm):
            if self.peace_start_time is None:
                self.peace_start_time = time.time()
            elapsed = time.time() - self.peace_start_time
            if elapsed >= self.PEACE_HOLD:
                self.smartboard_open   = not self.smartboard_open
                self.peace_start_time  = None
                self.cd["toggle"]      = 55
                return True, 1.0, True
            return True, elapsed / self.PEACE_HOLD, False
        self.peace_start_time = None
        return False, 0.0, False

    # ── Screenshot  3-fingers hold ────────────────────────────────────────────
    def check_screenshot(self, lm):
        """Returns (taken, progress 0→1)."""
        if self._screenshot_start is None:
            self._screenshot_start = time.time()
        elapsed = time.time() - self._screenshot_start
        if elapsed >= self.SS_HOLD:
            self._screenshot_start = None
            ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(os.path.expanduser("~"), "Desktop",
                                f"screenshot_{ts}.png")
            pyautogui.screenshot().save(path)
            return True, 1.0
        return False, elapsed / self.SS_HOLD

    def reset_screenshot(self):
        self._screenshot_start = None

    # ── Open Settings  🖐 hold ────────────────────────────────────────────────
    def check_open_settings(self, lm):
        """Returns (is_holding, progress, done)."""
        if self.palm_start_time is None:
            self.palm_start_time = time.time()
        elapsed = time.time() - self.palm_start_time
        if elapsed >= self.PALM_HOLD:
            self.palm_start_time = None
            if platform.system() == "Windows":
                subprocess.Popen(["explorer", "ms-settings:"])
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", "-a", "System Preferences"])
            return True, 1.0, True
        return True, elapsed / self.PALM_HOLD, False

    def reset_palm(self):
        self.palm_start_time = None

    # ── Open File Explorer  ✊ hold ────────────────────────────────────────────
    def check_open_explorer(self, lm):
        """Returns (is_holding, progress, done)."""
        if self.fist_start_time is None:
            self.fist_start_time = time.time()
        elapsed = time.time() - self.fist_start_time
        if elapsed >= self.FIST_HOLD:
            self.fist_start_time = None
            if platform.system() == "Windows":
                subprocess.Popen(["explorer", "shell:MyComputerFolder"])
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", os.path.expanduser("~")])
            return True, 1.0, True
        return True, elapsed / self.FIST_HOLD, False

    def reset_fist(self):
        self.fist_start_time = None

    # ── Smartboard colour cycle  pinch ────────────────────────────────────────
    def check_board_colour_change(self, lm):
        if self.cd["color"] > 0: return False
        if self.is_index_thumb_pinch(lm):
            self.cd["color"] = 30
            return True
        return False

    # ── Smartboard clear  🤘 rock ─────────────────────────────────────────────
    def check_smartboard_clear(self, lm):
        if self.cd["clear"] > 0: return False
        if self.is_rock(lm):
            self.cd["clear"] = 55
            return True
        return False

    # ── Cursor movement ───────────────────────────────────────────────────────
    def move_cursor(self, lm):
        x, y = lm[INDEX_FINGER_TIP]
        sx = int(np.interp(x, [50, self.cam_w - 50], [0, self.screen_w]))
        sy = int(np.interp(y, [50, self.cam_h - 50], [0, self.screen_h]))
        sx = self.prev_x + (sx - self.prev_x) / self.smoothing
        sy = self.prev_y + (sy - self.prev_y) / self.smoothing
        pyautogui.moveTo(sx, sy)
        self.prev_x, self.prev_y = sx, sy

    # ── Mute toggle  🤙 pinky ─────────────────────────────────────────────────
    def check_mute_toggle(self):
        """Call only after confirming is_pinky_only(). Returns True if toggled."""
        if self.cd["mute"] > 0: return False
        pyautogui.press("volumemute")
        self.cd["mute"] = 75
        return True

    # ── Click & Scroll ────────────────────────────────────────────────────────
    def check_click(self):
        if self.cd["click"] > 0: return
        pyautogui.click()
        self.cd["click"] = 12

    def check_right_click(self):
        pyautogui.rightClick()
        time.sleep(0.2)

    def check_scroll_up(self):
        pyautogui.scroll(4)

    def check_scroll_down(self):
        pyautogui.scroll(-4)
