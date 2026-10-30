#!/bin/bash
# 4 · PostgreSQL database contents
cd "/Users/shivansh/Desktop/proof of repair" || exit 1
if [ -f .env ]; then set -a; source .env; set +a; fi   # DATABASE_URL (e.g. Supabase), else local PostgreSQL
printf '\033]0;4 · PostgreSQL database contents\007'
clear
echo '=== 4 · PostgreSQL database contents ==='; echo
P=(/opt/homebrew/opt/postgresql@15/bin/psql "${DATABASE_URL:-postgresql://localhost/proof_of_repair}")
"${P[@]}" -c "SELECT (SELECT count(*) FROM repair_guides) AS repair_guides, (SELECT count(*) FROM assets) AS devices, (SELECT count(*) FROM repair_records) AS repair_records, (SELECT count(*) FROM anchor_batches) AS anchor_batches;"
"${P[@]}" -c "SELECT asset_type, source, count(*) AS procedures FROM repair_guides GROUP BY 1,2 ORDER BY 1,2;"
"${P[@]}" -c "SELECT asset_type, asset_id, device, fault_code, usage_value, usage_unit, chain_network, block_number, left(chain_tx,20) AS tx, ots_status FROM v_device_history;"
echo; echo '(finished; this window stays open, run it again with the same command or close it)'
exec /bin/zsh -l
