# Audio Converter

> **50+ 音频格式一键互转，市面所有音源 → WAV / MP3**

---

## 功能特色

| | 特性 | 说明 |
|---|------|------|
| 🖱️ | **拖拽式 GUI** | 支持拖拽文件和文件夹，一键转换 |
| 🎛️ | **51 种格式支持** | FLAC、AAC、OGG、WMA、APE、DSD……市面几乎所有音频格式 |
| ⚡ | **FFmpeg 驱动** | 底层基于 FFmpeg，稳定高效，质量无损 |
| 📦 | **批量处理** | 支持文件夹递归扫描，批量排队转换 |
| 🌸 | **动漫主题** | 内置萌系动漫风格 GUI 主题（可选） |

---

## GUI 界面

```
python audio_convert_gui.py
```

拖拽音频文件或整个文件夹到窗口即可开始转换。支持 WAV / MP3 / 同时输出，可选比特率、位深、采样率，实时进度条一目了然。

**动漫主题版：**
```
python audio_convert_gui_anime.py
```

---

## CLI 命令行

```
python audio_convert.py <路径...> [选项]
```

| 选项 | 说明 |
|------|------|
| `--to wav\|mp3\|both` | 输出格式（默认 both） |
| `--outdir`, `-o` | 输出目录（默认 ./converted） |
| `--mp3-bitrate` | 128k / 192k / 256k / 320k（默认） |
| `--wav-bit` | 16（默认）/ 24 |
| `--samplerate`, `-r` | 重采样（0 = 保持原始） |
| `--recursive`, `-R` | 递归处理子目录 |
| `--delete-original` | 转换后删除源文件 |
| `--formats` | 列出所有支持的输入格式 |

**示例：**
```
python audio_convert.py song.flac --to mp3
python audio_convert.py music/ -R --to both -o output/
```

---

## 安装

```
pip install -r requirements.txt
```

### FFmpeg 安装

| 系统 | 命令 |
|------|------|
| Windows | `scoop install ffmpeg` 或下载 ffmpeg.org 并将 `bin` 加入 PATH |
| macOS   | `brew install ffmpeg` |
| Linux   | `sudo apt install ffmpeg` |

---

## 对比：Audio Converter vs 在线转换工具

| 维度 | Audio Converter | 在线转换工具 |
|------|----------------|-------------|
| 🔒 **隐私安全** | ✅ 本地转换，文件不上传 | ❌ 文件需上传到服务器 |
| 📦 **批量处理** | ✅ 支持文件夹批量递归处理 | ❌ 通常单文件限制 |
| 🚫 **离线可用** | ✅ 完全离线，无需网络 | ❌ 必须联网 |
| ⚡ **转换速度** | ✅ FFmpeg 本地极速转换 | ❌ 受上传带宽和服务器排队限制 |
| 🎯 **格式数量** | ✅ 51 种输入格式 | ⚠️ 通常仅支持常见格式 |
| 💰 **费用** | ✅ 免费开源 | ⚠️ 付费订阅或次数限制 |

---

## 支持格式

FLAC、WAV、AIFF、ALAC、APE、WV、TTA、DSF、DFF、MP3、AAC、OGG、Opus、WMA、AC3、DTS、MID、RA、AMR、AU、CAF、VOC、RAW、PCM 等 50+ 种格式。
