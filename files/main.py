# ═══════════════════════════════════════════════════════════════════════════════
#  main.py  v4.0  ─  Premium Gesture Controller
#  Fixed: volume, mute gesture, smartboard erase/clear split, reliable flow
# ═══════════════════════════════════════════════════════════════════════════════
import cv2
import pyautogui
import numpy as np
import time

from hand_detector      import HandDetector
from gesture_controller import GestureController
from smartboard         import Smartboard

# ── Resolution ───────────────────────────────────────────────────────────────
CAM_W,  CAM_H  = 640, 480
SCR_W,  SCR_H  = pyautogui.size()

BOARD_WIN  = "Smartboard"
CAMERA_WIN = "✋ Gesture Controller v4.0"

# ── Design tokens ────────────────────────────────────────────────────────────
#  BGR colours
C_BG      = (14, 14, 18)         # panel background
C_TEAL    = (210, 230, 0)        # primary accent  (teal in RGB)
C_ORANGE  = (0, 150, 255)        # secondary accent (orange in RGB)
C_GREEN   = (80, 220, 60)        # positive / active
C_RED     = (60, 60, 255)        # warning / muted
C_PURPLE  = (220, 60, 180)       # screenshot accent
C_WHITE   = (230, 230, 230)
C_DIM     = (90, 90, 90)
C_DARKER  = (40, 40, 45)

PANEL_W   = 140   # right panel width
TOP_H     = 38    # top status bar height
BOT_H     = 80    # bottom legend height


# ═══════════════════════════════════════════════════════════════════════════════
#  PREMIUM UI HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _alpha_rect(frame, x1, y1, x2, y2, color=C_BG, alpha=0.82):
    """Blend a solid colour rectangle over the frame region."""
    roi = frame[y1:y2, x1:x2]
    if roi.size == 0: return
    bg  = np.full_like(roi, color)
    cv2.addWeighted(roi, 1 - alpha, bg, alpha, 0, roi)
    frame[y1:y2, x1:x2] = roi


def _txt(frame, text, pos, scale=0.45, color=C_WHITE, bold=False):
    thick = 2 if bold else 1
    cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX,
                scale, color, thick, cv2.LINE_AA)


def _glow_circle(frame, cx, cy, r, color, inner_color=(255, 255, 255)):
    """Draw a circle with a soft glow halo."""
    dim = tuple(max(0, c // 4) for c in color)
    cv2.circle(frame, (cx, cy), r + 8, dim, -1, cv2.LINE_AA)
    cv2.circle(frame, (cx, cy), r + 3, tuple(c // 2 for c in color), -1, cv2.LINE_AA)
    cv2.circle(frame, (cx, cy), r,     color,       -1, cv2.LINE_AA)
    cv2.circle(frame, (cx, cy), r // 3, inner_color, -1, cv2.LINE_AA)


def _progress_ring(frame, cx, cy, progress, color, radius=34, label=""):
    """Animated arc progress ring."""
    # Background ring
    cv2.ellipse(frame, (cx, cy), (radius, radius), -90, 0, 360,
                C_DARKER, 3, cv2.LINE_AA)
    # Progress arc
    angle = int(360 * min(progress, 1.0))
    cv2.ellipse(frame, (cx, cy), (radius, radius), -90, 0, angle,
                color, 3, cv2.LINE_AA)
    # Percentage text
    pct = f"{int(progress * 100)}%"
    (tw, th), _ = cv2.getTextSize(pct, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
    cv2.putText(frame, pct, (cx - tw // 2, cy + th // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA)
    if label:
        (lw, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.36, 1)
        cv2.putText(frame, label, (cx - lw // 2, cy + radius + 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.36, color, 1, cv2.LINE_AA)


def _separator(frame, y, x1=0, x2=None, color=C_TEAL, alpha=0.4):
    if x2 is None: x2 = frame.shape[1]
    overlay = frame.copy()
    cv2.line(overlay, (x1, y), (x2, y), color, 1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


# ═══════════════════════════════════════════════════════════════════════════════
#  PANEL DRAW FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def draw_top_bar(frame, gesture_name, fps, board_open):
    h, w = frame.shape[:2]
    _alpha_rect(frame, 0, 0, w - PANEL_W, TOP_H, alpha=0.88)
    _separator(frame, TOP_H, 0, w - PANEL_W)

    # App name tag
    cv2.rectangle(frame, (6, 6), (90, TOP_H - 6), C_TEAL, -1)
    _txt(frame, "GESTURE", (10, 20), 0.38, C_BG, bold=True)
    _txt(frame, "CTRL v4", (10, 32), 0.35, C_BG)

    # Gesture label
    _txt(frame, "ACTIVE:", (100, 16), 0.38, C_DIM)
    _txt(frame, gesture_name, (100, 32), 0.50, C_GREEN, bold=True)

    # Board status badge
    badge_col = C_TEAL if board_open else C_DIM
    bx = w - PANEL_W - 120
    cv2.rectangle(frame, (bx, 8), (bx + 100, TOP_H - 8), badge_col, -1)
    label = "BOARD: ON" if board_open else "BOARD: OFF"
    _txt(frame, label, (bx + 5, TOP_H - 12), 0.38, C_BG, bold=True)

    # FPS
    _txt(frame, f"FPS {fps:>3}", (w - PANEL_W - 55, 24), 0.38, C_DIM)


def draw_right_panel(frame, board_open, peace_active, peace_prog,
                     palm_active, palm_prog,
                     fist_active, fist_prog,
                     is_muted, vol_dir):
    h, w = frame.shape[:2]
    x0 = w - PANEL_W

    _alpha_rect(frame, x0, 0, w, h, alpha=0.90)
    cv2.line(frame, (x0, 0), (x0, h), C_TEAL, 1)

    cy = TOP_H + 20

    # ── Board Toggle Icon ─────────────────────────────────────────────────────
    col = C_TEAL if board_open else C_DIM
    cx  = x0 + PANEL_W // 2
    # Board icon (monitor)
    cv2.rectangle(frame, (cx-18, cy-10), (cx+18, cy+10), col, 2)
    cv2.rectangle(frame, (cx-18, cy-10), (cx+18, cy+10), tuple(c//3 for c in col), -1)
    cv2.circle(frame, (cx, cy), 4, col, -1)
    cv2.rectangle(frame, (cx-6, cy-16), (cx+6, cy-10), col, -1)
    if peace_active and peace_prog < 1.0:
        _progress_ring(frame, cx, cy, peace_prog, C_TEAL, 28, "BOARD")
    else:
        _txt(frame, "✌ BOARD", (cx-26, cy+26), 0.36, col)
        _txt(frame, "ON" if board_open else "OFF", (cx-10, cy+40), 0.38, col)
    cy += 90

    # ── Settings Icon ─────────────────────────────────────────────────────────
    col2 = C_ORANGE if palm_active else C_DIM
    for a in range(0, 360, 60):
        r = np.radians(a)
        px, py = int(cx + 16 * np.cos(r)), int(cy + 16 * np.sin(r))
        cv2.circle(frame, (px, py), 3, col2, -1)
    cv2.circle(frame, (cx, cy), 8, col2, 2)
    cv2.circle(frame, (cx, cy), 3, col2, -1)
    if palm_active and palm_prog < 1.0:
        _progress_ring(frame, cx, cy, palm_prog, C_ORANGE, 28, "SETTINGS")
    else:
        _txt(frame, "🖐 SETTINGS", (cx - 36, cy + 30), 0.34, col2)
    cy += 90

    # ── Explorer Icon ─────────────────────────────────────────────────────────
    col3 = C_GREEN if fist_active else C_DIM
    cv2.rectangle(frame, (cx-18, cy-12), (cx+18, cy+8), col3, 2)
    cv2.rectangle(frame, (cx-9, cy-6),   (cx+9,  cy+2), col3, 1)
    cv2.rectangle(frame, (cx-4, cy+8),   (cx+4,  cy+14), col3, -1)
    cv2.rectangle(frame, (cx-12,cy+14),  (cx+12, cy+16), col3, -1)
    if fist_active and fist_prog < 1.0:
        _progress_ring(frame, cx, cy, fist_prog, C_GREEN, 28, "EXPLORER")
    else:
        _txt(frame, "✊ EXPLORER", (cx - 36, cy + 30), 0.34, col3)
    cy += 90

    # ── Mute Indicator ────────────────────────────────────────────────────────
    if is_muted:
        cv2.rectangle(frame, (x0+8, cy-14), (x0+PANEL_W-8, cy+14), C_RED, -1)
        _txt(frame, "🔇 MUTED", (x0+14, cy+5), 0.40, (255,255,255), bold=True)
    else:
        cv2.rectangle(frame, (x0+8, cy-14), (x0+PANEL_W-8, cy+14), C_DARKER, -1)
        _txt(frame, "🔊 SOUND", (x0+14, cy+5), 0.40, C_DIM)
    cy += 40

    # ── Volume Direction ──────────────────────────────────────────────────────
    if vol_dir == "up":
        _txt(frame, "▲ VOL+", (x0+20, cy+8), 0.42, C_GREEN)
    elif vol_dir == "down":
        _txt(frame, "▼ VOL-", (x0+20, cy+8), 0.42, C_ORANGE)


def draw_volume_hud(frame, direction, level, flash):
    if not flash: return
    h, w = frame.shape[:2]
    col  = C_GREEN if direction == "up" else C_ORANGE
    x0, y0, bw, bh = 8, h - BOT_H - 60, 130, 52

    _alpha_rect(frame, x0, y0, x0+bw, y0+bh, C_BG, 0.85)
    cv2.rectangle(frame, (x0, y0), (x0+bw, y0+bh), col, 1)

    icon = "VOL +" if direction == "up" else "VOL -"
    _txt(frame, icon, (x0+8, y0+20), 0.55, col, bold=True)

    bar_max = bw - 14
    bar_w   = int(bar_max * max(0.0, min(1.0, level)))
    cv2.rectangle(frame, (x0+7, y0+28), (x0+7+bar_max, y0+42), C_DARKER, -1)
    cv2.rectangle(frame, (x0+7, y0+28), (x0+7+bar_w,   y0+42), col,      -1)


def draw_screenshot_hud(frame, progress, just_taken):
    h, w = frame.shape[:2]
    if just_taken:
        overlay = frame.copy()
        cv2.rectangle(overlay, (0,0), (w, h), (255,255,255), -1)
        cv2.addWeighted(frame, 0.75, overlay, 0.25, 0, frame)
        cv2.rectangle(frame, (0,0), (w,h), C_TEAL, 4)
        _txt(frame, "✓  SCREENSHOT SAVED",
             (w//2-115, h//2), 0.80, C_TEAL, bold=True)
        return
    if progress > 0.01:
        _progress_ring(frame, w//2, h//2, progress, C_PURPLE, 50, "SCREENSHOT")


def draw_bottom_legend(frame):
    h, w = frame.shape[:2]
    x2   = w - PANEL_W
    y0   = h - BOT_H
    _alpha_rect(frame, 0, y0, x2, h, C_BG, 0.88)
    _separator(frame, y0, 0, x2)

    lines = [
        ("CURSOR MODE",  "☝Index=Move  |  👌Pinch(Idx+Thumb)=Click  |  🤏Pinch(Mid+Thumb)=Scroll"),
        ("SYSTEM",       "👍ThumbUp=Vol+  |  👎ThumbDown=Vol-  |  🤙Pinky=Mute  |  ✌Peace(hold)=Board"),
        ("APPS/CAPTURE", "🖐Palm(hold 2s)=Settings  |  ✊Fist(hold 2s)=Explorer  |  🤟3-Fingers(hold)=Screenshot"),
        ("SMARTBOARD",   "☝Draw  |  🖐OpenPalm=Erase  |  🤘Rock=Clear All  |  👌Pinch=NextColor"),
    ]
    col_labels = [C_TEAL, C_ORANGE, C_PURPLE, C_GREEN]
    for i, (tag, desc) in enumerate(lines):
        y = y0 + 14 + i * 16
        _txt(frame, f"[{tag}]", (8, y), 0.35, col_labels[i], bold=True)
        _txt(frame, desc,       (130, y), 0.33, C_DIM)


def draw_smartboard_mode_overlay(frame, board):
    """Indicator strip when smartboard is open."""
    h, w = frame.shape[:2]
    x2 = w - PANEL_W
    _alpha_rect(frame, 0, TOP_H, x2, TOP_H + 28, (0, 40, 35), 0.85)
    _txt(frame, f"SMARTBOARD ACTIVE  ●  Color: {board.brush_color_name}  ●  "
                f"Brush: {board.brush_size}px  ●  Undo: {len(board._undo_stack)}",
         (10, TOP_H + 18), 0.40, C_TEAL)


# ═══════════════════════════════════════════════════════════════════════════════
#  LANDMARK GLOW OVERLAY
# ═══════════════════════════════════════════════════════════════════════════════

def draw_landmark_glow(frame, lm, gesture_name):
    """Highlight key fingertip with a glow dot matching active gesture."""
    if not lm: return
    tip = lm[8]  # Index tip

    if "Move" in gesture_name or "Draw" in gesture_name:
        col = C_TEAL
    elif "Click" in gesture_name:
        col = C_GREEN
    elif "Vol" in gesture_name:
        col = C_ORANGE
    elif "Erase" in gesture_name:
        col = C_DIM
    elif "Screenshot" in gesture_name:
        col = C_PURPLE
    else:
        col = C_WHITE

    cx, cy = tip
    dim = tuple(max(0, c // 5) for c in col)
    cv2.circle(frame, (cx, cy), 18, dim, -1, cv2.LINE_AA)
    cv2.circle(frame, (cx, cy), 9,  col, -1, cv2.LINE_AA)
    cv2.circle(frame, (cx, cy), 4,  (255, 255, 255), -1, cv2.LINE_AA)


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN LOOP
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAM_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)
    cap.set(cv2.CAP_PROP_FPS, 60)

    detector   = HandDetector(detection_confidence=0.82, tracking_confidence=0.82)
    controller = GestureController(
        screen_w=SCR_W, screen_h=SCR_H,
        cam_w=CAM_W,    cam_h=CAM_H,
        smoothing=4)
    board = Smartboard(width=1920, height=1080)

    # ── State ──────────────────────────────────────────────────────────────────
    current_gesture  = "—"
    vol_direction    = None
    vol_flash_frames = 0
    vol_level        = 0.50
    is_muted         = False
    screenshot_flash = 0
    screenshot_prog  = 0.0
    peace_active, peace_prog = False, 0.0
    palm_active,  palm_prog  = False, 0.0
    fist_active,  fist_prog  = False, 0.0

    fps_counter = 0
    fps_display = 0
    fps_timer   = time.time()

    cv2.namedWindow(CAMERA_WIN, cv2.WINDOW_NORMAL)

    while True:
        ok, frame = cap.read()
        if not ok: break

        frame = cv2.flip(frame, 1)
        frame = detector.find_hands(frame, draw=True)
        lm    = detector.get_landmark_positions(frame)

        # ── FPS ───────────────────────────────────────────────────────────────
        fps_counter += 1
        if time.time() - fps_timer >= 1.0:
            fps_display = fps_counter
            fps_counter = 0
            fps_timer   = time.time()

        # ── Reset per-frame state ─────────────────────────────────────────────
        controller.tick()
        peace_active, peace_prog = False, 0.0
        palm_active,  palm_prog  = False, 0.0
        fist_active,  fist_prog  = False, 0.0
        screenshot_prog          = 0.0
        screenshot_flash        -= 1

        # ── Gesture dispatch ──────────────────────────────────────────────────
        if lm:
            # ── 1. PRIORITY: Peace sign → toggle smartboard (both modes) ─────
            peace_active, peace_prog, just_toggled = controller.check_smartboard_toggle(lm)

            if peace_active:
                current_gesture = f"✌ Board {'ON' if controller.smartboard_open else 'OFF'} {int(peace_prog*100)}%"

            # ── 2. SMARTBOARD MODE ────────────────────────────────────────────
            elif controller.smartboard_open:

                # 2a. Colour change: index-thumb pinch
                if controller.check_board_colour_change(lm):
                    board.next_color()
                    current_gesture = f"🎨 Color → {board.brush_color_name}"

                # 2b. Clear all: rock sign (index + pinky)
                elif controller.check_smartboard_clear(lm):
                    board.clear()
                    current_gesture = "🤘 Canvas Cleared!"

                # 2c. Erase: open palm (NEW — distinct from draw/clear)
                elif controller.is_open_palm(lm):
                    x, y = lm[8]   # use index tip position for eraser centre
                    bx = int(np.interp(x, [0, CAM_W],  [0, 1920]))
                    by = int(np.interp(y, [0, CAM_H], [0, 1080]))
                    board.erase(bx, by)
                    current_gesture = "🖐 Erasing"

                # 2d. Draw: index finger only
                elif controller.is_index_only(lm):
                    x, y = lm[8]
                    bx = int(np.interp(x, [0, CAM_W],  [0, 1920]))
                    by = int(np.interp(y, [0, CAM_H], [0, 1080]))
                    board.draw(bx, by)
                    current_gesture = "☝ Drawing"

                else:
                    board.stop_drawing()
                    board.stop_erasing()
                    current_gesture = "— (Board Open)"

            # ── 3. NORMAL MODE ────────────────────────────────────────────────
            else:
                # 3a. Volume Up/Down — must use explicit thumbs gestures
                if controller.is_thumbs_up(lm):
                    vol = controller.check_volume(lm)
                    if vol == "up":
                        vol_direction, vol_flash_frames = "up", 40
                        vol_level = min(1.0, vol_level + 0.05)
                    current_gesture = "👍 Volume Up"

                elif controller.is_thumbs_down(lm):
                    vol = controller.check_volume(lm)
                    if vol == "down":
                        vol_direction, vol_flash_frames = "down", 40
                        vol_level = max(0.0, vol_level - 0.05)
                    current_gesture = "👎 Volume Down"

                # 3b. Mute toggle — pinky only (explicit gesture check, FIXED)
                elif controller.is_pinky_only(lm):
                    if controller.check_mute_toggle():
                        is_muted = not is_muted
                    current_gesture = "🔇 MUTED" if is_muted else "🔊 UNMUTED"

                # 3c. Screenshot — three fingers held
                elif controller.is_three_fingers(lm):
                    taken, screenshot_prog = controller.check_screenshot(lm)
                    current_gesture = f"📸 Screenshot {int(screenshot_prog*100)}%"
                    if taken:
                        screenshot_flash = 50
                else:
                    controller.reset_screenshot()

                # 3d. Open Settings — open palm held 2s
                if not any([controller.is_thumbs_up(lm), controller.is_thumbs_down(lm),
                            controller.is_pinky_only(lm), controller.is_three_fingers(lm),
                            peace_active]):
                    if controller.is_open_palm(lm):
                        palm_active, palm_prog, done = controller.check_open_settings(lm)
                        current_gesture = f"🖐 Settings {int(palm_prog*100)}%"

                    # 3e. Open Explorer — fist held 2s (only plain fist, not thumbs)
                    elif (controller.is_fist(lm) and
                          controller._get_thumb_dir(lm) == "neutral"):
                        fist_active, fist_prog, done = controller.check_open_explorer(lm)
                        current_gesture = f"✊ Explorer {int(fist_prog*100)}%"

                    else:
                        controller.reset_palm()
                        controller.reset_fist()

                        # 3f. Click — index+thumb pinch
                        if controller.is_index_thumb_pinch(lm):
                            controller.check_click()
                            current_gesture = "👌 Click"

                        # 3g. Scroll — middle+thumb pinch
                        elif controller.is_middle_thumb_pinch(lm):
                            controller.check_scroll_up()
                            current_gesture = "🤏 Scroll"

                        # 3h. Cursor move — index only
                        elif controller.is_index_only(lm):
                            controller.move_cursor(lm)
                            current_gesture = "☝ Move Cursor"

                        else:
                            current_gesture = "—"

        else:
            # No hand detected
            board.stop_drawing()
            board.stop_erasing()
            controller.reset_palm()
            controller.reset_fist()
            controller.reset_screenshot()
            current_gesture = "— No Hand"

        # ── Volume flash decay ─────────────────────────────────────────────────
        if vol_flash_frames > 0:
            vol_flash_frames -= 1
        else:
            vol_direction = None

        # ── Render smartboard (fullscreen) ────────────────────────────────────
        if controller.smartboard_open:
            board_frame = board.render()
            cv2.namedWindow(BOARD_WIN, cv2.WINDOW_NORMAL)
            cv2.setWindowProperty(BOARD_WIN, cv2.WND_PROP_FULLSCREEN,
                                  cv2.WINDOW_FULLSCREEN)
            cv2.imshow(BOARD_WIN, board_frame)
        else:
            try: cv2.destroyWindow(BOARD_WIN)
            except: pass

        # ── Render camera HUD ─────────────────────────────────────────────────
        # Landmark glow on fingertip
        draw_landmark_glow(frame, lm, current_gesture)

        # Panels
        draw_top_bar(frame, current_gesture, fps_display, controller.smartboard_open)
        draw_right_panel(frame, controller.smartboard_open,
                         peace_active, peace_prog,
                         palm_active,  palm_prog,
                         fist_active,  fist_prog,
                         is_muted, vol_direction)
        draw_volume_hud(frame, vol_direction, vol_level, vol_flash_frames > 0)
        draw_screenshot_hud(frame, screenshot_prog, screenshot_flash > 0)

        if controller.smartboard_open:
            draw_smartboard_mode_overlay(frame, board)

        draw_bottom_legend(frame)

        cv2.imshow(CAMERA_WIN, frame)

        # ── Keyboard shortcuts ─────────────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('z') and (cv2.waitKey(1) & 0xFF == 26):  # Ctrl+Z
            board.undo()
        elif key == ord('w') and controller.smartboard_open:
            board.set_brush_size(+1)
        elif key == ord('s') and controller.smartboard_open:
            board.set_brush_size(-1)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
