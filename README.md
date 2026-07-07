# lmu_tracklimit_recorder
Tool to map track boundaries in Le Mans Ultimate. Records boundary points from shared memory, then lets you visually refine them.

## Requirements

- **Le Mans Ultimate** — running and on-track (shared memory must be available)
- **Python >= 3.14**
- **pyLMUSharedMemory** submodule (see Installation)

## Installation

### 1. Clone with submodule (recommended)
```bash
git clone --recurse-submodules https://github.com/La22e/lmu_tracklimit_recorder.git
```

### 2. Or clone then init submodule
```bash
git clone https://github.com/La22e/lmu_tracklimit_recorder.git
git submodule update --init
```

### 3. Install Python dependencies
```bash
pip install -e .
```

## Workflow

### 1. Record

Get on track, drive in the center at a consistent speed (pit limiter helps). Press **Ctrl+C** to stop — laps are averaged automatically.

```bash
py src\track_limit_recorder\main.py
```

See [Recording README](src/track_limit_recorder/README.md) for tips on best results.

### 2. Edit

Visually inspect, smooth, optimize (RDP simplification), and tweak points. Supports undo/redo.

```bash
py src\boundary_editor\main.py
```

See [Editor README](src/boundary_editor/README.md) for full controls.

### 3. Export (optional)

Export averaged data as CSV.

```bash
py src\track_limit_recorder\main.py --export-csv ./exports
```

Or use the editor's Export button.
