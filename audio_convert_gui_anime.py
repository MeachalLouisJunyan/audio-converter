#!/usr/bin/env python3
"""
Audio Converter GUI — Anime / Moe edition
Drag & drop files/folders, batch convert to WAV/MP3.

Requires: ffmpeg on PATH, tkinterdnd2 (pip install tkinterdnd2)
"""

import os
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).parent))
from audio_convert import SUPPORTED_EXTS, find_ffmpeg, human_size, \
    collect_files, convert_file

# ── Drag-drop ──────────────────────────────────────────────────

DRAG_DROP_OK = False
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DRAG_DROP_OK = True
except ImportError:
    pass

# ── Sakura palette ─────────────────────────────────────────────

P = {
    "bg":        "#fff0f5",  # lavender blush
    "surface":   "#ffe4ec",  # misty rose
    "card":      "#ffffff",
    "border":    "#f5c6d0",
    "text":      "#4a2040",
    "dim":       "#b8869e",
    "accent":    "#ff6b9d",
    "accent2":   "#c084fc",
    "green":     "#86dba6",
    "red":       "#ff6b6b",
    "yellow":    "#f5c842",
    "pink":      "#ff9ec3",
    "mint":      "#9ee5d0",
    "sky":       "#8ecae6",
    "lavender":  "#c3aed6",
}


def _primary_btn(parent, text, command):
    return tk.Button(parent, text=text, command=command,
                     bg=P["accent"], fg="white",
                     font=("Microsoft YaHei UI", 11, "bold"),
                     padx=24, pady=8, borderwidth=0,
                     activebackground="#ff4081", activeforeground="white",
                     cursor="hand2")


def _ghost_btn(parent, text, command):
    return tk.Button(parent, text=text, command=command,
                     bg=P["surface"], fg=P["text"],
                     font=("Microsoft YaHei UI", 10),
                     padx=16, pady=6, borderwidth=0,
                     activebackground=P["pink"], activeforeground=P["text"],
                     cursor="hand2")


def _small_btn(parent, text, command):
    return tk.Button(parent, text=text, command=command,
                     bg=P["surface"], fg=P["accent"],
                     font=("Microsoft YaHei UI", 9),
                     padx=12, pady=3, borderwidth=0,
                     activebackground=P["pink"], activeforeground="white",
                     cursor="hand2")


def _card(parent, **kw):
    return tk.Frame(parent, bg=P["card"], highlightthickness=1,
                    highlightbackground=P["border"], **kw)


# ── App ────────────────────────────────────────────────────────


class MoeConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("Moe Audio Converter")
        self.root.geometry("720x700")
        self.root.minsize(600, 600)
        self.root.configure(bg=P["bg"])

        self.file_paths = []
        self.converting = False

        self._build_ui()

        if DRAG_DROP_OK:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind("<<Drop>>", self._on_drop)
        else:
            self._status("pip install tkinterdnd2 以启用拖拽")

    # ── UI ──────────────────────────────────────────────────

    def _build_ui(self):
        px = 24

        # ══════ Header ══════
        header = tk.Frame(self.root, bg=P["bg"])
        header.pack(fill="x", padx=px, pady=(16, 0))

        tk.Label(header, text="Moe Audio Converter",
                 fg=P["accent"], bg=P["bg"],
                 font=("Microsoft YaHei UI", 18, "bold")).pack(side="left")

        tk.Label(header, text="音 频 转 换 器  ♪",
                 fg=P["dim"], bg=P["bg"],
                 font=("Microsoft YaHei UI", 10)).pack(side="left", padx=10)

        # ── Banner ──
        banner = _card(self.root)
        banner.pack(fill="x", padx=px, pady=(10, 12), ipady=6)
        tk.Label(banner, text=(
            "♡  ✿  ♪  ✧  ♫  ★  ♡\n"
            "把文件拖进来，一键变 WAV / MP3 ！\n"
            "♡  ★  ♫  ✧  ♪  ✿  ♡"),
            fg=P["accent2"], bg=P["card"],
            font=("Microsoft YaHei UI", 10),
            justify="center").pack(pady=(10, 10))

        # ══════ Drop zone ══════
        self.drop_frame = tk.Frame(self.root, bg=P["lavender"],
                                   highlightthickness=2,
                                   highlightbackground=P["accent2"])
        self.drop_frame.pack(fill="x", padx=px, pady=(0, 10), ipady=16)

        drop_inner = tk.Frame(self.drop_frame, bg=P["lavender"])
        drop_inner.pack()

        tk.Label(drop_inner, text="♪", fg=P["accent2"],
                 bg=P["lavender"],
                 font=("Segoe UI Symbol", 32)).pack(pady=(6, 0))

        self.drop_label = tk.Label(
            drop_inner,
            text="━  把文件 / 文件夹拖到这里  ━",
            fg=P["text"], bg=P["lavender"],
            font=("Microsoft YaHei UI", 12, "bold"),
        )
        self.drop_label.pack(pady=(2, 6))

        btn_row = tk.Frame(drop_inner, bg=P["lavender"])
        btn_row.pack(pady=(0, 4))
        _ghost_btn(btn_row, " 选文件 ", self._browse_files
                   ).pack(side="left", padx=4)
        _ghost_btn(btn_row, " 选文件夹 ", self._browse_folder
                   ).pack(side="left", padx=4)

        # ══════ File list ══════
        list_header = tk.Frame(self.root, bg=P["bg"])
        list_header.pack(fill="x", padx=px, pady=(4, 4))

        self.count_label = tk.Label(
            list_header, text="尚未选择文件  (◞‸◟)",
            fg=P["dim"], bg=P["bg"],
            font=("Microsoft YaHei UI", 10))
        self.count_label.pack(side="left")

        self.clear_btn = _small_btn(list_header, "清空", self._clear_list)
        self.clear_btn.pack(side="right")
        self.clear_btn.config(state="disabled")

        list_wrap = _card(self.root)
        list_wrap.pack(fill="both", expand=True, padx=px, pady=(0, 8))

        scrollbar = tk.Scrollbar(list_wrap, bg=P["card"],
                                 troughcolor=P["bg"], borderwidth=0)
        scrollbar.pack(side="right", fill="y")

        self.file_list = tk.Listbox(
            list_wrap,
            bg=P["card"], fg=P["text"],
            font=("Consolas", 10),
            selectbackground=P["pink"], selectforeground=P["text"],
            borderwidth=0, highlightthickness=0,
            yscrollcommand=scrollbar.set,
            activestyle="none",
        )
        self.file_list.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.file_list.yview)

        # ══════ Settings ══════
        settings = _card(self.root)
        settings.pack(fill="x", padx=px, pady=(0, 8), ipady=4)

        ipx = 18
        S = P  # alias for settings panel

        def _row(r, pady=(10, 0)):
            f = tk.Frame(settings, bg=S["card"])
            f.grid(row=r, column=0, sticky="ew", padx=ipx, pady=pady)
            return f

        def _lbl(parent, text):
            return tk.Label(parent, text=text, fg=S["dim"], bg=S["card"],
                            font=("Microsoft YaHei UI", 10))

        def _radio(parent, text, var, val):
            return tk.Radiobutton(parent, text=text, variable=var, value=val,
                                  bg=S["card"], fg=S["text"],
                                  selectcolor=S["pink"],
                                  font=("Microsoft YaHei UI", 10),
                                  activebackground=S["card"],
                                  activeforeground=S["accent"],
                                  cursor="hand2")

        def _combo(parent, var, vals, w=12):
            return ttk.Combobox(parent, textvariable=var, values=vals,
                                state="readonly", width=w,
                                font=("Microsoft YaHei UI", 10))

        def _sep(r):
            tk.Frame(settings, bg=S["border"], height=1).grid(
                row=r, column=0, sticky="ew", padx=ipx, pady=(8, 0))

        # Row 0: format
        r0 = _row(0)
        _lbl(r0, "输出格式").pack(side="left")
        self.fmt_var = tk.StringVar(value="both")
        for t, v in [("WAV", "wav"), ("MP3", "mp3"), ("两者", "both")]:
            _radio(r0, t, self.fmt_var, v).pack(side="left", padx=(10, 0))
        _sep(1)

        # Row 2: quality
        r2 = _row(2)
        _lbl(r2, "MP3 码率").pack(side="left")
        self.mp3_var = tk.StringVar(value="320k")
        _combo(r2, self.mp3_var, ["320k", "256k", "192k", "128k"], 6
               ).pack(side="left", padx=(6, 18))
        _lbl(r2, "WAV 位深").pack(side="left")
        self.wav_var = tk.StringVar(value="16-bit")
        _combo(r2, self.wav_var, ["16-bit", "24-bit"], 6
               ).pack(side="left", padx=(6, 18))
        _lbl(r2, "采样率").pack(side="left")
        self.sr_var = tk.StringVar(value="保持原样")
        _combo(r2, self.sr_var,
               ["保持原样", "44100 Hz", "48000 Hz", "96000 Hz"], 12
               ).pack(side="left", padx=(6, 0))
        _sep(3)

        # Row 4: outdir
        r4 = _row(4)
        _lbl(r4, "输出到").pack(side="left")
        self.outdir_var = tk.StringVar(value="converted")
        tk.Entry(r4, textvariable=self.outdir_var, width=26,
                 bg=S["surface"], fg=S["text"],
                 insertbackground=S["text"],
                 font=("Microsoft YaHei UI", 10),
                 borderwidth=0, relief="flat").pack(
                     side="left", padx=(6, 4), ipady=3)
        _ghost_btn(r4, "浏览", self._browse_outdir).pack(side="left")
        _sep(5)

        # Row 6: delete + convert
        r6 = _row(6, pady=(12, 12))
        self.delete_var = tk.BooleanVar(value=False)
        tk.Checkbutton(r6, text="转换后删除原文件",
                       variable=self.delete_var,
                       bg=S["card"], fg=S["red"],
                       selectcolor=S["card"],
                       activebackground=S["card"],
                       font=("Microsoft YaHei UI", 9), cursor="hand2"
                       ).pack(side="left")
        self.convert_btn = _primary_btn(r6, "★ 开始转换 ★",
                                        self._start_convert)
        self.convert_btn.pack(side="right")

        # ══════ Progress ══════
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = tk.Canvas(self.root, height=6, bg=P["surface"],
                                      highlightthickness=0, borderwidth=0)
        self.progress_bar.pack(fill="x", padx=px, pady=(0, 4))
        self._draw_progress(0, 100)
        self.progress_bar_width = 0
        self.root.after(100, self._sync_progress_width)

        # ══════ Status ══════
        status_frame = tk.Frame(self.root, bg=P["bg"])
        status_frame.pack(fill="x", padx=px)

        self.status_var = tk.StringVar(value="(｡･ ω ･｡)  等待文件...")
        tk.Label(status_frame, textvariable=self.status_var,
                 fg=P["dim"], bg=P["bg"],
                 font=("Microsoft YaHei UI", 10),
                 anchor="w").pack(side="left", fill="x")

    def _sync_progress_width(self):
        self.progress_bar_width = self.progress_bar.winfo_width()
        self._draw_progress(self.progress_var.get(), 100)

    # ── Custom progress bar ─────────────────────────────────

    def _draw_progress(self, val, maximum):
        if maximum == 0:
            return
        w = self.progress_bar.winfo_width()
        if w < 10:
            w = 680
        self.progress_bar.delete("all")
        if val > 0:
            ratio = val / maximum
            fill_w = int(w * ratio)
            self.progress_bar.create_rectangle(
                0, 0, fill_w, 6, fill=P["accent"], outline="")

    def _set_progress(self, val, maximum):
        self.progress_var.set(val)
        self._draw_progress(val, maximum)
        self.root.update_idletasks()

    # ── Events ───────────────────────────────────────────────

    def _on_drop(self, event):
        paths = self._parse_drop(event.data)
        if paths:
            self.file_paths = paths
            self._refresh_list()
            self._status(f"(｀・ω・´)  收到 {len(self.file_paths)} 个文件！")

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
            filetypes=[("音频文件",
                        "*.flac;*.wav;*.mp3;*.ogg;*.wma;*.aac;"
                        "*.m4a;*.aiff;*.ape;*.opus;*.ac3;*.dts;"
                        "*.mid;*.wv;*.tta;*.dsf;*.dff;*.midi"),
                       ("全部", "*.*")],
        )
        if files:
            self.file_paths = sorted(set(list(files)), key=str.lower)
            self._refresh_list()
            self._status(f"★ 已选择 {len(self.file_paths)} 个文件 ★")

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
                messagebox.showinfo("(´・ω・`)", "文件夹里没有支持的音频文件...")
                return
            self.file_paths = sorted(set(collected), key=str.lower)
            self._refresh_list()
            self._status(f"☆ {len(self.file_paths)} 个文件已就绪 (含子文件夹)")

    def _browse_outdir(self):
        d = filedialog.askdirectory(title="选择输出目录")
        if d:
            self.outdir_var.set(d)

    def _clear_list(self):
        self.file_paths = []
        self.file_list.delete(0, "end")
        self.count_label.config(text="尚未选择文件  (◞‸◟)")
        self.clear_btn.config(state="disabled")
        self.status_var.set("(｡･ ω ･｡)  等待文件...")
        self.drop_label.config(
            text="━  把文件 / 文件夹拖到这里  ━",
            fg=P["text"])

    def _refresh_list(self):
        self.file_list.delete(0, "end")
        for p in self.file_paths:
            name = Path(p)
            size = human_size(Path(p).stat().st_size)
            self.file_list.insert("end", f"  ♪ {name.name:<48} {size:>8}")
        self.count_label.config(
            text=f"已选择 {len(self.file_paths)} 个文件   (｀・ω・´) ノ")
        self.clear_btn.config(state="normal")
        self.drop_label.config(
            text=f"♪  已加载 {len(self.file_paths)} 个音频文件！",
            fg=P["accent"])

    # ── Conversion ───────────────────────────────────────────

    def _start_convert(self):
        if self.converting:
            return
        if not self.file_paths:
            messagebox.showwarning("(´;ω;`)", "请先添加音频文件！")
            return

        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            messagebox.showerror(
                "(´;ω;`) 呜...",
                "找不到 ffmpeg ！！\n\n"
                "  winget install ffmpeg\n"
                "  scoop install ffmpeg")
            return

        self.converting = True
        self.convert_btn.config(text="转换中...",
                                bg=P["dim"], state="disabled",
                                cursor="watch")
        self.drop_label.config(text="正在努力转换中... (o・ω・o)",
                               fg=P["accent2"])

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

        self._set_progress(0, total)
        t0 = time.perf_counter()

        for i, raw in enumerate(self.file_paths, 1):
            src = Path(raw)
            for fmt in formats:
                attempt = (i - 1) * len(formats) + formats.index(fmt) + 1
                self._ui(f"[{attempt}/{total}] ♪ {src.name}", attempt, total, fmt)
                if convert_file(src, fmt, outdir, wav_bit,
                                mp3_bitrate, samplerate, delete):
                    ok += 1

        elapsed = time.perf_counter() - t0
        if ok == total:
            emoji = "(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧"
        elif ok > 0:
            emoji = "(-ω-、)"
        else:
            emoji = "(´;ω;`)"
        self._ui(f"完成！ {emoji}  {ok}/{total} 成功, {elapsed:.1f}s",
                 total, total, "done")
        self._finish_convert()

    def _ui(self, msg, val, total, fmt=""):
        def run():
            self.status_var.set(msg)
            self._set_progress(val, total)
        self.root.after(0, run)

    def _finish_convert(self):
        self.root.after(0, lambda: self.convert_btn.config(
            text="★ 开始转换 ★", bg=P["accent"], state="normal",
            cursor="hand2"))
        self.root.after(0, lambda: self._set_progress(0, 100))
        self.converting = False
        self.drop_label.config(text="━  把文件 / 文件夹拖到这里  ━",
                               fg=P["text"])

    def _status(self, msg):
        self.root.after(0, lambda: self.status_var.set(msg))


# ── Entry ──────────────────────────────────────────────────────

def main():
    if DRAG_DROP_OK:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    MoeConverter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
