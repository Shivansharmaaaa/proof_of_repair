#!/bin/bash
# Opens every showcase terminal window (run START_DEMO.command first so the server is up).
cd "/Users/shivansh/Desktop/proof of repair/showcase" || exit 1
for f in 7_automated_tests 6_model_evaluation 5_merkle_tamper_demo 4_database_contents 3_bitcoin_timestamps 2_database_blockchain_audit 1_live_blockchain_feed; do
  open -a Terminal "$f.command"
  sleep 0.7
done
echo "Opened 7 windows. To turn them into tabs of one window: Terminal menu > Window > Merge All Windows."
