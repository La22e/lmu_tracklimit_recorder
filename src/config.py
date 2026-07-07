import logging
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "track_limits.db")

ACTIVE_PHASES = frozenset({1, 2, 3, 4, 5, 6, 7})
MIN_DIST_DELTA = 0.5

BG = "#1e1e2e"
FG = "#cdd6f4"
LEFT_COLOR = "#89b4fa"
RIGHT_COLOR = "#f38ba8"
SELECTED_COLOR = "#f9e2af"
CANVAS_BG = "#11111b"
PAD = 20
RADIUS = 4


def setup_logging(debug=False):
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
        force=True,
    )
