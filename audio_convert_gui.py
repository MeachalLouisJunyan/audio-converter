#!/usr/bin/env python3
"""
Audio Converter GUI — drag & drop files/folders, batch convert to WAV/MP3.

Requires: ffmpeg on PATH, tkinterdnd2 for drag-drop (pip install tkinterdnd2)
"""

import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).parent))
from audio_convert import SUPPORTED_EXTS, find_ffmpeg, human_size, \
    collect_files, convert_file

# ── Drag-drop support ──────────────────────────────────────────

DRAG_DROP_OK = False
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DRAG_DROP_OK = True
except ImportError:
    pass

# ── Colors ─────────────────────────────────────────────────────

C = {
    "bg":       "#0d0d14",
    "surface":  "#171724",
    "card":     "#1e1e30",
    "border":   "#2a2a3c",
    "text":     "#e2e2ed",
    "dim":      "#6b6b80",
    "accent":   "#818cf8",
    "accent_h": "#a5b4fc",
    "green":    "#4ade80",
    "red":      "#f87171",
    "yellow":   "#fbbf24",
    "orange":   "#fb923c",
    "pink":     "#f472b6",
    "cyan":     "#22d3ee",
}


# ── Widget helpers ─────────────────────────────────────────────

def _a_button(parent, text, command, color=C["accent"], width=None):
    """Accent (primary) button."""
    btn = tk.Button(parent, text=text, command=command,
                    bg=color, fg=C["bg"], font=("Segoe UI", 10, "bold"),
                    padx=20, pady=7, borderwidth=0, width=width,
                    activebackground=C["accent_h"], activeforeground=C["bg"],
                    cursor="hand2")
    return btn


def _s_button(parent, text, command, width=None):
    """Secondary (ghost) button."""
    btn = tk.Button(parent, text=text, command=command,
                    bg=C["surface"], fg=C["text"], font=("Segoe UI", 10),
                    padx=16, pady=6, borderwidth=0, width=width,
                    activebackground=C["card"], activeforeground=C["text"],
                    cursor="hand2")
    return btn


def _rounded_frame(parent, **kw):
    """Card-like frame with border."""
    f = tk.Frame(parent, bg=C["card"], highlightthickness=1,
                 highlightbackground=C["border"])
    return f


# ── App ────────────────────────────────────────────────────────


class AudioConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio Converter")
        self.root.geometry("720x680")
        self.root.minsize(600, 580)
        self.root.configure(bg=C["bg"])

        self.file_paths = []
        self.converting = False

        self._setup_fonts()
        self._build_ui()

        if DRAG_DROP_OK:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind("<<Drop>>", self._on_drop)
        else:
            self._status("拖拽功能未启用 (pip install tkinterdnd2)")

    # ── Fonts ────────────────────────────────────────────────

    def _setup_fonts(self):
        self.F = {
            "h1":   ("Segoe UI", 16, "bold"),
            "h2":   ("Segoe UI", 11, "bold"),
            "body": ("Segoe UI", 10),
            "sm":   ("Segoe UI", 9),
            "mono": ("Consolas", 10),
            "icon": ("Segoe UI", 13),
        }

    # ── UI Build ─────────────────────────────────────────────

    def _build_ui(self):
        pad_x = 24

        # ── Title bar ──
        header = tk.Frame(self.root, bg=C["bg"])
        header.pack(fill="x", padx=pad_x, pady=(18, 12))

        tk.Label(header, text="Audio Converter", fg=C["text"],
                 bg=C["bg"], font=self.F["h1"]).pack(side="left")
        tk.Label(header, text="WAV / MP3", fg=C["dim"],
                 bg=C["bg"], font=self.F["sm"]).pack(side="left", padx=(8, 0))

        # ── Drop zone ──
        self.drop_frame = tk.Frame(self.root, bg=C["card"],
                                   highlightthickness=2,
                                   highlightbackground=C["accent"])
        self.drop_frame.pack(fill="x", padx=pad_x, pady=(0, 10), ipady=22)

        drop_inner = tk.Frame(self.drop_frame, bg=C["card"])
        drop_inner.pack()

        tk.Label(drop_inner, text="\U0001f4c2", fg=C["accent"],
                 bg=C["card"], font=("Segoe UI", 28)).pack(pady=(8, 0))
        self.drop_label = tk.Label(
            drop_inner,
            text="拖放文件或文件夹到此处",
            fg=C["dim"], bg=C["card"], font=self.F["h2"],
        )
        self.drop_label.pack(pady=(2, 6))

        btn_row = tk.Frame(drop_inner, bg=C["card"])
        btn_row.pack()
        _s_button(btn_row, "选择文件", self._browse_files).pack(side="left", padx=4)
        _s_button(btn_row, "选择文件夹", self._browse_folder).pack(side="left", padx=4)

        # ── File list ──
        list_header = tk.Frame(self.root, bg=C["bg"])
        list_header.pack(fill="x", padx=pad_x, pady=(6, 4))

        self.count_label = tk.Label(list_header,
                                    text="已选择 0 个文件",
                                    fg=C["dim"], bg=C["bg"], font=self.F["body"])
        self.count_label.pack(side="left")

        self.clear_btn = _s_button(list_header, "清空", self._clear_list)
        self.clear_btn.pack(side="right")
        self.clear_btn.config(state="disabled")

        list_wrap = _rounded_frame(self.root)
        list_wrap.pack(fill="both", expand=True, padx=pad_x, pady=(0, 8))

        scrollbar = tk.Scrollbar(list_wrap, bg=C["card"],
                                 troughcolor=C["bg"], borderwidth=0)
        scrollbar.pack(side="right", fill="y")

        self.file_list = tk.Listbox(
            list_wrap,
            bg=C["card"], fg=C["text"], font=self.F["mono"],
            selectbackground=C["accent"], selectforeground=C["bg"],
            borderwidth=0, highlightthickness=0,
            yscrollcommand=scrollbar.set,
            activestyle="none",
        )
        self.file_list.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.file_list.yview)

        # ── Settings panel ──
        settings = _rounded_frame(self.root)
        settings.pack(fill="x", padx=pad_x, pady=(0, 8), ipady=6)

        def _row(parent, r, pady=(6, 0)):
            f = tk.Frame(parent, bg=C["card"])
            f.grid(row=r, column=0, sticky="ew", pady=pady, padx=16)
            return f

        def _label(parent, text):
            return tk.Label(parent, text=text, fg=C["dim"], bg=C["card"],
                            font=self.F["body"])

        def _radio(parent, text, var, val):
            return tk.Radiobutton(parent, text=text, variable=var, value=val,
                                  bg=C["card"], fg=C["text"],
                                  selectcolor=C["accent"],
                                  font=self.F["body"],
                                  activebackground=C["card"],
                                  activeforeground=C["text"],
                                  cursor="hand2")

        def _combo(parent, var, vals, w=10):
            cb = ttk.Combobox(parent, textvariable=var, values=vals,
                              state="readonly", width=w,
                              font=self.F["body"])
            return cb

        def _sep(parent, r):
            tk.Frame(parent, bg=C["border"], height=1).grid(
                row=r, column=0, sticky="ew", padx=16, pady=(8, 0))

        # Row 0: format selector
        r0 = _row(settings, 0)
        _label(r0, "输出格式").pack(side="left")
        self.fmt_var = tk.StringVar(value="both")
        for text, val in [("WAV", "wav"), ("MP3", "mp3"), ("两者", "both")]:
            _radio(r0, text, self.fmt_var, val).pack(side="left", padx=(12, 0))

        _sep(settings, 1)

        # Row 2: quality
        r2 = _row(settings, 2)
        _label(r2, "MP3 码率").pack(side="left")
        self.mp3_var = tk.StringVar(value="320k")
        _combo(r2, self.mp3_var, ["320k", "256k", "192k", "128k"], 6
               ).pack(side="left", padx=(6, 20))

        _label(r2, "WAV 位深").pack(side="left")
        self.wav_var = tk.StringVar(value="16-bit")
        _combo(r2, self.wav_var, ["16-bit", "24-bit"], 6
               ).pack(side="left", padx=(6, 20))

        _label(r2, "采样率").pack(side="left")
        self.sr_var = tk.StringVar(value="保持原样")
        _combo(r2, self.sr_var, ["保持原样", "44100 Hz", "48000 Hz", "96000 Hz"], 12
               ).pack(side="left", padx=(6, 0))

        _sep(settings, 3)

        # Row 4: output dir
        r4 = _row(settings, 4)
        _label(r4, "输出到").pack(side="left")
        self.outdir_var = tk.StringVar(value="converted")
        tk.Entry(r4, textvariable=self.outdir_var, width=28,
                 bg=C["surface"], fg=C["text"],
                 insertbackground=C["text"], font=self.F["body"],
                 borderwidth=0, relief="flat").pack(side="left", padx=(6, 4),
                                                    ipady=3)
        _s_button(r4, "浏览", self._browse_outdir).pack(side="left")

        _sep(settings, 5)

        # Row 6: delete checkbox + convert
        r6 = _row(settings, 6, pady=(10, 10))
        self.delete_var = tk.BooleanVar(value=False)
        tk.Checkbutton(r6, text="转换后删除原文件",
                       variable=self.delete_var,
                       bg=C["card"], fg=C["red"],
                       selectcolor=C["card"],
                       activebackground=C["card"],
                       font=self.F["sm"], cursor="hand2"
                       ).pack(side="left")

        self.convert_btn = _a_button(r6, "开始转换", self._start_convert,
                                     color=C["accent"])
        self.convert_btn.pack(side="right")

        # ── Progress bar ──
        self.progress = ttk.Progressbar(self.root, mode="determinate",
                                        style="Custom.Horizontal.TProgressbar")
        self.progress.pack(fill="x", padx=pad_x, pady=(0, 2))

        progress_style = ttk.Style()
        progress_style.theme_use("clam")
        progress_style.configure("Custom.Horizontal.TProgressbar",
                                 troughcolor=C["surface"],
                                 background=C["accent"],
                                 bordercolor=C["border"],
                                 lightcolor=C["accent"],
                                 darkcolor=C["accent"])

        # ── Status strip ──
        self.status_var = tk.StringVar(value="就绪")
        tk.Label(self.root, textvariable=self.status_var,
                 fg=C["dim"], bg=C["bg"], font=self.F["sm"],
                 anchor="w").pack(fill="x", padx=pad_x, pady=(0, 8))

    # ── Events ───────────────────────────────────────────────

    def _on_drop(self, event):
        paths = self._parse_drop(event.data)
        if paths:
            self.file_paths = paths
            self._refresh_list()
            self._status(f"已加载 {len(self.file_paths)} 个音频文件")

    def _parse_drop(self, data):
        results = []
        for raw in data.split("}"):
            raw = raw.strip()
            if not raw:
                continue
            p = raw.lstrip("{").strip()
            if p:
                results.append(p)
        collected = []
        for p in results:
            pp = Path(p)
            if pp.is_file():
                if pp.suffix.lower() in SUPPORTED_EXTS:
                    collected.append(str(pp))
            elif pp.is_dir():
                for root, _, fnames in os.walk(pp):
                    for fn in fnames:
                        fp = Path(root) / fn
                        if fp.suffix.lower() in SUPPORTED_EXTS:
                            collected.append(str(fp))
        return sorted(set(collected), key=str.lower)

    def _browse_files(self):
        files = filedialog.askopenfilenames(
            title="选择音频文件",
            filetypes=[("音频文件", "*.flac;*.wav;*.mp3;*.ogg;*.wma;*.aac;"
                        "*.m4a;*.aiff;*.ape;*.opus;*.ac3;*.dts;*.mid;"
                        "*.wv;*.tta;*.dsf;*.dff;*.midi"),
                       ("全部文件", "*.*")],
        )
        if files:
            self.file_paths = sorted(set(list(files)), key=str.lower)
            self._refresh_list()
            self._status(f"已选择 {len(self.file_paths)} 个文件")

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="选择文件夹")
        if folder:
            collected = []
            for root, _, fnames in os.walk(folder):
                for fn in fnames:
                    fp = Path(root) / fn
                    if fp.suffix.lower() in SUPPORTED_EXTS:
                        collected.append(str(fp))
            if not collected:
                messagebox.showinfo("提示", "该文件夹中没有支持的音频文件。")
                return
            self.file_paths = sorted(set(collected), key=str.lower)
            self._refresh_list()
            self._status(f"已加载 {len(self.file_paths)} 个文件 (含子文件夹)")

    def _browse_outdir(self):
        d = filedialog.askdirectory(title="选择输出目录")
        if d:
            self.outdir_var.set(d)

    def _clear_list(self):
        self.file_paths = []
        self.file_list.delete(0, "end")
        self.count_label.config(text="已选择 0 个文件")
        self.clear_btn.config(state="disabled")
        self._status("就绪")

    def _refresh_list(self):
        self.file_list.delete(0, "end")

        # Group files by extension for color coding
        ext_colors = {
            ".flac": C["cyan"], ".wav": C["green"],
            ".mp3": C["orange"], ".ogg": C["pink"],
            ".aac": C["yellow"], ".m4a": C["accent"],
            ".wma": C["red"], ".aiff": C["dim"],
        }

        for p in self.file_paths:
            name = Path(p)
            ext = name.suffix.lower()
            color = ext_colors.get(ext, C["text"])
            size = human_size(Path(p).stat().st_size)
            display = f"  {name.name:<50} {size:>8}"
            self.file_list.insert("end", display)
            # Can't color individual items in tk Listbox easily;
            # we use a uniform look instead.

        self.count_label.config(
            text=f"已选择 {len(self.file_paths)} 个文件")
        self.clear_btn.config(state="normal")
        self.drop_label.config(
            text=f"已加载 {len(self.file_paths)} 个音频文件",
            fg=C["accent"])

    # ── Conversion ───────────────────────────────────────────

    def _start_convert(self):
        if self.converting:
            return
        if not self.file_paths:
            messagebox.showwarning("提示", "请先添加音频文件。")
            return

        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            messagebox.showerror(
                "错误",
                "找不到 ffmpeg。请安装后重试。\n\n"
                "  winget install ffmpeg\n"
                "  scoop install ffmpeg")
            return

        self.converting = True
        self.convert_btn.config(text="转换中...", bg=C["dim"], state="disabled",
                                cursor="watch")
        self.drop_label.config(text="正在转换...", fg=C["yellow"])

        threading.Thread(target=self._run_convert, daemon=True).start()

    def _run_convert(self):
        to = self.fmt_var.get()
        outdir = Path(self.outdir_var.get())
        mp3_bitrate = self.mp3_var.get()
        wav_bit = 16 if "16" in self.wav_var.get() else 24
        sr_raw = self.sr_var.get()
        samplerate = 0 if "保持" in sr_raw else int(sr_raw.split()[0])
        delete = self.delete_var.get()

        outdir.mkdir(parents=True, exist_ok=True)
        formats = ["wav", "mp3"] if to == "both" else [to]
        total = len(self.file_paths) * len(formats)
        ok = 0

        self.progress.config(maximum=total)
        self.progress["value"] = 0

        t0 = time.perf_counter()

        for i, raw in enumerate(self.file_paths, 1):
            src = Path(raw)
            for fmt in formats:
                attempt = (i - 1) * len(formats) + formats.index(fmt) + 1
                self._update_ui(f"[{attempt}/{total}]", src.name,
                                attempt, fmt)
                if convert_file(src, fmt, outdir, wav_bit,
                                mp3_bitrate, samplerate, delete):
                    ok += 1

        elapsed = time.perf_counter() - t0
        self._update_ui("完成", f"{ok}/{total} 成功, 耗时 {elapsed:.1f}s",
                        total, "done", ok=ok, total=total)
        self._finish_convert()

    def _update_ui(self, prefix, detail, val, fmt="", ok=None, total=None):
        def run():
            self.progress["value"] = val
            if ok is not None:
                color = C["green"] if ok == total else C["dim"]
                self.status_var.set(f"{prefix}  {detail}")
                self._set_status_color(color)
                self.drop_label.config(text="转换完成", fg=C["green"])
            else:
                self.status_var.set(f"{prefix} {fmt.upper()}  {detail}")
                self._set_status_color(C["dim"])
        self.root.after(0, run)

    def _set_status_color(self, c):
        pass  # tk Label doesn't support per-character colors

    def _finish_convert(self):
        self.root.after(0, lambda: self.convert_btn.config(
            text="开始转换", bg=C["accent"], state="normal", cursor="hand2"))
        self.root.after(0, lambda: self.progress.configure(value=0))
        self.converting = False

    def _status(self, msg):
        self.root.after(0, lambda: self.status_var.set(msg))


# ── Entry point ────────────────────────────────────────────────

def main():
    if DRAG_DROP_OK:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    AudioConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
