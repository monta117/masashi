#!/usr/bin/env python3
"""Download a video (Instagram, YouTube, etc.) and transcribe it with local Whisper."""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path


def download_audio(url: str, out_dir: Path) -> Path:
    import yt_dlp

    out_template = str(out_dir / "audio.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": False,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    audio_path = out_dir / "audio.mp3"
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio download failed: {audio_path} not found")
    return audio_path


def transcribe(audio_path: Path, model_name: str, language: str | None) -> dict:
    import whisper

    model = whisper.load_model(model_name)
    return model.transcribe(str(audio_path), language=language, verbose=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="Video URL (Instagram reel, YouTube, etc.)")
    parser.add_argument(
        "-m",
        "--model",
        default="medium",
        help="Whisper model: tiny, base, small, medium, large, large-v3 (default: medium)",
    )
    parser.add_argument(
        "-l",
        "--language",
        default="ja",
        help="Source language code, e.g. ja, en. Omit or set 'auto' to auto-detect (default: ja)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write transcript to this file (default: stdout)",
    )
    parser.add_argument(
        "--keep-audio",
        type=Path,
        help="If set, save the downloaded mp3 to this path",
    )
    args = parser.parse_args()

    if shutil.which("ffmpeg") is None:
        print("Error: ffmpeg is required. Install it (e.g. `apt install ffmpeg` or `brew install ffmpeg`).", file=sys.stderr)
        return 1

    language = None if args.language.lower() == "auto" else args.language

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        print(f"Downloading audio from {args.url} ...", file=sys.stderr)
        audio_path = download_audio(args.url, tmp_dir)

        if args.keep_audio:
            args.keep_audio.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(audio_path, args.keep_audio)
            print(f"Saved audio to {args.keep_audio}", file=sys.stderr)

        print(f"Loading Whisper model '{args.model}' and transcribing ...", file=sys.stderr)
        result = transcribe(audio_path, args.model, language)

    text = result.get("text", "").strip()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"Wrote transcript to {args.output}", file=sys.stderr)
    else:
        print(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
