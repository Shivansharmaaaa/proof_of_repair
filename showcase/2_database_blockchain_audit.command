#!/bin/bash
# 2 · Database <-> blockchain audit
cd "/Users/shivansh/Desktop/proof of repair" || exit 1
if [ -f .env ]; then set -a; source .env; set +a; fi   # DATABASE_URL (e.g. Supabase), else local PostgreSQL
printf '\033]0;2 · Database <-> blockchain audit\007'
clear
echo '=== 2 · Database <-> blockchain audit ==='; echo
.venv/bin/python scripts/check_db_chain.py
echo; echo '(finished; this window stays open, run it again with the same command or close it)'
exec /bin/zsh -l
