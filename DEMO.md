# Demo guide: Cloud Proof of Repair for Phones, Cars and Appliances

About 10 minutes. Everything runs on this Mac; all three back ends are real, standard software:

| Layer | Software | Where you show it |
|---|---|---|
| Database | **PostgreSQL 15** | **pgAdmin 4** (already installed) |
| Blockchain | **Ethereum**: Hardhat node (local) or **Sepolia public testnet** | Hardhat Terminal log / **Etherscan** |
| Timestamping | **OpenTimestamps** (anchors into **Bitcoin**) | receipt in the UI, `.ots` files in `artifacts/ots_calendar/` |
| AI | **Mistral-7B-Instruct + LoRA** fine-tuned on iFixit + MechanicDB + NHTSA | web UI ("Grounded on …") |

## 0. Before the teacher arrives (1 min)

**One click:** double-click `scripts/showcase.command` in Finder. It starts PostgreSQL and the server on the
public **Ethereum Sepolia** testnet, then opens the web app, the smart contract and the latest anchor
transaction on **sepolia.etherscan.io**, and pgAdmin.
Contract: https://sepolia.etherscan.io/address/0x37C9383cdCBb52126D238925a6EDbcccF8b3b6d9

The contract source is verified on Etherscan (Contract tab ✓ → Read Contract → `isRootAnchored`).
After anchoring live, prove the database matches the chain:
`.venv/bin/python scripts/check_db_chain.py` → `RESULT: DATABASE AND BLOCKCHAIN ARE CONSISTENT`.

**Terminal showcase:** double-click `showcase/RUN_SHOWCASE.command` to open 7 windows: the live blockchain feed,
the database ↔ blockchain audit, Bitcoin timestamps, database contents, the Merkle tamper demo, model
evaluation and the tests. Terminal → Window → *Merge All Windows* turns them into tabs.

Manual / offline alternative:

```bash
cd "/Users/shivansh/Desktop/proof of repair"
python scripts/init_db.py --reset        # optional: empty repair history, keeps the 4,666 guides
bash scripts/start_demo.sh               # local Ethereum; or: bash scripts/start_demo.sh sepolia
```

Or double-click in Finder: `scripts/demo_chain.command` (Ethereum node window) and then
`scripts/demo_server.command` (server window).

The script starts PostgreSQL, opens a **Terminal window running the Hardhat Ethereum node**, deploys the
`ProofOfRepair` smart contract, and opens the web UI at http://127.0.0.1:8000, or **:8080** if port 8000 is
taken (your `Desktop/nosql` app uses 8000; the script prints which port it chose).

Warm the model once (the first diagnosis loads Mistral-7B, ~20 s): seal one demo case, then
`python scripts/init_db.py --reset` if you want an empty history again (restart the script afterwards).

**pgAdmin (first time only):** pgAdmin → Tools → *Import/Export Servers* → Import → `docs/pgadmin_servers.json`
(or *Register → Server*: host `localhost`, port `5432`, user `shivansh`, database `proof_of_repair`, no password).
Open *Query Tool* and load `docs/demo_queries.sql`.

## 1. The problem (30 s)

A buyer of a second-hand phone, car or washing machine cannot tell whether the repair history they are
shown is real or was edited before the sale.

## 2. Workshop seals a repair (3 min): web UI, section 01

1. Top bar: point at **PostgreSQL · N guides**, **LIVE · hardhat-local / Ethereum Sepolia**, **OTS live · Bitcoin**.
2. **Phone** tab → chip **iPhone 6 · battery** → *Seal repair to device*.
   - The system looked up a real repair manual in PostgreSQL (full-text search over 4,666 procedures), and
     Mistral-7B with the LoRA adapter wrote the structured report. The **Grounded on** card links the iFixit guide.
   - Hash plate: the report hash, plus a leaf digest that binds the IMEI, battery cycles, report, evidence and model.
3. **Car** tab → **Civic · P0420** (OBD-II code → MechanicDB fix list).
4. **Appliance** tab → **Kenmore washer · drain**.

## 3. Show it in the database (2 min): pgAdmin

- Tables: `assets`, `repair_records`, `anchor_batches`, `record_anchors`, `repair_guides`
  (right-click the database → *ERD For Database* for a diagram).
- Run queries 1–5 from `docs/demo_queries.sql`. `v_device_history` shows every repair with its anchor.

## 4. Anchor on the blockchain (2 min): web UI, section 03

1. *Anchor pending batch* → one **Merkle root** for all three records, one **Ethereum transaction**,
   one **OpenTimestamps** receipt (pending → confirmed in Bitcoin within a few hours).
2. Show the blockchain:
   - **Local:** the Hardhat Terminal window shows `eth_sendTransaction`, `Contract call: ProofOfRepair#anchorMerkleRoot`,
     the transaction hash, gas used and block number, and the hash matches the UI.
   - **Sepolia:** click the transaction hash; Etherscan opens the public transaction. The footer link
     *Smart contract* opens the contract page (Events tab = every anchored root).
3. pgAdmin: query 6 (`anchor_batches`) shows the same tx hash and block.

## 5. Buyer verifies, then tamper detection (2 min)

1. Section 00: enter IMEI `356938035643809` → **VERIFIED** banner + timeline.
2. Click **Verify stored record** → INTACT (report hash, leaf, Merkle path, on-chain root).
3. In pgAdmin run query 7 (roll back battery cycles 812 → 120). Click **Verify stored record** again →
   **TAMPERED · failed: leaf_digest, all_ok**. Query 8 (change the fault code) → `report_hash` fails.
   Query 9 restores the row → INTACT again.
   Point: even someone with full database access cannot quietly rewrite history, because the fingerprint is on the blockchain.

## 6. Honest limits (say them)

- Verification proves the record was **not changed after sealing**; it does not prove the repair was done well.
- The fault taxonomy for phones/appliances (`PH-BATT`, `AP-WATER`, …) is defined by this project; car codes are real OBD-II.
  The code itself is assigned deterministically (OBD-II/display code, else issue text + matched manual);
  the LLM writes the diagnosis, steps, parts, QA checks and buyer advice.
- Symptom wording for iFixit-based training examples is templated per component; procedures, parts and tools are real.
- Local Hardhat state is lost when the node stops; Sepolia is permanent and public.

## Switching to the public Sepolia testnet

1. Get free test ETH for `DEPLOYER_ADDRESS` in `.env` (Google Cloud Web3 faucet, Sepolia).
2. `bash scripts/deploy_sepolia.sh` → writes `artifacts/chain_config.sepolia.json`.
3. `bash scripts/start_demo.sh sepolia`. Transactions now show on https://sepolia.etherscan.io.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Top bar says `sim · in_memory` | Hardhat node not running → rerun `bash scripts/start_demo.sh` |
| `chain_anchor: FAIL` on old records | Local chain was restarted; `python scripts/init_db.py --reset` |
| `SQLite` in the top bar | PostgreSQL not running → `brew services start postgresql@15` |
| Port 8000 busy | `PORT=8010 bash scripts/start_demo.sh` |
