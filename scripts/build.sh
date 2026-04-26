#!/usr/bin/env bash
set -euo pipefail

# ── Configuration ──────────────────────────────────────────────
IDENTITY="Developer ID Application: Saturn Studio (449B2G47F7)"
BUILD_MODE="release"
BUNDLE="dist/vvrite.app"
ENTITLEMENTS="entitlements.plist"
NOTARY_PROFILE="notarytool-profile"
ZIP="dist/vvrite.zip"
DMG="dist/vvrite.dmg"
if [[ -z "${PYTHON:-}" && -x ".venv/bin/python" ]]; then
    PYTHON_BIN=".venv/bin/python"
else
    PYTHON_BIN="${PYTHON:-python3}"
fi
if [[ -z "${PIP:-}" && -x ".venv/bin/pip" ]]; then
    PIP_BIN=".venv/bin/pip"
else
    PIP_BIN="${PIP:-pip3}"
fi
if [[ -z "${PYINSTALLER:-}" && -x ".venv/bin/pyinstaller" ]]; then
    PYINSTALLER_BIN=".venv/bin/pyinstaller"
else
    PYINSTALLER_BIN="${PYINSTALLER:-pyinstaller}"
fi

usage() {
    cat <<'EOF'
Usage: ./scripts/build.sh [--local]

Build modes:
  release   Build, Developer ID sign, notarize, staple, and create a notarized DMG.
  --local   Build a local test DMG without Developer ID notarization.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --local)
            BUILD_MODE="local"
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

LOCAL_SIGN_IDENTITY="${LOCAL_SIGN_IDENTITY:-}"
if [[ "$BUILD_MODE" == "local" && -z "$LOCAL_SIGN_IDENTITY" ]]; then
    LOCAL_SIGN_IDENTITY="-"
fi

SIGN_IDENTITY="$IDENTITY"
if [[ "$BUILD_MODE" == "local" ]]; then
    SIGN_IDENTITY="$LOCAL_SIGN_IDENTITY"
fi

codesign_runtime() {
    local target="$1"
    local args=(
        --force
        --options runtime
        --entitlements "$ENTITLEMENTS"
        --sign "$SIGN_IDENTITY"
    )
    if [[ "$BUILD_MODE" != "local" ]]; then
        args+=(--timestamp)
    fi
    codesign "${args[@]}" "$target"
}

SIGNED_TARGETS_FILE=$(mktemp)
sign_once_runtime() {
    local target="$1"
    if grep -Fxq -- "$target" "$SIGNED_TARGETS_FILE"; then
        return
    fi
    codesign_runtime "$target"
    printf '%s\n' "$target" >> "$SIGNED_TARGETS_FILE"
}

codesign_dmg() {
    local args=(--force --sign "$SIGN_IDENTITY")
    if [[ "$BUILD_MODE" != "local" ]]; then
        args+=(--timestamp)
    fi
    codesign "${args[@]}" "$DMG"
}

# ── Step 0: Preflight ───────────────────────────────────────────
echo "▸ Checking build environment..."
"$PYTHON_BIN" - <<'PY'
import importlib
import importlib.util
import sys

import_modules = {
    "ServiceManagement": "pyobjc-framework-ServiceManagement",
}
find_spec_modules = {
    "mlx_whisper": "mlx-whisper",
}

missing = []
for module_name, package_name in import_modules.items():
    try:
        importlib.import_module(module_name)
    except ImportError:
        missing.append(f"{package_name} ({module_name})")
for module_name, package_name in find_spec_modules.items():
    if importlib.util.find_spec(module_name) is None:
        missing.append(f"{package_name} ({module_name})")

if missing:
    details = "\n".join(f"  - {item}" for item in missing)
    raise SystemExit(
        "Missing required Python bridge modules:\n"
        f"{details}\n"
        "Run `pip install -r requirements.txt` and retry."
    )

print("  ✓ Required Python bridge modules available")
PY

# ── Step 0.5: Backward-compatible metallib ────────────────────
# mlx-metal ships per-macOS-version wheels. A metallib built for macOS 26
# (MSL 4.0) won't load on macOS 15. Swap in the macOS 15 wheel's metallib
# so the resulting .app runs on macOS 15+.
MLX_METAL_VER=$("$PIP_BIN" show mlx-metal | awk '/^Version:/{print $2}')
MLX_METAL_PLATFORM="macosx_15_0_arm64"
MLX_COMPAT_CACHE_DIR="build/mlx-metal-compat/$MLX_METAL_VER/$MLX_METAL_PLATFORM"
CACHE_METALLIB="$MLX_COMPAT_CACHE_DIR/mlx.metallib"
SITE=$("$PYTHON_BIN" -c "import site; print(site.getsitepackages()[0])")
TARGET_METALLIB="$SITE/mlx/lib/mlx.metallib"
if [[ ! -f "$CACHE_METALLIB" ]]; then
    echo "▸ Fetching macOS 15-compatible mlx-metal $MLX_METAL_VER..."
    MLX_COMPAT_DIR=$(mktemp -d)
    mkdir -p "$MLX_COMPAT_CACHE_DIR"
    "$PIP_BIN" download --no-deps -d "$MLX_COMPAT_DIR" \
        "mlx-metal==$MLX_METAL_VER" \
        --platform "$MLX_METAL_PLATFORM" --only-binary :all: --quiet
    unzip -p "$MLX_COMPAT_DIR"/mlx_metal-*.whl "mlx/lib/mlx.metallib" \
        > "$CACHE_METALLIB"
    rm -rf "$MLX_COMPAT_DIR"
else
    echo "▸ Using cached macOS 15-compatible mlx-metal $MLX_METAL_VER..."
fi
if cmp -s "$CACHE_METALLIB" "$TARGET_METALLIB"; then
    echo "  ✓ Backward-compatible metallib already installed (macOS 15+)"
else
    cp "$CACHE_METALLIB" "$TARGET_METALLIB"
    echo "  ✓ Backward-compatible metallib installed (macOS 15+)"
fi

# ── Step 1: Build ──────────────────────────────────────────────
echo "▸ Building with PyInstaller..."
"$PYINSTALLER_BIN" vvrite.spec --noconfirm
echo "  ✓ Build complete"

# ── Step 2: Sign all binaries inside the bundle ────────────────
if [[ "$BUILD_MODE" == "local" ]]; then
    echo "▸ Local build mode: signing with '$SIGN_IDENTITY' and skipping notarization."
else
    echo "▸ Release build mode: signing with '$SIGN_IDENTITY'."
fi
echo "▸ Signing embedded binaries..."

# Sign .so and .dylib files first (innermost → outermost)
find "$BUNDLE" -type f \( -name "*.so" -o -name "*.dylib" \) | while read -r lib; do
    sign_once_runtime "$lib"
done

# Sign embedded frameworks
find "$BUNDLE/Contents/Frameworks" -type f -perm +111 2>/dev/null | while read -r bin; do
    sign_once_runtime "$bin"
done

# Sign the main executable
sign_once_runtime "$BUNDLE/Contents/MacOS/vvrite"

# Sign the .app bundle itself
codesign_runtime "$BUNDLE"
rm -f "$SIGNED_TARGETS_FILE"

echo "  ✓ Signing complete"

# ── Step 3: Verify signature ──────────────────────────────────
echo "▸ Verifying signature..."
codesign --verify --deep --strict "$BUNDLE"
echo "  ✓ Signature valid"

if [[ "$BUILD_MODE" == "local" ]]; then
    echo "▸ Skipping notarization and Gatekeeper assessment for local build."
else
# ── Step 4: Notarize ──────────────────────────────────────────
echo "▸ Creating zip for notarization..."
ditto -c -k --keepParent "$BUNDLE" "$ZIP"

echo "▸ Submitting for notarization (this may take a few minutes)..."
xcrun notarytool submit "$ZIP" \
    --keychain-profile "$NOTARY_PROFILE" \
    --wait

# ── Step 5: Staple ────────────────────────────────────────────
echo "▸ Stapling notarization ticket..."
xcrun stapler staple "$BUNDLE"
echo "  ✓ Staple complete"

# ── Step 6: Final verification ────────────────────────────────
echo "▸ Final Gatekeeper check..."
spctl --assess --type exec --verbose "$BUNDLE"
fi

# ── Step 7: Create distribution DMG ─────────────────────────
echo "▸ Creating DMG..."
rm -f "$DMG"
DMG_STAGE=$(mktemp -d)
cp -R "$BUNDLE" "$DMG_STAGE/"
ln -s /Applications "$DMG_STAGE/Applications"
hdiutil create -volname "vvrite" -srcfolder "$DMG_STAGE" \
    -ov -format UDZO "$DMG"
rm -rf "$DMG_STAGE"

echo "▸ Signing DMG..."
codesign_dmg

if [[ "$BUILD_MODE" == "local" ]]; then
    echo "▸ Skipping DMG notarization for local build."
    echo "  ✓ Local DMG ready: $DMG"
    echo "▸ Cleaning local intermediate app bundle..."
    rm -rf "$BUNDLE" "dist/vvrite"
    echo ""
    echo "✓ Done! $DMG is ready for local testing."
    exit 0
fi

echo "▸ Notarizing DMG..."
xcrun notarytool submit "$DMG" \
    --keychain-profile "$NOTARY_PROFILE" \
    --wait

echo "▸ Stapling DMG..."
xcrun stapler staple "$DMG"
echo "  ✓ DMG ready: $DMG"

echo ""
echo "✓ Done! $DMG is signed, notarized, and ready for distribution."
