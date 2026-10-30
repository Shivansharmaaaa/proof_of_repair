#!/bin/bash
# Double-click (or: open -a Terminal scripts/demo_chain.command) to run the local Ethereum node in Terminal.
cd "/Users/shivansh/Desktop/proof of repair/chain" || exit 1
printf '\033]0;Ethereum node (Hardhat, chainId 31337)\007'
echo "=== Ethereum node (Hardhat) on http://127.0.0.1:8545 — every Proof of Repair transaction appears below ==="
npx hardhat node --hostname 127.0.0.1 --port 8545 2>&1 | tee ../artifacts/hardhat_node.log
