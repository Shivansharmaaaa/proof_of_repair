#!/bin/bash
# Stop the Proof of Repair server (and the local Hardhat chain if it is running). PostgreSQL keeps running.
for pid in $(pgrep -f "uvicorn src.cloud.api"); do kill "$pid" && echo "stopped server (pid $pid)"; done
for pid in $(pgrep -f "hardhat node"); do kill "$pid" && echo "stopped local Ethereum node (pid $pid)"; done
echo "Done. Start again with START_DEMO.command"
