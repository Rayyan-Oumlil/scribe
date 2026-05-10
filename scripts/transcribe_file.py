"""Transcribe a single audio file with faster-whisper.

Usage: python transcribe_file.py <audio_path> [--lang fr|en|auto] [--model large-v3-turbo]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path


def add_cuda_to_path() -> None:
    nvidia_root = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    if not nvidia_root.exists():
        return
    for sub in ("cublas/bin", "cudnn/bin"):
        p = nvidia_root / sub
        if p.exists():
            os.add_dll_directory(str(p))
            os.environ["PATH"] = f"{p};{os.environ.get('PATH', '')}"


add_cuda_to_path()
from faster_whisper import WhisperModel  # noqa: E402


def pick_device() -> tuple[str, str]:
    try:
        import ctranslate2  # type: ignore
        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("audio", help="Path to audio/video file")
    ap.add_argument("--lang", default="auto", help="Language code or 'auto'")
    ap.add_argument("--model", default="large-v3-turbo")
    ap.add_argument("--out", default=None, help="Output .txt path (default alongside audio)")
    args = ap.parse_args()

    audio_path = Path(args.audio).expanduser().resolve()
    if not audio_path.exists():
        print(f"ERROR: file not found: {audio_path}", file=sys.stderr)
        return 1

    device, compute_type = pick_device()
    print(f"[load] model={args.model} device={device} compute_type={compute_type}")
    t0 = time.time()
    model = WhisperModel(args.model, device=device, compute_type=compute_type)
    print(f"[load] ready in {time.time() - t0:.1f}s")

    lang = None if args.lang == "auto" else args.lang
    print(f"[transcribe] {audio_path.name}  lang={lang or 'auto'}")
    t0 = time.time()
    segments, info = model.transcribe(
        str(audio_path),
        language=lang,
        beam_size=5,
        vad_filter=True,
    )
    detected = info.language
    print(f"[transcribe] detected_language={detected}  duration={info.duration:.1f}s")

    out_path = Path(args.out) if args.out else audio_path.with_suffix(".txt")
    parts: list[str] = []
    with out_path.open("w", encoding="utf-8") as f:
        for seg in segments:
            line = f"[{seg.start:7.2f} -> {seg.end:7.2f}] {seg.text.strip()}"
            print(line, flush=True)
            f.write(seg.text.strip() + "\n")
            parts.append(seg.text.strip())

    elapsed = time.time() - t0
    print(f"\n[done] wrote {out_path}  ({elapsed:.1f}s, {len(parts)} segments)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
