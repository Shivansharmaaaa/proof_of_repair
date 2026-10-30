const fs = require("fs");
const path = require("path");

async function main() {
  const [deployer] = await ethers.getSigners();
  const network = await ethers.provider.getNetwork();
  console.log("Deployer:", deployer.address);
  console.log("chainId=", network.chainId.toString());

  const Factory = await ethers.getContractFactory("ProofOfRepair");
  const contract = await Factory.deploy();
  await contract.waitForDeployment();
  const address = await contract.getAddress();
  console.log("ProofOfRepair deployed:", address);

  const artifact = await artifacts.readArtifact("ProofOfRepair");
  const chainId = Number(network.chainId);
  const isSepolia = chainId === 11155111;
  const cfg = {
    network: isSepolia ? "sepolia" : "hardhat-local",
    chain_id: chainId,
    rpc_url: isSepolia ? process.env.SEPOLIA_RPC_URL : "http://127.0.0.1:8545",
    contract_address: address,
    deployer: deployer.address,
    // Public networks: the key stays in .env (read by the API), never in this file.
    // Local: Hardhat node Account #0 (printed at node startup; local only).
    private_key: isSepolia ? null : "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    deploy_tx: contract.deploymentTransaction()?.hash || null,
    explorer_tx_prefix: isSepolia ? "https://sepolia.etherscan.io/tx/" : null,
    explorer_address_prefix: isSepolia ? "https://sepolia.etherscan.io/address/" : null,
    abi: artifact.abi,
    deployed_at: new Date().toISOString(),
  };

  const outDir = path.join(__dirname, "..", "..", "artifacts");
  fs.mkdirSync(outDir, { recursive: true });
  for (const name of ["chain_config.json", `chain_config.${cfg.network}.json`]) {
    const outPath = path.join(outDir, name);
    fs.writeFileSync(outPath, JSON.stringify(cfg, null, 2));
    console.log("Wrote", outPath);
  }
  if (cfg.explorer_address_prefix) console.log("Explorer:", cfg.explorer_address_prefix + address);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
