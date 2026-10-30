#!/bin/bash
# 1 · Live blockchain feed (Ethereum Sepolia)
cd "/Users/shivansh/Desktop/proof of repair" || exit 1
if [ -f .env ]; then set -a; source .env; set +a; fi   # DATABASE_URL (e.g. Supabase), else local PostgreSQL
printf '\033]0;1 · Live blockchain feed (Ethereum Sepolia)\007'
clear
echo '=== 1 · Live blockchain feed (Ethereum Sepolia) ==='; echo
.venv/bin/python scripts/watch_chain.py
echo; echo '(finished; this window stays open, run it again with the same command or close it)'
exec /bin/zsh -l
