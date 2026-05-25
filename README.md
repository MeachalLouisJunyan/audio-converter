# Audio Converter

Convert 50+ audio formats to WAV / MP3. Two interfaces:

- **GUI** — drag & drop files/folders, batch convert
- **CLI** — command-line for scripting

Requires `ffmpeg` on PATH. GUI requires `tkinterdnd2` (optional, falls back to buttons).

## Install

```bash
pip install -r requirements.txt
# ffmpeg:
#   Windows: scoop install ffmpeg
#   macOS:   brew install ffmpeg
#   Linux:   sudo apt install ffmpeg
```

## GUI

```bash
python audio_convert_gui.py
```

- Drag & drop files or entire folders
- Also supports a folder-picker dialog
- Options: WAV / MP3 / both, bitrate, bit depth, samplerate
- Real-time progress bar

## CLI

```bash
python audio_convert.py <paths...> [options]
```

| Option | Description |
|--------|-------------|
| `--to wav\|mp3\|both` | Output format (default: both) |
| `--outdir`, `-o` | Output directory (default: ./converted) |
| `--mp3-bitrate` | 128k / 192k / 256k / 320k (default) |
| `--wav-bit` | 16 (default) / 24 |
| `--samplerate`, `-r` | Resample (0 = keep original) |
| `--recursive`, `-R` | Recurse into directories |
| `--delete-original` | Delete source after conversion |
| `--formats` | List all supported input formats |

## Examples

```bash
# CLI
python audio_convert.py song.flac --to mp3
python audio_convert.py music/ -R --to both -o output/

# GUI — just launch and drag files in
python audio_convert_gui.py
```

## Supported formats

50+ formats: flac, wav, aiff, alac, ape, wv, tta, dsf, dff, mp3, aac, ogg, opus, wma, ac3, dts, mid, ra, amr, au, caf, voc, raw, pcm, and more.
