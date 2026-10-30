# Case study and algorithm text — 500-character chunks
Paste one chunk at a time into the humanizer. Leave the hexadecimal strings, the VIN, the batch identifier and the reference markers [46]-[48] exactly as written.

## Case study 1 — Odometer rollback (the NBC Nightly News example)

**A1 (483 chars)**

Odometer tampering is the clearest form of the information asymmetry this project addresses, and it is widening rather than closing. A segment broadcast by NBC Nightly News on 1 April 2023 reported rising odometer fraud at a time when a record number of American buyers had moved to the used market [46]. The figures published since have confirmed that trend rather than contradicted it, which makes the fraud a useful test of what a verifiable repair history can and cannot deliver.

**A2 (463 chars)**

CARFAX estimated in December 2025 that roughly 2.45 million vehicles on United States roads carry rolled-back odometers, a rise of fourteen per cent in one year after a four per cent rise the year before, costing the average affected buyer about 3,300 dollars [47]. The National Highway Traffic Safety Administration puts the number of vehicles sold each year with false odometer readings near 450,000, at a cost to buyers above one billion dollars annually [48].

**A3 (465 chars)**

The mechanism has also changed in a way that matters for system design. A mechanical odometer had to be dismantled to be altered, whereas a digital cluster can be rewritten with inexpensive tools sold openly, which is the explanation CARFAX itself offers for the increase [47]. Tampering is therefore cheap, quick, and leaves no mark on the instrument it falsifies, so detection has to come from records held outside the vehicle rather than from the vehicle itself.

**A4 (446 chars)**

The defences normally offered to a buyer are weaker than they appear. Inspecting pedal wear or commissioning a mechanic detects only gross inconsistency, and checking a history report for mileage discrepancies depends on records that are themselves unsigned, incomplete, and supplied voluntarily. The buyer is also asked to trust the operator of the database rather than to verify anything, which is precisely the dependency this project removes.

**A5 (450 chars)**

The prototype was exercised against this scenario. A repair event for a 2016 Honda Civic, recorded under the sample vehicle identification number 1HGBH41JXMN109186 at an odometer reading of 98,000 kilometres with fault code P0420, was sealed through the normal workshop path. The canonical repair report hashed to 44bd1f44aea8, the stored evidence received the content identifier d6faec167aef, and the resulting Proof-of-Repair leaf was 1ecf00f00b0c.

**A6 (454 chars)**

That leaf was batched with one further event, a Toyota Camry record with leaf ac512c77df8b, under batch identifier ui-1788331032592. The pair produced the Merkle root 46f5565e9a17, which was anchored on the local development chain in transaction 0x22785f1ddd0d and submitted to the public OpenTimestamps calendars under receipt 526ea1c4, whose Bitcoin attestation remained pending at the time of writing, as such receipts ordinarily do for several hours.

**A7 (437 chars)**

Re-running the verification path over the stored record reproduced the committed report hash, the leaf digest, the evidence content identifier and the Merkle inclusion proof, all four of which passed. The on-chain check was not repeated, because the local chain was not running when this report was prepared; the anchor record in the registry retains the transaction hash from the original submission, and no stronger claim is made here.

**A8 (415 chars)**

The rollback was then simulated on the sealed record. Reducing the committed odometer reading from 98,000 to 76,000 kilometres, and leaving every other field untouched, changed the leaf digest from 1ecf00f00b0c to 3ca71fb55475 and the recomputed root from 46f5565e9a17 to 263fc73abe0b. Sixty-three of the sixty-four hexadecimal characters of the root differed, so the mismatch requires no careful reading to notice.

**A9 (390 chars)**

The forged record also fails the proof it was issued with: replaying the stored membership proof against the altered leaf does not reproduce the anchored root. A far smaller edit behaves identically, as reducing the reading by a single kilometre to 97,999 yields the unrelated leaf 93e8cccc8ccf and root 9fc49570d5bd. The construction offers no tolerance band an attacker could work within.

**A10 (432 chars)**

What the case establishes should be stated narrowly. The buyer learns that the record presented is the record that was sealed, and that it was sealed before the root was published; the buyer does not learn that the diagnosis it contains was correct, nor that every repair the vehicle received was sealed at all. Completeness and diagnostic truth remain outside what a commitment can certify, and the prototype does not claim either.

## Case study 2 — Invoice substitution (short)

**B1 (431 chars)**

A second scenario tested substitution of the supporting evidence rather than the record. The invoice and diagnostic payload stored for the Civic event is held in the content-addressed evidence store under the identifier d6faec167aef and verified correctly as retrieved. Altering two bytes of that file, so that the odometer figure printed on the invoice read 76,000 rather than 98,000, moved its content identifier to 2c2f8a2364db.

**B2 (340 chars)**

Because the leaf commits to the identifier and not to a copy of the document, the substituted invoice no longer corresponds to anything that was anchored, and the mismatch is detected without the original file being available for comparison. A two-byte edit to a 1,966-byte document is therefore as visible as a wholesale replacement of it.

## Case study 3 — Record reuse across vehicles (short)

**C1 (319 chars)**

A third scenario tested reuse of a genuine record across vehicles, the practice of presenting work carried out on one car as evidence of work carried out on another. The Camry leaf ac512c77df8b was relabelled with the Civic's vehicle identification number and description, every other committed field being left intact.

**C2 (415 chars)**

The leaf digest moved to 63ab48af3bda and the recomputed root to cc9b95ac3b70, neither of which matches the anchored root, and the membership proof issued for the original leaf fails when replayed against the relabelled one. Because the vehicle identification number sits inside the hashed payload, a repair record is bound to one vehicle and cannot be transferred to a second without the transfer becoming evident.

## Working of the algorithm

**G1 (442 chars)**

The algorithm proceeds in four stages: canonical encoding, leaf construction, tree construction, and proof. Its purpose is narrow but strict, in that it must produce a value that changes whenever any committed detail changes, and that two parties computing it independently from the same record will always agree upon. Determinism is therefore a requirement rather than a convenience, and every stage is specified to remove avoidable freedom.

**G2 (416 chars)**

Encoding is handled first. The fields to be committed are serialised as JSON with the keys sorted and all optional whitespace removed, so that a record cannot be re-serialised into a different byte string with the same meaning. Two representations that differ only in field order or spacing would otherwise hash differently and break verification for an honest party, which would be indistinguishable from tampering.

**G3 (404 chars)**

The repair report is itself reduced to a digest before the leaf is formed, and the supporting evidence is reduced to a content identifier computed over the stored bytes. The leaf therefore commits to the diagnosis, the invoice and the photographs by reference. It remains small and free of personal data, while any edit to the underlying documents changes the digest or identifier that the leaf contains.

**G4 (439 chars)**

The leaf digest is then computed as the SHA-256 hash of the canonical payload prefixed with a single zero byte. Internal nodes are computed as the hash of a one byte prefixed to the concatenation of their two children. The two prefixes separate the domains, so that a leaf digest can never be presented as an internal node, nor an internal node as a leaf, which is the standard defence against second-preimage attacks on this construction.

**G5 (387 chars)**

Tree construction is iterative. The leaves are taken in the order they were sealed and hashed in pairs to form the level above; that level is paired in turn, and the process repeats until one value remains. Where a level holds an odd number of nodes, the final node is paired with itself, a rule the implementation applies consistently and which the verification path reproduces exactly.

**G6 (408 chars)**

The remaining value is the Merkle root, a fixed thirty-two bytes regardless of how many repairs the batch contains. It is the only value that leaves the system: it is written to the smart contract with its batch identifier and metadata reference, and the same root is submitted to the OpenTimestamps calendars. Publication fixes the batch in time, which is what later makes any divergence from it meaningful.

**G7 (421 chars)**

A membership proof is extracted by walking from a leaf to the root and recording the sibling of each node visited. The proof is the list of those siblings, and nothing else; no other record in the batch is disclosed. Its length grows with the logarithm of the batch size, so four repairs require two sibling digests, and a thousand repairs require ten, which is sixty-four and three hundred and twenty bytes respectively.

**G8 (408 chars)**

Verification inverts the construction without any privileged access. The verifier recomputes the report digest from the report it was given, recomputes the evidence identifier from the stored bytes, rebuilds the leaf from the canonical payload, and then folds the leaf with each sibling in turn, combining on the left or the right according to the parity of the index at that level, until a root is produced.

**G9 (438 chars)**

That root is compared with the one recorded on chain. Agreement establishes that the record is the record that was committed; disagreement localises the problem, since a single altered field changes its leaf, every internal node on the path above it, and therefore the root. The avalanche behaviour of the hash function means the altered root bears no resemblance to the anchored one, so the comparison is exact and requires no threshold.

## New references to append (next free numbers)

[46] NBC News, "Odometer fraud rises as record number of Americans seek used cars," NBC Nightly News, 1 Apr. 2023. [Online]. Available: https://www.nbcnews.com/nightly-news/video/odometer-fraud-rises-as-record-number-of-americans-seek-used-cars-167391301535

[47] CARFAX, "Odometer rollbacks see dramatic jump of 14% to 2.45 million vehicles," press release, 19 Dec. 2025.

[48] National Highway Traffic Safety Administration, "Odometer fraud," U.S. Department of Transportation. [Online]. Available: https://www.nhtsa.gov/equipment/odometer-fraud

## Full values (do not humanize — for the tables if you want them)

| Item | Value |
|---|---|
| VIN / vehicle / odometer | 1HGBH41JXMN109186 / 2016 Honda Civic / 98,000 km |
| Fault code | P0420 |
| Report hash | 44bd1f44aea82cdda8f211664a11292a016ab82755da81f313a77d51298b4524 |
| Evidence CID | d6faec167aef47511a1d572ae8f962b9e42cd8aa62283ab861da24097943bd1e |
| Leaf digest | 1ecf00f00b0c9856794338ab82074efe1a333a56b16d89674c1ef2fd44de16f4 |
| Second leaf (Camry) | ac512c77df8b6a8b8e5d76e4a8ee0ed5dc60335a7876051d5f448492096dfb83 |
| Batch id | ui-1788331032592 |
| Anchored root | 46f5565e9a172ecb7021b9f652ada16dadfe9de42c76b0b1bf921a6f79e78d9d |
| Chain tx (hardhat-local, chain id 31337) | 0x22785f1ddd0d4b7771ed7219bfafe50e6bbf667db6b1a08d1fa66ad7654b1910 |
| Contract | 0x5FbDB2315678afecb367f032d93F642f64180aa3 |
| OTS receipt (live, pending) | 526ea1c4-7d79-4ca3-a7e0-7a7733a555bb |
| Forged leaf (odometer 76,000) | 3ca71fb55475126df33af233a3e93c015b4ba4e02ddffa7561e818801422bba6 |
| Root after forgery | 263fc73abe0b57aaa23cfc3fe02af5ee68951a0d05d4336b12c76f5b5fc42165 |
| Forged leaf (odometer 97,999) | 93e8cccc8ccf634919e8f57690a28ec20fc12d76dfd85568948728e67043e9a0 |
| Root after 1 km change | 9fc49570d5bd3e33878c671a072019d2270a902815e05f6dd1ecd9b4fa401b2f |
| Evidence CID after 2-byte edit | 2c2f8a2364db9ef1d9ba772ba7db807d70d32dafa22d369e0b693e0f3aea454a |
| Relabelled leaf (VIN swap) | 63ab48af3bdad18c06e050cffe87446befac25054f653e4c49a1981b96122e5f |
| Root after VIN swap | cc9b95ac3b703fb077744042f05683bbd424e9891e93d2c7e1ae4f2aae8a743f |

Reproduce with: `python scripts/merkle_worked_example.py`
