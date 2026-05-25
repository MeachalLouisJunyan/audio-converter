# Audio Converter

A standalone tool to convert audio files to WAV / MP3.

## Project structure

- `audio_convert.py` — CLI script
- `audio_convert_gui.py` — GUI with drag & drop (requires tkinterdnd2)
- `requirements.txt` — Python deps

## Running

```bash
pip install -r requirements.txt
python audio_convert_gui.py        # GUI with drag & drop
python audio_convert.py --formats  # CLI
```

Dependencies: `ffmpeg` on PATH, `tkinterdnd2` for GUI drag-drop.
