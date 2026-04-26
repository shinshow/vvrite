"""PyInstaller spec for vvrite macOS app."""
import importlib.util
import os
import sys
import sysconfig

ROOT_DIR = os.path.abspath(os.getcwd())
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from PyInstaller.utils.hooks import collect_submodules
from vvrite import APP_BUNDLE_IDENTIFIER

block_cipher = None

site_packages = sysconfig.get_paths()["purelib"]
mlx_spec = importlib.util.find_spec("mlx")
if mlx_spec is None or not mlx_spec.submodule_search_locations:
    raise RuntimeError("Unable to locate mlx package for PyInstaller datas")
mlx_package_dir = mlx_spec.submodule_search_locations[0]
mlx_whisper_spec = importlib.util.find_spec("mlx_whisper")
if mlx_whisper_spec is None or not mlx_whisper_spec.submodule_search_locations:
    raise RuntimeError("Unable to locate mlx_whisper package for PyInstaller datas")
mlx_whisper_package_dir = mlx_whisper_spec.submodule_search_locations[0]

# PyObjC bridge modules need all submodules collected
pyobjc_hiddenimports = (
    sorted(collect_submodules("objc"))
    + sorted(collect_submodules("AppKit"))
    + sorted(collect_submodules("Foundation"))
    + sorted(collect_submodules("Quartz"))
    + sorted(collect_submodules("ApplicationServices"))
    + sorted(collect_submodules("AVFoundation"))
    + sorted(collect_submodules("ServiceManagement"))
)

a = Analysis(
    ["vvrite/main.py"],
    pathex=[],
    binaries=[],
    datas=[
        # soundfile needs libsndfile
        (os.path.join(site_packages, "_soundfile_data"), "_soundfile_data"),
        # MLX Metal shaders and native libs
        (os.path.join(mlx_package_dir, "lib"), os.path.join("mlx", "lib")),
        # MLX Whisper tokenizer and mel filter assets
        (
            os.path.join(mlx_whisper_package_dir, "assets"),
            os.path.join("mlx_whisper", "assets"),
        ),
    ],
    hiddenimports=pyobjc_hiddenimports + [
        # Locale modules (dynamically imported by vvrite.locales)
        *sorted(collect_submodules("vvrite.locales")),
        # ASR backends (dynamically imported by vvrite.transcriber)
        *sorted(collect_submodules("vvrite.asr_backends")),
        # MLX (namespace package — must be explicit)
        "mlx",
        "mlx._reprlib_fix",
        "mlx.core",
        "mlx.nn",
        "mlx.optimizers",
        "mlx.utils",
        # MLX ecosystem
        "mlx_lm",
        "mlx_audio",
        "mlx_audio.stt",
        "mlx_audio.stt.models",
        "mlx_audio.stt.models.qwen3_asr",
        "mlx_whisper",
        "mlx_whisper.audio",
        "mlx_whisper.decoding",
        "mlx_whisper.load_models",
        "mlx_whisper.timing",
        "mlx_whisper.tokenizer",
        "mlx_whisper.transcribe",
        "mlx_whisper.whisper",
        # Transformers
        "transformers",
        "tokenizers",
        "tiktoken",
        "more_itertools",
        # Audio
        "sounddevice",
        "soundfile",
        # Other
        "huggingface_hub",
        "safetensors",
        "numpy",
        "scipy",
        "scipy.signal",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "pytest",
        # Heavy packages not needed (we use mlx, not torch)
        "torch",
        "torchaudio",
        "torchvision",
        "pyarrow",
        "cv2",
        "opencv-python",
        "onnxruntime",
        "PIL",
        "matplotlib",
        "pandas",
        "__main__",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="vvrite",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    target_arch="arm64",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="vvrite",
)

app = BUNDLE(
    coll,
    name="vvrite.app",
    icon="assets/vvrite.icns",
    bundle_identifier=APP_BUNDLE_IDENTIFIER,
    info_plist={
        "CFBundleName": "vvrite",
        "CFBundleShortVersionString": "1.1.4",  # keep in sync with vvrite/__init__.__version__
        "CFBundleVersion": "11",
        "LSUIElement": True,
        "NSMicrophoneUsageDescription": (
            "vvrite needs microphone access to record and transcribe your speech."
        ),
        "NSHighResolutionCapable": True,
        "NSSupportsAutomaticTermination": False,
        "NSSupportsSuddenTermination": False,
    },
)
