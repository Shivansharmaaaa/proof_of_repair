#!/bin/bash
# One-command demo: PostgreSQL + Ethereum + OpenTimestamps + API/web UI.
#   bash scripts/start_demo.sh            local Hardhat Ethereum node (opens its own Terminal window with live logs)
#   bash scripts/start_demo.sh sepolia    public Ethereum Sepolia testnet (wallet in .env must hold test ETH)
set -e
ROOT="/Users/shivansh/Desktop/proof of repair"
cd "$ROOT"
source .venv/bin/activate
# .env may set DATABASE_URL (e.g. Supabase); without it the local PostgreSQL below is used.
if [ -f .env ]; then set -a; source .env; set +a; fi
NETWORK="${1:-local}"
PORT="${PORT:-8000}"
PG_BIN=/opt/homebrew/opt/postgresql@15/bin
export DATABASE_URL="${DATABASE_URL:-postgresql://localhost/proof_of_repair}"
export OTS_MODE="${OTS_MODE:-live}"
export HF_HUB_OFFLINE=1
export PYTHONUNBUFFERED=1

echo "== 1/4 PostgreSQL (${DATABASE_URL##*@})"   # host/db only, never the password
brew services start postgresql@15 >/dev/null 2>&1 || true
for _ in $(seq 1 30); do "$PG_BIN/pg_isready" -q -h localhost && break; sleep 0.5; done
[ -f data/processed/repair_kb.jsonl ] || python scripts/prepare_multidomain.py >/dev/null
# Load the guides only into an empty database: re-sending all 4,666 in one batch is slow and
# breaks over Supabase's pooler. Refresh them by hand with: python scripts/init_db.py
if python -c "import os, sys, psycopg; c = psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=15); sys.exit(0 if c.execute('SELECT count(*) FROM repair_guides').fetchone()[0] else 1)" 2>/dev/null; then
  echo "   database ready: repair guides already loaded"
else
  python scripts/init_db.py | head -1
fi

echo "== 2/4 Ethereum ($NETWORK)"
rpc_up() {
  curl -s -X POST http://127.0.0.1:8545 -H 'content-type: application/json' \
    --data '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' | grep -q 0x7a69
}
if [ "$NETWORK" = "sepolia" ]; then
  [ -f artifacts/chain_config.sepolia.json ] || bash scripts/deploy_sepolia.sh
  export CHAIN_CONFIG="$ROOT/artifacts/chain_config.sepolia.json"
  python -c "import json;c=json.load(open('$CHAIN_CONFIG'));print('   contract', c['explorer_address_prefix']+c['contract_address'])"
else
  if ! rpc_up; then
    echo "   starting Hardhat node in a new Terminal window…"
    open -a Terminal "$ROOT/scripts/demo_chain.command"
    for _ in $(seq 1 60); do rpc_up && break; sleep 0.5; done
  fi
  CFG="$ROOT/artifacts/chain_config.hardhat-local.json"
  HAS_CODE=$(python - "$CFG" <<'PY'
import json, sys
from web3 import Web3
try:
    cfg = json.load(open(sys.argv[1]))
    w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
    print("yes" if len(w3.eth.get_code(Web3.to_checksum_address(cfg["contract_address"]))) > 0 else "no")
except Exception:
    print("no")
PY
)
  if [ "$HAS_CODE" != "yes" ]; then
    (cd chain && npx hardhat run scripts/deploy.js --network localhost | grep -E "deployed|Wrote")
    ANCHORS=$("$PG_BIN/psql" -h localhost -d proof_of_repair -Atc "SELECT count(*) FROM anchor_batches" 2>/dev/null || echo 0)
    if [ "${ANCHORS:-0}" != "0" ]; then
      echo "   NOTE: fresh local chain, but the database has $ANCHORS batch(es) anchored on the previous one."
      echo "         For a clean demo run:  python scripts/init_db.py --reset   (keeps the 4,666 guides)"
    fi
  fi
  export CHAIN_CONFIG="$CFG"
fi

echo "== 3/4 OpenTimestamps: $OTS_MODE (Bitcoin calendar servers)"
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "   port $PORT is used by another app; using 8080 instead"
  PORT=8080
fi
echo "== 4/4 API + web UI  ->  http://127.0.0.1:$PORT   (API docs: /docs)"
[ -n "$NO_BROWSER" ] || (sleep 4 && open "http://127.0.0.1:$PORT") >/dev/null 2>&1 &
exec uvicorn src.cloud.api:app --host 127.0.0.1 --port "$PORT"
