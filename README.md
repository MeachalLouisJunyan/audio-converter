# Audio Converter

Convert 50+ audio formats to WAV / MP3. Zero Python dependencies — just needs `ffmpeg`.

## Quick start

```bash
python audio_convert.py song.flac --to mp3
python audio_convert.py music/ -R --to both -o output/
```

## Usage

```
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

## Supported formats

50+ formats including: flac, wav, aiff, alac, ape, wv, tta, dsf, dff, mp3, aac, ogg, opus, wma, ac3, dts, mid, ra, amr, au, caf, voc, raw, pcm, and more.
