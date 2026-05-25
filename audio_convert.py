#!/usr/bin/env python3
"""
Audio Converter — converts 50+ audio formats to WAV / MP3.

Requires ffmpeg on PATH. Download: https://ffmpeg.org

Supported input formats:
  Lossless: flac, wav, aiff, alac, ape, wv, tta, dsf, dff
  Lossy:    mp3, aac, ogg, opus, wma, ac3, dts
  Others:   mid, ra, amr, au, caf, voc, raw/pcm

Usage:
  python audio_convert.py <paths...> [options]

Examples:
  python audio_convert.py song.flac --to mp3
  python audio_convert.py music/ -R --to both -o output/
  python audio_convert.py *.wav --to mp3 --mp3-bitrate 192k
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

SUPPORTED_EXTS = {
    # Lossless
    ".flac", ".wav", ".wave", ".aiff", ".aif", ".aifc",
    ".alac", ".ape", ".wv", ".tta", ".m4a",
    # DSD
    ".dsf", ".dff",
    # Lossy
    ".mp3", ".mp2", ".mp1",
    ".aac", ".m4a", ".m4b", ".m4p", ".m4r", ".3gp", ".3g2",
    ".ogg", ".oga", ".ogv", ".ogx", ".spx", ".opus",
    ".wma", ".asf", ".wmv",
    ".ac3", ".eac3", ".dts", ".mka",
    # Others
    ".ra", ".rm", ".ram",
    ".amr", ".awb",
    ".au", ".snd",
    ".caf",
    ".voc",
    ".mid", ".midi", ".rmi",
    ".aa", ".aax",
    ".raw", ".pcm",
}


def find_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return "ffmpeg"
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    candidates = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\tools\ffmpeg\bin\ffmpeg.exe",
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
    ]
    for p in candidates:
        if Path(p).is_file():
            return p
    return None


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def collect_files(paths, recursive):
    files = []
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            if p.suffix.lower() in SUPPORTED_EXTS:
                files.append(p)
        elif p.is_dir():
            if recursive:
                for root, _, fnames in os.walk(p):
                    root_p = Path(root)
                    for fn in fnames:
                        fp = root_p / fn
                        if fp.suffix.lower() in SUPPORTED_EXTS:
                            files.append(fp)
            else:
                for fn in p.iterdir():
                    if fn.is_file() and fn.suffix.lower() in SUPPORTED_EXTS:
                        files.append(fn)
    return sorted(set(str(f) for f in files), key=str.lower)


def convert_file(src, fmt, outdir, wav_bit, mp3_bitrate, samplerate, delete):
    out_ext = ".wav" if fmt == "wav" else ".mp3"
    dst = outdir / (src.stem + out_ext)

    if dst.resolve() == src.resolve():
        dst = outdir / (src.stem + "_converted" + out_ext)
    if dst.exists():
        base = outdir / src.stem
        idx = 1
        while True:
            dst = Path(f"{base}_{idx}{out_ext}")
            if not dst.exists():
                break
            idx += 1

    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src)]
    if fmt == "wav":
        cmd += ["-acodec", f"pcm_s{16 if wav_bit == 16 else 24}le"]
    else:
        cmd += ["-acodec", "libmp3lame", "-b:a", mp3_bitrate]
    if samplerate:
        cmd += ["-ar", str(samplerate)]
    cmd.append(str(dst))

    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=300)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="replace").strip()
        print(f"  FAIL  {src.name} — {stderr[:120]}")
        return False
    except subprocess.TimeoutExpired:
        print(f"  FAIL  {src.name} — timed out")
        return False

    in_size = src.stat().st_size
    out_size = dst.stat().st_size
    if delete and dst.exists():
        src.unlink()
    print(f"  OK    {src.name}  ->  {dst.name}  "
          f"[{human_size(in_size)} -> {human_size(out_size)}]")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Convert audio files to WAV / MP3 using ffmpeg.",
    )
    parser.add_argument("paths", nargs="+",
                        help="Files and/or directories to convert")
    parser.add_argument("--to", choices=["wav", "mp3", "both"], default="both",
                        help="Output format (default: both)")
    parser.add_argument("--outdir", "-o",
                        help="Output directory (default: ./converted)")
    parser.add_argument("--mp3-bitrate", default="320k",
                        choices=["128k", "192k", "256k", "320k"],
                        help="MP3 bitrate (default: 320k)")
    parser.add_argument("--wav-bit", type=int, default=16, choices=[16, 24],
                        help="WAV bit depth (default: 16)")
    parser.add_argument("--samplerate", "-r", type=int, default=0,
                        help="Resample to this rate (0 = keep original)")
    parser.add_argument("--recursive", "-R", action="store_true",
                        help="Recurse into directories")
    parser.add_argument("--delete-original", action="store_true",
                        help="Delete original after conversion (DANGEROUS)")
    parser.add_argument("--formats", action="store_true",
                        help="List supported input formats and exit")

    args = parser.parse_args()

    if args.formats:
        print(f"\nSupported input formats ({len(SUPPORTED_EXTS)} total):\n")
        for ext in sorted(SUPPORTED_EXTS):
            print(f"  {ext}")
        print()
        return

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("ERROR: ffmpeg not found. Install it and add to PATH.")
        print("  Windows: scoop install ffmpeg")
        print("  macOS:   brew install ffmpeg")
        print("  Linux:   sudo apt install ffmpeg")
        sys.exit(1)

    src_files = collect_files(args.paths, args.recursive)
    if not src_files:
        print("No supported audio files found.")
        return

    outdir = Path(args.outdir) if args.outdir else Path.cwd() / "converted"
    outdir.mkdir(parents=True, exist_ok=True)

    formats = ["wav", "mp3"] if args.to == "both" else [args.to]
    total = len(src_files) * len(formats)
    ok = 0
    t0 = time.perf_counter()

    for i, raw in enumerate(src_files, 1):
        src = Path(raw)
        for fmt in formats:
            attempt = (i - 1) * len(formats) + formats.index(fmt) + 1
            print(f"[{attempt}/{total}] {fmt.upper()}  ", end="", flush=True)
            if convert_file(src, fmt, outdir, args.wav_bit,
                            args.mp3_bitrate, args.samplerate,
                            args.delete_original):
                ok += 1

    elapsed = time.perf_counter() - t0
    print(f"\nDone. {ok}/{total} succeeded in {elapsed:.1f}s.")
    print(f"Output: {outdir.resolve()}\n")


if __name__ == "__main__":
    main()
