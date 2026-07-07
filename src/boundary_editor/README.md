# Track Boundary Editor

A visual editor for the track boundary points stored in `track_limits.db` (recorded by `record_limits.py`).  
Lets you view, edit, smooth, and optimize left/right track edges.

---

## Getting started

1. Run the editor from the project root:
   ```
   py boundary_editor.py
   ```
2. If any tracks exist in the database, the first one loads automatically.
3. Select a different track from the dropdown at any time.
4. Click **Refresh** to reload the track list after importing a new track via CSV.

---

## Mouse controls

| Action | Result |
|--------|--------|
| **Left-click** a point | Selects it (deselects others) |
| **Shift + left-click** a point | Starts a range selection; click another point on the same side to select the entire range between them |
| **Drag** a selected point | Moves it |
| **Right-click** | Deletes the clicked point (or all selected points if any are selected) |
| **Double-click** on a line segment | Inserts a new point at that position |
| **Scroll wheel** | Zooms in/out centered on the mouse cursor |
| **Click + drag** on empty canvas | Pans the view |

---

## Toolbar buttons (right to left)

| Button | Function |
|--------|----------|
| **Save** | Writes all edits to the database |
| **Export CSV** | Saves the current track's boundary points to a CSV file |
| **Import CSV** | Loads boundary points from a CSV file as a new track (replaces existing data) |
| **Delete Track** | Permanently removes the selected track and all its boundary points from the database |
| **Discard** | Reverts all unsaved changes back to the last saved state |
| **Auto-Smooth** | Smooths points by averaging with their neighbors — see details below |
| **Smooth window** | Spinbox — sets the averaging window for Auto-Smooth |
| **Optimize** | Removes redundant points on straight sections using the RDP algorithm — see details below |
| **Eps (cm)** | Spinbox — sets the tolerance for Optimize |
| **Refresh** | Reloads the track list from the database |

---

## Auto-Smooth

Each point is replaced by the average of itself and its immediate neighbors.  
The **Smooth window** value controls how many neighbors participate:

- Window = 5 → each point blends with 2 points to the left and 2 points to the right.
- Larger values = smoother but may lose fine detail.
- If points are selected, only the selected ranges are smoothed; otherwise the entire track is smoothed.

**Range**: 3–31 (odd numbers only)  
**Default**: 5

---

## Optimize (Ramer–Douglas–Peucker)

Removes points that lie on nearly straight lines while preserving corners.  
The **Eps (cm)** value controls how aggressively points are removed:

- 5 cm — very conservative, keeps almost all points
- 20 cm — default, removes obvious redundant points on straights
- 100 cm — aggressive, reduces long straights to just a few points

**Range**: 5–100 cm (step 5)  
**Default**: 20 cm

If points are selected, only the selected ranges are optimized; otherwise the entire track is optimized.

---

## Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` / `Ctrl+Shift+Z` | Redo |
| `Delete` | Remove selected points |

---

## Status bar

The bar at the bottom shows the current track name, left/right point counts, selection info, and action feedback (save, undo, optimize results, etc.).
