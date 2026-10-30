#!/bin/bash
# 7 · Automated tests
cd "/Users/shivansh/Desktop/proof of repair" || exit 1
printf '\033]0;7 · Automated tests\007'
clear
echo '=== 7 · Automated tests ==='; echo
.venv/bin/python -m pytest tests/ -v
echo; echo '(finished; this window stays open, run it again with the same command or close it)'
exec /bin/zsh -l
