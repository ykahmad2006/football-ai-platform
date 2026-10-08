"""CLI commands for the database: db, match, player, video, event."""
import logging
from pathlib import Path

from . import db
from .clip import make_clip, parse_timestamp
from .probe import VideoError

log = logging.getLogger(__name__)
COMMANDS = {"db", "match", "player", "video", "event"}


def _fmt(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 60:02d}:{s % 60:02d}"


def register(sub) -> None:
    sub.add_parser("db", help="Database tools").add_subparsers(
        dest="action", required=True).add_parser("init", help="Create the database")

    m = sub.add_parser("match", help="Matches").add_subparsers(dest="action", required=True)
    a = m.add_parser("add")
    a.add_argument("--home", required=True)
    a.add_argument("--away", required=True)
    a.add_argument("--date")
    a.add_argument("--competition")

    p = sub.add_parser("player", help="Players").add_subparsers(dest="action", required=True)
    a = p.add_parser("add")
    a.add_argument("--name", required=True)
    a.add_argument("--team")

    v = sub.add_parser("video", help="Videos").add_subparsers(dest="action", required=True)
    a = v.add_parser("link", help="Link a video file to a match")
    a.add_argument("--match", type=int, required=True)
    a.add_argument("--file", required=True)
    a.add_argument("--h1", default="0", help="Video time when 1st half kicks off")
    a.add_argument("--h2", default="0", help="Video time when 2nd half kicks off")

    e = sub.add_parser("event", help="Events").add_subparsers(dest="action", required=True)
    a = e.add_parser("add")
    a.add_argument("--match", type=int, required=True)
    a.add_argument("--player", type=int)
    a.add_argument("--type", required=True, help="Goal, Shot, Pass, Dribble...")
    a.add_argument("--period", type=int, choices=[1, 2], required=True)
    a.add_argument("--clock", required=True, help="Match clock, e.g. 75:21")
    a = e.add_parser("list")
    a.add_argument("--match", type=int, required=True)
    a = e.add_parser("clip", help="Cut a clip around an event")
    a.add_argument("event_id", type=int)
    a.add_argument("--pre", type=float, default=10, help="Seconds before the event")
    a.add_argument("--post", type=float, default=8, help="Seconds after the event")


def handle(args) -> None:
    cmd, act = args.command, args.action
    if cmd == "db":
        db.init_db()
        log.info("Database ready: %s", db.DB_PATH)
    elif cmd == "match":
        log.info("Match saved with ID %d", db.add_match(args.home, args.away, args.date, args.competition))
    elif cmd == "player":
        log.info("Player saved with ID %d", db.add_player(args.name, args.team))
    elif cmd == "video":
        path = Path(args.file)
        if not path.exists():
            raise VideoError(f"File not found: {path}")
        vid = db.link_video(args.match, str(path.resolve()),
                            parse_timestamp(args.h1), parse_timestamp(args.h2))
        log.info("Video linked with ID %d", vid)
    elif cmd == "event" and act == "add":
        eid = db.add_event(args.match, args.player, args.type, args.period, parse_timestamp(args.clock))
        log.info("Event saved with ID %d", eid)
    elif cmd == "event" and act == "list":
        rows = db.list_events(args.match)
        if not rows:
            print("No events for this match.")
        for r in rows:
            print(f"[{r['id']}] {_fmt(r['match_clock'])}  half {r['period']}  "
                  f"{r['event_type']}  {r['player'] or '-'}")
    elif cmd == "event" and act == "clip":
        ev = db.get_event_with_video(args.event_id)
        t = db.event_video_time(ev["match_clock"], ev["period"],
                                ev["first_half_start"], ev["second_half_start"])
        start, end = max(0.0, t - args.pre), t + args.post
        clip_path = make_clip(ev["path"], str(start), str(end))
        db.add_clip(args.event_id, clip_path, start, end)
        log.info("Clip linked to event %d", args.event_id)