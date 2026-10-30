"""Publish the ProofOfRepair source on Etherscan (Sepolia) so transactions show decoded method names.

Needs ETHERSCAN_API_KEY in .env (free: etherscan.io -> sign in -> API Keys -> Add).
Run: python scripts/verify_etherscan.py
"""

from __future__ import annotations

import glob
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.blockchain.evm_ledger import _env_value  # noqa: E402

API = "https://api.etherscan.io/v2/api?chainid={chain_id}"
CONTRACT_NAME = "contracts/ProofOfRepair.sol:ProofOfRepair"


def call(chain_id: int, params: dict, post: bool = False) -> dict:
    url = API.format(chain_id=chain_id)
    data = urllib.parse.urlencode(params).encode()
    if post:
        req = urllib.request.Request(url, data=data, method="POST")
    else:
        req = urllib.request.Request(url + "&" + data.decode())
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def main() -> None:
    key = _env_value("ETHERSCAN_API_KEY")
    if not key:
        sys.exit("Add ETHERSCAN_API_KEY=... to .env first (etherscan.io -> API Keys).")
    cfg = json.loads((ROOT / "artifacts/chain_config.sepolia.json").read_text())
    build = json.loads(Path(sorted(glob.glob(str(ROOT / "chain/artifacts/build-info/*.json")))[-1]).read_text())
    chain_id, address = int(cfg["chain_id"]), cfg["contract_address"]

    submit = call(chain_id, {
        "module": "contract",
        "action": "verifysourcecode",
        "apikey": key,
        "contractaddress": address,
        "sourceCode": json.dumps(build["input"]),
        "codeformat": "solidity-standard-json-input",
        "contractname": CONTRACT_NAME,
        "compilerversion": "v" + build["solcLongVersion"],
        "constructorArguements": "",
    }, post=True)
    print("submit:", submit.get("message"), "|", submit.get("result"))
    if str(submit.get("status")) != "1":
        if "already verified" in str(submit.get("result", "")).lower():
            print(f"Already verified: {cfg['explorer_address_prefix']}{address}#code")
            return
        sys.exit(1)

    guid = submit["result"]
    for _ in range(20):
        time.sleep(5)
        status = call(chain_id, {"module": "contract", "action": "checkverifystatus", "guid": guid, "apikey": key})
        print("status:", status.get("result"))
        result = str(status.get("result", ""))
        if "Pass" in result or "Already Verified" in result:
            print(f"Verified: {cfg['explorer_address_prefix']}{address}#code")
            return
        if "Fail" in result:
            sys.exit(1)
    sys.exit("Timed out waiting for Etherscan; run again in a minute.")


if __name__ == "__main__":
    main()
