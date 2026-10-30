#!/bin/bash
# Mistral-7B-Instruct 4-bit MLX LoRA on phones + cars + appliances (prompt-masked)
set -e
cd "/Users/shivansh/Desktop/proof of repair"
source .venv/bin/activate
export PYTHONUNBUFFERED=1
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

MODEL="$HOME/.cache/huggingface/hub/models--mlx-community--Mistral-7B-Instruct-v0.2-4bit/snapshots/64481e3a4a7bb0990c45c991958f8d6c00c1e785"
if [ ! -f "$MODEL/model.safetensors" ]; then
  echo "Missing local model at $MODEL"
  exit 1
fi
[ -f data/mlx_multidomain/train.jsonl ] || python scripts/prepare_multidomain.py

mkdir -p artifacts/adapters/multidomain-mlx-lora
echo "=== MLX multi-domain LoRA $(date) ==="

python -m mlx_lm lora \
  --model "$MODEL" \
  --train \
  --data data/mlx_multidomain \
  --fine-tune-type lora \
  --mask-prompt \
  --batch-size 1 \
  --iters "${ITERS:-600}" \
  --learning-rate 2e-5 \
  --num-layers 8 \
  --max-seq-length 1024 \
  --grad-checkpoint \
  --steps-per-report 10 \
  --steps-per-eval 200 \
  --val-batches 10 \
  --save-every 100 \
  --clear-cache-threshold 2000000000 \
  --adapter-path artifacts/adapters/multidomain-mlx-lora \
  2>&1 | tee artifacts/finetune_multidomain_mlx.log

echo "=== MULTI-DOMAIN LORA DONE $(date) ==="
