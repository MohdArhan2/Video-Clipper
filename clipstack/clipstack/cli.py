"""Command line interface."""
from __future__ import annotations

import argparse
from pathlib import Path

from .core import Box, Clip, Settings, make_preview, process_all


def load_config(path: Path) -> Settings:
    import yaml
    d = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    s = Settings(url=d["url"], clips=[Clip(**c) for c in d.get("clips", [])])
    for key in ("captions", "model", "words_per_caption", "top_height", "font", "font_size"):
        if key in d:
            setattr(s, key, d[key])
    if "out_dir" in d:
        s.out_dir = Path(d["out_dir"]).expanduser()
    if d.get("cookies"):
        s.cookies = Path(d["cookies"]).expanduser()
    if "facecam" in d:
        s.facecam = Box(**d["facecam"])
    if "game" in d:
        s.game = Box(**d["game"])
    return s


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="clipstack",
        description="Turn YouTube gameplay into vertical face-cam + gameplay clips with captions.")
    p.add_argument("-c", "--config", type=Path, help="YAML config file (see config.example.yaml)")
    p.add_argument("--url", help="YouTube URL (quick mode, no config file)")
    p.add_argument("--start", help="start time, e.g. 00:04:34")
    p.add_argument("--end", help="end time, e.g. 00:05:04")
    p.add_argument("--name", default="clip", help="output file name")
    p.add_argument("-o", "--out", type=Path, help="output directory")
    p.add_argument("--cookies", type=Path, help="cookies.txt for age-gated / bot-checked videos")
    p.add_argument("--no-captions", action="store_true", help="skip Whisper captions")
    p.add_argument("--preview", action="store_true", help="draw crop boxes on one frame and exit")
    a = p.parse_args(argv)

    if a.config:
        s = load_config(a.config)
    elif a.url and a.start and a.end:
        s = Settings(url=a.url, clips=[Clip(a.start, a.end, a.name)])
    else:
        p.error("provide --config, or --url with --start and --end")

    if a.out:
        s.out_dir = a.out
    if a.cookies:
        s.cookies = a.cookies
    if a.no_captions:
        s.captions = False

    if a.preview:
        make_preview(s)
    else:
        process_all(s)
    return 0
