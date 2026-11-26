#!/bin/sh
set -eu
cache="$HOME/.cache/mdcw"
mkdir -p "$cache"
base=https://huggingface.co/Xenova/all-MiniLM-L6-v2/resolve/main
curl -fL "$base/onnx/model_quantized.onnx" -o "$cache/model.onnx.part"
mv "$cache/model.onnx.part" "$cache/model.onnx"
curl -fL "$base/tokenizer.json" -o "$cache/tokenizer.json"
# Optional local generation on Macs with Apple Intelligence enabled.
if [ "$(uname -s)" = Darwin ] && command -v swiftc >/dev/null; then
  swiftc "$(dirname "$0")/explain.swift" -o "$cache/explain"
fi
