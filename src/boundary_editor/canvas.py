import math
import tkinter as tk
from config import CANVAS_BG, LEFT_COLOR, RIGHT_COLOR, SELECTED_COLOR, PAD, RADIUS


class TrackCanvas:
    def __init__(self, parent):
        self.canvas = tk.Canvas(parent, bg=CANVAS_BG, highlightthickness=0)
        self.left_points = []
        self.right_points = []
        self.selected_points = set()

        self._map_min_x = 0
        self._map_min_z = 0
        self._map_w = 1
        self._map_h = 1
        self._map_scale = 1
        self._map_pan_x = 0
        self._map_pan_y = 0
        self._pan_start = None

        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Configure>", self._on_resize)

    def set_refs(self, left, right, selected):
        self.left_points = left
        self.right_points = right
        self.selected_points = selected

    def rebuild_map(self):
        all_pts = [(p[0], p[1]) for p in self.left_points] + [(p[0], p[1]) for p in self.right_points]
        if not all_pts:
            self.canvas.delete("all")
            return

        xs = [p[0] for p in all_pts]
        zs = [p[1] for p in all_pts]
        self._map_min_x = min(xs)
        self._map_min_z = min(zs)
        self._map_w = max(xs) - self._map_min_x or 1
        self._map_h = max(zs) - self._map_min_z or 1

        cw = self.canvas.winfo_width() or 800
        ch = self.canvas.winfo_height() or 500
        sx = (cw - 2 * PAD) / self._map_w
        sy = (ch - 2 * PAD) / self._map_h
        self._map_scale = min(sx, sy)
        self._map_pan_x = 0
        self._map_pan_y = 0

    def to_canvas(self, x, z):
        return (
            (x - self._map_min_x) * self._map_scale + self._map_pan_x + PAD,
            (self._map_min_z + self._map_h - z) * self._map_scale + self._map_pan_y + PAD,
        )

    def from_canvas(self, cx, cy):
        x = (cx - self._map_pan_x - PAD) / self._map_scale + self._map_min_x
        z = self._map_min_z + self._map_h - (cy - self._map_pan_y - PAD) / self._map_scale
        return x, z

    def draw(self):
        self.canvas.delete("all")

        def draw_line(pts, color, side):
            if len(pts) < 2:
                return
            coords = []
            for i, (x, z, _, _) in enumerate(pts):
                cx, cy = self.to_canvas(x, z)
                coords.extend([cx, cy])
                fill = SELECTED_COLOR if (side, i) in self.selected_points else color
                self.canvas.create_rectangle(
                    cx - RADIUS, cy - RADIUS, cx + RADIUS, cy + RADIUS,
                    fill=fill, outline="", tags="point",
                )
            self.canvas.create_line(*coords, fill=color, width=2, tags="line")
            if len(pts) >= 2:
                self.canvas.create_line(
                    coords[0], coords[1], coords[-2], coords[-1],
                    fill=color, width=2, tags="line",
                )

        draw_line(self.left_points, LEFT_COLOR, 0)
        draw_line(self.right_points, RIGHT_COLOR, 1)

    def nearest_point(self, cx, cy, threshold=15):
        best = None
        best_d = threshold
        for side, pts in [(0, self.left_points), (1, self.right_points)]:
            for idx, (x, z, _, _) in enumerate(pts):
                px, py = self.to_canvas(x, z)
                d = math.hypot(px - cx, py - cy)
                if d < best_d:
                    best_d = d
                    best = (side, idx)
        return best

    def nearest_segment(self, cx, cy, threshold=20):
        best = None
        best_d = threshold
        for side, pts in [(0, self.left_points), (1, self.right_points)]:
            if len(pts) < 2:
                continue
            for i in range(len(pts) - 1):
                mx = (pts[i][0] + pts[i + 1][0]) / 2
                mz = (pts[i][1] + pts[i + 1][1]) / 2
                px, py = self.to_canvas(mx, mz)
                d = math.hypot(px - cx, py - cy)
                if d < best_d:
                    best_d = d
                    nlap = (pts[i][3] + pts[i + 1][3]) / 2
                    best = (side, i, mx, mz, nlap)
        return best

    def start_pan(self, x, y):
        self._pan_start = (x, y)

    def do_pan(self, x, y):
        if self._pan_start is None:
            return
        dx = x - self._pan_start[0]
        dy = y - self._pan_start[1]
        self._map_pan_x += dx
        self._map_pan_y += dy
        self._pan_start = (x, y)
        self.draw()

    def end_pan(self):
        self._pan_start = None

    def _on_resize(self, event):
        if self.left_points or self.right_points:
            cw = self.canvas.winfo_width() or 800
            ch = self.canvas.winfo_height() or 500
            sx = (cw - 2 * PAD) / self._map_w
            sy = (ch - 2 * PAD) / self._map_h
            self._map_scale = min(sx, sy)
            self.draw()

    def _on_wheel(self, event):
        wx, wz = self.from_canvas(event.x, event.y)
        factor = 1.1 if event.delta > 0 else 0.9
        new_scale = self._map_scale * factor
        self._map_pan_x = event.x - (wx - self._map_min_x) * new_scale - PAD
        self._map_pan_y = event.y - (self._map_min_z + self._map_h - wz) * new_scale - PAD
        self._map_scale = new_scale
        self.draw()
