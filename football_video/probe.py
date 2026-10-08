"""Read video metadata with ffprobe (ships with FFmpeg)."""
import json
import logging
import subprocess
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

log = logging.getLogger(__name__)
SUPPORTED = {".mp4", ".mov", ".mkv", ".webm"}


class VideoError(Exception):
    """Raised when a video cannot be read. The message says what to fix."""


@dataclass
class VideoInfo:
    path: Path
    duration: float
    fps: float
    width: int
    height: int
    codec: str
    size_mb: float

    def duration_hms(self) -> str:
        total = int(round(self.duration))
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"


def probe(path: str) -> VideoInfo:
    p = Path(path)
    if not p.exists():
        raise VideoError(f"File not found: {p}. Check the path.")
    if p.suffix.lower() not in SUPPORTED:
        raise VideoError(f"Unsupported format '{p.suffix}'. Use: {sorted(SUPPORTED)}")

    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
           "-show_entries", "stream=codec_name,width,height,r_frame_rate:format=duration,size",
           "-of", "json", str(p)]
    log.info("Reading metadata: %s", p.name)
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except FileNotFoundError:
        raise VideoError("ffprobe not found. Install FFmpeg and reopen your terminal.")
    except subprocess.CalledProcessError as e:
        raise VideoError(f"ffprobe failed (file may be corrupt): {e.stderr.strip()}")

    data = json.loads(out.stdout)
    if not data.get("streams"):
        raise VideoError("No video stream found in this file.")
    s, f = data["streams"][0], data["format"]
    return VideoInfo(
        path=p,
        duration=float(f["duration"]),
        fps=round(float(Fraction(s["r_frame_rate"])), 3),
        width=int(s["width"]),
        height=int(s["height"]),
        codec=s["codec_name"],
        size_mb=round(int(f["size"]) / 1_048_576, 2),
    )