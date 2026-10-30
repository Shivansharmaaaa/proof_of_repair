# Drafts awaiting humanizing
Neither has been put into the document.

**Keep exact:** 57, 93.0%, 98.3%, one-kilometre, two-byte, SHA-256, thirty-two bytes.


## A1 — Abstract  (replaces the current 296-word abstract; IEEE venues usually cap at 250)
*223 words*

A used vehicle's repair history exists mainly as paper invoices, workshop stamps and unsigned PDFs, which can be edited, back-dated or withheld. A buyer therefore has no way to check that a declared repair happened, at the odometer reading claimed, with the paperwork unaltered. This paper presents Proof of Repair, a prototype that produces a repair history tied to one vehicle identification number that a stranger can verify. Diagnostic context captured in the workshop is interpreted by a language model adapted with low-rank adaptation, which emits a structured diagnosis together with an ordered repair procedure. Each sealed repair becomes a canonical leaf committing the identification number, the odometer reading, a report digest, an evidence identifier and the model provenance, while the evidence itself stays off-chain under content identifiers. The leaves are gathered into a Merkle tree, and its root is anchored on an EVM-compatible contract and timestamped independently. On a hold-out of 57 real OBD cases the adapted models identified the correct fault code in 93.0% and 98.3% of cases, and lost that accuracy entirely on free-text owner complaints they had not been adapted for. Every alteration attempted against sealed records was detected, including a one-kilometre odometer change and a two-byte invoice edit. The construction establishes that a record is the one that was sealed, not that the diagnosis it contains is correct.


## A2 — 4. Attestation Algorithm  (replaces the current 942-word section; saves about half a page)
*387 words*

The attestation layer rests on one algorithm with four stages: canonical encoding, leaf construction, tree construction and proof. Determinism is a requirement rather than a convenience, since two parties computing a digest independently from the same record must arrive at the same value.

Encoding comes first. The committed fields are serialised as JSON with sorted keys and no optional whitespace, so that a record cannot be re-serialised into a different byte string carrying the same meaning. Without that rule an honest verifier recomputing a digest from a faithfully stored record would obtain a mismatch indistinguishable from tampering. The repair report is then replaced by its digest and the evidence by a content identifier computed over the stored bytes, so the leaf commits to both by reference and stays small enough to batch cheaply.

The leaf is the SHA-256 digest of the canonical payload prefixed with a zero byte, while internal nodes prefix a one byte to the concatenation of their two children. The two prefixes separate the domains of the construction, so that a leaf digest can never be presented as an internal node, which is the standard defence against second-preimage attacks on Merkle trees.

Leaves are hashed in pairs, level by level, until a single value remains. Where a level holds an odd number of nodes the last is paired with itself, a rule the verification path reproduces exactly, since a verifier handling the odd case differently would derive a different root from identical data. The remaining value is the Merkle root, thirty-two bytes whatever the batch size, and the only value that leaves the system.

A membership proof is the list of siblings along the path from a leaf to the root, and nothing else, so one repair can be shown to a buyer without revealing the others. Its length grows logarithmically: four repairs need two siblings, a thousand need ten. Verification recomputes the report digest and the evidence identifier, rebuilds the leaf, folds it with each sibling according to the parity of the index at that level, and compares the result against the anchored root. Agreement establishes that the record is the one committed, and that it was committed no later than the anchoring transaction. Disagreement localises the failure, since one altered field changes its leaf, every node above it, and therefore the root.
