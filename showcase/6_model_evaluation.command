#!/bin/bash
# 6 · Fine-tuned LLM evaluation + datasets
cd "/Users/shivansh/Desktop/proof of repair" || exit 1
printf '\033]0;6 · Fine-tuned LLM evaluation + datasets\007'
clear
echo '=== 6 · Fine-tuned LLM evaluation + datasets ==='; echo
echo "Held-out test set, raw model output (Mistral-7B + multi-domain LoRA):"
.venv/bin/python -m json.tool artifacts/eval_metrics_multidomain.json
echo; echo "Training data / knowledge base:"
.venv/bin/python -m json.tool artifacts/dataset_manifest_multidomain.json
echo; echo '(finished; this window stays open, run it again with the same command or close it)'
exec /bin/zsh -l
