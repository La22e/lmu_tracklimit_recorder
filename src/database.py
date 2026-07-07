import csv
import os
import sqlite3


class TrackDatabase:
    def __init__(self, db_path):
        self.con = sqlite3.connect(db_path, timeout=10)
        self.con.execute("PRAGMA journal_mode=WAL")
        self._ensure_schema()

    def _ensure_schema(self):
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS boundary_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id INTEGER NOT NULL,
                side INTEGER NOT NULL,
                edge_x REAL NOT NULL,
                edge_z REAL NOT NULL,
                lap_dist REAL NOT NULL,
                recorded_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE
            )
        """)
        self.con.execute("CREATE INDEX IF NOT EXISTS idx_bp_track_side ON boundary_points(track_id, side)")
        self.con.commit()

    def get_tracks(self):
        return self.con.execute("SELECT id, track_name FROM tracks ORDER BY track_name").fetchall()

    def get_or_create_track(self, track_name):
        cur = self.con.execute("SELECT id FROM tracks WHERE track_name=?", (track_name,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur = self.con.execute("INSERT INTO tracks (track_name) VALUES (?)", (track_name,))
        self.con.commit()
        return cur.lastrowid

    def get_points(self, track_id, side):
        return self.con.execute(
            "SELECT id, edge_x, edge_z, lap_dist FROM boundary_points WHERE track_id=? AND side=? ORDER BY lap_dist",
            (track_id, side),
        ).fetchall()

    def get_all_points(self, track_id):
        return self.con.execute(
            "SELECT side, edge_x, edge_z, lap_dist FROM boundary_points WHERE track_id=? ORDER BY lap_dist",
            (track_id,),
        ).fetchall()

    def insert_point(self, track_id, side, edge_x, edge_z, lap_dist):
        self.con.execute(
            "INSERT INTO boundary_points (track_id, side, edge_x, edge_z, lap_dist) VALUES (?, ?, ?, ?, ?)",
            (track_id, side, edge_x, edge_z, lap_dist),
        )

    def replace_side_points(self, track_id, side, points):
        self.con.execute("DELETE FROM boundary_points WHERE track_id=? AND side=?", (track_id, side))
        for x, z, ld in points:
            self.con.execute(
                "INSERT INTO boundary_points (track_id, side, edge_x, edge_z, lap_dist) VALUES (?, ?, ?, ?, ?)",
                (track_id, side, x, z, ld),
            )

    def replace_all_points(self, track_id, left, right, step=2.0):
        self.con.execute("DELETE FROM boundary_points WHERE track_id=?", (track_id,))
        for side, pts in [(0, left), (1, right)]:
            for i, p in enumerate(pts):
                self.con.execute(
                    "INSERT INTO boundary_points (track_id, side, edge_x, edge_z, lap_dist) VALUES (?, ?, ?, ?, ?)",
                    (track_id, side, p[0], p[1], i * step),
                )
        self.con.commit()

    def delete_track(self, track_id):
        self.con.execute("DELETE FROM boundary_points WHERE track_id=?", (track_id,))
        self.con.execute("DELETE FROM tracks WHERE id=?", (track_id,))
        self.con.commit()

    def parse_csv(self, path):
        name = os.path.splitext(os.path.basename(path))[0].replace("_", " ")
        with open(path, newline="") as f:
            header = f.readline().strip()
        required = {"side", "edge_x", "edge_z", "lap_dist"}
        cols = {c.strip().lower() for c in header.split(",")}
        if not required.issubset(cols):
            missing = required - cols
            raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")

        valid = []
        errors = []
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, start=2):
                try:
                    side = int(row["side"])
                    ex = float(row["edge_x"])
                    ez = float(row["edge_z"])
                    ld = float(row["lap_dist"])
                    if side not in (0, 1):
                        raise ValueError(f"side must be 0 or 1, got {side}")
                    valid.append((side, ex, ez, ld))
                except (ValueError, KeyError) as e:
                    errors.append(f"  Line {i}: {e}")
                    if len(errors) >= 10:
                        errors.append("  ... more errors omitted")
                        break
        return name, valid, errors

    def import_points(self, track_name, points):
        self.con.execute("INSERT OR IGNORE INTO tracks (track_name) VALUES (?)", (track_name,))
        tid = self.con.execute("SELECT id FROM tracks WHERE track_name=?", (track_name,)).fetchone()[0]
        self.con.execute("DELETE FROM boundary_points WHERE track_id=?", (tid,))
        for side, ex, ez, ld in points:
            self.con.execute(
                "INSERT INTO boundary_points (track_id, side, edge_x, edge_z, lap_dist) VALUES (?, ?, ?, ?, ?)",
                (tid, side, ex, ez, ld),
            )
        self.con.commit()
        return tid

    def export_csv_to_dir(self, track_id, track_name, directory):
        rows = self.get_all_points(track_id)
        if not rows:
            return None
        name = track_name.replace(" ", "_") + ".csv"
        path = os.path.join(directory, name)
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["side", "edge_x", "edge_z", "lap_dist"])
            for r in rows:
                w.writerow([r[0], f"{r[1]:.6f}", f"{r[2]:.6f}", f"{r[3]:.2f}"])
        return path

    @staticmethod
    def write_csv(path, points):
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["side", "edge_x", "edge_z", "lap_dist"])
            for side, x, z, ld in points:
                w.writerow([side, f"{x:.6f}", f"{z:.6f}", f"{ld:.2f}"])

    def commit(self):
        self.con.commit()

    def close(self):
        self.con.close()
