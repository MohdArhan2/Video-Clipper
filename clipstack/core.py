"""Core pipeline: download a time range, transcribe, caption, stack, export."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

import numpy as np

OUT_W, OUT_H = 1080, 1920
Time = Union[str, int, float]

FORMAT = "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]"


@dataclass(frozen=True)
class Box:
    """A crop region as fractions (0-1) of the source frame."""
    x: float
    y: float
    w: float
    h: float

    def crop(self) -> str:
        return f"crop=iw*{self.w}:ih*{self.h}:iw*{self.x}:ih*{self.y}"

    def drawbox(self, color: str) -> str:
        return (f"drawbox=x=iw*{self.x}:y=ih*{self.y}:w=iw*{self.w}:h=ih*{self.h}"
                f":color={color}:t=8")


@dataclass
class Clip:
    start: Time
    end: Time
    name: str


@dataclass
class Settings:
    url: str
    clips: List[Clip]
    out_dir: Path = Path("clips")
    cookies: Optional[Path] = None
    captions: bool = True
    model: str = "base.en"            # any faster-whisper model name
    words_per_caption: int = 3
    top_height: int = 860             # height (px) of the face section in the 1080x1920 output
    facecam: Box = Box(0.00, 0.40, 0.20, 0.25)
    game: Box = Box(0.21, 0.00, 0.57, 1.00)
    font: str = "DejaVu Sans"
    font_size: int = 74
    tmp_dir: Path = field(default_factory=lambda: Path(tempfile.gettempdir()) / "clipstack")


# ----------------------------------------------------------------- helpers
def seconds(t: Time) -> float:
    """'HH:MM:SS', 'MM:SS', 'SS' or a number -> seconds."""
    if isinstance(t, (int, float)):
        return float(t)
    return float(sum(float(x) * 60**i for i, x in enumerate(reversed(str(t).split(":")))))


def ass_time(sec: float) -> str:
    cs = round(sec * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def safe_name(name: str) -> str:
    name = re.sub(r"[^\w.-]+", "_", name)
    return (name[:-4] if name.lower().endswith(".mp4") else name) + ".mp4"


def _filter_path(p: Path) -> str:
    """Escape a path for use inside an ffmpeg filter."""
    return str(p).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def _run(cmd: list, **kw) -> subprocess.CompletedProcess:
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        raise RuntimeError(f"{cmd[0]} failed:\n{r.stderr[-1500:]}")
    return r


def check_dependencies() -> None:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found. Install it (apt install ffmpeg / "
                           "brew install ffmpeg / winget install ffmpeg).")


# ---------------------------------------------------------------- download
def download(s: Settings, start: Time, end: Time, out: Path) -> None:
    print(f"Fetching clip at {start} ...")
    cookie_args = ["--cookies", str(s.cookies)] if s.cookies and Path(s.cookies).exists() else []
    urls = _run([sys.executable, "-m", "yt_dlp", "--no-playlist", "-g", "-f", FORMAT,
                 *cookie_args, s.url], timeout=120).stdout.split()
    if not urls:
        raise RuntimeError("yt-dlp returned no stream URLs. Check the video URL / cookies.")

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for u in urls:
        cmd += ["-ss", str(seconds(start)), "-i", u]
    cmd += ["-t", str(seconds(end) - seconds(start))]
    cmd += ["-map", "0:v", "-map", "1:a"] if len(urls) == 2 else ["-map", "0"]
    cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-c:a", "aac", str(out)]
    _run(cmd, timeout=600)
    print("Downloaded.")


# ---------------------------------------------------------------- captions
def load_audio(path: Path) -> np.ndarray:
    out = subprocess.run(
        ["ffmpeg", "-nostdin", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(out, np.float32)


def make_ass(s: Settings, model, video: Path, path: Path) -> bool:
    """Transcribe `video` and write a word-grouped ASS subtitle file. False if no speech."""
    segs, _ = model.transcribe(load_audio(video), word_timestamps=True)
    words = [(w.start, w.end, w.word.strip())
             for seg in segs for w in (seg.words or []) if w.word.strip()]
    if not words:
        return False

    margin_v = OUT_H - s.top_height - 60   # captions sit on the seam between face and game
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {OUT_W}
PlayResY: {OUT_H}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: S,{s.font},{s.font_size},&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,6,2,2,60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    n = s.words_per_caption
    with open(path, "w", encoding="utf-8") as f:
        f.write(head)
        for i in range(0, len(words), n):
            g = words[i:i + n]
            txt = " ".join(w[2] for w in g).upper().replace("{", "(").replace("}", ")")
            f.write(f"Dialogue: 0,{ass_time(g[0][0])},{ass_time(g[-1][1])},S,,0,0,0,,{txt}\n")
    return True


# ------------------------------------------------------------------- build
def _fill(w: int, h: int) -> str:
    return f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1"


def build_video(s: Settings, raw: Path, out: Path, ass: Optional[Path]) -> None:
    subs = f",ass='{_filter_path(ass)}'" if ass else ""
    fc = (f"[0:v]{s.facecam.crop()},{_fill(OUT_W, s.top_height)}[t];"
          f"[0:v]{s.game.crop()},{_fill(OUT_W, OUT_H - s.top_height)}[b];"
          f"[t][b]vstack{subs}[v]")
    _run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(raw),
          "-filter_complex", fc, "-map", "[v]", "-map", "0:a?",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
          "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)])


def make_preview(s: Settings) -> Path:
    """Grab one frame and draw the crop boxes (red = face, green = gameplay)."""
    check_dependencies()
    s.tmp_dir.mkdir(parents=True, exist_ok=True)
    t = seconds(s.clips[0].start) + 2
    prev_mp4, prev_jpg = s.tmp_dir / "prev.mp4", s.tmp_dir / "prev.jpg"
    download(s, t, t + 2, prev_mp4)
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(prev_mp4), "-frames:v", "1",
          "-vf", f"{s.facecam.drawbox('red')},{s.game.drawbox('lime')}", str(prev_jpg)])
    print(f"Preview saved: {prev_jpg}\nRED = face, GREEN = gameplay. Adjust facecam / game and re-run.")
    return prev_jpg


def process_all(s: Settings) -> List[Path]:
    """Download, caption and export every clip in `s.clips`."""
    check_dependencies()
    s.tmp_dir.mkdir(parents=True, exist_ok=True)
    s.out_dir = Path(s.out_dir)
    s.out_dir.mkdir(parents=True, exist_ok=True)

    model = None
    if s.captions:
        from faster_whisper import WhisperModel   # lazy import: heavy
        model = WhisperModel(s.model, device="cpu", compute_type="int8")

    results = []
    for i, c in enumerate(s.clips, 1):
        raw, ass, out = (s.tmp_dir / f"raw{i}.mp4", s.tmp_dir / f"subs{i}.ass",
                         s.tmp_dir / f"out{i}.mp4")
        download(s, c.start, c.end, raw)

        print("Adding captions and building the video ...")
        has_subs = bool(model) and make_ass(s, model, raw, ass)
        build_video(s, raw, out, ass if has_subs else None)

        final = s.out_dir / safe_name(c.name)
        shutil.move(str(out), final)
        for p in (raw, ass):
            p.unlink(missing_ok=True)
        print("Saved:", final)
        results.append(final)
    return results
