(() => {
  const $ = (sel) => document.querySelector(sel);
  const form = $("#diagForm");
  const loader = $("#loader");
  const loaderText = $("#loaderText");
  const proofSection = $("#proof");
  const healthPill = $("#healthPill");
  const dbPill = $("#dbPill");
  const chainPill = $("#chainPill");
  const otsPill = $("#otsPill");
  const pendingCount = $("#pendingCount");
  const verifyGrid = $("#verifyGrid");
  const anchorPlate = $("#anchorPlate");
  const btnVerify = $("#btnVerify");
  const btnAnchor = $("#btnAnchor");
  const demoChips = $("#demoChips");
  const engineSelect = $("#engineSelect");
  const vinForm = $("#vinForm");
  const vinTimeline = $("#vinTimeline");
  const vinTrust = $("#vinTrust");
  const vinHint = $("#vinHint");
  const typeSwitch = $("#typeSwitch");

  const TYPES = {
    phone: { id: "IMEI (15 digits, dial *#06#)", idPh: "356938035643809", usage: "Battery cycles", code: "Error code (optional)", device: "Apple iPhone 6" },
    car: { id: "VIN", idPh: "1HGBH41JXMN109186", usage: "Odometer (km)", code: "OBD-II DTC code", device: "2016 Honda Civic" },
    appliance: { id: "Serial number", idPh: "KM110-CW4417", usage: "Usage cycles", code: "Display error code (e.g. OE, 5C, E24)", device: "Kenmore 110 Series Washing Machine" },
  };
  const UNIT = { km: "km", battery_cycles: "battery cycles", cycles: "cycles" };

  let lastProof = null;
  let pending = 0;
  let lastLookupVin = "";
  let demoCases = [];
  let assetType = "phone";
  let explorerAvailable = false;

  function setLoading(on, text) {
    loader.hidden = !on;
    if (text) loaderText.textContent = text;
  }

  function short(hex, n = 18) {
    if (!hex) return "—";
    return hex.length > n ? `${hex.slice(0, n)}…` : hex;
  }

  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function setType(type) {
    assetType = type;
    form.elements.asset_type.value = type;
    typeSwitch.querySelectorAll("button").forEach((b) => b.classList.toggle("active", b.dataset.type === type));
    const t = TYPES[type];
    $("#idLabel").textContent = t.id;
    $("#usageLabel").textContent = t.usage;
    $("#codeLabel").textContent = t.code;
    form.elements.asset_id.placeholder = t.idPh;
    form.elements.device.placeholder = t.device;
    const tiny = engineSelect.querySelector('option[value="tinyllama"]');
    tiny.disabled = type !== "car";
    if (type !== "car") engineSelect.value = "multidomain";
    renderChips();
  }

  typeSwitch.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-type]");
    if (b) setType(b.dataset.type);
  });

  function fillForm(c) {
    if (c.asset_type !== assetType) setType(c.asset_type);
    const f = form.elements;
    f.asset_id.value = c.asset_id || "";
    f.device.value = c.device || "";
    f.usage_value.value = c.usage_value ?? 0;
    f.error_code.value = c.error_code || "";
    f.issue.value = c.issue || "";
    f.notes.value = c.notes || "";
  }

  function renderChips() {
    demoChips.innerHTML = "";
    demoCases
      .filter((c) => c.asset_type === assetType)
      .forEach((c) => {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "chip";
        b.textContent = c.label;
        b.addEventListener("click", () => {
          fillForm(c);
          vinForm.elements.vin.value = c.asset_id || "";
        });
        demoChips.appendChild(b);
      });
  }

  async function refreshHealth() {
    try {
      const res = await fetch("/api/health");
      const data = await res.json();
      const engines = data.engines || {};
      healthPill.textContent = `api ok · mistral ${engines.multidomain_adapter ? "lora" : "base"} · tinyllama ${engines.tinyllama ? "ready" : "missing"}`;
      healthPill.classList.add("ok");
      const st = data.storage || {};
      dbPill.textContent = st.backend === "postgresql" ? `PostgreSQL · ${st.proofs} records · ${st.guides} guides` : `SQLite · ${st.proofs} records`;
      dbPill.classList.toggle("live", st.backend === "postgresql");
      pending = data.pending_leaves || 0;
      pendingCount.textContent = `${pending} pending`;
      const chain = data.chain || {};
      if (chain.mode === "live_evm") {
        const net = chain.network === "sepolia" ? "Ethereum Sepolia" : chain.network;
        chainPill.textContent = `LIVE · ${net} · id ${chain.chain_id} · block ${chain.block_number}`;
        chainPill.classList.add("live");
        chainPill.title = `RPC ${chain.rpc_url} | contract ${chain.contract_address}`;
        const link = $("#contractLink");
        explorerAvailable = Boolean(chain.explorer_address);
        if (chain.explorer_address) {
          link.href = chain.explorer_address;
          link.hidden = false;
        }
      } else {
        chainPill.textContent = `sim · ${chain.mode || "in_memory"}`;
        chainPill.classList.remove("live");
      }
      const ots = data.ots || {};
      if (ots.mode === "live_ots") {
        otsPill.textContent = "OTS live · Bitcoin";
        otsPill.classList.add("live");
        otsPill.title = (ots.calendars || []).join("\n") || ots.note || "";
      } else {
        otsPill.textContent = `OTS · ${ots.mode || "sim"}`;
        otsPill.classList.remove("live");
        otsPill.title = ots.note || "";
      }
    } catch (e) {
      healthPill.textContent = "api offline";
      healthPill.classList.remove("ok");
      dbPill.textContent = "db offline";
      chainPill.textContent = "chain offline";
      otsPill.textContent = "ots offline";
    }
  }

  async function loadKbCounts() {
    try {
      const res = await fetch("/api/kb_stats");
      if (!res.ok) return;
      const data = await res.json();
      $("#kbPhone").textContent = (data.phone ?? 0).toLocaleString();
      $("#kbCar").textContent = (data.car ?? 0).toLocaleString();
      $("#kbAppliance").textContent = (data.appliance ?? 0).toLocaleString();
    } catch (_) {
      /* optional */
    }
  }

  function formatWhen(ts) {
    if (!ts) return "—";
    try {
      return new Date(Number(ts) * 1000).toLocaleString();
    } catch (_) {
      return String(ts);
    }
  }

  function trustLabel(summary, count, anchored) {
    if (summary === "verified_timeline") return `VERIFIED · ${count} repair(s) anchored on Ethereum + OpenTimestamps`;
    if (summary === "partial") return `PARTIAL · ${anchored}/${count} anchored — remaining records not batched yet`;
    if (summary === "sealed_only") return `SEALED · ${count} repair(s) not yet anchored`;
    return "NO ATTESTATIONS · no workshop has sealed this device here";
  }

  async function lookupVin(vin, { scroll } = { scroll: true }) {
    const v = (vin || "").trim().toUpperCase();
    if (v.length < 4) {
      vinHint.textContent = "Enter a full IMEI, VIN or serial number.";
      return;
    }
    lastLookupVin = v;
    setLoading(true, "Looking up repair history…");
    try {
      const res = await fetch(`/api/asset/${encodeURIComponent(v)}`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || res.statusText);
      }
      const data = await res.json();
      const kind = data.identifier_kind ? `${data.identifier_kind} ` : "";
      vinHint.textContent = `${kind}${data.asset_id}${data.device ? " · " + data.device : ""} · ${data.count} sealed repair(s)`;
      vinTrust.hidden = false;
      vinTrust.className = `trust-banner ${data.trust_summary || "empty"}`;
      if (data.trust_summary === "verified_timeline") vinTrust.classList.add("verified");
      vinTrust.textContent = trustLabel(data.trust_summary, data.count, data.anchored_count);

      vinTimeline.hidden = false;
      vinTimeline.innerHTML = "";
      (data.timeline || []).forEach((ev, i) => {
        const item = document.createElement("article");
        item.className = `tl-item${ev.anchored ? " anchored" : ""}`;
        item.style.animationDelay = `${i * 0.06}s`;
        const parts = (ev.parts || []).map((p) => `<li>${esc(p)}</li>`).join("");
        const badge = ev.anchored ? `<span class="tl-badge on">anchored</span>` : `<span class="tl-badge">sealed</span>`;
        const a = ev.anchor || {};
        const tx = a.chain_tx
          ? a.explorer_url
            ? ` · tx <a href="${esc(a.explorer_url)}" target="_blank" rel="noreferrer">${esc(short(a.chain_tx, 14))}</a>`
            : ` · tx ${esc(short(a.chain_tx, 14))}`
          : "";
        item.innerHTML = `
          <div class="tl-head">
            <span class="tl-code">${esc(ev.fault_code || "—")}</span>
            ${badge}
            <span class="tl-meta">${esc(ev.asset_type)} · ${formatWhen(ev.when)} · ${esc(ev.usage_value ?? "—")} ${esc(UNIT[ev.usage_unit] || ev.usage_unit || "")} · ${esc(ev.issuer_id || "workshop")}</span>
          </div>
          <p class="tl-body">${esc(ev.diagnosis || "")}</p>
          ${parts ? `<ul class="tl-parts">${parts}</ul>` : ""}
          <p class="tl-meta" style="margin-top:0.45rem">leaf ${esc(short(ev.leaf_digest, 20))}${a.merkle_root ? ` · root ${esc(short(a.merkle_root, 16))}` : ""}${tx}${ev.reference_guide ? ` · grounded on ${esc(ev.reference_guide)}` : ""}</p>
          <div class="tl-verify">
            <button type="button" class="chip" data-proof="${esc(ev.proof_id)}">Verify stored record</button>
            <span class="tl-result"></span>
          </div>
        `;
        item.querySelector("button[data-proof]").addEventListener("click", (e) => verifyStored(ev.proof_id, item.querySelector(".tl-result")));
        vinTimeline.appendChild(item);
      });
      if (!(data.timeline || []).length) {
        vinTimeline.innerHTML = `<p class="hint">No sealed repairs for this device in the registry.</p>`;
      }
      if (scroll) document.getElementById("lookup").scrollIntoView({ behavior: "smooth" });
    } catch (err) {
      alert(`Lookup failed: ${err.message || err}`);
    } finally {
      setLoading(false);
    }
  }

  async function verifyStored(proofId, out) {
    out.textContent = "verifying…";
    out.className = "tl-result";
    try {
      const res = await fetch(`/api/proofs/${encodeURIComponent(proofId)}/verify`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || res.statusText);
      const failed = Object.entries(data).filter(([, v]) => v === false).map(([k]) => k);
      out.textContent = data.all_ok
        ? "INTACT · report hash, leaf, Merkle path and on-chain root all match"
        : `TAMPERED / NOT PROVEN · failed: ${failed.join(", ")}`;
      out.classList.add(data.all_ok ? "ok" : "bad");
    } catch (err) {
      out.textContent = `verify failed: ${err.message || err}`;
      out.classList.add("bad");
    }
  }

  vinForm.addEventListener("submit", (e) => {
    e.preventDefault();
    lookupVin(new FormData(vinForm).get("vin").toString());
  });

  async function loadDemoCases() {
    try {
      const res = await fetch("/api/demo_cases");
      demoCases = await res.json();
      renderChips();
    } catch (_) {
      /* ignore */
    }
  }

  function fillList(sel, items) {
    const el = $(sel);
    el.innerHTML = "";
    (items || []).forEach((s) => {
      const li = document.createElement("li");
      li.textContent = s;
      el.appendChild(li);
    });
  }

  function renderReport(payload) {
    const report = payload.report || {};
    const proof = payload.proof || {};
    const model = proof.model || {};

    proofSection.hidden = false;
    $("#assetType").textContent = proof.asset_type || "—";
    $("#faultCode").textContent = report.fault_code || "—";
    $("#severity").textContent = `severity · ${report.severity || "—"} · ~${report.estimated_minutes || "?"} min`;
    $("#diagnosis").textContent = report.diagnosis || "";
    $("#buyerAdvice").textContent = report.buyer_advice || "";
    const unit = UNIT[proof.usage_unit] || proof.usage_unit || "";
    $("#reportMeta").textContent = `${proof.device || ""} · ${proof.asset_id || ""} · ${proof.usage_value ?? ""} ${unit} · engine ${payload.engine || ""} (${model.model_version || ""}) · ${payload.seconds ?? "?"} s`;
    fillList("#repairSteps", report.repair_steps);
    fillList("#parts", report.parts);
    fillList("#qaChecks", report.qa_checks);

    const ref = payload.reference;
    $("#refCard").hidden = !ref;
    if (ref) {
      $("#refLink").textContent = `${ref.title} — ${ref.source}`;
      if (ref.url) $("#refLink").href = ref.url;
      else $("#refLink").removeAttribute("href");
      $("#refId").textContent = ref.ref_id;
    }

    $("#leafDigest").textContent = proof.leaf_digest || "—";
    $("#reportHash").textContent = proof.report_hash || "—";
    $("#evidenceCid").textContent = proof.evidence_cid || "—";
    $("#adapterHash").textContent = model.adapter_hash ? short(model.adapter_hash, 24) : "base model (no adapter)";
    $("#storedIn").textContent = `repair_records · proof_id ${proof.proof_id}`;

    lastProof = proof;
    pending = payload.pending_batch_size ?? pending + 1;
    pendingCount.textContent = `${pending} pending`;
    btnVerify.disabled = !lastProof;
    verifyGrid.hidden = true;
    proofSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    const body = {
      asset_type: fd.get("asset_type").toString(),
      asset_id: fd.get("asset_id").toString().trim(),
      device: fd.get("device").toString().trim(),
      usage_value: Number(fd.get("usage_value")),
      error_code: fd.get("error_code").toString().trim(),
      issue: fd.get("issue").toString().trim(),
      notes: fd.get("notes").toString().trim(),
      engine: fd.get("engine").toString(),
    };

    setLoading(true, body.engine === "multidomain" ? "Retrieving repair manual · Mistral-7B diagnosing…" : "TinyLlama diagnosing…");
    try {
      const res = await fetch("/api/diagnose_and_prove", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const detail = Array.isArray(err.detail) ? err.detail.map((d) => d.msg).join("; ") : err.detail;
        throw new Error(detail || res.statusText);
      }
      const data = await res.json();
      renderReport(data);
      $("#formHint").textContent = "Sealed and stored in PostgreSQL. Anchor the batch so a buyer can verify it.";
      vinForm.elements.vin.value = body.asset_id;
      lookupVin(body.asset_id, { scroll: false });
      refreshHealth();
    } catch (err) {
      alert(`Diagnosis failed: ${err.message || err}`);
    } finally {
      setLoading(false);
    }
  });

  btnAnchor.addEventListener("click", async () => {
    // Public chain: open the explorer tab inside the click (so it is not blocked as a pop-up),
    // then point it at the transaction once it is mined.
    const explorerTab = explorerAvailable ? window.open("", "_blank") : null;
    if (explorerTab) {
      explorerTab.document.title = "Waiting for Ethereum…";
      explorerTab.document.body.innerHTML =
        '<p style="font:16px system-ui;margin:3rem">Sending the Merkle root to Ethereum Sepolia… ' +
        "this tab opens the transaction on Etherscan as soon as it is in a block (~15 s).</p>";
    }
    setLoading(true, "Building Merkle tree · sending Ethereum transaction · OpenTimestamps…");
    try {
      const res = await fetch("/api/anchor_batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ batch_id: `ui-${Date.now()}` }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || res.statusText);
      }
      const data = await res.json();
      anchorPlate.hidden = false;
      $("#merkleRoot").textContent = `${data.merkle_root || "—"}  (${(data.leaf_order || []).length} records)`;
      const ots = data.ots_receipt || {};
      if (ots.mode === "live_ots") {
        const cal = (ots.pending_calendars && ots.pending_calendars[0]) || ots.calendar_url || "";
        $("#otsId").textContent = `${ots.receipt_id} · ${ots.status}${cal ? " · " + cal.replace(/^https?:\/\//, "") : ""}`;
      } else {
        $("#otsId").textContent = ots.receipt_id ? `${ots.receipt_id} · simulated` : "—";
      }
      const files = data.ots_files;
      $("#otsFiles").textContent = files
        ? `${files.bin.split("/").pop()}  +  ${files.ots.split("/").pop()}`
        : "not generated (timestamp simulator or receipt missing)";
      const tx = data.chain_tx || {};
      const txHash = tx.tx_hash || "—";
      if (tx.explorer_url) {
        $("#chainTx").innerHTML = `<a href="${esc(tx.explorer_url)}" target="_blank" rel="noreferrer">${esc(txHash)}</a>`;
        if (explorerTab) explorerTab.location.href = tx.explorer_url;
      } else {
        $("#chainTx").textContent = txHash;
        if (explorerTab) explorerTab.close();
      }
      $("#chainBlock").textContent = tx.mode === "live_evm"
        ? `${tx.network === "sepolia" ? "Ethereum Sepolia testnet" : tx.network} · chainId ${tx.chain_id} · block ${tx.block_number} · contract ${tx.contract_address}`
        : "in-memory simulator";
      pending = 0;
      pendingCount.textContent = "0 pending";
      btnVerify.disabled = !lastProof;
      refreshHealth();
      if (lastLookupVin || lastProof?.asset_id) lookupVin(lastLookupVin || lastProof.asset_id, { scroll: false });
    } catch (err) {
      if (explorerTab) explorerTab.close();
      alert(`Anchor failed: ${err.message || err}`);
    } finally {
      setLoading(false);
    }
  });

  btnVerify.addEventListener("click", async () => {
    if (!lastProof) return;
    setLoading(true, "Re-hashing record · checking Merkle path · querying smart contract…");
    try {
      const res = await fetch("/api/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ proof: lastProof }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || res.statusText);
      }
      const data = await res.json();
      verifyGrid.hidden = false;
      verifyGrid.innerHTML = "";
      Object.entries(data).forEach(([k, v]) => {
        if (typeof v !== "boolean") return;
        const el = document.createElement("div");
        el.className = `v-item ${v ? "ok" : "bad"}`;
        el.textContent = `${k}: ${v ? "PASS" : "FAIL"}`;
        verifyGrid.appendChild(el);
      });
    } catch (err) {
      alert(`Verify failed: ${err.message || err}`);
    } finally {
      setLoading(false);
    }
  });

  setType("phone");
  refreshHealth();
  loadDemoCases();
  loadKbCounts();
  setInterval(refreshHealth, 60000);
})();
