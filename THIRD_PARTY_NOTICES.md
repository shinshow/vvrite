# Third-Party Notices

vvrite is distributed under the MIT License. This file summarizes key third-party components, model sources, and license notes that matter for direct distribution.

## Runtime Dependencies

The packaged app includes Python runtime dependencies installed from `requirements.txt` and their transitive dependencies. Important direct runtime components include:

| Component | Purpose | License |
|---|---|---|
| PyObjC frameworks | macOS AppKit, Quartz, Foundation, AVFoundation, ServiceManagement bridges | MIT-style / PyObjC license |
| MLX (`mlx`, `mlx-metal`) | Apple Silicon ML array/runtime backend | MIT |
| `mlx-audio` | Qwen3-ASR inference integration | MIT |
| `mlx-whisper` | Whisper inference integration | MIT |
| `sounddevice` | Microphone input | MIT |
| `soundfile` | Audio file I/O | BSD-style |
| `scipy` | Audio processing utilities | BSD-3-Clause |
| `numpy` | Numerical processing | BSD-3-Clause |
| `huggingface_hub` | Model metadata and snapshot downloads | Apache-2.0 |
| `transformers` | Model/tokenizer support used by MLX audio tooling | Apache-2.0 |
| `tokenizers` | Tokenizer support | Apache-2.0 |
| `safetensors` | Model tensor file support | Apache-2.0 |

Some binary Python wheels may bundle additional native libraries, for example BLAS/LAPACK/runtime libraries. Their license notices are retained in the installed package metadata and wheel distributions.

## Models

vvrite downloads model weights separately into the user's Application Support folder. Model files are not bundled in the app DMG.

| Model | Source | License note |
|---|---|---|
| Qwen3-ASR 1.7B 8-bit | `mlx-community/Qwen3-ASR-1.7B-8bit` on Hugging Face | Converted from Qwen3-ASR; model license remains Apache-2.0 according to the upstream model card. |
| Whisper small 4-bit MLX | `mlx-community/whisper-small-4bit` on Hugging Face | Distributed through the MLX community model repository. Check the model card before redistribution. |
| Whisper large-v3-turbo 4-bit MLX | `mlx-community/whisper-large-v3-turbo-4bit` on Hugging Face | Distributed through the MLX community model repository. Check the model card before redistribution. |

Users download model weights directly from Hugging Face through the app. The user is responsible for complying with the model providers' terms when using downloaded models.

## No FFmpeg Bundle

Current vvrite builds do not bundle `ffmpeg`. Audio capture and processing use `sounddevice`, `soundfile`, `scipy`, and MLX-related Python packages.

## Source Availability

vvrite's source code is available from the project repository. Third-party source code and license text are available from each upstream project and package distribution.
