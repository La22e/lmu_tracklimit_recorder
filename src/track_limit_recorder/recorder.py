import logging
import math
import os
import sys
import time

from pyLMUSharedMemory import lmu_data

from config import ACTIVE_PHASES, MIN_DIST_DELTA
from geometry import average_side, compute_both_edges

logger = logging.getLogger(__name__)


class Recorder:
    def __init__(self, db, args):
        self.db = db
        self.args = args
        self.sim = None
        self.track_id = None
        self.track_name = None
        self.recording = False
        self.last_lap_dist = None
        self.recorded = 0
        self.skipped_edge = 0
        self.skipped_dedup = 0
        self.skipped_player = 0
        self._history = None

    def run(self):
        try:
            self._connect()
            self._main_loop()
        except KeyboardInterrupt:
            logger.info("Interrupted by user.")
        finally:
            self._finalize()

    def _connect(self):
        logger.info("Connecting to LMU shared memory...")
        try:
            self.sim = lmu_data.SimInfo()
        except PermissionError:
            logger.error("Cannot access LMU shared memory. Is Le Mans Ultimate running?")
            sys.exit(1)

    def _is_on_track(self):
        scoring = self.sim.LMUData.scoring.scoringInfo
        tele = self.sim.LMUData.telemetry
        phase = scoring.mGamePhase
        in_car = tele.playerHasVehicle
        return in_car and scoring.mInRealtime and phase in ACTIVE_PHASES, scoring, tele

    def _get_player(self, scoring_data):
        for veh in scoring_data.vehScoringInfo:
            if veh.mIsPlayer:
                return veh
        return None

    @staticmethod
    def _decode(b):
        return b.decode("utf-8").rstrip("\x00")

    def _main_loop(self):
        while True:
            on_track, scoring, tele = self._is_on_track()

            if not on_track:
                if self.recording:
                    logger.info("Recording stopped (left track).")
                    self.recording = False
                    self.last_lap_dist = None
                    self._history = None
                time.sleep(0.05)
                continue

            vel = tele.telemInfo[tele.playerVehicleIdx].mLocalVel
            speed = math.sqrt(vel.x ** 2 + vel.y ** 2 + vel.z ** 2)

            if speed < 1.0:
                time.sleep(0.016 if self.recording else 0.05)
                continue

            if not self.recording:
                self.track_name = self._decode(scoring.mTrackName)
                self.track_id = self.db.get_or_create_track(self.track_name)
                self.recording = True
                self.recorded = 0
                self.last_lap_dist = None
                self._history = []
                logger.info("Recording started \u2014 Track: %s", self.track_name)

            player = self._get_player(self.sim.LMUData.scoring)
            if player is None:
                self.skipped_player += 1
                time.sleep(0.016)
                continue

            telem = tele.telemInfo[tele.playerVehicleIdx]
            pos = telem.mPos
            ori = telem.mOri
            heading = math.atan2(ori[2].x, ori[2].z)

            path_lateral = player.mPathLateral
            track_edge = player.mTrackEdge
            lap_dist = player.mLapDist

            logger.debug(
                "Frame: path_lateral=%.3f, track_edge=%.3f, lap_dist=%.3f",
                path_lateral, track_edge, lap_dist,
            )

            if abs(track_edge) > 30:
                self.skipped_edge += 1
                logger.debug("Skipped (edge): track_edge=%.3f", track_edge)
                time.sleep(0.016)
                continue

            if self.last_lap_dist is not None and abs(lap_dist - self.last_lap_dist) < MIN_DIST_DELTA:
                self.skipped_dedup += 1
                time.sleep(0.016)
                continue
            self.last_lap_dist = lap_dist

            left_ex, left_ez, right_ex, right_ez = compute_both_edges(
                pos.x, pos.z, heading, path_lateral, track_edge, self._history,
            )

            self.db.insert_point(self.track_id, 0, left_ex, left_ez, lap_dist)
            self.db.insert_point(self.track_id, 1, right_ex, right_ez, lap_dist)
            self.recorded += 2

            if self.recorded % 100 == 0:
                self.db.commit()
                logger.debug("Recorded %d points...", self.recorded)

            time.sleep(0.016)

    def _finalize(self):
        if self.recorded > 0:
            self.db.commit()
            logger.info("Averaging data across laps...")
            self._average_and_save()
            self.db.commit()

            if self.args.export_csv and self.track_name:
                os.makedirs(self.args.export_csv, exist_ok=True)
                path = self.db.export_csv_to_dir(
                    self.track_id, self.track_name, self.args.export_csv,
                )
                if path:
                    logger.info("Exported to %s", path)

        if self.sim:
            self.sim.close()

        logger.info(
            "Done \u2014 %d boundary points recorded (skipped: edge=%d, dedup=%d, player=%d).",
            self.recorded, self.skipped_edge, self.skipped_dedup, self.skipped_player,
        )

    def _average_and_save(self):
        all_rows = self.db.get_all_points(self.track_id)
        if not all_rows:
            return

        track_length = max(r[3] for r in all_rows)
        if track_length < 100:
            return

        halves = {0: [], 1: []}
        for r in all_rows:
            halves[r[0]].append(r[1:])

        for side in (0, 1):
            rows = halves[side]
            if len(rows) < 20:
                continue

            result = average_side(rows, track_length)
            if not result:
                continue

            self.db.replace_side_points(self.track_id, side, result)
            logger.debug(
                "Side %d: %d raw points \u2192 %d averaged points",
                side, len(rows), len(result),
            )
