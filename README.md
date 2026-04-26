<p align="center">
  <img src="assets/icon.png" width="128" height="128" alt="vvrite icon">
</p>

<h1 align="center">vvrite</h1>

<p align="center">
  macOS menu bar app that transcribes your voice and pastes the text — powered by on-device AI.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-macOS_(Apple_Silicon)-blue" alt="macOS">
  <img src="https://img.shields.io/badge/models-Qwen3--ASR_%2B_Whisper-green" alt="Models">
  <img src="https://img.shields.io/badge/runtime-MLX-orange" alt="Runtime">
</p>

<p align="center">
  <a href="README.ko.md">한국어</a> · <a href="README.ja.md">日本語</a> · <a href="README.zh-Hans.md">简体中文</a> · <a href="README.zh-Hant.md">繁體中文</a> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <a href="README.de.md">Deutsch</a> · <a href="CHANGELOG.md">Changelog</a>
</p>

---

## How It Works

1. Press the hotkey (default: `Option + Space`)
2. Speak — a recording overlay appears on screen
3. Press the hotkey again to stop
4. Your speech is transcribed locally and pasted into the active text field

Everything runs on-device using [MLX](https://github.com/ml-explore/mlx). No audio leaves your Mac.
The default Qwen3-ASR model and optional Whisper models support multilingual dictation, including Korean and English mixed in one recording.

## Features

- **On-device transcription** — Qwen3-ASR via mlx-audio or Whisper via mlx-whisper, no cloud API needed
- **Selectable ASR models** — switch between Qwen3-ASR 1.7B 8-bit, Whisper small 4-bit MLX, and Whisper large-v3-turbo 4-bit MLX in Settings
- **Multilingual-ready** — Korean, English, and mixed Korean/English dictation are supported by the local models
- **English translation mode** — Whisper small 4-bit MLX can translate spoken Korean or multilingual speech to English text
- **Global hotkey** — trigger from any app, configurable in Settings
- **Menu bar app** — lives quietly in your status bar
- **Recording overlay** — visual feedback with audio level bars and timer
- **ESC to cancel** — press Escape during recording to dismiss without transcribing
- **Auto-paste** — transcribed text is pasted directly into the active field
- **Guided onboarding** — first launch walks you through permissions and model download

## ASR Models

| Model | Best for | Approx. disk use | English translation |
|---|---|---:|---|
| Qwen3-ASR 1.7B 8-bit | Default multilingual dictation | ~2.5 GB | No |
| Whisper small 4-bit MLX | Fastest Whisper option and Korean-to-English translation | ~139 MB | Yes |
| Whisper large-v3-turbo 4-bit MLX | Higher-quality fast Whisper dictation | ~463 MB | No in vvrite |

Qwen3-ASR runs in-process through mlx-audio. Whisper models run through mlx-whisper, and the selected model is warmed up after preparation to avoid paying the model startup cost during dictation.

## Model Storage

Downloaded models are stored under `~/Library/Application Support/vvrite/models/`.
Deleting `/Applications/vvrite.app` does not automatically delete downloaded models.
Use Settings > Model > Delete selected model to reclaim disk space, or remove model folders manually.
Older vvrite builds may also have cached Qwen files under `~/.cache/huggingface/hub/`.

## Language Support

The default [`mlx-community/Qwen3-ASR-1.7B-8bit`](https://huggingface.co/mlx-community/Qwen3-ASR-1.7B-8bit) model is an MLX conversion of [`Qwen/Qwen3-ASR-1.7B`](https://huggingface.co/Qwen/Qwen3-ASR-1.7B). According to the official Qwen model card, Qwen3-ASR-1.7B supports language identification and speech recognition for 30 languages and 22 Chinese dialects.

Whisper small 4-bit MLX and Whisper large-v3-turbo 4-bit MLX add fast Whisper-family transcription options. For Korean plus English code-switching, use transcription mode. For Korean or multilingual speech translated into English output, choose Whisper small 4-bit MLX and English translation mode.

## Requirements

- macOS 13+ on Apple Silicon (M1/M2/M3/M4)
- ~2.5 GB disk space for the default model, or ~3.2 GB if all selectable models are installed
- Microphone permission
- Accessibility permission (for global hotkey)

## Installation

### From Source

```bash
# Clone
git clone https://github.com/shinshow/vvrite.git
cd vvrite

# Install dependencies
pip install -r requirements.txt

# Run
python -m vvrite
```

### Build as .app

```bash
pip install -r requirements.txt
./scripts/build.sh
open dist/vvrite.dmg
```

`./scripts/build.sh` is the supported build path. It performs the PyInstaller build, code signing, notarization, stapling, and DMG creation. It requires a configured Apple Developer signing identity and `notarytool` profile.

## Usage

| Action | Shortcut |
|---|---|
| Start / stop recording | `Option + Space` (configurable) |
| Cancel recording | `Escape` |
| Open settings | Click menu bar icon → Settings |

On first launch, the onboarding wizard will guide you through:
1. Granting microphone and accessibility permissions
2. Setting your preferred hotkey
3. Downloading the default ASR model

## Tech Stack

| Component | Technology |
|---|---|
| UI | PyObjC (AppKit, Quartz) |
| ASR Models | [Qwen3-ASR-1.7B-8bit](https://huggingface.co/mlx-community/Qwen3-ASR-1.7B-8bit), [Whisper small 4-bit](https://huggingface.co/mlx-community/whisper-small-4bit), [Whisper large-v3-turbo 4-bit](https://huggingface.co/mlx-community/whisper-large-v3-turbo-4bit) |
| Inference | [mlx-audio](https://github.com/ml-explore/mlx-audio) and [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) on Apple Silicon |
| Audio | sounddevice + soundfile + scipy |
| Packaging | PyInstaller |

## License

MIT — see [LICENSE](LICENSE) for details.

Whisper model weights are distributed through the [mlx-community](https://huggingface.co/mlx-community) Hugging Face organization. The Qwen3-ASR model remains Apache 2.0 licensed.
