"""PyInstaller spec for vvrite macOS app."""
import glob
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

whisper_cli = os.path.join(ROOT_DIR, "vendor", "whisper.cpp", "whisper-cli")
if not os.path.exists(whisper_cli):
    whisper_cli = os.path.join(ROOT_DIR, "vendor", "whisper.cpp", "main")
if not os.path.exists(whisper_cli):
    raise RuntimeError("Missing whisper.cpp sidecar. Run scripts/build_whisper_cpp.sh")
whisper_dylibs = glob.glob(os.path.join(ROOT_DIR, "vendor", "whisper.cpp", "*.dylib"))
if not whisper_dylibs:
    raise RuntimeError("Missing whisper.cpp dylibs. Run scripts/build_whisper_cpp.sh")
whisper_binaries = [(whisper_cli, "whisper.cpp")] + [
    (path, "whisper.cpp") for path in sorted(whisper_dylibs)
]

# PyObjC bridge modules need all submodules collected
pyobjc_hiddenimports = (
    collect_submodules("objc")
    + collect_submodules("AppKit")
    + collect_submodules("Foundation")
    + collect_submodules("Quartz")
    + collect_submodules("ApplicationServices")
    + collect_submodules("AVFoundation")
    + collect_submodules("ServiceManagement")
)

a = Analysis(
    ["vvrite/main.py"],
    pathex=[],
    binaries=[
        ("/opt/homebrew/bin/ffmpeg", "."),
        *whisper_binaries,
    ],
    datas=[
        # soundfile needs libsndfile
        (os.path.join(site_packages, "_soundfile_data"), "_soundfile_data"),
        # MLX Metal shaders and native libs
        (os.path.join(mlx_package_dir, "lib"), os.path.join("mlx", "lib")),
    ],
    hiddenimports=pyobjc_hiddenimports + [
        # Locale modules (dynamically imported by vvrite.locales)
        *collect_submodules("vvrite.locales"),
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
        # Transformers
        "transformers",
        "tokenizers",
        # Audio
        "sounddevice",
        "soundfile",
        # Other
        "huggingface_hub",
        "safetensors",
        "numpy",
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
        "CFBundleShortVersionString": "1.0.6",  # keep in sync with vvrite/__init__.__version__
        "CFBundleVersion": "6",
        "LSUIElement": True,
        "NSMicrophoneUsageDescription": (
            "vvrite needs microphone access to record and transcribe your speech."
        ),
        "NSHighResolutionCapable": True,
        "NSSupportsAutomaticTermination": False,
        "NSSupportsSuddenTermination": False,
    },
)
