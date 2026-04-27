<p align="center">
  <img src="assets/qdicta-icon.png" width="128" height="128" alt="Qdicta icon">
</p>

<h1 align="center">Qdicta</h1>

<p align="center">
  Local dictation for Mac. On-device voice transcription that pastes into any app.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-macOS_(Apple_Silicon)-blue" alt="macOS">
  <img src="https://img.shields.io/badge/models-Qwen3--ASR_%2B_Whisper-green" alt="Models">
  <img src="https://img.shields.io/badge/runtime-MLX-orange" alt="Runtime">
</p>

<p align="center">
  <a href="README.md">한국어</a> · English · <a href="CHANGELOG.md">Changelog</a>
</p>

---

## How It Works

1. Press the hotkey (default: `Option + Space`)
2. Speak — a recording overlay appears on screen
3. Press the hotkey again to stop
4. Your speech is transcribed locally and pasted into the active text field

You can also transcribe an existing audio or video file from the menu bar. File transcription uses the same selected model and output settings, then pastes the result into the active text field.

Everything runs on-device using [MLX](https://github.com/ml-explore/mlx). No audio leaves your Mac.
The default Qwen3-ASR model and optional Whisper models support multilingual dictation, including Korean and English mixed in one recording.

## Features

- **On-device transcription** — Qwen3-ASR via mlx-audio or Whisper via mlx-whisper, no cloud API needed
- **Selectable ASR models** — switch between 5 local ASR models in Settings: Qwen3-ASR 8-bit/BF16 and three Whisper MLX options
- **Multilingual-ready** — Korean, English, and mixed Korean/English dictation are supported by the local models
- **English translation mode** — Whisper small 4-bit MLX and Whisper large-v3 4-bit MLX can translate spoken Korean or multilingual speech to English text
- **Global hotkey** — trigger from any app, configurable in Settings
- **Menu bar app** — lives quietly in your status bar
- **Recording overlay** — visual feedback with audio level bars and timer
- **ESC to cancel** — press Escape during recording to dismiss without transcribing
- **Auto-paste** — transcribed text is pasted directly into the active field
- **Audio/video file transcription** — transcribe existing WAV, MP3, M4A, MP4, CAF, AIFF, or FLAC files from the menu bar
- **Recent dictations** — copy the latest result or review recent results from the menu bar
- **Output modes and replacements** — choose voice/message/note/email formatting, add custom words, and define automatic text replacements
- **Guided onboarding** — first launch walks you through permissions and model download

## ASR Models

| Model | Best for | Approx. disk use | English translation |
|---|---|---:|---|
| Qwen3-ASR 1.7B 8-bit | Default multilingual dictation | ~2.5 GB | No |
| Qwen3-ASR 1.7B BF16 MLX | Higher-precision Qwen3-ASR dictation | ~4.08 GB | No |
| Whisper small 4-bit MLX | Fastest Whisper option and Korean-to-English translation | ~139 MB | Yes |
| Whisper large-v3 4-bit MLX | Higher-quality Whisper transcription and English translation | ~878 MB | Yes |
| Whisper large-v3-turbo 4-bit MLX | Higher-quality fast Whisper dictation | ~463 MB | No in Qdicta |

Qwen3-ASR runs in-process through mlx-audio. Whisper models run through mlx-whisper, and the selected model is warmed up after preparation to avoid paying the model startup cost during dictation.

## Model Storage

Downloaded models are stored under `~/Library/Application Support/vvrite/models/`.
Deleting `/Applications/Qdicta.app` does not automatically delete downloaded models.
Use Settings > Model > Delete selected model to reclaim disk space, or remove model folders manually.
Qdicta keeps the existing `vvrite` Application Support folder for upgrade compatibility.
Older builds may also have cached Qwen files under `~/.cache/huggingface/hub/`.

## Language Support

The default [`mlx-community/Qwen3-ASR-1.7B-8bit`](https://huggingface.co/mlx-community/Qwen3-ASR-1.7B-8bit) model is an MLX conversion of [`Qwen/Qwen3-ASR-1.7B`](https://huggingface.co/Qwen/Qwen3-ASR-1.7B). According to the official Qwen model card, Qwen3-ASR-1.7B supports language identification and speech recognition for 30 languages and 22 Chinese dialects.

The Whisper MLX models add fast Whisper-family transcription options. For Korean plus English code-switching, use transcription mode. For Korean or multilingual speech translated into English output, choose Whisper small 4-bit MLX or Whisper large-v3 4-bit MLX and English translation mode.

## Requirements

- macOS 13+ on Apple Silicon (M1/M2/M3/M4)
- ~2.5 GB disk space for the default model, or ~8.1 GB if all selectable models are installed
- Microphone permission
- Accessibility permission (for global hotkey)

## Installation

### From Source

```bash
# Clone
git clone https://github.com/shinshow/qdicta.git
cd qdicta

# Install dependencies
pip install -r requirements.txt

# Run
python -m vvrite
```

### Build as .app

```bash
pip install -r requirements.txt
./scripts/build.sh
open dist/Qdicta.dmg
```

`./scripts/build.sh` is the supported release build path. It performs the PyInstaller build, Developer ID code signing, notarization, stapling, and DMG creation. It requires a configured Apple Developer signing identity and `notarytool` profile.

For local development without an Apple Developer Program account, use:

```bash
./scripts/build.sh --local
open dist/Qdicta.dmg
```

Local builds use ad-hoc signing by default and skip notarization, so they are not suitable for public distribution. To use a local signing identity instead, run `LOCAL_SIGN_IDENTITY="Apple Development: ..." ./scripts/build.sh --local`.

## Usage

| Action | Shortcut |
|---|---|
| Start / stop recording | `Option + Space` (configurable) |
| Cancel recording | `Escape` |
| Open settings | Click menu bar icon → Settings |
| Transcribe an existing file | Click menu bar icon → Transcribe Audio/Video File... |
| Copy the latest result | Click menu bar icon → Copy Last Dictation |
| View recent results | Click menu bar icon → Recent Dictations... |

On first launch, the onboarding wizard will guide you through:
1. Granting microphone and accessibility permissions
2. Setting your preferred hotkey
3. Downloading the default ASR model

### Live Dictation

1. Put the cursor where you want the text to appear.
2. Press the configured hotkey.
3. Speak while the recording overlay is visible.
4. Press the hotkey again to stop.
5. Qdicta transcribes locally, pastes the result into the active app, and stores it in recent dictations.

If you press `Escape` while recording, Qdicta cancels the recording and does not transcribe or paste anything.

### File Transcription

1. Put the cursor where you want the result to appear.
2. Click the menu bar icon and choose **Transcribe Audio/Video File...**.
3. Select a supported file: `WAV`, `MP3`, `M4A`, `MP4`, `CAF`, `AIFF`, or `FLAC`.
4. Qdicta copies the selected file to a temporary working file, transcribes it locally with the currently selected model, pastes the result into the active app, and stores it in recent dictations.

File transcription does not open a separate results window. If the active app is not ready for text input, use **Copy Last Dictation** or **Recent Dictations...** from the menu bar to recover the result.

### Settings

Open **Settings** from the menu bar to configure:

- **General** — UI language, recognition language, launch at login, and automatic update checks
- **Recording** — global hotkey, microphone, and permission status
- **Model** — ASR model, model download/delete, and transcription vs English translation output
- **Output** — voice/message/note/email mode, custom words, and automatic replacements
- **Sound** — recording start/stop sounds and volume
- **Advanced** — optional delete-by-keystroke shortcut for retracting the most recently pasted result

## Tech Stack

| Component | Technology |
|---|---|
| UI | PyObjC (AppKit, Quartz) |
| ASR Models | [Qwen3-ASR 1.7B 8-bit](https://huggingface.co/mlx-community/Qwen3-ASR-1.7B-8bit), [Qwen3-ASR 1.7B BF16 MLX](https://huggingface.co/mlx-community/Qwen3-ASR-1.7B-bf16), [Whisper small 4-bit MLX](https://huggingface.co/mlx-community/whisper-small-4bit), [Whisper large-v3 4-bit MLX](https://huggingface.co/mlx-community/whisper-large-v3-4bit), [Whisper large-v3-turbo 4-bit MLX](https://huggingface.co/mlx-community/whisper-large-v3-turbo-4bit) |
| Inference | [mlx-audio](https://github.com/ml-explore/mlx-audio) and [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) on Apple Silicon |
| Audio | sounddevice + soundfile + scipy |
| Packaging | PyInstaller |

## License

MIT — see [LICENSE](LICENSE) for details.

Third-party dependency and model notices are documented in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Privacy and local data handling notes are documented in [PRIVACY.md](PRIVACY.md).
