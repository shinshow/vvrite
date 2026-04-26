<p align="center">
  <img src="assets/icon.png" width="128" height="128" alt="vvrite 아이콘">
</p>

<h1 align="center">vvrite</h1>

<p align="center">
  음성을 받아쓰기하여 텍스트로 붙여넣는 macOS 메뉴 막대 앱 — 온디바이스 AI로 구동됩니다.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-macOS_(Apple_Silicon)-blue" alt="macOS">
  <img src="https://img.shields.io/badge/models-Qwen3--ASR_%2B_Whisper-green" alt="Models">
  <img src="https://img.shields.io/badge/runtime-MLX-orange" alt="Runtime">
</p>

<p align="center">
  <a href="README.md">English</a> · 한국어 · <a href="README.ja.md">日本語</a> · <a href="README.zh-Hans.md">简体中文</a> · <a href="README.zh-Hant.md">繁體中文</a> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <a href="README.de.md">Deutsch</a> · <a href="CHANGELOG.md">변경이력</a>
</p>

---

## 작동 방식

1. 단축키를 누릅니다 (기본값: `Option + Space`)
2. 말합니다 — 화면에 녹음 오버레이가 나타납니다
3. 단축키를 다시 눌러 녹음을 중지합니다
4. 음성이 로컬에서 변환되어 활성 텍스트 필드에 붙여넣기됩니다

모든 처리는 [MLX](https://github.com/ml-explore/mlx)를 통해 기기에서 이루어집니다. 음성 데이터가 Mac 밖으로 나가지 않습니다.
기본 Qwen3-ASR 모델과 선택 가능한 Whisper 모델은 한국어와 영어가 섞인 받아쓰기를 포함한 다국어 전사를 지원합니다.

## 주요 기능

- **온디바이스 변환** — Qwen3-ASR은 mlx-audio로, Whisper는 mlx-whisper로 실행되며 클라우드 API가 필요 없습니다
- **모델 선택** — 설정에서 Qwen3-ASR 1.7B 8-bit, Whisper small 4-bit MLX, Whisper large-v3-turbo 4-bit MLX를 전환할 수 있습니다
- **다국어 지원** — 한국어, 영어, 한국어/영어 혼합 받아쓰기를 로컬 모델로 처리합니다
- **영어 번역 모드** — Whisper small 4-bit MLX는 한국어 또는 다국어 음성을 영어 텍스트로 번역 전사할 수 있습니다
- **전역 단축키** — 어떤 앱에서든 실행 가능하며, 설정에서 변경할 수 있습니다
- **메뉴 막대 앱** — 상태 막대에 조용히 자리 잡습니다
- **녹음 오버레이** — 오디오 레벨 바와 타이머로 시각적 피드백을 제공합니다
- **ESC로 취소** — 녹음 중 Escape를 누르면 변환 없이 취소됩니다
- **자동 붙여넣기** — 변환된 텍스트가 활성 필드에 바로 붙여넣기됩니다
- **안내형 온보딩** — 첫 실행 시 권한 설정과 모델 다운로드를 안내합니다

## ASR 모델

| 모델 | 적합한 용도 | 예상 디스크 사용량 | 영어 번역 |
|---|---|---:|---|
| Qwen3-ASR 1.7B 8-bit | 기본 다국어 받아쓰기 | 약 2.5 GB | 아니오 |
| Whisper small 4-bit MLX | 가장 빠른 Whisper 옵션과 한국어→영어 번역 | 약 139 MB | 예 |
| Whisper large-v3-turbo 4-bit MLX | 더 높은 품질의 빠른 Whisper 받아쓰기 | 약 463 MB | vvrite에서는 아니오 |

Qwen3-ASR은 mlx-audio를 통해 앱 프로세스 안에서 실행됩니다. Whisper 모델은 mlx-whisper로 실행되며, 준비된 뒤에는 선택한 모델을 미리 워밍업해 받아쓰기마다 반복되는 모델 시작 비용을 줄입니다.

## 모델 저장 위치

다운로드된 모델은 `~/Library/Application Support/vvrite/models/` 아래에 저장됩니다.
`/Applications/vvrite.app`을 삭제해도 다운로드된 모델은 자동으로 삭제되지 않습니다.
디스크 공간을 회수하려면 설정 > 모델 > 선택한 모델 삭제를 사용하거나 모델 폴더를 직접 삭제하세요.
이전 vvrite 빌드는 Qwen 파일을 `~/.cache/huggingface/hub/` 아래에 캐시했을 수도 있습니다.

## 언어 지원

기본 [`mlx-community/Qwen3-ASR-1.7B-8bit`](https://huggingface.co/mlx-community/Qwen3-ASR-1.7B-8bit) 모델은 [`Qwen/Qwen3-ASR-1.7B`](https://huggingface.co/Qwen/Qwen3-ASR-1.7B)의 MLX 변환 버전입니다. 공식 Qwen 모델 카드에 따르면, Qwen3-ASR-1.7B은 30개 언어와 22개 중국어 방언의 언어 식별 및 음성 인식을 지원합니다.

Whisper small 4-bit MLX와 Whisper large-v3-turbo 4-bit MLX는 빠른 Whisper 계열 전사 옵션입니다. 한국어와 영어가 섞인 입력은 전사 모드를 사용하세요. 한국어 또는 다국어 음성을 영어 결과로 받고 싶다면 Whisper small 4-bit MLX와 영어 번역 모드를 선택하세요.

## 요구 사항

- Apple Silicon (M1/M2/M3/M4) 탑재 macOS 13 이상
- 기본 모델용 디스크 공간 약 2.5 GB, 모든 선택 모델 설치 시 약 3.2 GB
- 마이크 권한
- 손쉬운 사용 권한 (전역 단축키용)

## 설치

### 소스에서 실행

```bash
# 복제
git clone https://github.com/shinshow/vvrite.git
cd vvrite

# 의존성 설치
pip install -r requirements.txt

# 실행
python -m vvrite
```

### .app으로 빌드

```bash
pip install -r requirements.txt
./scripts/build.sh
open dist/vvrite.dmg
```

`./scripts/build.sh`가 지원되는 빌드 방법입니다. PyInstaller 빌드, 코드 서명, 공증, 스테이플링, DMG 생성을 수행합니다. 설정된 Apple Developer 서명 인증서와 `notarytool` 프로파일이 필요합니다.

## 사용법

| 동작 | 단축키 |
|---|---|
| 녹음 시작 / 중지 | `Option + Space` (변경 가능) |
| 녹음 취소 | `Escape` |
| 설정 열기 | 메뉴 막대 아이콘 클릭 → 설정 |

첫 실행 시 온보딩 마법사가 다음을 안내합니다:
1. 마이크 및 손쉬운 사용 권한 부여
2. 선호하는 단축키 설정
3. 기본 ASR 모델 다운로드

## 기술 스택

| 구성 요소 | 기술 |
|---|---|
| UI | PyObjC (AppKit, Quartz) |
| ASR 모델 | [Qwen3-ASR-1.7B-8bit](https://huggingface.co/mlx-community/Qwen3-ASR-1.7B-8bit), [Whisper small 4-bit](https://huggingface.co/mlx-community/whisper-small-4bit), [Whisper large-v3-turbo 4-bit](https://huggingface.co/mlx-community/whisper-large-v3-turbo-4bit) |
| 추론 | Apple Silicon에서 [mlx-audio](https://github.com/ml-explore/mlx-audio) 및 [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) |
| 오디오 | sounddevice + soundfile + scipy |
| 패키징 | PyInstaller |

## 라이선스

MIT — 자세한 내용은 [LICENSE](LICENSE)를 참조하세요.

Whisper 모델 가중치는 Hugging Face의 [mlx-community](https://huggingface.co/mlx-community) 조직을 통해 배포됩니다. Qwen3-ASR 모델은 Apache 2.0 라이선스를 유지합니다.
