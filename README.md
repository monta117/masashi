# masashi

Local video transcription using [yt-dlp](https://github.com/yt-dlp/yt-dlp) and
[OpenAI Whisper](https://github.com/openai/whisper). Works with Instagram reels,
YouTube, and any other source yt-dlp supports.

## Setup

System requirements:

- Python 3.9+
- `ffmpeg` (`brew install ffmpeg` on macOS, `apt install ffmpeg` on Debian/Ubuntu)

Python packages:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

A CUDA-capable GPU is optional but greatly speeds up the larger Whisper models.
On CPU, prefer `small` or `medium`; `large-v3` will be slow.

## Usage

```bash
# Transcribe an Instagram reel to stdout (Japanese, medium model)
python transcribe.py "https://www.instagram.com/reel/XXXXXXXX/"

# Specify model and write to a file
python transcribe.py "https://..." -m large-v3 -o transcript.txt

# Auto-detect language and keep the downloaded audio
python transcribe.py "https://..." -l auto --keep-audio out/audio.mp3
```

Options:

- `-m, --model`: `tiny` / `base` / `small` / `medium` / `large` / `large-v3` (default `medium`)
- `-l, --language`: ISO code such as `ja`, `en`. Use `auto` to auto-detect (default `ja`)
- `-o, --output`: write transcript to file instead of stdout
- `--keep-audio`: save the extracted mp3 to the given path

## Notes

- Some Instagram posts require authentication. If a download fails, export your
  browser cookies and pass them via yt-dlp's `--cookies` mechanism (you can
  extend `transcribe.py` to forward `cookiefile` in `ydl_opts`).
- Whisper models are downloaded on first use and cached under `~/.cache/whisper/`.
