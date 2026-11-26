<div align="center">

# 🎬 Video Clipper

**Turn any YouTube gameplay stream into vertical Shorts / Reels / TikToks in one command.**
Face-cam on top, gameplay below, word-by-word auto-captions. No video editor needed.

[![CI](https://github.com/MohdArhan2/video-clipper/actions/workflows/ci.yml/badge.svg)](https://github.com/MohdArhan2/video-clipper/actions)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/MohdArhan2/video-clipper/blob/main/notebooks/clipstack_colab.ipynb)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

</div>
<img src="demo.gif" width="300" alt="Video Clipper demo">

## ✨ Features

- ⚡ **Only downloads the part you need**: no 6-hour VOD downloads, just the time range you ask for
- 📱 **1080×1920 vertical output**: face-cam on top, gameplay on the bottom
- 💬 **Auto-captions** with [faster-whisper](https://github.com/SYSTRAN/faster-whisper): runs locally, free, no API key
- 🎯 **Preview mode**: draws crop boxes on a frame so you can line things up before rendering
- 🧩 **Batch mode**: list as many clips as you want in one YAML file
- ☁️ **Works anywhere**: CLI, Python API, or one-click Google Colab notebook (no GPU needed)

## 🚀 Quick start

### Option 1: Google Colab (zero setup)
Click the **Open in Colab** badge above, paste your URL and timestamps, run.

### Option 2: Command line

```bash
# requires Python 3.9+ and ffmpeg
git clone https://github.com/MohdArhan2/video-clipper && cd video-clipper
pip install -e .

# one clip
clipstack --url "https://youtu.be/XXXX" --start 00:04:34 --end 00:05:04 --name my_clip

# many clips from a config
cp config.example.yaml config.yaml
clipstack -c config.yaml --preview     # check the crop boxes first
clipstack -c config.yaml               # render everything
```

> The command and Python package are called `clipstack`.

Install ffmpeg: `sudo apt install ffmpeg` · `brew install ffmpeg` · `winget install ffmpeg`

### Option 3: Python API

```python
from clipstack import Settings, Clip, process_all

process_all(Settings(
    url="https://youtu.be/XXXX",
    clips=[Clip("00:04:34", "00:05:04", "funny_moment")],
))
```

## 🧭 How it works

```
YouTube URL ──yt-dlp──► stream URLs ──ffmpeg -ss/-t──► raw clip
                                                          │
                                   faster-whisper ◄───────┤ (audio)
                                          │               │
                                   word-timed .ass        │
                                          ▼               ▼
                    crop face-cam ──►  ┌───────────┐
                                       │ face-cam  │  1080×860
                    vstack + burn ──►  ├───────────┤
                    captions           │ gameplay  │  1080×1060
                    crop game     ──►  └───────────┘
                                          │
                                          ▼
                          vertical .mp4 (H.264 + AAC)
```

## ⚙️ Configuration

| Option | Default | Description |
|---|---|---|
| `url` | required | YouTube video URL |
| `clips` | required | List of `{start, end, name}` |
| `out_dir` | `clips` | Where finished videos are saved |
| `captions` | `true` | Burn in auto-captions |
| `model` | `base.en` | Whisper model: `tiny.en`, `base.en`, `small.en`, `medium.en`, `large-v3` |
| `words_per_caption` | `3` | Words shown at once |
| `top_height` | `860` | Pixels of the 1920px frame used by the face section |
| `facecam` | `x0 y.40 w.20 h.25` | Crop box for the face-cam (fractions of source frame) |
| `game` | `x.21 y0 w.57 h1` | Crop box for gameplay |
| `font`, `font_size` | `DejaVu Sans`, `74` | Caption style |
| `cookies` | none | Path to `cookies.txt` (see below) |

### Finding the right crop boxes
Run with `--preview`. You'll get a frame with a **red** box (face-cam) and a **green** box (gameplay). Adjust `facecam` / `game` until they fit your streamer's layout, then render.

### Cookies (age-restricted or "confirm you're not a bot" videos)
Export your YouTube cookies with a browser extension such as *Get cookies.txt LOCALLY*, save as `cookies.txt`, and pass `--cookies cookies.txt` or set `cookies:` in the config. **Never commit this file** (it's in `.gitignore`).

## 🛠 Troubleshooting

| Problem | Fix |
|---|---|
| `ffmpeg not found` | Install ffmpeg and make sure it's on your PATH |
| `Sign in to confirm you're not a bot` | Use cookies (above) and `pip install -U yt-dlp` |
| Captions missing | The clip had no detected speech, or try a bigger `model` |
| Face-cam is cut off | Run `--preview` and tweak `facecam` |
| Slow transcription | Use `tiny.en` / `base.en` |

## 🗺 Roadmap

- [ ] Auto-detect face-cam position
- [ ] Karaoke-style highlighted captions + colour themes
- [ ] More layouts (side-by-side, picture-in-picture, full-screen)
- [ ] Auto-find highlight moments (audio peaks / chat spikes)
- [ ] GPU encoding (NVENC)
- [ ] Direct upload to YouTube Shorts

PRs welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## ⚖️ Legal / responsible use

This tool is for clipping content **you own or have permission to reuse**. Downloading videos may violate YouTube's Terms of Service, and reuploading other creators' content without permission may infringe copyright. You are responsible for how you use it. Not affiliated with YouTube, Google or OpenAI.

## 📄 License

[MIT](LICENSE)

## 🙏 Built with

[yt-dlp](https://github.com/yt-dlp/yt-dlp) · [FFmpeg](https://ffmpeg.org) · [faster-whisper](https://github.com/SYSTRAN/faster-whisper)

---
⭐ If Video Clipper saved you editing time, please star the repo, it really helps!
