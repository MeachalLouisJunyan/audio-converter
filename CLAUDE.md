# Audio Converter

A standalone CLI tool to convert audio files to WAV / MP3. Zero Python dependencies, requires `ffmpeg` on PATH.

## Project structure

- `audio_convert.py` — main script

## Running

```bash
python audio_convert.py <paths...> [options]
```

## Examples

```bash
python audio_convert.py song.flac --to mp3
python audio_convert.py music/ -R --to both -o output/
python audio_convert.py *.wav --to mp3 --mp3-bitrate 192k
python audio_convert.py --formats
```
