#!/bin/bash
# START HERE (also after opening the laptop lid): double-click this file in Finder.
# Restarts whatever stopped, checks the database <-> blockchain link, and opens everything.
#   NETWORK=local  -> force the offline Hardhat chain      NO_OPEN=1 -> don't open browser/pgAdmin
ROOT="/Users/shivansh/Desktop/proof of repair"
cd "$ROOT" || exit 1
printf '\033]0;Proof of Repair - START\007'
PG_BIN=/opt/homebrew/opt/postgresql@15/bin
PY="$ROOT/.venv/bin/python"
# Same database as the server: DATABASE_URL from .env (e.g. Supabase), else local PostgreSQL.
if [ -f .env ]; then set -a; source .env; set +a; fi

echo "=================================================="
echo "  Proof of Repair: start / recover"
echo "=================================================="

echo "[1/5] PostgreSQL"
brew services start postgresql@15 >/dev/null 2>&1 || true
for _ in $(seq 1 30); do "$PG_BIN/pg_isready" -q -h localhost && break; sleep 1; done
if ! "$PG_BIN/pg_isready" -q -h localhost; then
  brew services restart postgresql@15 >/dev/null 2>&1
  for _ in $(seq 1 30); do "$PG_BIN/pg_isready" -q -h localhost && break; sleep 1; done
fi
"$PG_BIN/pg_isready" -q -h localhost && echo "      OK  database proof_of_repair is up" || { echo "      FAIL PostgreSQL did not start"; exit 1; }

echo "[2/5] Blockchain network"
if [ -z "$NETWORK" ]; then
  if [ -f artifacts/chain_config.sepolia.json ] && curl -s -m 8 -X POST https://ethereum-sepolia-rpc.publicnode.com \
       -H 'content-type: application/json' --data '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' | grep -q 0xaa36a7; then
    NETWORK=sepolia
  else
    NETWORK=local
    echo "      Sepolia not reachable (no internet?) -> using the local Hardhat chain"
  fi
fi
if [ "$NETWORK" = "sepolia" ]; then
  WANT=sepolia; CFG="$ROOT/artifacts/chain_config.sepolia.json"; LAUNCHER=scripts/demo_server_sepolia.command
else
  WANT=hardhat-local; CFG="$ROOT/artifacts/chain_config.hardhat-local.json"; LAUNCHER=scripts/demo_server.command
fi
echo "      OK  network: $NETWORK"

echo "[3/5] Proof of Repair server"
net_on() {
  curl -s -m 5 "http://127.0.0.1:$1/api/health" 2>/dev/null \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['chain'].get('network',''))" 2>/dev/null
}
find_port() { for p in 8080 8000; do [ "$(net_on "$p")" = "$WANT" ] && { echo "$p"; return; }; done; }
PORT=$(find_port)
if [ -n "$PORT" ]; then
  echo "      OK  already running on port $PORT"
else
  # Stop only our own stale server (never another app on the port).
  for pid in $(lsof -tiTCP:8080 -sTCP:LISTEN 2>/dev/null); do
    ps -o command= -p "$pid" | grep -q "src.cloud.api" && kill "$pid" && echo "      restarting stale server (pid $pid)"
  done
  sleep 2
  open -a Terminal "$ROOT/$LAUNCHER"
  echo -n "      starting"
  for _ in $(seq 1 180); do PORT=$(find_port); [ -n "$PORT" ] && break; echo -n "."; sleep 1; done
  echo
  [ -n "$PORT" ] && echo "      OK  running on port $PORT" || { echo "      FAIL server did not start; check the server window"; exit 1; }
fi
URL="http://127.0.0.1:$PORT"

echo "[4/5] Database <-> blockchain audit"
CHAIN_CONFIG="$CFG" "$PY" scripts/check_db_chain.py | tail -2 | sed 's/^/      /'
echo "      Bitcoin timestamps (OpenTimestamps):"
"$PY" scripts/ots_status.py --db-only 2>/dev/null | grep -E "^(CONFIRMED|pending)" | sed 's/^/        /'
"$PY" scripts/export_ots_files.py >/dev/null 2>&1 && echo "      files for opentimestamps.org: artifacts/ots_public/"

echo "[5/5] Opening"
CONTRACT=$(python3 -c "import json;c=json.load(open('$CFG'));p=c.get('explorer_address_prefix');print(p+c['contract_address'] if p else '')")
echo "      web app   $URL"
[ -n "$CONTRACT" ] && echo "      contract  $CONTRACT"
echo "      pgAdmin   server 'Proof of Repair', database proof_of_repair"
if [ -z "$NO_OPEN" ]; then
  open "$URL"
  [ -n "$CONTRACT" ] && open "$CONTRACT"
  open -a "pgAdmin 4"
fi

echo
echo "READY. Demo script: DEMO.md  |  pgAdmin SQL: docs/demo_queries.sql  |  stop: STOP_DEMO.command"
