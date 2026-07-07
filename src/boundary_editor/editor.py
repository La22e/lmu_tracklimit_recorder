import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from config import BG, FG, LEFT_COLOR, RIGHT_COLOR, DB_PATH
from canvas import TrackCanvas
from database import TrackDatabase
from geometry import rdp_simplify


class BoundaryEditor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Track Boundary Editor")
        self.root.geometry("1000x700")
        self.root.configure(bg=BG)

        self.db = TrackDatabase(DB_PATH)
        self.track_id = None
        self.track_name = None
        self.left_points = []
        self.right_points = []
        self.selected_points = set()
        self.range_anchor = {}
        self.dirty = False
        self._undo_stack = []
        self._redo_stack = []
        self._max_undo = 50
        self._tracks = []

        self._build_ui()
        self.canvas.set_refs(self.left_points, self.right_points, self.selected_points)
        self._load_track_list()
        if self._tracks:
            self.track_combo.current(0)
            self._on_track_selected()
        self.root.mainloop()

    def _build_ui(self):
        top = tk.Frame(self.root, bg=BG)
        top.pack(fill=tk.X, padx=8, pady=4)

        tk.Label(top, text="Track:", fg=FG, bg=BG).pack(side=tk.LEFT)
        self.track_var = tk.StringVar()
        self.track_combo = ttk.Combobox(top, textvariable=self.track_var, state="readonly", width=40)
        self.track_combo.pack(side=tk.LEFT, padx=4)
        self.track_combo.bind("<<ComboboxSelected>>", self._on_track_selected)
        tk.Button(top, text="Refresh", command=self._load_track_list, bg=BG, fg=FG).pack(side=tk.LEFT, padx=2)

        tk.Button(top, text="Save", command=self._save, bg=BG, fg=LEFT_COLOR).pack(side=tk.RIGHT, padx=2)
        tk.Button(top, text="Export CSV", command=self._export_csv, bg=BG, fg=FG).pack(side=tk.RIGHT, padx=2)
        tk.Button(top, text="Import CSV", command=self._import_csv, bg=BG, fg=FG).pack(side=tk.RIGHT, padx=2)
        tk.Button(top, text="Delete Track", command=self._delete_track, bg=BG, fg=RIGHT_COLOR).pack(side=tk.RIGHT, padx=2)
        tk.Button(top, text="Discard", command=self._discard, bg=BG, fg=RIGHT_COLOR).pack(side=tk.RIGHT, padx=2)

        tk.Button(top, text="Auto-Smooth", command=self._auto_smooth, bg=BG, fg=LEFT_COLOR).pack(side=tk.RIGHT, padx=(2, 12))
        self.smooth_var = tk.IntVar(value=5)
        tk.Spinbox(top, from_=3, to=31, increment=2, textvariable=self.smooth_var, width=4, bg=BG, fg=FG).pack(side=tk.RIGHT)
        tk.Label(top, text="Smooth window:", fg=FG, bg=BG).pack(side=tk.RIGHT, padx=(8, 2))

        tk.Button(top, text="Optimize", command=self._optimize, bg=BG, fg=LEFT_COLOR).pack(side=tk.RIGHT, padx=2)
        self.optimize_eps_var = tk.IntVar(value=20)
        tk.Spinbox(top, from_=5, to=100, increment=5, textvariable=self.optimize_eps_var, width=4, bg=BG, fg=FG).pack(side=tk.RIGHT)
        tk.Label(top, text="Eps (cm):", fg=FG, bg=BG).pack(side=tk.RIGHT, padx=(8, 2))

        self.canvas = TrackCanvas(self.root)
        self.canvas.canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self.canvas.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.canvas.bind("<Button-2>", self._on_right_click)
        self.canvas.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.canvas.bind("<Double-Button-1>", self._on_double_click)

        bottom = tk.Frame(self.root, bg=BG)
        bottom.pack(fill=tk.X, padx=8, pady=4)
        self.status_label = tk.Label(bottom, text="Ready", fg=FG, bg=BG)
        self.status_label.pack(side=tk.LEFT)

        self.root.bind("<Control-s>", lambda e: self._save())
        self.root.bind("<Control-z>", lambda e: self._undo())
        self.root.bind("<Control-y>", lambda e: self._redo())
        self.root.bind("<Control-Shift-Z>", lambda e: self._redo())
        self.root.bind("<Delete>", self._on_delete_key)

    def _load_track_list(self, event=None):
        try:
            self._tracks = self.db.get_tracks()
        except Exception:
            self._tracks = []
        self.track_combo["values"] = [t[1] for t in self._tracks]

    def _on_track_selected(self, event=None):
        name = self.track_var.get()
        for tid, tname in self._tracks:
            if tname == name:
                self._load_track(tid, tname)
                break

    def _load_track(self, tid, name):
        self.track_id = tid
        self.track_name = name
        self.left_points.clear()
        self.right_points.clear()
        self.selected_points.clear()
        self.range_anchor.clear()
        self.dirty = False
        self._undo_stack.clear()
        self._redo_stack.clear()

        for side, arr in [(0, self.left_points), (1, self.right_points)]:
            rows = self.db.get_points(tid, side)
            arr.extend([(r[1], r[2], r[0], r[3]) for r in rows])

        self.canvas.rebuild_map()
        self.canvas.draw()
        self._update_status()

    def _on_press(self, event):
        nearest = self.canvas.nearest_point(event.x, event.y)
        if nearest:
            side, idx = nearest
            if event.state & 0x0001:
                if side in self.range_anchor:
                    anchor = self.range_anchor[side]
                    self.selected_points.difference_update({k for k in self.selected_points if k[0] == side})
                    lo, hi = sorted([anchor, idx])
                    for i in range(lo, hi + 1):
                        self.selected_points.add((side, i))
                else:
                    self.selected_points.add((side, idx))
                    self.range_anchor[side] = idx
            else:
                self._push_undo()
                self.selected_points.clear()
                self.selected_points.add((side, idx))
                self.range_anchor.clear()
            self.canvas.draw()
            self._update_status()
        else:
            self.selected_points.clear()
            self.range_anchor.clear()
            self.canvas.start_pan(event.x, event.y)
            self.canvas.draw()
            self._update_status()

    def _on_drag(self, event):
        if len(self.selected_points) == 1:
            side, idx = next(iter(self.selected_points))
            wx, wz = self.canvas.from_canvas(event.x, event.y)
            pts = self.left_points if side == 0 else self.right_points
            pts[idx] = (wx, wz, pts[idx][2], pts[idx][3])
            self.dirty = True
            self.canvas.draw()
            self._update_status("Unsaved changes")
        else:
            self.canvas.do_pan(event.x, event.y)

    def _on_release(self, event):
        self.canvas.end_pan()

    def _on_right_click(self, event):
        if self.selected_points:
            self._push_undo()
            self._delete_selected()
        else:
            nearest = self.canvas.nearest_point(event.x, event.y)
            if nearest:
                self._push_undo()
                side, idx = nearest
                pts = self.left_points if side == 0 else self.right_points
                if 0 <= idx < len(pts):
                    del pts[idx]
                    self.dirty = True
                    self.canvas.draw()
                    self._update_status("Unsaved changes")

    def _on_double_click(self, event):
        nearest = self.canvas.nearest_segment(event.x, event.y)
        if nearest:
            self._push_undo()
            side, i, nx, nz, nlap = nearest
            pts = self.left_points if side == 0 else self.right_points
            pts.insert(i + 1, (nx, nz, -1, nlap))
            self.dirty = True
            self.canvas.draw()
            self._update_status("Unsaved changes")

    def _on_delete_key(self, event):
        if self.selected_points:
            self._delete_selected()

    def _delete_selected(self):
        self._push_undo()
        by_side = {0: [], 1: []}
        for side, idx in self.selected_points:
            by_side[side].append(idx)
        self.selected_points.clear()
        self.range_anchor.clear()
        for side in (0, 1):
            for idx in sorted(by_side[side], reverse=True):
                pts = self.left_points if side == 0 else self.right_points
                if 0 <= idx < len(pts):
                    del pts[idx]
        self.dirty = True
        self.canvas.draw()
        self._update_status("Unsaved changes")

    def _update_status(self, msg=None):
        t = []
        if self.track_name:
            t.append(f"{self.track_name} \u2014 L:{len(self.left_points)}  R:{len(self.right_points)}")
        if self.selected_points:
            sides = {s for s, _ in self.selected_points}
            ranges = []
            for s in sorted(sides):
                idxs = sorted(i for (side, i) in self.selected_points if side == s)
                label = "L" if s == 0 else "R"
                if len(idxs) >= 2 and idxs == list(range(idxs[0], idxs[-1] + 1)):
                    ranges.append(f"{label}[{idxs[0]}-{idxs[-1]}]")
                else:
                    ranges.append(f"{label}:{len(idxs)}")
            t.append(f"({' '.join(ranges)})")
        if msg:
            t.append(msg)
        self.status_label.config(text="  ".join(t))

    def _push_undo(self):
        self._undo_stack.append((
            [(p[0], p[1], p[2], p[3]) for p in self.left_points],
            [(p[0], p[1], p[2], p[3]) for p in self.right_points],
            set(self.selected_points),
        ))
        if len(self._undo_stack) > self._max_undo:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _apply_snapshot(self, snap):
        left, right, sel = snap
        self.left_points.clear()
        self.left_points.extend(left)
        self.right_points.clear()
        self.right_points.extend(right)
        self.selected_points.clear()
        self.selected_points.update(sel)

    def _undo(self, event=None):
        if not self._undo_stack:
            return
        self._redo_stack.append((
            [(p[0], p[1], p[2], p[3]) for p in self.left_points],
            [(p[0], p[1], p[2], p[3]) for p in self.right_points],
            set(self.selected_points),
        ))
        self._apply_snapshot(self._undo_stack.pop())
        self.dirty = True
        self.canvas.draw()
        self._update_status("Undone")

    def _redo(self, event=None):
        if not self._redo_stack:
            return
        self._undo_stack.append((
            [(p[0], p[1], p[2], p[3]) for p in self.left_points],
            [(p[0], p[1], p[2], p[3]) for p in self.right_points],
            set(self.selected_points),
        ))
        self._apply_snapshot(self._redo_stack.pop())
        self.dirty = True
        self.canvas.draw()
        self._update_status("Redone")

    def _delete_track(self):
        if self.track_id is None:
            messagebox.showinfo("No track", "Select a track first.")
            return
        name = self.track_name
        if not messagebox.askyesno("Delete Track", f'Permanently delete "{name}" and all its boundary points?'):
            return
        self.db.delete_track(self.track_id)
        self.track_id = None
        self.track_name = None
        self.left_points.clear()
        self.right_points.clear()
        self.selected_points.clear()
        self.range_anchor.clear()
        self.dirty = False
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._load_track_list()
        self.canvas.canvas.delete("all")
        self._update_status(f'Deleted "{name}"')

    def _auto_smooth(self):
        self._push_undo()
        window = self.smooth_var.get()
        half = window // 2
        for side, pts in [(0, self.left_points), (1, self.right_points)]:
            n = len(pts)
            if n < window + 2:
                continue
            indices = sorted({i for (s, i) in self.selected_points if s == side}) if self.selected_points else list(range(n))
            if not indices:
                continue
            xs = [p[0] for p in pts]
            zs = [p[1] for p in pts]
            new_x = xs[:]
            new_z = zs[:]
            for i in indices:
                lo = max(0, i - half)
                hi = min(n - 1, i + half)
                total_x = 0.0
                total_z = 0.0
                count = 0
                for j in range(lo, hi + 1):
                    total_x += xs[j]
                    total_z += zs[j]
                    count += 1
                new_x[i] = total_x / count
                new_z[i] = total_z / count
            for i in indices:
                pts[i] = (new_x[i], new_z[i], pts[i][2], pts[i][3])
        self.dirty = True
        self.canvas.draw()
        self._update_status("Unsaved changes (smoothed)")

    def _optimize(self):
        if not self.left_points and not self.right_points:
            return
        epsilon = self.optimize_eps_var.get() / 100.0
        self._push_undo()
        before = len(self.left_points) + len(self.right_points)
        for side, pts in [(0, self.left_points), (1, self.right_points)]:
            n = len(pts)
            if n < 3:
                continue
            indices = sorted({i for (s, i) in self.selected_points if s == side}) if self.selected_points else None
            if indices is not None:
                groups = []
                start = indices[0]
                end = indices[0]
                for i in indices[1:]:
                    if i == end + 1:
                        end = i
                    else:
                        groups.append((start, end))
                        start = end = i
                groups.append((start, end))
                for lo, hi in groups:
                    seg = pts[lo:hi + 1]
                    keep = rdp_simplify([(p[0], p[1]) for p in seg], epsilon)
                    keep_set = set(keep)
                    new_seg = [seg[i] for i in range(len(seg)) if i in keep_set]
                    pts[lo:hi + 1] = new_seg
            else:
                keep = rdp_simplify([(p[0], p[1]) for p in pts], epsilon)
                keep_set = set(keep)
                pts[:] = [pts[i] for i in range(len(pts)) if i in keep_set]
        after = len(self.left_points) + len(self.right_points)
        self.dirty = True
        self.selected_points.clear()
        self.range_anchor.clear()
        self.canvas.draw()
        self._update_status(f"Optimized: {before} \u2192 {after} points (eps={epsilon:.2f}m)")

    def _save(self):
        if self.track_id is None or not self.dirty:
            return
        self.db.replace_all_points(self.track_id, self.left_points, self.right_points)
        self.dirty = False
        self._update_status("Saved")

        next_id = 0
        for pts in (self.left_points, self.right_points):
            for i in range(len(pts)):
                pts[i] = (pts[i][0], pts[i][1], next_id, i * 2.0)
                next_id += 1

    def _export_csv(self):
        if self.track_name is None:
            messagebox.showinfo("No track", "Select a track first.")
            return
        default_name = self.track_name.replace(" ", "_") + ".csv"
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=default_name,
        )
        if not path:
            return
        try:
            points = []
            for side, pts in [(0, self.left_points), (1, self.right_points)]:
                for x, z, _, ld in pts:
                    points.append((side, x, z, ld))
            TrackDatabase.write_csv(path, points)
            self._update_status(f"Exported to {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    def _import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            name, valid, errors = self.db.parse_csv(path)
        except ValueError as e:
            messagebox.showerror("Invalid CSV", str(e))
            return
        except Exception as e:
            messagebox.showerror("Read error", str(e))
            return

        if not valid:
            messagebox.showwarning("Empty file", "No valid data rows found.")
            return

        summary = f'Import {len(valid)} points as track "{name}"?\nExisting boundary data will be replaced.'
        if errors:
            summary += f"\n\n{len(errors)} row(s) skipped:\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                summary += f"\n  ... and {len(errors) - 5} more"

        if not messagebox.askyesno("Import", summary):
            return

        self._push_undo()
        try:
            tid = self.db.import_points(name, valid)
            self._load_track_list()
            self.track_var.set(name)
            self._load_track(tid, name)
            self._update_status(f'Imported {len(valid)} points for "{name}"')
        except Exception as e:
            messagebox.showerror("Import failed", str(e))

    def _discard(self):
        if self.dirty and messagebox.askyesno("Discard changes?", "Unsaved changes will be lost."):
            self._load_track(self.track_id, self.track_name)
