#!/bin/bash
# 3 · Bitcoin timestamps (OpenTimestamps)
cd "/Users/shivansh/Desktop/proof of repair" || exit 1
if [ -f .env ]; then set -a; source .env; set +a; fi   # DATABASE_URL (e.g. Supabase), else local PostgreSQL
printf '\033]0;3 · Bitcoin timestamps (OpenTimestamps)\007'
clear
echo '=== 3 · Bitcoin timestamps (OpenTimestamps) ==='; echo
.venv/bin/python scripts/ots_status.py --db-only
echo; echo "Older confirmed batches:"
.venv/bin/python scripts/ots_status.py | grep -A6 "^CONFIRMED" | head -24
.venv/bin/python scripts/export_ots_files.py | tail -3
echo; echo '(finished; this window stays open, run it again with the same command or close it)'
exec /bin/zsh -l
