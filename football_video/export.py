"""Export clips as WhatsApp-compatible MP4 and GIF."""
import logging
from pathlib import Path

from .clip import OUTPUT_DIR, _check, _run
from .probe import VideoError, probe

log = logging.getLogger(__name__)
WHATSAPP_LIMIT_MB = 16


def make_whatsapp(video: str, crf: int = 28) -> Path:
    src = _check(video)
    out_dir = OUTPUT_DIR / "whatsapp"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{src.stem}_whatsapp.mp4"
    log.info("Converting to WhatsApp format (H.264 + AAC, max height 720)")
    _run(["ffmpeg", "-y", "-i", str(src),
          "-vf", "scale=-2:'min(720,ih)'",
          "-c:v", "libx264", "-profile:v", "main", "-pix_fmt", "yuv420p",
          "-preset", "veryfast", "-crf", str(crf),
          "-map", "0:v:0", "-map", "0:a:0?",
          "-c:a", "aac", "-b:a", "128k", "-ac", "2",
          "-movflags", "+faststart", str(out)], "WhatsApp conversion")
    size = out.stat().st_size / 1_048_576
    log.info("Saved: %s (%.1f MB)", out, size)
    if size > WHATSAPP_LIMIT_MB:
        log.warning("File is over %d MB. WhatsApp may send it as a document. "
                    "Use a shorter clip or a higher --crf (for example 32).", WHATSAPP_LIMIT_MB)
    return out


def make_gif(video: str, fps: int = 12, width: int = 480, max_seconds: float = 15.0) -> Path:
    src = _check(video)
    info = probe(str(src))
    if info.duration > max_seconds:
        raise VideoError(f"Video is {info.duration:.0f}s. GIFs get huge past {max_seconds:.0f}s. "
                         "Cut a shorter clip first, or raise --max-seconds.")
    out_dir = OUTPUT_DIR / "gifs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{src.stem}.gif"
    log.info("Creating GIF (%d fps, %dpx wide)", fps, width)
    vf = (f"fps={fps},scale={width}:-1:flags=lanczos,split[a][b];"
          "[a]palettegen[p];[b][p]paletteuse")
    _run(["ffmpeg", "-y", "-i", str(src), "-vf", vf, "-loop", "0", str(out)], "GIF creation")
    log.info("Saved: %s (%.1f MB)", out, out.stat().st_size / 1_048_576)
    return out