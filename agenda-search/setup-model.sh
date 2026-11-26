#!/bin/sh
set -eu
cache="$HOME/.cache/mdcw"
mkdir -p "$cache"
base=https://huggingface.co/Xenova/all-MiniLM-L6-v2/resolve/main
curl -fL "$base/onnx/model_quantized.onnx" -o "$cache/model.onnx.part"
mv "$cache/model.onnx.part" "$cache/model.onnx"
curl -fL "$base/tokenizer.json" -o "$cache/tokenizer.json"
