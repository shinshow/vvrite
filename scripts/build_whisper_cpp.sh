#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$ROOT/build/whisper.cpp"
OUT_DIR="$ROOT/vendor/whisper.cpp"
PINNED_TAG="v1.8.1"

mkdir -p "$(dirname "$BUILD_DIR")" "$OUT_DIR"

if [ ! -d "$BUILD_DIR/.git" ]; then
    rm -rf "$BUILD_DIR"
    git clone --depth 1 --branch "$PINNED_TAG" \
        https://github.com/ggml-org/whisper.cpp.git "$BUILD_DIR"
else
    git -C "$BUILD_DIR" fetch --depth 1 origin tag "$PINNED_TAG"
    git -C "$BUILD_DIR" checkout --detach "$PINNED_TAG"
fi

cmake -S "$BUILD_DIR" -B "$BUILD_DIR/build" \
    -DCMAKE_BUILD_TYPE=Release \
    -DGGML_METAL=ON
cmake --build "$BUILD_DIR/build" -j

rm -f "$OUT_DIR/whisper-cli" "$OUT_DIR/main" "$OUT_DIR"/*.dylib

if [ -x "$BUILD_DIR/build/bin/whisper-cli" ]; then
    cp "$BUILD_DIR/build/bin/whisper-cli" "$OUT_DIR/whisper-cli"
elif [ -x "$BUILD_DIR/build/bin/main" ]; then
    cp "$BUILD_DIR/build/bin/main" "$OUT_DIR/main"
else
    echo "Unable to find built whisper.cpp CLI binary" >&2
    exit 1
fi

cp "$BUILD_DIR/build/src/libwhisper.1.8.1.dylib" "$OUT_DIR/libwhisper.1.dylib"
cp "$BUILD_DIR/build/ggml/src/libggml.dylib" "$OUT_DIR/libggml.dylib"
cp "$BUILD_DIR/build/ggml/src/libggml-base.dylib" "$OUT_DIR/libggml-base.dylib"
cp "$BUILD_DIR/build/ggml/src/libggml-cpu.dylib" "$OUT_DIR/libggml-cpu.dylib"
cp "$BUILD_DIR/build/ggml/src/ggml-blas/libggml-blas.dylib" "$OUT_DIR/libggml-blas.dylib"
cp "$BUILD_DIR/build/ggml/src/ggml-metal/libggml-metal.dylib" "$OUT_DIR/libggml-metal.dylib"

for binary in "$OUT_DIR"/whisper-cli "$OUT_DIR"/main "$OUT_DIR"/*.dylib; do
    [ -e "$binary" ] || continue
    otool -l "$binary" | awk '
        $1 == "cmd" && $2 == "LC_RPATH" { in_rpath = 1; next }
        in_rpath && $1 == "path" { print $2; in_rpath = 0 }
    ' | while read -r rpath; do
        install_name_tool -delete_rpath "$rpath" "$binary" 2>/dev/null || true
    done
    install_name_tool -add_rpath "@loader_path" "$binary" 2>/dev/null || true
done

chmod +x "$OUT_DIR/whisper-cli" "$OUT_DIR/main" 2>/dev/null || true
echo "whisper.cpp sidecar ready in $OUT_DIR"
