"""SQLite database: Match -> Video -> Event -> Player -> Clip."""
import sqlite3
from pathlib import Path

from .probe import VideoError

DB_PATH = Path("data") / "football.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    match_date TEXT,
    competition TEXT
);
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    team TEXT
);
CREATE TABLE IF NOT EXISTS video_files (
    id INTEGER PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES matches(id),
    path TEXT NOT NULL,
    first_half_start REAL NOT NULL DEFAULT 0,
    second_half_start REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES matches(id),
    player_id INTEGER REFERENCES players(id),
    event_type TEXT NOT NULL,
    period INTEGER NOT NULL CHECK (period IN (1, 2)),
    match_clock REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS clips (
    id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id),
    path TEXT NOT NULL,
    start_sec REAL NOT NULL,
    end_sec REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_match ON events(match_id);
CREATE INDEX IF NOT EXISTS idx_events_player ON events(player_id);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def event_video_time(match_clock: float, period: int, first_half_start: float,
                     second_half_start: float) -> float:
    """Convert a match clock (seconds) to a position in the video file."""
    if period == 1:
        return first_half_start + match_clock
    elapsed = match_clock - 45 * 60
    if elapsed < 0:
        raise VideoError("A second-half event cannot be before 45:00 on the match clock.")
    return second_half_start + elapsed


def _insert(sql: str, params: tuple) -> int:
    try:
        with connect() as conn:
            return conn.execute(sql, params).lastrowid
    except sqlite3.OperationalError:
        raise VideoError("Database not ready. Run: python -m football_video db init")
    except sqlite3.IntegrityError as e:
        raise VideoError(f"Database rejected that: {e}. Check the IDs you used.")


def add_match(home, away, date, competition) -> int:
    return _insert("INSERT INTO matches (home_team, away_team, match_date, competition) "
                   "VALUES (?, ?, ?, ?)", (home, away, date, competition))


def add_player(name, team) -> int:
    return _insert("INSERT INTO players (name, team) VALUES (?, ?)", (name, team))


def link_video(match_id, path, h1, h2) -> int:
    return _insert("INSERT INTO video_files (match_id, path, first_half_start, second_half_start) "
                   "VALUES (?, ?, ?, ?)", (match_id, path, h1, h2))


def add_event(match_id, player_id, event_type, period, clock) -> int:
    return _insert("INSERT INTO events (match_id, player_id, event_type, period, match_clock) "
                   "VALUES (?, ?, ?, ?, ?)", (match_id, player_id, event_type, period, clock))


def add_clip(event_id, path, start, end) -> int:
    return _insert("INSERT INTO clips (event_id, path, start_sec, end_sec) VALUES (?, ?, ?, ?)",
                   (event_id, str(path), start, end))


def list_events(match_id: int):
    with connect() as conn:
        return conn.execute(
            "SELECT e.id, e.event_type, e.period, e.match_clock, p.name AS player "
            "FROM events e LEFT JOIN players p ON p.id = e.player_id "
            "WHERE e.match_id = ? ORDER BY e.period, e.match_clock", (match_id,)).fetchall()


def get_event_with_video(event_id: int):
    with connect() as conn:
        row = conn.execute(
            "SELECT e.*, v.path, v.first_half_start, v.second_half_start "
            "FROM events e JOIN video_files v ON v.match_id = e.match_id "
            "WHERE e.id = ? ORDER BY v.id DESC LIMIT 1", (event_id,)).fetchone()
    if row is None:
        raise VideoError(f"Event {event_id} not found, or its match has no video linked. "
                         "Use 'video link' first.")
    return row


def get_comp_events(match_id: int, player_id: int, types: list[str] | None):
    """Events for one player in one match, with the video and match info needed for a comp."""
    sql = ("SELECT e.id, e.event_type, e.period, e.match_clock, p.name AS player, "
           "m.home_team, m.away_team, v.path, v.first_half_start, v.second_half_start "
           "FROM events e "
           "JOIN players p ON p.id = e.player_id "
           "JOIN matches m ON m.id = e.match_id "
           "JOIN video_files v ON v.id = (SELECT MAX(id) FROM video_files WHERE match_id = e.match_id) "
           "WHERE e.match_id = ? AND e.player_id = ?")
    params: list = [match_id, player_id]
    if types:
        sql += " AND LOWER(e.event_type) IN (%s)" % ",".join("?" * len(types))
        params += [t.lower() for t in types]
    sql += " ORDER BY e.period, e.match_clock"
    with connect() as conn:
        return conn.execute(sql, params).fetchall()