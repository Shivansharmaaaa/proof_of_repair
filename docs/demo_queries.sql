-- Proof of Repair: queries for the pgAdmin Query Tool (database: proof_of_repair)

-- 1. Knowledge base: real repair procedures per device type and source
SELECT asset_type, source, COUNT(*) AS procedures
FROM repair_guides GROUP BY 1, 2 ORDER BY 1, 2;

-- 2. Fault taxonomy used by the LLM (component -> platform fault code)
SELECT asset_type, component, fault_code, COUNT(*) AS guides
FROM repair_guides WHERE source <> 'MechanicDB'
GROUP BY 1, 2, 3 ORDER BY 1, 4 DESC;

-- 3. Full-text search, the same index the API uses to ground a diagnosis
SELECT ref_id, device, title, url
FROM repair_guides
WHERE asset_type = 'phone' AND component = 'battery'
  AND search @@ to_tsquery('simple', 'iphone & 6')
LIMIT 10;

-- 4. Every sealed repair with its blockchain anchor (one row per record)
SELECT * FROM v_device_history;

-- 5. Devices and how many repairs each has
SELECT a.asset_type, a.identifier_kind, a.asset_id, a.device, COUNT(r.proof_id) AS repairs
FROM assets a LEFT JOIN repair_records r USING (asset_id)
GROUP BY 1, 2, 3, 4 ORDER BY repairs DESC;

-- 6. Anchor batches: Merkle root -> Ethereum transaction -> Bitcoin timestamp
SELECT batch_id, merkle_root, leaf_count, chain_network, chain_id, block_number,
       chain_tx, explorer_url, ots_status, anchored_at
FROM anchor_batches ORDER BY anchored_at DESC;

-- 7. TAMPER DEMO: an "insider" rolls back a phone's battery cycles.
--    Then click "Verify stored record" in the buyer lookup -> leaf_digest FAIL.
UPDATE repair_records SET usage_value = 120 WHERE asset_id = '356938035643809';

-- 8. ... or rewrites the diagnosis code -> report_hash FAIL.
UPDATE repair_records SET fault_code = 'PH-GEN' WHERE asset_id = '356938035643809';

-- 9. Put the record back from its sealed JSON copy -> verification passes again.
UPDATE repair_records
SET usage_value = (proof->>'usage_value')::int, fault_code = proof->'report'->>'fault_code'
WHERE asset_id = '356938035643809';
