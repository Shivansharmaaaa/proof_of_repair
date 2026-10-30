#!/bin/bash
# Deploy ProofOfRepair to the public Ethereum Sepolia testnet (wallet + RPC in .env)
set -e
ROOT="/Users/shivansh/Desktop/proof of repair"
cd "$ROOT"
if [ ! -f .env ]; then
  echo "Create .env from .env.example with SEPOLIA_RPC_URL and DEPLOYER_PRIVATE_KEY"
  exit 1
fi
set -a
# shellcheck disable=SC1091
source .env
set +a
if [ -z "${SEPOLIA_RPC_URL}" ] || [ -z "${DEPLOYER_PRIVATE_KEY}" ]; then
  echo "SEPOLIA_RPC_URL and DEPLOYER_PRIVATE_KEY required in .env"
  exit 1
fi
BAL=$(.venv/bin/python -c "
from web3 import Web3
w3 = Web3(Web3.HTTPProvider('$SEPOLIA_RPC_URL'))
print(w3.from_wei(w3.eth.get_balance('$DEPLOYER_ADDRESS'), 'ether'))")
echo "Wallet $DEPLOYER_ADDRESS balance: $BAL Sepolia ETH"
if [ "$BAL" = "0" ]; then
  echo "Fund it first: https://cloud.google.com/application/web3/faucet/ethereum/sepolia"
  exit 1
fi
cd chain
npx hardhat compile
npx hardhat run scripts/deploy.js --network sepolia
echo "Sepolia config written to artifacts/chain_config.sepolia.json"
echo "Start the demo on Sepolia: bash scripts/start_demo.sh sepolia"
