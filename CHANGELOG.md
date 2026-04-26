# Changelog

All notable changes to this fork are documented here.

## Unreleased

## [1.1.3] - 2026-04-26

### Changed

- Changed the global dictation hotkey to push-to-talk behavior: press starts recording and release stops recording.
- Updated English and Korean onboarding text to describe hold-to-record behavior.
- Bumped app version from `1.1.2` to `1.1.3`.

### Fixed

- Fixed short, clipped recordings caused by key-down toggle semantics diverging from the intended key-down/key-up recording state machine.
- Started the microphone stream before playing the ready sound, and stopped the stream before playing the stop sound, so cue sounds do not define or pollute the captured speech boundary.

## [1.1.2] - 2026-04-26

### Changed

- Disabled timestamp generation in MLX Whisper transcription requests.
- Bumped app version from `1.1.1` to `1.1.2`.

### Fixed

- Cleared MLX runtime caches when unloading Qwen and MLX Whisper backends.
- Cleared the MLX Whisper model holder on unload so switched models are released from memory.

## [1.1.1] - 2026-04-26

This release packages the direct-distribution documentation, local DMG build mode, microphone device refresh fix, and MLX Whisper/backend cleanup that landed after `v1.1.0`.

### Added

- Added `THIRD_PARTY_NOTICES.md` with dependency and model license notes for direct distribution.
- Added `PRIVACY.md` documenting local audio handling, clipboard behavior, permissions, model storage, and network access.
- Added Qwen model download progress aggregation from Hugging Face download callbacks.

### Changed

- Replaced the selectable Whisper options with MLX-native `whisper-small-4bit` and `whisper-large-v3-turbo-4bit` models.
- Added an MLX Whisper backend that downloads Hugging Face snapshots into vvrite's app-managed model directory and warms up the selected model before dictation.
- Removed the PyInstaller build-time requirement for bundled whisper.cpp sidecar binaries.
- Reduced README documentation to English and Korean only.
- Updated the English translation-mode warning to name `Whisper small 4-bit MLX`, the model that currently supports translation in vvrite.
- Made PyInstaller hidden import ordering stable for repeatable build analysis.
- Cached the macOS 15-compatible `mlx-metal` metallib during release builds and avoided redundant codesigning of embedded binaries.
- Bumped app version from `1.1.0` to `1.1.1`.

## [1.1.0] - 2026-04-26

Compared with upstream `shaircast/vvrite` `v1.0.6`, this release adds selectable local ASR models, improves model lifecycle handling, and updates the app to use this fork's GitHub releases for update checks.

### Added

- Added selectable ASR models in Settings: Qwen3-ASR 1.7B 8-bit, Whisper small 4-bit MLX, and Whisper large-v3-turbo 4-bit MLX.
- Added app-managed model storage under `~/Library/Application Support/vvrite/models/`.
- Added model download progress, cached-model detection, and selected-model deletion controls.
- Added MLX-native Whisper support with model downloads from Hugging Face.
- Added English translation mode for Whisper small 4-bit MLX.
- Added persistent version history in `CHANGELOG.md`.

### Changed

- Bumped app version from `1.0.6` to `1.1.0`.
- Changed update checks to use `https://github.com/shinshow/vvrite` releases.
- Updated README documentation for selectable ASR models and fork installation URLs.
- Improved Qwen model loading so it uses the app-managed model directory.
- Improved Whisper response time by preparing and warming up the selected MLX Whisper model.
- Made model switching prepare the selected model immediately: downloaded models are loaded, missing models are downloaded first.

### Fixed

- Fixed `Qwen3-ASR model is not loaded` after switching from a downloaded Whisper model back to Qwen.
- Fixed model switch behavior so the previous backend is unloaded before the selected backend is activated.
