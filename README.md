# Cloud Based Proof of Repair Platform for Phones, Cars, and Appliances
### using Blockchain Anchoring and Large Language Models

A workshop records a repair on a phone (IMEI), car (VIN) or home appliance (serial number).
A fine-tuned LLM writes a structured repair report grounded on a real repair manual; the record is
hashed, stored in **PostgreSQL**, batched into a Merkle tree and anchored on **Ethereum** (smart contract)
and **Bitcoin** (OpenTimestamps). A second-hand buyer looks up the device and verifies the history.

Demo walkthrough: **[DEMO.md](DEMO.md)** · one command: `bash scripts/start_demo.sh`

---

## Architecture

```
Technician (web UI) ──► FastAPI ──► PostgreSQL full-text search over 4,666 repair procedures
                                     │   (iFixit/MyFixit phones · appliances · cars, MechanicDB OBD-II)
                                     ▼
                         Mistral-7B-Instruct 4-bit + multi-domain LoRA (MLX)  ──► RepairReport JSON
                                     │
                                     ▼
            evidence (content-addressed) + leaf digest  ──► repair_records (PostgreSQL)
                                     │
                     Merkle batch ───┴──► ProofOfRepair.sol (Ethereum: Hardhat local / Sepolia)
                                     └──► OpenTimestamps calendars (Bitcoin)
Buyer ──► lookup by IMEI / VIN / serial ──► re-hash record + Merkle path + on-chain root check
```

| Layer | Software |
|---|---|
| Database | PostgreSQL 15 (`DATABASE_URL`; any managed Postgres works: Supabase, Neon, RDS, Cloud SQL), SQLite fallback |
| Blockchain | Solidity 0.8.20 contract, Hardhat node (chainId 31337) or Ethereum Sepolia (11155111) via web3.py |
| Timestamp | OpenTimestamps public calendars → Bitcoin |
| LLM | Mistral-7B-Instruct-v0.2 (4-bit, MLX) + LoRA; TinyLlama-1.1B + LoRA for cars (fast path) |
| API / UI | FastAPI + static HTML/JS |

---

## Datasets (`data/raw/`)

| Dataset | Path | Used for |
|---|---|---|
| **MyFixit** (iFixit manuals; Nabizadeh et al., LREC 2020; CC BY-NC-SA 3.0) | `data/raw/MyFixit/` | 3,682 phone, 609 appliance, 286 car/truck repair procedures (steps, tools, parts) |
| **MechanicDB OBD-II sample** | `data/raw/MechanicDB/` | 89 DTC codes → ranked fixes → parts |
| **NHTSA ODI complaints** | `data/raw/NHTSA/` | real owner complaints (car training prompts) |
| automotive-dtc-finetune (HF `RRK1987`) | `data/raw/DTC_FT/` | vehicle-only TinyLlama adapter |
| NASA CMAPSS, UCI AI4I 2020 | `data/raw/CMAPSS/`, `data/raw/AI4I/` | degradation / failure-mode language (vehicle adapter) |

`bash scripts/download_datasets.sh` re-fetches MyFixit. `python scripts/prepare_multidomain.py` builds
`data/processed/repair_kb.jsonl` (knowledge base) and `data/mlx_multidomain/` (train 1,625 / valid 70 / test 70,
split by source guide). Counts and the training-set Merkle root: `artifacts/dataset_manifest_multidomain.json`.

### Fault taxonomy

Cars use real OBD-II codes (`P0420`) when present. Phones and appliances use a component taxonomy defined
in `src/kb/catalog.py`, e.g. `PH-BATT`, `PH-DISP`, `PH-CHRG`, `AP-WATER`, `AP-HEAT`, `AP-CTRL`, `CR-BRAKE`.
Common washer/dishwasher display codes (LG `OE`, Samsung `5C`, Bosch `E24`, …) map onto the taxonomy.

---

## Fine-tuning

| Adapter | Base | Data | Path |
|---|---|---|---|
| **multi-domain** (phones · cars · appliances) | Mistral-7B-Instruct 4-bit (MLX) | MyFixit + MechanicDB + NHTSA, prompt-masked | `artifacts/adapters/multidomain-mlx-lora/` |
| vehicle DTC | TinyLlama-1.1B-Chat | MechanicDB + DTC_FT + NHTSA | `artifacts/adapters/vehicle-lora-dtc/` |
| vehicle (Mistral) | Mistral-7B-Instruct 4-bit | same as above | `artifacts/adapters/mistral-mlx-lora/` |

```bash
bash scripts/train_multidomain_mlx.sh        # ~35 min on an M3 Pro
```

Every prompt contains one retrieved reference procedure; the same prompt builder (`src/llm/multidomain.py`)
is used for training and inference. If a model field is empty or degenerate, it falls back to the grounded
reference report, so every sealed report traces to a real procedure (`extra.reference_guide`). The fault
code is assigned deterministically (OBD-II/display code, else issue text + matched manual component); the
LLM writes diagnosis, steps, parts, QA checks and buyer advice. Raw-model metrics on the held-out split:
`python scripts/eval_multidomain.py` → `artifacts/eval_metrics_multidomain.json`.

---

## Run

```bash
source .venv/bin/activate
bash scripts/start_demo.sh              # PostgreSQL + local Ethereum (Hardhat) + OTS + UI on :8000
bash scripts/start_demo.sh sepolia      # public Sepolia testnet (fund DEPLOYER_ADDRESS in .env first)
python -m pytest tests/ -q              # crypto, registry, multi-domain tests
```

## Proof object

Each leaf commits `asset_type + asset_id (IMEI/VIN/serial) + device + usage (battery cycles / km / cycles)
+ report_hash + evidence_cid + model provenance + issuer + timestamp`. Records sealed before the
multi-domain change (`vin/vehicle/odometer_km`) still verify (`schema_version = 1`).

Raw evidence stays off-chain (content-addressed). Only Merkle roots go on-chain (`contracts/ProofOfRepair.sol`).
Per-record Merkle paths are stored in `record_anchors`, so verification works after a restart, and
`GET /api/proofs/{id}/verify` re-checks the row exactly as it is stored, so any edit to the table is detected.
