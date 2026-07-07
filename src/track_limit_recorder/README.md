# LMU Track Limit Recorder

The script polls LMU's shared memory at ~60 Hz. For each frame, it reads your car's position, heading, lateral path offset (`mPathLateral`), and the track edge distance (`mTrackEdge`). It computes both left and right boundary points from these values.

## Usage

Start Le Mans Ultimate, get on track, then run:

```bash
py src\track_limit_recorder\main.py
```

Press **Ctrl+C** to stop recording. The tool will automatically average your laps and save the result.

### Options

```bash
py src\track_limit_recorder\main.py --export-csv ./exports
```

Exports the averaged boundary points as CSV files.

## Tips for Best Results

- **Drive in the center of the track**: the tool computes the center path from your `mPathLateral` offset. Driving center means `path_lateral ≈ 0`, giving the cleanest center-line calculation for the game's `mTrackEdge` to derive both boundaries.
- **Enable the pit limiter and keep a consistent speed**: uniform speed produces even point density around the whole lap. Slow sections cluster points; fast sections leave gaps.
- **Complete at least 2–3 full laps**: more laps give the averaging pass more data to smooth out noise and produce accurate boundaries.
- **Drive the whole track layout**: ensure you cover every corner and straight to get complete boundary coverage.

## Boundary Editor
Use the [Boundary Editor](../boundary_editor/README.py) to visually inspect, tweak, smooth, optimize, and export the recorded data.

