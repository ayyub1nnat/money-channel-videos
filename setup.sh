#!/usr/bin/env bash
# One-time setup per fresh machine (~2 min). Run from the repo root.
set -e
cd "$(dirname "$0")"
pip install --break-system-packages -q kokoro-onnx soundfile skia-python scipy pillow numpy 2>&1 | grep -v WARNING || true
mkdir -p models
[ -s models/kokoro-v1.0.onnx ] || curl -sSL -o models/kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
[ -s models/voices-v1.0.bin ] || curl -sSL -o models/voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
which ffmpeg >/dev/null || (apt-get update -qq && apt-get install -y -qq ffmpeg)
ls -la models
echo "setup ok"
