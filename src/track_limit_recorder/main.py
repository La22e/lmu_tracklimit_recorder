import os
import sys

_script_dir = os.path.dirname(os.path.abspath(__file__))
_src_dir = os.path.dirname(_script_dir)
_proj_root = os.path.dirname(_src_dir)
sys.path.insert(0, _proj_root)
sys.path.insert(0, _src_dir)

import argparse
import logging

from config import DB_PATH, setup_logging
from database import TrackDatabase
from recorder import Recorder


def main():
    parser = argparse.ArgumentParser(description="Record track boundary points from LMU")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    parser.add_argument("--export-csv", metavar="DIR", help="export averaged data as CSV files to DIR")
    args = parser.parse_args()

    setup_logging(args.debug)
    logger = logging.getLogger(__name__)
    logger.debug("Debug logging enabled")

    db = TrackDatabase(DB_PATH)
    rec = Recorder(db, args)
    rec.run()
    db.close()


if __name__ == "__main__":
    main()
