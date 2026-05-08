# ═══════════════════════════════════════════════════════════════════════════════
#  smartboard.py  v4.0  ─  Full-Screen Black Canvas Smartboard
#  Erase = Open Palm  |  Clear All = Rock Sign  |  Color = Pinch
# ═══════════════════════════════════════════════════════════════════════════════
import cv2
import numpy as np


class Smartboard:
    """Full-screen smartboard with black background, undo stack, and premium HUD."""

    # BGR palette with name and display hex
    PALETTE = [
        ((0,   255,   0),  "Green",   (0,   200,   0)),
        ((0,   100, 255),  "Orange",  (0,   100, 255)),
        ((255,   0,   0),  "Blue",    (255,   0,   0)),
        ((0,     0, 255),  "Red",     (0,     0, 255)),
        ((0,   255, 255),  "Yellow",  (0,   220, 200)),
        ((255, 255,   0),  "Cyan",    (200, 220,   0)),
        ((255,   0, 255),  "Magenta", (200,   0, 200)),
        ((255, 255, 255),  "White",   (220, 220, 220)),
    ]

    def __init__(self, width=1920, height=1080):
        self.width  = width
        self.height = height
        self._reset_canvas()
        self.prev_x, self.prev_y = None, None
        self.color_index  = 0
        self.brush_size   = 7
        self.eraser_radius = 50

        # ── Undo stack ────────────────────────────────────────────────────────
        self._undo_stack = []
        self._MAX_UNDO   = 25

        # ── Erase cursor anim ─────────────────────────────────────────────────
        self._erase_x, self._erase_y = None, None

    # ── Canvas management ─────────────────────────────────────────────────────
    def _reset_canvas(self):
        self.canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)

    def _push_undo(self):
        if len(self._undo_stack) >= self._MAX_UNDO:
            self._undo_stack.pop(0)
        self._undo_stack.append(self.canvas.copy())

    def undo(self):
        if self._undo_stack:
            self.canvas = self._undo_stack.pop()
            self.prev_x, self.prev_y = None, None
            return True
        return False

    # ── Drawing ───────────────────────────────────────────────────────────────
    def draw(self, x, y):
        """Continuous stroke — call each frame while index finger is up."""
        if self.prev_x is not None:
            cv2.line(self.canvas,
                     (self.prev_x, self.prev_y), (x, y),
                     self.brush_color, self.brush_size, cv2.LINE_AA)
        else:
            self._push_undo()      # save state at stroke start
        self.prev_x, self.prev_y = x, y
        self._erase_x, self._erase_y = None, None

    def stop_drawing(self):
        self.prev_x, self.prev_y = None, None

    # ── Erasing (Open Palm) ───────────────────────────────────────────────────
    def erase(self, x, y):
        """Erase with circular palm eraser — called when open palm detected."""
        cv2.circle(self.canvas, (x, y), self.eraser_radius, (0, 0, 0), -1)
        self.prev_x, self.prev_y = None, None
        self._erase_x, self._erase_y = x, y

    def stop_erasing(self):
        self._erase_x, self._erase_y = None, None

    # ── Clear all (Rock Sign) ─────────────────────────────────────────────────
    def clear(self):
        self._push_undo()
        self._reset_canvas()
        self.prev_x, self.prev_y = None, None

    # ── Colour ────────────────────────────────────────────────────────────────
    @property
    def brush_color(self):
        return self.PALETTE[self.color_index][0]

    @property
    def brush_color_name(self):
        return self.PALETTE[self.color_index][1]

    def next_color(self):
        self.color_index = (self.color_index + 1) % len(self.PALETTE)

    def prev_color(self):
        self.color_index = (self.color_index - 1) % len(self.PALETTE)

    def set_brush_size(self, delta):
        self.brush_size = max(2, min(30, self.brush_size + delta))

    # ═══════════════════════════════════════════════════════════════════════════
    #  RENDER
    # ═══════════════════════════════════════════════════════════════════════════

    def render(self):
        """Return the full-screen board frame — pure black background."""
        frame = self.canvas.copy()
        self._draw_toolbar(frame)
        self._draw_title(frame)
        self._draw_brush_preview(frame)
        self._draw_erase_cursor(frame)
        self._draw_hint_bar(frame)
        return frame

    # ── Internal HUD ─────────────────────────────────────────────────────────
    def _panel(self, frame, x1, y1, x2, y2, color=(15,15,15), alpha=0.80):
        """Semi-transparent dark panel."""
        roi = frame[y1:y2, x1:x2]
        overlay = np.full_like(roi, color)
        cv2.addWeighted(roi, 1 - alpha, overlay, alpha, 0, roi)
        frame[y1:y2, x1:x2] = roi

    def _draw_toolbar(self, frame):
        TH = 68
        self._panel(frame, 0, 0, self.width, TH, color=(10,10,12), alpha=0.88)
        # Separator line with teal glow
        cv2.line(frame, (0, TH), (self.width, TH), (0, 180, 160), 1)
        cv2.line(frame, (0, TH+1), (self.width, TH+1), (0, 80, 70), 1)

        cv2.putText(frame, "COLOR PALETTE",
                    (14, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.48,
                    (80, 80, 80), 1)

        sw, gap, sx = 42, 8, 14
        cy = TH // 2 + 10

        for i, (col, name, glow_col) in enumerate(self.PALETTE):
            cx = sx + i * (sw + gap) + sw // 2
            # Shadow
            cv2.circle(frame, (cx+2, cy+2), sw // 2, (0,0,0), -1)
            # Main swatch
            cv2.circle(frame, (cx, cy), sw // 2, col, -1, cv2.LINE_AA)
            if i == self.color_index:
                # Outer glow ring
                cv2.circle(frame, (cx, cy), sw // 2 + 6, glow_col, 2, cv2.LINE_AA)
                cv2.circle(frame, (cx, cy), sw // 2 + 3, (255,255,255), 2, cv2.LINE_AA)
            else:
                cv2.circle(frame, (cx, cy), sw // 2, (50,50,50), 1, cv2.LINE_AA)

        # Brush size indicator
        bx = sx + len(self.PALETTE) * (sw + gap) + 20
        cv2.putText(frame, f"BRUSH", (bx, cy - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (100,100,100), 1)
        cv2.putText(frame, f"{self.brush_size}px", (bx, cy + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (210,230,0), 1)

        # Undo count
        ux = self.width - 160
        cv2.putText(frame, f"UNDO STACK: {len(self._undo_stack)}",
                    (ux, cy + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (70,70,70), 1)

    def _draw_title(self, frame):
        text = "SMARTBOARD"
        (tw, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, 1.1, 2)
        cx = (self.width - tw) // 2
        # Glow pass
        cv2.putText(frame, text, (cx + 2, 45),
                    cv2.FONT_HERSHEY_DUPLEX, 1.1, (0, 80, 70), 3, cv2.LINE_AA)
        cv2.putText(frame, text, (cx, 44),
                    cv2.FONT_HERSHEY_DUPLEX, 1.1, (0, 230, 210), 2, cv2.LINE_AA)

    def _draw_brush_preview(self, frame):
        bx, by = self.width - 70, self.height - 80
        r = max(5, self.brush_size * 2)
        # Glow
        cv2.circle(frame, (bx, by), r + 6, tuple(c // 3 for c in self.brush_color), -1)
        cv2.circle(frame, (bx, by), r, self.brush_color, -1, cv2.LINE_AA)
        cv2.putText(frame, "BRUSH",
                    (bx - 22, by + r + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.36, (120,120,120), 1)

    def _draw_erase_cursor(self, frame):
        """Show eraser circle at palm position while erasing."""
        if self._erase_x is None: return
        x, y = self._erase_x, self._erase_y
        cv2.circle(frame, (x, y), self.eraser_radius, (60, 60, 60), 2, cv2.LINE_AA)
        cv2.circle(frame, (x, y), 3, (100, 100, 100), -1, cv2.LINE_AA)
        cv2.putText(frame, "ERASE", (x - 22, y - self.eraser_radius - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (80, 80, 80), 1)

    def _draw_hint_bar(self, frame):
        BH = 30
        y0 = self.height - BH
        self._panel(frame, 0, y0, self.width, self.height, color=(10,10,12), alpha=0.88)
        cv2.line(frame, (0, y0), (self.width, y0), (0, 60, 55), 1)
        hints = ("☝ Draw: Index  |  🖐 Erase: Open Palm  |  🤘 Clear All: Rock  |  "
                 "👌 Next Color: Pinch  |  ✌ Close: Peace (hold)  |  "
                 "W/S: Brush ±  |  Ctrl+Z: Undo  |  Q: Quit")
        cv2.putText(frame, hints,
                    (10, self.height - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.36, (90, 90, 90), 1)
