<p align="center">
  <img src="assets/qdicta-icon.png" width="128" height="128" alt="Qdicta 아이콘">
</p>

<h1 align="center">Qdicta</h1>

<p align="center">
  Mac용 로컬 받아쓰기 앱. 말하면 바로 전사해 현재 앱에 붙여넣습니다.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-macOS_(Apple_Silicon)-blue" alt="macOS">
  <img src="https://img.shields.io/badge/models-Qwen3--ASR_%2B_Whisper-green" alt="Models">
  <img src="https://img.shields.io/badge/runtime-MLX-orange" alt="Runtime">
</p>

<p align="center">
  한국어 · <a href="README.en.md">English</a> · <a href="CHANGELOG.md">변경이력</a>
</p>

---

## 작동 방식

1. 단축키를 누릅니다 (기본값: `Option + Space`)
2. 말합니다 — 화면에 녹음 오버레이가 나타납니다
3. 단축키를 다시 눌러 녹음을 중지합니다
4. 음성이 로컬에서 변환되어 활성 텍스트 필드에 붙여넣기됩니다

메뉴 막대에서 기존 오디오/비디오 파일을 선택해 전사할 수도 있습니다. 파일 전사는 현재 선택된 모델과 출력 설정을 그대로 사용하며, 결과는 활성 텍스트 필드에 붙여넣기됩니다.

모든 처리는 [MLX](https://github.com/ml-explore/mlx)를 통해 기기에서 이루어집니다. 음성 데이터가 Mac 밖으로 나가지 않습니다.
기본 Qwen3-ASR 모델과 선택 가능한 Whisper 모델은 한국어와 영어가 섞인 받아쓰기를 포함한 다국어 전사를 지원합니다.

## 주요 기능

- **온디바이스 변환** — Qwen3-ASR은 mlx-audio로, Whisper는 mlx-whisper로 실행되며 클라우드 API가 필요 없습니다
- **모델 선택** — 설정에서 Qwen3-ASR 8-bit/BF16과 세 가지 Whisper MLX 옵션, 총 5개 로컬 ASR 모델을 전환할 수 있습니다
- **다국어 지원** — 한국어, 영어, 한국어/영어 혼합 받아쓰기를 로컬 모델로 처리합니다
- **영어 번역 모드** — Whisper small 4-bit MLX와 Whisper large-v3 4-bit MLX는 한국어 또는 다국어 음성을 영어 텍스트로 번역 전사할 수 있습니다
- **전역 단축키** — 어떤 앱에서든 실행 가능하며, 설정에서 변경할 수 있습니다
- **메뉴 막대 앱** — 상태 막대에 조용히 자리 잡습니다
- **녹음 오버레이** — 오디오 레벨 바와 타이머로 시각적 피드백을 제공합니다
- **ESC로 취소** — 녹음 중 Escape를 누르면 변환 없이 취소됩니다
- **자동 붙여넣기** — 변환된 텍스트가 활성 필드에 바로 붙여넣기됩니다
- **오디오/비디오 파일 전사** — 메뉴 막대에서 WAV, MP3, M4A, MP4, CAF, AIFF, FLAC 파일을 전사합니다
- **최근 받아쓰기** — 메뉴 막대에서 마지막 결과를 복사하거나 최근 결과를 확인할 수 있습니다
- **출력 모드와 자동 치환** — 음성/메시지/노트/이메일 모드, 사용자 지정 단어, 자동 치환을 설정할 수 있습니다
- **안내형 온보딩** — 첫 실행 시 권한 설정과 모델 다운로드를 안내합니다

## ASR 모델

| 모델 | 적합한 용도 | 예상 디스크 사용량 | 영어 번역 |
|---|---|---:|---|
| Qwen3-ASR 1.7B 8-bit | 기본 다국어 받아쓰기 | 약 2.5 GB | 아니오 |
| Qwen3-ASR 1.7B BF16 MLX | 더 높은 정밀도의 Qwen3-ASR 받아쓰기 | 약 4.08 GB | 아니오 |
| Whisper small 4-bit MLX | 가장 빠른 Whisper 옵션과 한국어→영어 번역 | 약 139 MB | 예 |
| Whisper large-v3 4-bit MLX | 더 높은 품질의 Whisper 전사와 영어 번역 | 약 878 MB | 예 |
| Whisper large-v3-turbo 4-bit MLX | 더 높은 품질의 빠른 Whisper 받아쓰기 | 약 463 MB | Qdicta에서는 아니오 |

Qwen3-ASR은 mlx-audio를 통해 앱 프로세스 안에서 실행됩니다. Whisper 모델은 mlx-whisper로 실행되며, 준비된 뒤에는 선택한 모델을 미리 워밍업해 받아쓰기마다 반복되는 모델 시작 비용을 줄입니다.

## 모델 저장 위치

다운로드된 모델은 `~/Library/Application Support/vvrite/models/` 아래에 저장됩니다.
`/Applications/Qdicta.app`을 삭제해도 다운로드된 모델은 자동으로 삭제되지 않습니다.
디스크 공간을 회수하려면 설정 > 모델 > 선택한 모델 삭제를 사용하거나 모델 폴더를 직접 삭제하세요.
업그레이드 호환성을 위해 Qdicta는 기존 `vvrite` Application Support 폴더를 계속 사용합니다.
이전 빌드는 Qwen 파일을 `~/.cache/huggingface/hub/` 아래에 캐시했을 수도 있습니다.

## 언어 지원

기본 [`mlx-community/Qwen3-ASR-1.7B-8bit`](https://huggingface.co/mlx-community/Qwen3-ASR-1.7B-8bit) 모델은 [`Qwen/Qwen3-ASR-1.7B`](https://huggingface.co/Qwen/Qwen3-ASR-1.7B)의 MLX 변환 버전입니다. 공식 Qwen 모델 카드에 따르면, Qwen3-ASR-1.7B은 30개 언어와 22개 중국어 방언의 언어 식별 및 음성 인식을 지원합니다.

Whisper MLX 모델들은 빠른 Whisper 계열 전사 옵션입니다. 한국어와 영어가 섞인 입력은 전사 모드를 사용하세요. 한국어 또는 다국어 음성을 영어 결과로 받고 싶다면 Whisper small 4-bit MLX 또는 Whisper large-v3 4-bit MLX와 영어 번역 모드를 선택하세요.

## 요구 사항

- Apple Silicon (M1/M2/M3/M4) 탑재 macOS 13 이상
- 기본 모델용 디스크 공간 약 2.5 GB, 모든 선택 모델 설치 시 약 8.1 GB
- 마이크 권한
- 손쉬운 사용 권한 (전역 단축키용)

## 설치

### 소스에서 실행

```bash
# 복제
git clone https://github.com/shinshow/qdicta.git
cd qdicta

# 의존성 설치
pip install -r requirements.txt

# 실행
python -m vvrite
```

### .app으로 빌드

```bash
pip install -r requirements.txt
./scripts/build.sh
open dist/Qdicta.dmg
```

`./scripts/build.sh`가 지원되는 빌드 방법입니다. PyInstaller 빌드, 코드 서명, 공증, 스테이플링, DMG 생성을 수행합니다. 설정된 Apple Developer 서명 인증서와 `notarytool` 프로파일이 필요합니다.

## 사용법

| 동작 | 단축키 |
|---|---|
| 녹음 시작 / 중지 | `Option + Space` (변경 가능) |
| 녹음 취소 | `Escape` |
| 설정 열기 | 메뉴 막대 아이콘 클릭 → 설정 |
| 기존 파일 전사 | 메뉴 막대 아이콘 클릭 → 오디오/비디오 파일 전사... |
| 마지막 결과 복사 | 메뉴 막대 아이콘 클릭 → 마지막 받아쓰기 복사 |
| 최근 결과 보기 | 메뉴 막대 아이콘 클릭 → 최근 받아쓰기... |

첫 실행 시 온보딩 마법사가 다음을 안내합니다:
1. 마이크 및 손쉬운 사용 권한 부여
2. 선호하는 단축키 설정
3. 기본 ASR 모델 다운로드

### 실시간 받아쓰기

1. 텍스트가 들어갈 위치에 커서를 둡니다.
2. 설정된 단축키를 누릅니다.
3. 녹음 오버레이가 보이는 동안 말합니다.
4. 단축키를 다시 눌러 녹음을 중지합니다.
5. Qdicta가 로컬에서 전사한 뒤 활성 앱에 결과를 붙여넣고 최근 받아쓰기에 저장합니다.

녹음 중 `Escape`를 누르면 녹음이 취소되며 전사하거나 붙여넣지 않습니다.

### 파일 전사

1. 결과가 들어갈 위치에 커서를 둡니다.
2. 메뉴 막대 아이콘을 클릭하고 **오디오/비디오 파일 전사...**를 선택합니다.
3. 지원 파일을 선택합니다: `WAV`, `MP3`, `M4A`, `MP4`, `CAF`, `AIFF`, `FLAC`.
4. Qdicta가 선택한 파일을 임시 작업 파일로 복사하고, 현재 선택된 모델로 로컬 전사를 실행한 뒤 활성 앱에 결과를 붙여넣고 최근 받아쓰기에 저장합니다.

파일 전사는 별도 결과 창을 열지 않습니다. 활성 앱이 텍스트 입력을 받을 수 없는 상태였다면 메뉴 막대의 **마지막 받아쓰기 복사** 또는 **최근 받아쓰기...**에서 결과를 다시 확인하세요.

### 설정

메뉴 막대의 **설정**에서 다음을 조정할 수 있습니다:

- **일반** — UI 언어, 인식 언어, 로그인 시 실행, 자동 업데이트 확인
- **녹음** — 전역 단축키, 마이크, 권한 상태
- **모델** — ASR 모델, 모델 다운로드/삭제, 전사 또는 영어 번역 출력
- **출력** — 음성/메시지/노트/이메일 모드, 사용자 지정 단어, 자동 치환
- **소리** — 녹음 시작/중지 소리와 볼륨
- **고급** — 가장 최근에 붙여넣은 결과를 Delete 키 방식으로 삭제하는 선택 단축키

## 기술 스택

| 구성 요소 | 기술 |
|---|---|
| UI | PyObjC (AppKit, Quartz) |
| ASR 모델 | [Qwen3-ASR 1.7B 8-bit](https://huggingface.co/mlx-community/Qwen3-ASR-1.7B-8bit), [Qwen3-ASR 1.7B BF16 MLX](https://huggingface.co/mlx-community/Qwen3-ASR-1.7B-bf16), [Whisper small 4-bit MLX](https://huggingface.co/mlx-community/whisper-small-4bit), [Whisper large-v3 4-bit MLX](https://huggingface.co/mlx-community/whisper-large-v3-4bit), [Whisper large-v3-turbo 4-bit MLX](https://huggingface.co/mlx-community/whisper-large-v3-turbo-4bit) |
| 추론 | Apple Silicon에서 [mlx-audio](https://github.com/ml-explore/mlx-audio) 및 [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) |
| 오디오 | sounddevice + soundfile + scipy |
| 패키징 | PyInstaller |

## 라이선스

MIT — 자세한 내용은 [LICENSE](LICENSE)를 참조하세요.

서드파티 의존성과 모델 고지는 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)에 정리되어 있습니다. 개인정보와 로컬 데이터 처리 내용은 [PRIVACY.md](PRIVACY.md)를 참조하세요.
