#!/bin/bash
# Double-click (or: open -a Terminal scripts/demo_server.command) to run PostgreSQL + contract deploy + API/web UI.
cd "/Users/shivansh/Desktop/proof of repair" || exit 1
printf '\033]0;Proof of Repair server (PostgreSQL + API + UI)\007'
NO_BROWSER=1 bash scripts/start_demo.sh "$@"
