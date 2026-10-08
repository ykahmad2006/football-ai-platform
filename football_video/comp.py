"""Automated player comp: find events, cut clips, label them, join into one video."""
import logging
import re
import shutil
import subprocess
from pathlib import Path

from . import db
from .clip import OUTPUT_DIR, _run
from .probe import VideoError, probe

log = logging.getLogger(__name__)

SIZES = {"16:9": (1280, 720), "9:16": (720, 1280), "1:1": (720, 720), "4:5": (720, 900)}
FONTS = ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/System/Library/Fonts/Supplemental/Arial Bold.ttf"]


def clock_label(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 60}:{s % 60:02d}"


def merge_windows(windows: list[dict]) -> list[dict]:
    """Join clips that overlap so the same moment is not shown twice."""
    merged: list[dict] = []
    for w in sorted(windows, key=lambda w: w["start"]):
        if merged and w["start"] <= merged[-1]["end"]:
            merged[-1]["end"] = max(merged[-1]["end"], w["end"])
            merged[-1]["types"] += [t for t in w["types"] if t not in merged[-1]["types"]]
        else:
            merged.append({**w, "types": list(w["types"])})
    return merged


def build_windows(rows, pre: float, post: float, duration: float) -> list[dict]:
    windows = []
    for r in rows:
        t = db.event_video_time(r["match_clock"], r["period"],
                                r["first_half_start"], r["second_half_start"])
        if t >= duration:
            log.warning("Event %d is past the end of the video, skipped. Check --h1/--h2.", r["id"])
            continue
        windows.append({"start": max(0.0, t - pre), "end": min(duration, t + post),
                        "types": [r["event_type"]], "clock": r["match_clock"]})
    return merge_windows(windows)


def _clean(text: str) -> str:
    return re.sub(r"[%\\]", "", text)


def _has_audio(path: str) -> bool:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0",
                          "-show_entries", "stream=codec_type", "-of", "csv=p=0", path],
                         capture_output=True, text=True)
    return bool(out.stdout.strip())


def _find_font() -> Path | None:
    return next((Path(f) for f in FONTS if Path(f).exists()), None)


def _text(font: str, textfile: Path, size: int, pos: str) -> str:
    return (f"drawtext=fontfile={font}:textfile={textfile.as_posix()}:fontsize={size}:"
            f"fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=10:{pos}")


def _make_segment(src, w, idx, tmp, size, font, player, match_title, has_audio) -> Path:
    W, H = size
    base = min(W, H) // 18
    out = tmp / f"seg_{idx:03d}.mp4"
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25")
    if font:
        labels = {
            "name": (_clean(player), base, "x=24:y=24"),
            "event": (_clean(" / ".join(w["types"])) + "  " + clock_label(w["clock"]),
                      base, "x=24:y=h-text_h-24"),
            "match": (_clean(match_title), int(base * 0.7), "x=w-text_w-24:y=24"),
        }
        for key, (text, fsize, pos) in labels.items():
            f = tmp / f"label_{idx:03d}_{key}.txt"
            f.write_text(text, encoding="utf-8")
            vf += "," + _text((tmp / "font.ttf").as_posix(), f, fsize, pos)
    cmd = ["ffmpeg", "-y", "-ss", str(w["start"]), "-i", str(src)]
    if not has_audio:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    cmd += ["-t", str(w["end"] - w["start"]), "-vf", vf,
            "-map", "0:v:0", "-map", "0:a:0" if has_audio else "1:a:0",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-r", "25",
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2", "-shortest", str(out)]
    _run(cmd, f"Segment {idx + 1}")
    return out


def make_comp(match_id: int, player_id: int, types: list[str] | None, pre: float,
              post: float, fmt: str, name: str | None = None) -> Path:
    if fmt not in SIZES:
        raise VideoError(f"Unknown format '{fmt}'. Use one of: {', '.join(SIZES)}")
    rows = db.get_comp_events(match_id, player_id, types)
    if not rows:
        raise VideoError("No matching events. Check the match ID, player ID and event types, "
                         "and that a video is linked to the match.")
    src = Path(rows[0]["path"])
    if not src.exists():
        raise VideoError(f"Video file missing: {src}. Link the video again.")
    player = rows[0]["player"]
    match_title = f"{rows[0]['home_team']} vs {rows[0]['away_team']}"
    windows = build_windows(rows, pre, post, probe(str(src)).duration)
    if not windows:
        raise VideoError("All events fall outside the video. Check --h1 and --h2 when linking.")

    log.info("Comp for %s: %d events became %d clips (%s)", player, len(rows), len(windows), fmt)
    out_dir = OUTPUT_DIR / "comps"
    tmp = out_dir / "_tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    try:
        font = _find_font()
        if font:
            shutil.copy(font, tmp / "font.ttf")
        else:
            log.warning("No font found, labels will be skipped.")
        audio = _has_audio(str(src))
        segs = []
        for i, w in enumerate(windows):
            log.info("Cutting clip %d of %d (%s)", i + 1, len(windows), " / ".join(w["types"]))
            segs.append(_make_segment(src, w, i, tmp, SIZES[fmt], bool(font), player, match_title, audio))
        (tmp / "list.txt").write_text("".join(f"file '{s.name}'\n" for s in segs), encoding="utf-8")
        stem = name or re.sub(r"[^A-Za-z0-9]+", "_", f"{player}_{match_title}").strip("_")
        out = out_dir / f"{stem}_{fmt.replace(':', 'x')}.mp4"
        log.info("Joining clips")
        _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"),
              "-c", "copy", "-movflags", "+faststart", str(out)], "Joining clips")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    log.info("Comp saved: %s (%.1f MB)", out, out.stat().st_size / 1_048_576)
    return out