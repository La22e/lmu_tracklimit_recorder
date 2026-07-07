import os
import sys

_script_dir = os.path.dirname(os.path.abspath(__file__))
_src_dir = os.path.dirname(_script_dir)
_proj_root = os.path.dirname(_src_dir)
sys.path.insert(0, _proj_root)
sys.path.insert(0, _src_dir)

import argparse
import logging

from config import setup_logging
from editor import BoundaryEditor


def main():
    parser = argparse.ArgumentParser(description="Track Boundary Editor")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    args = parser.parse_args()

    setup_logging(args.debug)
    logger = logging.getLogger(__name__)
    logger.debug("Debug logging enabled")

    BoundaryEditor()


if __name__ == "__main__":
    main()
