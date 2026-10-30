#!/bin/bash
# 5 · Merkle tree + tamper detection (worked example)
cd "/Users/shivansh/Desktop/proof of repair" || exit 1
printf '\033]0;5 · Merkle tree + tamper detection (worked example)\007'
clear
echo '=== 5 · Merkle tree + tamper detection (worked example) ==='; echo
.venv/bin/python scripts/merkle_worked_example.py
echo; echo '(finished; this window stays open, run it again with the same command or close it)'
exec /bin/zsh -l
