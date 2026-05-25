#!/usr/bin/env python3
"""
Audio Converter GUI — drag & drop files/folders, batch convert to WAV/MP3.

Requires: ffmpeg on PATH, tkinterdnd2 for drag-drop (pip install tkinterdnd2)
If tkinterdnd2 is not installed, use the Browse buttons instead.
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

# ── Colors & styles ────────────────────────────────────────────

BG = "#1e1e2e"
FG = "#cdd6f4"
ACCENT = "#89b4fa"
ACCENT_HOVER = "#74c7ec"
SURFACE = "#313244"
SURFACE2 = "#45475a"
BORDER = "#585b70"
GREEN = "#a6e3a1"
RED = "#f38ba8"
YELLOW = "#f9e2af"
DIM = "#6c7086"
DROP_BG = "#1a1a2e"
DROP_BORDER = "#89b4fa"

# ── GUI Application ────────────────────────────────────────────


class AudioConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio Converter")
        self.root.geometry("680x620")
        self.root.minsize(560, 480)
        self.root.configure(bg=BG)

        self._setup_styles()
        self.file_paths = []
        self.converting = False

        self._build_ui()

        if DRAG_DROP_OK:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind("<<Drop>>", self._on_drop)
        else:
            self._log("拖拽功能未启用 (pip install tkinterdnd2), 请用下方按钮选择文件")

    # ── Styles ──────────────────────────────────────────────

    def _setup_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=FG, fieldbackground=SURFACE)
        style.configure("TButton", background=SURFACE, foreground=FG,
                        borderwidth=0, padding=(12, 6), font=("", 10))
        style.map("TButton", background=[("active", SURFACE2)])
        style.configure("Accent.TButton", background=ACCENT, foreground=BG,
                        font=("", 11, "bold"))
        style.map("Accent.TButton", background=[("active", ACCENT_HOVER)])
        style.configure("TLabel", background=BG, foreground=FG, font=("", 10))
        style.configure("TLabelframe", background=BG, foreground=DIM)
        style.configure("TLabelframe.Label", background=BG, foreground=DIM)
        style.configure("TCombobox", selectbackground=SURFACE2,
                        fieldbackground=SURFACE, background=SURFACE,
                        foreground=FG, arrowcolor=FG)
        style.map("TCombobox",
                  fieldbackground=[("readonly", SURFACE)],
                  selectbackground=[("readonly", SURFACE2)])
        style.configure("TEntry", fieldbackground=SURFACE, foreground=FG)

    # ── Build UI ────────────────────────────────────────────

    def _build_ui(self):
        # ── Drop zone ──
        self.drop_frame = tk.Frame(self.root, bg=DROP_BG, highlightthickness=2,
                                   highlightbackground=DROP_BORDER,
                                   highlightcolor=ACCENT_HOVER)
        self.drop_frame.place(relx=0.05, rely=0.03, relwidth=0.9, relheight=0.22)

        self.drop_label = tk.Label(
            self.drop_frame,
            text="拖放文件 / 文件夹到此处\n\n或",
            bg=DROP_BG, fg=DIM, font=("", 12), justify="center",
        )
        self.drop_label.pack(expand=True, pady=(25, 0))

        btn_frame = tk.Frame(self.drop_frame, bg=DROP_BG)
        btn_frame.pack(pady=(8, 15))

        tk.Button(btn_frame, text="选择文件", bg=SURFACE, fg=FG,
                  font=("", 10), padx=16, pady=4, borderwidth=0,
                  command=self._browse_files).pack(side="left", padx=5)
        tk.Button(btn_frame, text="选择文件夹", bg=SURFACE, fg=FG,
                  font=("", 10), padx=16, pady=4, borderwidth=0,
                  command=self._browse_folder).pack(side="left", padx=5)

        # ── File list ──
        info_frame = tk.Frame(self.root, bg=BG)
        info_frame.place(relx=0.05, rely=0.27, relwidth=0.9, relheight=0.38)

        self.count_label = tk.Label(info_frame, text="已选择: 0 个文件",
                                     bg=BG, fg=DIM, anchor="w")
        self.count_label.pack(fill="x")

        list_container = tk.Frame(info_frame, bg=SURFACE2,
                                  highlightthickness=1,
                                  highlightbackground=BORDER)
        list_container.pack(fill="both", expand=True, pady=(4, 0))

        scrollbar = tk.Scrollbar(list_container, bg=SURFACE,
                                 troughcolor=BG)
        scrollbar.pack(side="right", fill="y")

        self.file_list = tk.Listbox(
            list_container,
            bg=SURFACE, fg=FG, font=("Consolas", 10),
            selectbackground=SURFACE2, selectforeground=FG,
            borderwidth=0, highlightthickness=0,
            yscrollcommand=scrollbar.set,
        )
        self.file_list.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.file_list.yview)

        # ── Settings ──
        settings = tk.Frame(self.root, bg=BG)
        settings.place(relx=0.05, rely=0.67, relwidth=0.9, relheight=0.27)

        # Row 1: format
        tk.Label(settings, text="输出格式:", bg=BG, fg=DIM
                 ).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.fmt_var = tk.StringVar(value="both")
        for col, (text, val) in enumerate([("WAV", "wav"), ("MP3", "mp3"),
                                            ("两者", "both")]):
            tk.Radiobutton(settings, text=text, variable=self.fmt_var, value=val,
                           bg=BG, fg=FG, selectcolor=SURFACE,
                           activebackground=BG, activeforeground=ACCENT,
                           font=("", 10)
                           ).grid(row=0, column=1+col, sticky="w", padx=5)

        # Row 1 right: outdir
        tk.Label(settings, text="输出目录:", bg=BG, fg=DIM
                 ).grid(row=0, column=4, sticky="w", padx=(20, 8))
        self.outdir_var = tk.StringVar(value="converted")
        out_entry = tk.Entry(settings, textvariable=self.outdir_var, width=18,
                             bg=SURFACE, fg=FG, insertbackground=FG,
                             font=("", 10), borderwidth=0)
        out_entry.grid(row=0, column=5, sticky="w")
        tk.Button(settings, text="浏览", bg=SURFACE, fg=FG, font=("", 9),
                  padx=8, borderwidth=0, command=self._browse_outdir
                  ).grid(row=0, column=6, padx=4)

        # Row 2
        tk.Label(settings, text="MP3 码率:", bg=BG, fg=DIM
                 ).grid(row=1, column=0, sticky="w", pady=(12, 0), padx=(0, 8))
        self.mp3_var = tk.StringVar(value="320k")
        ttk.Combobox(settings, textvariable=self.mp3_var,
                     values=["128k", "192k", "256k", "320k"],
                     state="readonly", width=7
                     ).grid(row=1, column=1, sticky="w", pady=(12, 0), padx=5)

        tk.Label(settings, text="WAV 位深:", bg=BG, fg=DIM
                 ).grid(row=1, column=2, sticky="w", pady=(12, 0), padx=(20, 8))
        self.wav_var = tk.StringVar(value="16")
        ttk.Combobox(settings, textvariable=self.wav_var,
                     values=["16", "24"], state="readonly", width=5
                     ).grid(row=1, column=3, sticky="w", pady=(12, 0))

        tk.Label(settings, text="采样率:", bg=BG, fg=DIM
                 ).grid(row=1, column=4, sticky="w", pady=(12, 0), padx=(20, 8))
        self.sr_var = tk.StringVar(value="0")
        ttk.Combobox(settings, textvariable=self.sr_var,
                     values=["0 (保持原样)", "44100", "48000", "96000"],
                     state="readonly", width=14
                     ).grid(row=1, column=5, sticky="w", pady=(12, 0))

        # Row 3: delete checkbox
        self.delete_var = tk.BooleanVar(value=False)
        tk.Checkbutton(settings, text="转换后删除原文件 (危险!)",
                       variable=self.delete_var, bg=BG, fg=RED,
                       selectcolor=SURFACE, activebackground=BG,
                       activeforeground=RED,
                       font=("", 9)
                       ).grid(row=2, column=0, columnspan=3, sticky="w",
                              pady=(16, 0))

        # Row 3: convert button
        self.convert_btn = tk.Button(
            settings, text="▶  开始转换", bg=ACCENT, fg=BG,
            font=("", 12, "bold"), padx=24, pady=6, borderwidth=0,
            activebackground=ACCENT_HOVER, activeforeground=BG,
            command=self._start_convert,
        )
        self.convert_btn.grid(row=2, column=4, columnspan=3,
                              sticky="e", pady=(16, 0))

        # ── Status bar ──
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = tk.Label(self.root, textvariable=self.status_var,
                                      bg=SURFACE2, fg=DIM, anchor="w",
                                      font=("", 9), padx=8, pady=2)
        self.status_label.place(relx=0, rely=0.96, relwidth=1, relheight=0.04)

        # ── Progress bar ──
        self.progress = ttk.Progressbar(self.root, mode="determinate")
        self.progress.place(relx=0, rely=0.95, relwidth=1, relheight=0.015)

    # ── Events ──────────────────────────────────────────────

    def _on_drop(self, event):
        paths = self._parse_drop(event.data)
        if paths:
            self.file_paths = paths
            self._refresh_list()
            self._log(f"已加载 {len(self.file_paths)} 个音频文件")

    def _parse_drop(self, data):
        """Parse tkinterdnd2 drop data on Windows (brace-enclosed paths)."""
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
                        "*.m4a;*.aiff;*.ape;*.opus;*.ac3;*.dts;*.flac;*.mid;"
                        "*.wv;*.tta;*.dsf;*.dff;*.midi"),
                       ("全部文件", "*.*")],
        )
        if files:
            self.file_paths = sorted(set(list(files)), key=str.lower)
            self._refresh_list()
            self._log(f"已选择 {len(self.file_paths)} 个文件")

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
            self._log(f"已加载 {len(self.file_paths)} 个文件 (含子文件夹)")

    def _browse_outdir(self):
        d = filedialog.askdirectory(title="选择输出目录")
        if d:
            self.outdir_var.set(d)

    def _refresh_list(self):
        self.file_list.delete(0, "end")
        for p in self.file_paths:
            self.file_list.insert("end", Path(p).name)
        self.count_label.config(
            text=f"已选择: {len(self.file_paths)} 个文件")

    # ── Conversion ──────────────────────────────────────────

    def _start_convert(self):
        if self.converting:
            return
        if not self.file_paths:
            messagebox.showwarning("提示", "请先添加音频文件。")
            return

        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            messagebox.showerror("错误",
                                 "找不到 ffmpeg。请安装并确保它在 PATH 中。\n\n"
                                 "Windows: scoop install ffmpeg\n"
                                 "macOS:   brew install ffmpeg\n"
                                 "Linux:   sudo apt install ffmpeg")
            return

        self.converting = True
        self.convert_btn.config(text="转换中...", bg=SURFACE2,
                                state="disabled")

        threading.Thread(target=self._run_convert, daemon=True).start()

    def _run_convert(self):
        to = self.fmt_var.get()
        outdir = Path(self.outdir_var.get())
        mp3_bitrate = self.mp3_var.get()
        wav_bit = int(self.wav_var.get())
        sr_raw = self.sr_var.get()
        samplerate = 0 if "0" in sr_raw else int(sr_raw)
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
                self._update_status(f"[{attempt}/{total}] {fmt.upper()}  {src.name}")
                self._update_progress(attempt)
                if convert_file(src, fmt, outdir, wav_bit,
                                mp3_bitrate, samplerate, delete):
                    ok += 1
                else:
                    self._log(f"  失败  {src.name} -> {fmt}", "fail")

        elapsed = time.perf_counter() - t0
        self._update_status(f"完成: {ok}/{total} 成功, 耗时 {elapsed:.1f}s")
        self._log(f"完成: {ok}/{total} 成功, 耗时 {elapsed:.1f}s, 输出: {outdir.resolve()}", "ok")
        self._finish_convert()

    def _update_status(self, text):
        self.root.after(0, lambda: self.status_var.set(text))

    def _update_progress(self, val):
        self.root.after(0, lambda: self.progress.configure(value=val))

    def _finish_convert(self):
        self.root.after(0, lambda: self.convert_btn.config(
            text="▶  开始转换", bg=ACCENT, state="normal"))
        self.root.after(0, lambda: self.progress.configure(value=0))
        self.converting = False

    def _log(self, msg, kind="info"):
        color_map = {"ok": GREEN, "fail": RED, "info": DIM}
        color = color_map.get(kind, DIM)
        self.root.after(0, lambda: self.status_label.config(fg=color))
        self.root.after(0, lambda: self.status_var.set(msg))


# ── Entry point ──────────────────────────────────────────────

def main():
    if DRAG_DROP_OK:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = AudioConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
