# Changelog

All notable changes to this fork are documented here.

## Unreleased

## [1.2.1] - 2026-04-28

### Changed

- Pinned Hugging Face ASR model downloads to verified model revisions for reproducible installs.
- Added a Settings > Model action that checks for newer remote model revisions and reports them without downloading unpinned files.
- Localized the new model revision check UI across all supported app languages.
- Bumped app version from `1.2.0` to `1.2.1`.

### Fixed

- Removed temporary dictation audio when transcription fails before a backend can clean up the raw WAV file.

## [1.2.0] - 2026-04-27

### Changed

- Renamed the public app branding to Qdicta with the tagline "Local dictation for Mac."
- Updated the app bundle name, DMG name, About text, menu labels, onboarding title, README, privacy notice, and third-party notices for Qdicta.
- Updated the project repository and update-check URLs to `https://github.com/shinshow/qdicta`.
- Added a new Qdicta app icon and package icon asset.
- Bumped app version from `1.1.9` to `1.2.0`.

## [1.1.9] - 2026-04-27

### Changed

- Clarified that file transcription accepts audio/video files by renaming the menu item and showing supported formats in the file picker.
- Updated README usage docs and privacy notes to match file transcription, recent dictation history, output modes, and current settings.

### Fixed

- Show a supported-format error instead of starting transcription when an unsupported file reaches file transcription.
- Bumped app version from `1.1.8` to `1.1.9`.

## [1.1.8] - 2026-04-26

### Changed

- Reduced perceived dictation latency by capping the start cue wait, switching the default start cue to the shorter `Tink` sound, and restoring the clipboard asynchronously after paste.
- Preloaded the Settings window after launch and prepared selected ASR models from Settings so model-switching pays less cost on the next dictation.
- Let automatic ASR language mode remain model-driven instead of forcing the UI/system language as a backend language hint.

### Fixed

- Refreshed PortAudio input devices when opening or polling Settings so newly connected microphones appear without restarting vvrite.
- Routed Settings and About menu actions directly to the app delegate from the menu bar.
- Bumped app version from `1.1.7` to `1.1.8`.

## [1.1.7] - 2026-04-26

### Fixed

- Prevented the start cue sound from being included in dictation audio by opening the microphone first, waiting for the cue, discarding captured cue frames, and only then showing the recording UI.
- Reduced short-input hallucinations and clipped first utterances caused by cue audio contaminating the recorded speech boundary.
- Bumped app version from `1.1.6` to `1.1.7`.

## [1.1.6] - 2026-04-26

### Fixed

- Resolved `auto` ASR language to the app UI language or system language before calling model backends, so Korean dictation keeps a Korean language hint after switching models from Settings.
- Applied the resolved language hint consistently to Qwen3-ASR, Whisper MLX, and whisper.cpp backends.
- Bumped app version from `1.1.5` to `1.1.6`.

## [1.1.5] - 2026-04-26

### Fixed

- Cleared onboarding model download progress from the menu bar after model load success or failure so `100%` does not remain visible after launch.
- Bumped app version from `1.1.4` to `1.1.5`.

## [1.1.4] - 2026-04-26

### Fixed

- Restored the intended toggle hotkey behavior: first press starts recording and shows the recording UI, second press stops recording and starts transcription.
- Bumped app version from `1.1.3` to `1.1.4`.

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
- Changed update checks to use this fork's GitHub Releases.
- Updated README documentation for selectable ASR models and fork installation URLs.
- Improved Qwen model loading so it uses the app-managed model directory.
- Improved Whisper response time by preparing and warming up the selected MLX Whisper model.
- Made model switching prepare the selected model immediately: downloaded models are loaded, missing models are downloaded first.

### Fixed

- Fixed `Qwen3-ASR model is not loaded` after switching from a downloaded Whisper model back to Qwen.
- Fixed model switch behavior so the previous backend is unloaded before the selected backend is activated.
