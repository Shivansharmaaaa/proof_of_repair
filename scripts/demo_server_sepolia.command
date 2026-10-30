#!/bin/bash
# Double-click (or: open -a Terminal scripts/demo_server_sepolia.command) to run the server on the public Sepolia testnet.
cd "/Users/shivansh/Desktop/proof of repair" || exit 1
printf '\033]0;Proof of Repair server (Ethereum Sepolia)\007'
NO_BROWSER=1 bash scripts/start_demo.sh sepolia
