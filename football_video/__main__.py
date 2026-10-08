"""CLI entry point. Examples:
  python -m football_video info match.mp4
  python -m football_video clip match.mp4 --start 00:32:14 --end 00:32:28
  python -m football_video thumbnail match.mp4 --at 00:10:00
  python -m football_video frames match.mp4 --start 00:10:00 --end 00:10:10 --fps 2
  python -m football_video whatsapp clip.mp4
  python -m football_video comp --match 1 --player 1 --types Goal,Shot --format 16:9,9:16
  python -m football_video gif clip.mp4
"""
import argparse
import logging
import sys

from .clip import extract_frames, make_clip, make_thumbnail
from .comp import make_comp
from . import dbcli
from .export import make_gif, make_whatsapp
from .probe import VideoError, probe


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="football-video")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("info", help="Show video metadata").add_argument("video")

    c = sub.add_parser("clip", help="Cut a clip")
    c.add_argument("video")
    c.add_argument("--start", required=True)
    c.add_argument("--end", required=True)

    t = sub.add_parser("thumbnail", help="Save one frame as a JPG")
    t.add_argument("video")
    t.add_argument("--at", required=True)

    f = sub.add_parser("frames", help="Extract frames from a time range")
    f.add_argument("video")
    f.add_argument("--start", required=True)
    f.add_argument("--end", required=True)
    f.add_argument("--fps", type=float, default=1.0)

    w = sub.add_parser("whatsapp", help="Convert to a WhatsApp-compatible MP4")
    w.add_argument("video")
    w.add_argument("--crf", type=int, default=28, help="Quality, higher = smaller file")

    g = sub.add_parser("gif", help="Create a GIF")
    g.add_argument("video")
    g.add_argument("--fps", type=int, default=12)
    g.add_argument("--width", type=int, default=480)
    g.add_argument("--max-seconds", type=float, default=15.0)

    k = sub.add_parser("comp", help="Generate a player compilation")
    k.add_argument("--match", type=int, required=True)
    k.add_argument("--player", type=int, required=True)
    k.add_argument("--types", help="Comma list, e.g. Goal,Shot. Default: all events")
    k.add_argument("--pre", type=float, default=8, help="Seconds before each event")
    k.add_argument("--post", type=float, default=6, help="Seconds after each event")
    k.add_argument("--format", default="16:9", help="16:9, 9:16, 1:1, 4:5 (comma list allowed)")
    k.add_argument("--name", help="Output file name without extension")
    dbcli.register(sub)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        if args.command == "info":
            v = probe(args.video)
            print(f"File:       {v.path.name}")
            print(f"Duration:   {v.duration_hms()} ({v.duration:.1f}s)")
            print(f"FPS:        {v.fps}")
            print(f"Resolution: {v.width}x{v.height}")
            print(f"Codec:      {v.codec}")
            print(f"Size:       {v.size_mb} MB")
        elif args.command == "clip":
            make_clip(args.video, args.start, args.end)
        elif args.command == "thumbnail":
            make_thumbnail(args.video, args.at)
        elif args.command == "frames":
            extract_frames(args.video, args.start, args.end, args.fps)
        elif args.command == "whatsapp":
            make_whatsapp(args.video, args.crf)
        elif args.command == "comp":
            types = [t.strip() for t in args.types.split(",")] if args.types else None
            for fmt in [f.strip() for f in args.format.split(",")]:
                make_comp(args.match, args.player, types, args.pre, args.post, fmt, args.name)
        elif args.command in dbcli.COMMANDS:
            dbcli.handle(args)
        elif args.command == "gif":
            make_gif(args.video, args.fps, args.width, args.max_seconds)
    except VideoError as e:
        logging.error(e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())