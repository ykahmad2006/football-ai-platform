"""Clips, thumbnails and frame extraction using FFmpeg."""
import logging
import subprocess
from pathlib import Path

from .probe import VideoError

log = logging.getLogger(__name__)
OUTPUT_DIR = Path("outputs")


def parse_timestamp(value: str) -> float:
    """Accepts SS, MM:SS or HH:MM:SS (decimals allowed). Returns seconds."""
    try:
        parts = [float(x) for x in value.split(":")]
    except ValueError:
        raise VideoError(f"Bad timestamp '{value}'. Use HH:MM:SS, MM:SS or seconds.")
    if not 1 <= len(parts) <= 3 or any(p < 0 for p in parts):
        raise VideoError(f"Bad timestamp '{value}'. Use HH:MM:SS, MM:SS or seconds.")
    seconds = 0.0
    for p in parts:
        seconds = seconds * 60 + p
    return seconds


def _label(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600:02d}{(s % 3600) // 60:02d}{s % 60:02d}"


def _run(cmd: list[str], what: str) -> None:
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except FileNotFoundError:
        raise VideoError("ffmpeg not found. Install FFmpeg and reopen your terminal.")
    except subprocess.CalledProcessError as e:
        tail = "\n".join(e.stderr.strip().splitlines()[-3:])
        raise VideoError(f"{what} failed: {tail}")


def _check(video: str) -> Path:
    p = Path(video)
    if not p.exists():
        raise VideoError(f"File not found: {p}. Check the path.")
    return p


def make_clip(video: str, start: str, end: str) -> Path:
    src = _check(video)
    a, b = parse_timestamp(start), parse_timestamp(end)
    if b <= a:
        raise VideoError("End time must be after start time.")
    out_dir = OUTPUT_DIR / "clips"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{src.stem}_{_label(a)}-{_label(b)}.mp4"
    log.info("Cutting clip %s to %s (%.1fs)", start, end, b - a)
    _run(["ffmpeg", "-y", "-ss", str(a), "-i", str(src), "-t", str(b - a),
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
          "-c:a", "aac", "-movflags", "+faststart", str(out)], "Clip cutting")
    log.info("Clip saved: %s", out)
    return out


def make_thumbnail(video: str, at: str) -> Path:
    src = _check(video)
    t = parse_timestamp(at)
    out_dir = OUTPUT_DIR / "thumbnails"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{src.stem}_{_label(t)}.jpg"
    log.info("Creating thumbnail at %s", at)
    _run(["ffmpeg", "-y", "-ss", str(t), "-i", str(src), "-frames:v", "1",
          "-q:v", "2", str(out)], "Thumbnail")
    log.info("Thumbnail saved: %s", out)
    return out


def extract_frames(video: str, start: str, end: str, fps: float = 1.0) -> Path:
    src = _check(video)
    a, b = parse_timestamp(start), parse_timestamp(end)
    if b <= a:
        raise VideoError("End time must be after start time.")
    if (b - a) * fps > 500:
        raise VideoError("That would create over 500 frames. Use a shorter range or lower --fps.")
    out_dir = OUTPUT_DIR / "frames" / f"{src.stem}_{_label(a)}-{_label(b)}"
    out_dir.mkdir(parents=True, exist_ok=True)
    log.info("Extracting frames at %s fps", fps)
    _run(["ffmpeg", "-y", "-ss", str(a), "-i", str(src), "-t", str(b - a),
          "-vf", f"fps={fps}", "-q:v", "2", str(out_dir / "frame_%04d.jpg")], "Frame extraction")
    log.info("Frames saved in: %s", out_dir)
    return out_dir