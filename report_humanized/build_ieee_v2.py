#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild Proof_of_Repair_IEEE_v2.docx from the pristine original.

Removes the sequence-diagram subsection and inserts three new pieces of content:
  4.2.3  Attestation Algorithm        (blocks F, G)
  4.4.1  Worked Merkle Example        (blocks A, B + Table 11, Figure 7, Table 12)
  4.4.2  Case Study: Odometer Rollback (blocks C, D, E)
plus references [46]-[48].

All prose is the humanized text supplied by the author; corrections applied to it
are listed in CORRECTIONS below. The source file is never modified: the script
always rebuilds the output from scratch, so re-running it is safe.
"""
from __future__ import annotations

import zipfile
from xml.etree import ElementTree as ET

SRC = "/Users/shivansh/Downloads/Proof_of_Repair_IEEE.docx"
DST = "/Users/shivansh/Desktop/proof of repair/report_humanized/Proof_of_Repair_IEEE_v2.docx"

CORRECTIONS = [
    "R3: 'line of business' -> 'line of work'; 'guaranty' -> 'guarantee'",
    "R3: first-person 'systems we examined' -> 'reviewed systems'",
    "R3: detection sentence restored (it is the alteration that is detected)",
    "R4: second-person 'if you clone a new checkout' -> 'on a fresh checkout'",
    "R4: stray spaces before full stops; 'doesn\u2019t' -> 'does not'",
    "R2: \"Two index mappings...\" was a sentence fragment - verb restored",
    "R2: 'permission free' -> 'permissionless'; 'guaranty' -> 'guarantee'",
    "R2: identity-layer sentence was garbled ('read into the recorded address an identity layer')",
    "R2: deployment sentences reordered; first-person 'We have also done' removed",
    "R1: 'a record of nine fields' -> 'a report of nine fields' (the report has nine fields)",
    "R1: 'disallows ... from being' -> 'prevents ...'; 'can\u2019t' -> 'cannot' (register)",
    "A: restored file paths artifacts/por_registry.sqlite3 and scripts/merkle_worked_example.py",
    "B: 'Two conditions are met' -> 'Two qualifications apply' (meaning was inverted)",
    "B: Table 11 caption restored to describe leaves; 'trajectory' -> 'path'",
    "C: restored '2.45 million' and 'U.S. roads' (digits/initials had been split)",
    "D: 'it corrects every one of those fields' -> 'it commits ...' ('fixes' was misread)",
    "D: restored 'sample' before the VIN",
    "E: diagnosis sentence rewritten - humanized text implied the diagnosis was correct",
    "E: 'kilometer' normalised to 'kilometres'",
]

# --------------------------------------------------------------------------- text

ALGO = [
    "The attestation layer is built upon a single algorithm executed across four distinct stages: "
    "canonical encoding, leaf construction, tree construction, and proof generation. Its purpose is "
    "specific yet rigorous. It must generate a value that updates whenever any committed detail "
    "changes, ensuring that two parties computing it independently from the same record will always "
    "arrive at the same result. Consequently, determinism is a necessity rather than a mere "
    "convenience, with each stage meticulously defined to eliminate unnecessary freedom.",

    "The encoding process is performed first. The fields to be committed are serialized as JSON with "
    "sorted keys and all optional whitespace removed, ensuring that a record cannot be re-serialized "
    "into a different byte string that carries the same meaning. In the absence of this rule, two "
    "representations that differ only in field order or spacing would produce different hash values, "
    "causing an honest verifier who recomputes the digest from a faithfully stored record to obtain a "
    "mismatch that is indistinguishable from tampering. Canonicalization ensures that the encoding "
    "depends solely on the content.",

    "Before the leaf is formed, the two bulky components of the repair are reduced. The repair report "
    "is substituted with its digest, calculated using the same canonical encoding, while the "
    "supporting evidence—which may comprise invoices, photographs, and diagnostic exports—is "
    "replaced by a content identifier derived from the stored bytes [25]. Consequently, the leaf is "
    "committed to both the diagnosis and to each evidence item by reference. It stays small enough "
    "for cost-effective batching and holds no personal data, ensuring that any modification to the "
    "underlying document alters the digest or the identifier that the leaf carries, thereby changing "
    "the leaf itself.",

    "The leaf itself consists of the SHA-256 digest of the canonical payload, prefixed with a single "
    "zero byte [31]. The payload incorporates the fields previously outlined in this chapter, "
    "including the vehicle identification number, vehicle description, odometer reading, event type, "
    "issuing workshop, sealing timestamp, report digest, evidence identifier, and model provenance. "
    "Binding the records into a single digest ensures that a record cannot be decomposed and "
    "recombined, as a legitimate report would require a different leaf if moved to a different "
    "vehicle identification number or odometer reading.",

    "Internal nodes are computed differently, using the hash of a single byte prefixed to the "
    "concatenation of the two child digests. The two prefixes delineate the domains of the "
    "construction, ensuring that a leaf digest can never be represented as an internal node, and vice "
    "versa. This is the standard defense against second-preimage attacks on Merkle trees, where an "
    "attacker capable of blurring the line between a leaf and an internal node might present a "
    "different set of records that still produce the same root. The defense incurs a cost of one byte "
    "per hash, but the advantage is that the tree’s structure is committed alongside its contents.",

    "Tree construction is an iterative process that functions exclusively on digests. The leaves are "
    "processed in the order they were sealed and hashed in pairs to create the next level; this "
    "process repeats with each subsequent level until only a single value remains. When a level "
    "contains an odd number of nodes, the last node is paired with itself—a rule consistently "
    "applied by the implementation and precisely mirrored by the verification path, because a "
    "verifier handling the odd case differently would derive a different root from the same data.",

    "The remaining value is the Merkle root, which remains a fixed 32 bytes whether the batch "
    "contains four repairs or four thousand. It is the sole value that exits the system. It is "
    "recorded in the smart contract alongside the batch identifier and a metadata reference, with the "
    "same root also submitted to the OpenTimestamps calendars. Publication is what gives the root its "
    "force: once recorded, it fixes the contents of the batch at a point in time, and any later "
    "divergence from it becomes meaningful rather than merely surprising.",

    "A membership proof is generated by traversing from a leaf node up to the root and recording the "
    "sibling of each node encountered along the path. The proof consists solely of the list of "
    "siblings, with no other records from the batch disclosed, enabling a single repair to be "
    "presented to a prospective buyer without revealing the other repairs associated with it. Since "
    "the proof length scales logarithmically with the batch size, four repairs necessitate two sibling "
    "digests, while one thousand repairs require ten, corresponding to sizes of 64 and 320 bytes, "
    "respectively. The verification cost increases at the same rate.",

    "Verification reverses the construction process and operates without the need for privileged "
    "access. The verifier recalculates the report digest from the provided report, derives the "
    "evidence identifier from the stored bytes, reconstructs the leaf from the canonical payload, and "
    "then iteratively folds the leaf with each sibling—combining on the left or right based on the "
    "parity of the index at that level—until the root is generated. That root is compared against "
    "the one recorded on the chain.",

    "Agreement establishes that the submitted record is the one that was committed and that this "
    "commitment occurred no later than the anchoring transaction. Disagreement localizes the failure "
    "because a single altered field modifies its leaf node, every internal node along the path to it, "
    "and consequently the root. The avalanche effect of the hash function ensures that even a slight "
    "change in the input results in a completely different digest, allowing for an exact comparison "
    "without the need for any threshold or tolerance. The same reasoning applies to what the "
    "algorithm cannot do: it binds whatever was sealed, but remains silent on whether the sealed "
    "diagnosis was correct or whether any repairs were omitted from the batch entirely.",
]

WORKED_BEFORE_T12 = [
    "Since the construction described earlier in this chapter is sufficiently small to be presented in "
    "full, doing so renders the tamper-evidence claim concrete rather than merely asserted. The "
    "following example was not manually created for this report; instead, it was generated by the "
    "project’s own batching code executed against the Proof-of-Repair leaves stored in the registry "
    "at artifacts/por_registry.sqlite3, and it can be regenerated using the script located at "
    "scripts/merkle_worked_example.py.",

    "Each leaf represents the SHA-256 digest of a canonical encoding of the committed fields, "
    "serialized with sorted keys and without optional whitespace, and prefixed by a single zero byte "
    "[31]. Internal nodes prepend a one-byte marker to the concatenation of their two children, "
    "ensuring that a leaf digest can never be mistaken for an internal node. When a level contains an "
    "odd number of nodes, the last node is paired with itself, a rule that the implementation applies "
    "consistently and that the verification path reproduces.",

    "Table 11 presents the four leaves registered, arranged in the sequence of their sealing. Three of "
    "them are from the same Honda Civic, and one is from a Toyota Camry. The three Civic entries were "
    "sealed in separate runs during interactive testing, resulting in different report digests and "
    "evidence identifiers; consequently, they produce three distinct leaves because a leaf commits to "
    "a specific sealing event rather than to a repair description.",
]

WORKED_FIG_INTRO = (
    "Grouping these four leaves in registry order yields the tree shown in Figure 7. Each digest is "
    "displayed as an eight-character hexadecimal string, though the underlying values remain the full "
    "thirty-two-byte digests."
)

WORKED_AFTER_FIG = [
    "The batch’s root is 2c5aaf4162559d21421b4f31fd06049ff98e9eb59be52b869ef0efb90e760184, a single "
    "32-byte value that commits to all four records. A membership proof for the fourth leaf comprises "
    "only the two sibling digests, 5ba113c049c602dd and 54c97cacf508904e, totaling sixty-four bytes; "
    "the verifier hashes the leaf with the first left sibling, then hashes that result with the second "
    "left sibling, and finally compares the outcome against the anchored root. Since no other records "
    "in the batch are disclosed and the proof length increases logarithmically with the batch size, a "
    "batch of one thousand repairs would still require only ten sibling digests.",

    "The value of the construction only becomes apparent when a committed field is modified. Lowering "
    "the odometer reading on the fourth leaf from 98,000 to 76,000 kilometres—a typical "
    "rollback—preserves the stored report and evidence but alters the canonical encoding, thereby "
    "changing the leaf digest. Table 12 follows the consequences back along the path to the root.",
]

WORKED_CLOSE = (
    "The recomputed root fails to match the anchored one, and the membership proof generated for the "
    "original leaf fails upon replay against the modified leaf, allowing the edit to be detected "
    "without relying on the workshop that created the record or the database that stored it. Two "
    "qualifications apply. Detection relies on the root being published prior to the alteration, which "
    "is the function of both the on-chain anchor and the OpenTimestamps receipt; during interactive "
    "testing, the anchored batches were smaller than the example provided, such as the two-leaf batch "
    "ui-1788331032592 containing root 46f5565e9a172ecb in transaction 0x22785f1ddd0d4b77 on the local "
    "chain. The construction merely confirms that the committed record is the one that was sealed, not "
    "that the diagnosis it contains is accurate."
)

CASE = [
    "Odometer tampering represents the most obvious example of the information asymmetry this project "
    "aims to resolve, and the gap is growing rather than shrinking. A segment aired on NBC Nightly "
    "News on April 1, 2023, highlighted a surge in odometer fraud occurring as a record number of "
    "American buyers turned to the used car market [46]. Subsequent figures have confirmed rather than "
    "contradicted that trend. According to a December 2025 CARFAX estimate, approximately 2.45 million "
    "vehicles on U.S. roads have rolled-back odometers, representing a 14% increase in a single year "
    "after a 4% rise the previous year, with affected buyers losing an average of about $3,300 [47]. "
    "According to the National Highway Traffic Safety Administration, approximately 450,000 vehicles "
    "are sold each year with false odometer readings, costing buyers more than $1 billion annually "
    "[48].",

    "The fraud mechanism has evolved in a manner that significantly impacts system design. CARFAX "
    "itself explains the increase by noting that while a mechanical odometer must be physically "
    "dismantled to be altered, a digital instrument cluster can be modified using inexpensive tools "
    "that are readily available [47]. Consequently, tampering is inexpensive, rapid, and leaves no "
    "trace on the instrument being falsified. Since the vehicle itself cannot provide the detection, "
    "it must instead be derived from external records.",

    "The protections typically available to a buyer are not as robust as they initially seem. "
    "Inspecting pedal wear or hiring an independent mechanic will only reveal significant discrepancies "
    "between the vehicle’s apparent condition and its stated mileage. While reviewing a commercial "
    "history report for mileage discrepancies offers a more systematic approach, its effectiveness "
    "relies on records that are often unsigned, incomplete, and voluntarily provided by participating "
    "garages and insurers, ultimately requiring the buyer to trust the database operator rather than "
    "independently verify the data. When a repair record exists solely as a paper invoice or an "
    "unsigned PDF, the document provides no indication of its creation date or whether it has been "
    "altered since.",

    "This is exactly the gap the prototype aims to fill, and the fraud serves as a useful test because "
    "the falsified quantity, or odometer reading, is one of the fields the system commits. "
    "Consequently, the scenario below was executed end-to-end against the actual implementation "
    "instead of being discussed in abstract terms. The repair event was finalized through the standard "
    "workshop workflow, batched, anchored, and verified; the committed odometer reading was then "
    "modified precisely as a rollback would, and the verification process was executed a second time "
    "to determine if the alteration was detected, what the buyer would observe, and what the results "
    "confirm or fail to confirm.",

    "The case study utilizes a repair record for a 2016 Honda Civic (sample VIN: 1HGBH41JXMN109186) "
    "with an odometer reading of 98,000 km, which presented with fault code P0420, an illuminated "
    "check-engine light, a failed emissions test, and a sluggish rear oxygen sensor signal. The "
    "diagnostic context was submitted via the workshop bay form, after which the TinyLlama path, "
    "utilizing the automotive adapter, generated a structured repair report; subsequently, the report, "
    "its supporting evidence, and the model’s provenance were sealed.",

    "Sealing generated three values. The canonical repair report hashed to 44bd1f44aea82cdd, the "
    "stored evidence payload was written to the content-addressed store under the identifier "
    "d6faec167aef4751, and the Proof-of-Repair leaf that commits the vehicle identification number, "
    "vehicle description, odometer reading, report digest, evidence identifier, and model provenance "
    "was 1ecf00f00b0c9856. Although the leaf is small and holds no personal data, it commits every "
    "single one of those fields.",

    "The leaf was subsequently batched with an additional event—a Toyota Camry record featuring the "
    "leaf ac512c77df8b6a8b—under the batch identifier ui-1788331032592. The pair was hashed to "
    "produce the Merkle root 46f5565e9a172ecb, which was anchored on the local development chain via "
    "transaction 0x22785f1ddd0d4b77 against the contract deployed at 0x5FbDB2315678afec, and "
    "simultaneously submitted to the public OpenTimestamps calendars under receipt 526ea1c4. At the "
    "time of writing, the receipt was still pending, which is the expected state for a live submission "
    "until the aggregating transaction is confirmed in a Bitcoin block, thereby illustrating the "
    "earlier point that the two anchoring paths are redundant rather than duplicated.",

    "The stored record was then verified as an independent party would. The report digest, recomputed "
    "from the stored report, matched the committed value; the evidence identifier, derived from the "
    "stored bytes, matched the committed identifier; the leaf, reconstructed from the canonical "
    "payload, matched the committed leaf; and the membership proof, comprising the single sibling "
    "ac512c77df8b6a8b in this batch, successfully folded the leaf back to the anchored root. All four "
    "checks were successful.",

    "One qualification must be stated clearly. Since the local development chain was not running at "
    "the time of writing, the on-chain check was not repeated; however, the anchor record in the "
    "registry preserves the transaction hash from the submission, and no stronger assertion is made "
    "beyond that. This stems from anchoring to a local chain instead of a public testnet—a "
    "limitation already noted in this chapter—and is precisely the dependency that a public "
    "deployment would eliminate. The other four checks need only the record, the evidence file, and "
    "the published root, and can be executed by any party that possesses them.",

    "The rollback was subsequently simulated against the sealed record. Changing the committed "
    "odometer reading from 98,000 to 76,000 kilometres, while keeping all other fields unchanged, "
    "updated the leaf digest from 1ecf00f00b0c9856 to 3ca71fb55475126d and recalculated the root from "
    "46f5565e9a172ecb to 263fc73abe0b57aa. Since 63 out of the 64 hexadecimal characters in the root "
    "were different, the mismatch was immediately obvious without needing to read carefully. The "
    "membership proof generated for the original leaf also fails upon replay against the modified "
    "version, as the folding operation no longer yields the anchored value. A much smaller edit "
    "produces the same result: decreasing the reading by just one kilometre to 97,999 generates the "
    "completely unrelated leaf 93e8cccc8ccf6349 and root 9fc49570d5bd3e33. The design leaves no margin "
    "of error for an attacker to exploit.",

    "Two additional scenarios were executed using the same record. The first replaces the supporting "
    "evidence instead of the committed record. The invoice and diagnostic payload associated with this "
    "event, stored under content identifier d6faec167aef4751, have been successfully verified as "
    "retrieved. By modifying two bytes within the 1,966-byte file to change the odometer reading on "
    "the invoice from 98,000 to 76,000, the file’s identifier was updated to 2c2f8a2364db9ef1. "
    "Since the leaf binds to the identifier instead of a document copy, the substituted invoice no "
    "longer matches the originally anchored content, allowing the substitution to be detected even "
    "without access to the file for comparison.",

    "The second scenario evaluates the reuse of a legitimate record across different vehicles, a "
    "practice involving presenting work performed on one car as proof of work done on another. The "
    "Camry leaf ac512c77df8b6a8b was relabeled with the Civic’s vehicle identification number and "
    "description, while all other committed fields remained unchanged. The leaf digest shifted to "
    "63ab48af3bdad18c and the recomputed root to cc9b95ac3b703fb0, neither matching the anchored root, "
    "causing the proof issued for the original leaf to fail when replayed against the relabelled "
    "version. Since the vehicle identification number is embedded within the hashed payload, a repair "
    "record is inherently tied to a specific vehicle and cannot be transferred to another without the "
    "transfer becoming evident.",

    "The principles established by the case should be stated narrowly. The buyer discovers that the "
    "record in question is the one that was sealed, and that it was sealed prior to the publication of "
    "the root. The buyer does not, however, discover that the diagnosis the record contains was "
    "correct: the report sealed here labelled fault code P0420 as a cooler-circuit fault and listed "
    "coolant-system steps, which deviates from the code’s accepted meaning, and it was committed "
    "faithfully nonetheless. Nor does the buyer discover whether every repair performed on the vehicle "
    "was sealed at all, as the construction itself cannot testify to records that were never created. "
    "While integrity and completeness are distinct properties, only the former is asserted.",
]

CAP_T12 = ("Table 11. Proof-of-Repair leaves recorded in the prototype registry and used in the "
           "worked example")
CAP_FIG7 = ("Figure 7. The Merkle tree was computed by the project’s batching code using the four "
            "leaves listed in Table 11. The digests are truncated for display purposes.")
CAP_T13 = ("Table 12. The impact of a single modified field on the path from the fourth leaf to the "
           "root")

TREE = [
    "                    2c5aaf41…",
    "                  /           \\",
    "       54c97cac…                 c5d06c1d…",
    "       /       \\                 /       \\",
    " 8f804538…    f245491b…    5ba113c0…    1ecf00f0…",
    "    L0           L1           L2           L3",
]

REFS_NEW = [
    "NBC News, “Odometer fraud rises as record number of Americans seek used cars,” NBC Nightly "
    "News, 1 Apr. 2023. [Online]. Available: https://www.nbcnews.com",
    "CARFAX, “Odometer rollbacks see dramatic jump of 14% to 2.45 million vehicles,” press "
    "release, 19 Dec. 2025. [Online]. Available: https://www.carfax.com",
    "National Highway Traffic Safety Administration, “Odometer fraud,” U.S. Department of "
    "Transportation. [Online]. Available: https://www.nhtsa.gov/equipment/odometer-fraud",
]

LEAF = [
    "The leaf is the unit of commitment, and the contents are fixed by the implementation, not by "
    "choice of presentation. Eleven fields are included in the hashed payload: a proof identifier, "
    "the vehicle identification number, the vehicle description, the odometer reading, the event "
    "type, the issuing workshop, the sealing timestamp, the digest of the repair report, the content "
    "identifier of the stored evidence, a model provenance record, and an open extension map. "
    "Everything that a later dispute might turn on is therefore inside a single digest, and nothing "
    "that would identify a person is.",

    "Three of these merit a comment. The event type is chosen from a closed set of five values: "
    "diagnosis, repair, parts replacement, pre-purchase inspection and fault-code clearance. This "
    "prevents a diagnosis from being later presented as a completed repair. The vehicle "
    "identification number is converted to upper case before hashing, removing a trivial source of "
    "disagreement between two parties that recorded the same vehicle differently. The extension map "
    "is always present in the payload, even if empty, to avoid a record being augmented after "
    "sealing in a way that would not be obvious.",

    "Model provenance is a field without a counterpart in a paper service book. It records the base "
    "model, the adapter version, a digest of the adapter weights themselves, and a Merkle root over "
    "the training dataset manifest. A sealed diagnosis is thus attributable not just to a model by "
    "name, but to the exact parameters that produced it and the exact corpus those parameters were "
    "trained on. If a model version is found in the future that incorrectly labels a group of fault "
    "codes in a systematic manner, then all the records generated by it can be sought out and "
    "re-verified, a property the diagnostic layer cannot provide by itself.",

    "Both the report and the evidence are shrunk before they enter the leaf. The repair report is "
    "serialized canonically and hashed; the evidence is written to a content-addressable store whose "
    "identifier is the digest of the stored bytes. The leaf thus commits to a diagnosis of several "
    "hundred words and to invoices and photographs of arbitrary size through two fixed-length "
    "values. A report of nine fields and an evidence payload of 1,966 bytes is represented by "
    "thirty-two bytes each in the record examined later in this chapter.",

    "In practice this means the leaf is small enough to batch cheaply and publish without revealing "
    "anything. A workshop discloses a leaf without disclosing what it contains. A buyer who is shown "
    "the underlying report can verify that it is the report the leaf committed to. A party holding "
    "neither can still verify the leaf was included in a published batch. This is one structure that "
    "supports three different levels of disclosure, which is why the commitment is over a canonical "
    "encoding rather than over the documents themselves.",
]

LEAF_FIELDS = [
    ["proof_id", "Identifies the sealing event itself"],
    ["vin", "Binds the record to one vehicle; upper-cased before hashing"],
    ["vehicle", "Detects substitution of a different vehicle of similar description"],
    ["odometer_km", "Fixes the point in the vehicle\u2019s life at which the work was done"],
    ["event_type", "Separates a diagnosis from a completed repair"],
    ["issuer_id", "Records the workshop that sealed the record"],
    ["timestamp", "Orders events within one vehicle\u2019s history"],
    ["report_hash", "Any edit to the repair report breaks the digest"],
    ["evidence_cid", "Detects substitution of invoices, photographs or reports"],
    ["model", "Attributes the diagnosis to a model, adapter and training corpus"],
    ["extra", "Present even when empty, so later augmentation is visible"],
]


CONTRACT = [
    "The anchoring contract is intentionally small. It is written in Solidity for the 0.8.20 "
    "compiler series and stores one record type: a root, the block timestamp at which it was "
    "accepted, the batch identifier it belongs to, a metadata reference, and the address that "
    "submitted it. Two mappings index that record, one from root to anchor and one from batch "
    "identifier to root, so that a batch can be located either by the commitment it produced or by "
    "the name under which it was sealed.",

    "One single external function does the anchoring, and it enforces four conditions before it "
    "writes anything. The root cannot be zero, the batch identifier cannot be empty, the root cannot "
    "already exist, and the batch identifier cannot already be bound to a different root. The third "
    "and fourth conditions are the ones that prevent reuse: a root cannot be anchored twice, and a "
    "batch identifier cannot be quietly re-pointed at a new root after the fact. Any of these "
    "attempts leads to a reversion, which is the behavior that the verification path relies on when "
    "it considers a recorded anchor to be final.",

    "Each accepted anchor creates an event with the root, the batch identifier, the metadata "
    "reference, the submitting address and the timestamp, and the root and the submitter are "
    "indexed. Thus an observer who never queries the contract state can reconstruct the full "
    "anchoring history from logs alone, which matters for a verifier that holds only a record and a "
    "root and wishes to establish when that root first appeared.",

    "One property should be declared in a straightforward manner, not found by a reader of the "
    "source. Anchoring is permissionless. The contract has an owner and an ownership transfer "
    "function, but the anchoring function is not restricted to the owner, so any address can anchor "
    "any root. The submitting address recorded with the root is therefore a claim about who sealed a "
    "batch, not an authorization to seal it. Establishing that a particular workshop made such a "
    "claim requires an identity layer the prototype does not implement, and the recorded address "
    "should be read accordingly. What the contract does guarantee is narrower but still useful: that "
    "a given root was present at a given block time, and has not been replaced since.",

    "The deployment used for this work is a local development chain with chain id 31337, with the "
    "contract deployed at 0x5FbDB2315678afec. Four batches were anchored through it during "
    "interactive testing, each returning a transaction hash that the registry stores alongside the "
    "batch. This exercises the complete path including rejection of duplicate roots but confers no "
    "public persistence: a root anchored on a development chain is only as durable as that chain, "
    "which is why the same roots are submitted in parallel to a public timestamping service.",
]

GUARDS = [
    ["Root is non-zero", "An empty or unset commitment"],
    ["Batch identifier is non-empty", "A batch recorded without a name"],
    ["Root not already anchored", "The same root being recorded a second time"],
    ["Batch identifier unused", "An identifier being re-pointed at a different root"],
]


SYNTH = [
    "Taken together, the reviewed work provides all the pieces this problem needs but never puts "
    "them together. The fault inferences and remaining-life estimates are produced, but the vehicle "
    "diagnosis research stops when the inference is produced. Transparency-log and timestamping "
    "research develops mechanisms for proving that a record existed and has not changed, and takes "
    "the content of that record as given. Parameter-efficient adaptation makes it affordable to "
    "specialize a language model to a narrow technical vocabulary and says nothing about what should "
    "be done with the output. Each line of work is mature in its own terms.",

    "The gap is the join. A diagnosis is only useful to a buyer when it is linked to a certain "
    "vehicle at a certain odometer reading, with proof that the suggested work was in fact "
    "performed, in a way that a stranger can verify without having to trust the garage that made it "
    "or the database that stored it. None of the reviewed systems ties those four things together. "
    "Vehicle proposals based on blockchain tend to anchor telemetry or transfer of ownership rather "
    "than repair events and the documents supporting them. Diagnostic systems produce text, but do "
    "not handle the custody of it. Transparency logs are built for certificates where the object to "
    "be committed is already a structured artifact with an understood meaning.",

    "Two consequences for the design follow. First, before anything can be anchored, the object of "
    "commitment has to be defined, for a commitment is only as meaningful as the thing it commits "
    "to; this is why the leaf specification precedes the anchoring mechanism in the following "
    "chapter. Second, the roles of the two technologies must be separated unambiguously. The adapted "
    "language model translates diagnostic context into a structured record and does not guarantee "
    "the correctness of the record. The cryptographic layer ensures that whatever was recorded "
    "cannot be changed afterward and does not give any opinion about whether it was right. "
    "Conflating these is to make the common and mistaken claim that putting a diagnosis on a chain "
    "makes the diagnosis trustworthy.",

    "The separation also makes clear what the evaluation obligations are. The diagnostic layer must "
    "be measured on whether it identifies the correct fault and emits a record that survives "
    "downstream processing, and must be reported honestly when it does not. It is not enough to "
    "assert that the construction detects tampering; the attestation layer must be demonstrated by "
    "showing that an altered record is detected. These are dealt with separately in the subsequent "
    "chapters, and the limitations of each are reported without an appeal to the strengths of the "
    "other.",
]

THEMES = [
    ["Used-vehicle information asymmetry", "[1], [2]", "Why verifiable history has value, not how to produce it"],
    ["OBD-II diagnostics and identifiers", "[28], [29], [30]", "A shared vocabulary; no custody of what is recorded"],
    ["Vehicle and machine health analytics", "[7], [8], [18], [19]", "Degradation models in which the inference is the end point"],
    ["Language models for structured output", "[9], [13], [14], [15], [16]", "Structure without a guarantee of correctness"],
    ["Parameter-efficient fine-tuning", "[10], [11], [12], [26], [27]", "Affordable adaptation, silent on downstream use"],
    ["Blockchain integrity and vehicular ledgers", "[3], [4], [6], [22], [23], [24]", "Ledgers for telemetry and ownership, not repair evidence"],
    ["Merkle trees and transparency logs", "[20], [31], [32], [33], [34]", "Membership proofs for already-structured objects"],
    ["Timestamping and content-addressed storage", "[5], [25], [35]", "Existence in time; the committed object is assumed"],
]

RESULTS = [
    "The diagnostic layer was evaluated on a split disjoint by fault code, meaning that no code seen "
    "during training appears at evaluation. A fixed seed is used to split the corpus into 721 "
    "training, 86 validation and 163 test examples. The manifest describing the corpus is itself "
    "hashed and the resulting root is recorded in the provenance field of each sealed record.",

    "On the primary hold-out of 57 real OBD cases, the 4-bit Mistral path adapted with MLX "
    "identified the correct fault code in 98.3% of cases and emitted a schema-complete record in "
    "98.3%, failing outright once. The TinyLlama path with the automotive adapter achieved 93.0% on "
    "fault code while providing a valid record each time. It is the contrast that matters more than "
    "the gap. A pipeline that must hash its output treats an unparsable response as a repair that "
    "cannot be sealed, so perfect structural validity on a weaker model is not obviously worse than "
    "one failure on a stronger one.",

    "Both figures decrease in situations for which the models have not been adapted. Mistral\u2019s "
    "fault-code accuracy drops to 43.6%, and TinyLlama\u2019s drops to 32.5% across the entire "
    "163-case profile. The 106 free-text owner complaints in the national defects database are "
    "symptom descriptions with no quote of a diagnostic code, and fault-code accuracy on them is "
    "zero. The models learned to map codes to procedures, but not to infer codes from prose, and "
    "nothing in the training data asked them to do so. The figure of 98.3% would be misleading on "
    "its own.",

    "Severity classification is weak, between 56% and 60% accuracy, and overlap with reference "
    "repair steps is low, with ROUGE-L scores of 0.13 to 0.24. These are both to be expected when "
    "there are several equally correct phrasings of a procedure, and neither is a safety claim. "
    "Within the hold-out, performance also splits by origin: Mistral labels every case from the "
    "instruction-tuned subset correctly, but is better calibrated on severity for the real workshop "
    "subset, 75.8% against 37.5%. This suggests the two corpora teach different things, and should "
    "not be pooled when reporting.",

    "The attestation layer is reported separately because it has no accuracy. It either detects the "
    "change or it does not. Four batches were sealed, anchored on the development chain and "
    "timestamped, and each verification run against the stored records regenerated the committed "
    "digests. As set out in full in the following worked example, every attempted alteration against "
    "them was detected.",

    "A deployment condition is reported and not hidden. On a fresh checkout the sealing path fails "
    "before it reaches the model, since the trained adapter is not pulled into the adapter directory "
    "by the repository itself. This is a packaging gap in that working copy, not a defect in either "
    "layer, and it means the full workflow, including live inference, has not been shown end to end "
    "on that machine.",
]

EVAL = [
    ["Mistral 4-bit", "Real OBD hold-out (57)", "98.3%", "98.3%", "59.7%"],
    ["TinyLlama", "Real OBD hold-out (57)", "93.0%", "100%", "56.1%"],
    ["Mistral 4-bit", "Full DTC profile (163)", "43.6%", "96.9%", "66.9%"],
    ["TinyLlama", "Full DTC profile (163)", "32.5%", "82.8%", "60.1%"],
    ["TinyLlama", "Free-text complaints (106)", "0.0%", "73.6%", "62.3%"],
]


# ---------------------------------------------------------------------- xml helpers

HEAD3_PR = ('<w:numPr><w:ilvl w:val="0"/><w:numId w:val="0"/></w:numPr><w:keepNext/>'
            '<w:spacing w:before="4pt" w:after="2pt"/><w:ind w:start="0pt" w:firstLine="0pt"/>')
CAP_PR = ('<w:numPr><w:ilvl w:val="0"/><w:numId w:val="0"/></w:numPr><w:keepNext/>'
          '<w:ind w:start="0pt" w:firstLine="0pt"/>')
MONO = ('<w:rFonts w:ascii="Courier New" w:hAnsi="Courier New" w:cs="Courier New"/>'
        '<w:sz w:val="14"/><w:szCs w:val="14"/>')


def para_span(s: str, needle: str) -> tuple[int, int]:
    i = s.index(needle)
    return s.rindex("<w:p>", 0, i), s.index("</w:p>", i) + len("</w:p>")


def drop_para(s: str, needle: str) -> str:
    a, b = para_span(s, needle)
    return s[:a] + s[b:]


def P(text: str, style: str = "BodyText", extra: str = "") -> str:
    return (f'<w:p><w:pPr><w:pStyle w:val="{style}"/>{extra}</w:pPr>'
            f'<w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>')


def heading3(text: str) -> str:
    return (f'<w:p><w:pPr><w:pStyle w:val="Heading3"/>{HEAD3_PR}</w:pPr>'
            f'<w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>')


def caption(text: str) -> str:
    return (f'<w:p><w:pPr><w:pStyle w:val="tablehead"/>{CAP_PR}</w:pPr>'
            f'<w:r><w:rPr><w:i/><w:iCs/></w:rPr><w:t xml:space="preserve">{text}</w:t></w:r></w:p>')


def figcaption(text: str) -> str:
    return (f'<w:p><w:pPr><w:pStyle w:val="figurecaption"/>'
            '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="0"/></w:numPr>'
            '<w:spacing w:before="2pt" w:after="8pt"/>'
            '<w:ind w:start="0pt" w:firstLine="0pt"/></w:pPr>'
            f'<w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>')


def mono_block(lines: list[str]) -> str:
    runs = []
    for i, ln in enumerate(lines):
        if i:
            runs.append("<w:br/>")
        runs.append(f'<w:t xml:space="preserve">{ln}</w:t>')
    return ('<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:keepNext/><w:keepLines/>'
            '<w:spacing w:before="6pt" w:after="2pt"/>'
            '<w:ind w:start="14pt" w:firstLine="0pt"/><w:jc w:val="start"/>'
            f'<w:rPr>{MONO}</w:rPr></w:pPr><w:r><w:rPr>{MONO}</w:rPr>{"".join(runs)}</w:r></w:p>')


def table(widths: list[int], header: list[str], rows: list[list[str]]) -> str:
    borders = "".join(f'<w:{k} w:val="single" w:sz="2" w:space="0" w:color="auto"/>'
                      for k in ("top", "start", "bottom", "end", "insideH", "insideV"))
    out = ['<w:tbl><w:tblPr><w:tblW w:w="5040" w:type="dxa"/><w:jc w:val="center"/>'
           f'<w:tblBorders>{borders}</w:tblBorders><w:tblLayout w:type="fixed"/>'
           '<w:tblCellMar><w:top w:w="15" w:type="dxa"/><w:start w:w="43" w:type="dxa"/>'
           '<w:bottom w:w="15" w:type="dxa"/><w:end w:w="43" w:type="dxa"/></w:tblCellMar>'
           '<w:tblLook w:firstRow="1" w:lastRow="0" w:firstColumn="0" w:lastColumn="0"'
           ' w:noHBand="1" w:noVBand="1"/></w:tblPr><w:tblGrid>']
    out += [f'<w:gridCol w:w="{w}"/>' for w in widths]
    out.append("</w:tblGrid><w:tr><w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>")
    for w, cell in zip(widths, header):
        out.append(f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
                   f'<w:p><w:pPr><w:pStyle w:val="tablecolhead"/></w:pPr>'
                   f'<w:r><w:rPr><w:b/><w:bCs/></w:rPr>'
                   f'<w:t xml:space="preserve">{cell}</w:t></w:r></w:p></w:tc>')
    out.append("</w:tr>")
    for row in rows:
        out.append('<w:tr><w:trPr><w:cantSplit/></w:trPr>')
        for w, cell in zip(widths, row):
            out.append(f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/><w:vAlign w:val="top"/></w:tcPr>'
                       f'<w:p><w:pPr><w:pStyle w:val="tablecopy"/><w:jc w:val="start"/></w:pPr>'
                       f'<w:r><w:t xml:space="preserve">{cell}</w:t></w:r></w:p></w:tc>')
        out.append("</w:tr>")
    out.append("</w:tbl>")
    return "".join(out)


def reference(text: str) -> str:
    return f'<w:p><w:pPr><w:pStyle w:val="references"/></w:pPr><w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>'


# ---------------------------------------------------------------------------- build

def replace_section(doc: str, heading: str, next_heading: str, new_xml: str) -> str:
    """Drop everything between two headings and put new_xml in its place."""
    _, a = para_span(doc, heading)
    b, _ = para_span(doc, next_heading)
    return doc[:a] + new_xml + doc[b:]


def main() -> None:
    zin = zipfile.ZipFile(SRC)
    doc = zin.read("word/document.xml").decode("utf-8")
    before = len(doc)

    # 1. the 4.2 lead-in: drop the sequence diagrams, announce the algorithm
    old_lead = ("The design is documented using a context and level-1 data flow diagram, a conceptual "
                "class model, and two sequence diagrams that cover the sealing and verification "
                "processes.")
    new_lead = ("The design is documented using a context and level-1 data flow diagram, a conceptual "
                "class model, and a statement of the attestation algorithm.")
    assert doc.count(old_lead) == 1, "lead-in sentence not found"
    doc = doc.replace(old_lead, new_lead)

    # 2. remove the sequence-diagram subsection
    for needle in ("4.2.3 Sequence Diagram",
                   "Figure 7 illustrates the workshop journey.",
                   "The comparison step is where the guarantee is actually delivered."):
        doc = drop_para(doc, needle)

    # 2b. rewritten 4.1.1 with an eleven-field table replacing the six-field Table 7
    leaf_block = "".join(P(t) for t in LEAF)
    leaf_block += caption("Table 7. Fields bound in the hashed leaf payload")
    leaf_block += table([1400, 3640], ["Field", "Why it is bound"], LEAF_FIELDS)
    doc = replace_section(doc, "4.1.1 The Proof-of-Repair Leaf",
                          "4.1.2 Merkle Tree and Root", leaf_block)

    # 2c. rewritten 4.1.3; Table 8 becomes the contract's four preconditions
    c_block = "".join(P(t) for t in CONTRACT)
    c_block += caption("Table 8. Conditions enforced before a root is recorded")
    c_block += table([1700, 3340], ["Condition", "What it rejects"], GUARDS)
    doc = replace_section(doc, "4.1.3 Smart Contract and On-Chain Anchoring",
                          "4.1.4 OpenTimestamps", c_block)

    # 2d. rewritten 2.1.9 with a reframed Table 1
    syn = "".join(P(t) for t in SYNTH)
    syn += caption("Table 1. What each line of work establishes and what it leaves open")
    syn += table([1500, 1100, 2440],
                 ["Theme", "Representative works", "What it leaves open"], THEMES)
    doc = replace_section(doc, "2.1.9 Synthesis", "2.2 Research Gap", syn)

    # 2e. rewritten 4.4; the implementation-status table is dropped and Table 10 rebuilt
    res = "".join(P(t) for t in RESULTS[:2])
    res += caption("Table 10. Diagnostic evaluation across all three evaluation sets")
    res += table([1150, 1450, 850, 800, 790],
                 ["Model", "Evaluation set (n)", "Fault code", "Valid JSON", "Severity"], EVAL)
    res += "".join(P(t) for t in RESULTS[2:])
    doc = replace_section(doc, "4.4 Implementation Status and Preliminary Results",
                          "4.5 Limitations and Future Work", res)
    doc = doc.replace("4.4 Implementation Status and Preliminary Results", "4.4 Results")

    # 3. 4.2.3 Attestation Algorithm, in the slot the sequence diagram vacated
    algo = [heading3("4.2.3 Attestation Algorithm")] + [P(t) for t in ALGO]
    a, _ = para_span(doc, "4.3 Dataset Description and Model Development")
    doc = doc[:a] + "".join(algo) + doc[a:]

    # 4. 4.4.1 Worked Merkle Example and 4.4.2 Case Study, before 4.5
    block = [heading3("4.4.1 Worked Merkle Example")]
    block += [P(t) for t in WORKED_BEFORE_T12]
    block.append(caption(CAP_T12))
    block.append(table([420, 1740, 900, 500, 1480],
                       ["Leaf", "VIN", "Odometer (km)", "DTC", "Leaf digest (first 16 hex)"],
                       [["L0", "1HGBH41JXMN109186", "98 000", "P0420", "8f8045381b3de6c5"],
                        ["L1", "4T1BF1FK5EU123456", "142 000", "P0300", "f245491b88338a09"],
                        ["L2", "1HGBH41JXMN109186", "98 000", "P0420", "5ba113c049c602dd"],
                        ["L3", "1HGBH41JXMN109186", "98 000", "P0420", "1ecf00f00b0c9856"]]))
    block.append(P(WORKED_FIG_INTRO, extra='<w:spacing w:before="8pt"/>'))
    block.append(mono_block(TREE))
    block.append(figcaption(CAP_FIG7))
    block += [P(t) for t in WORKED_AFTER_FIG]
    block.append(caption(CAP_T13))
    block.append(table([1040, 2000, 2000],
                       ["Node", "Digest before", "Digest after"],
                       [["Leaf L3", "1ecf00f00b0c9856", "3ca71fb55475126d"],
                        ["Level-1 node", "c5d06c1dc0d761cd", "786c0f13b0a5e96e"],
                        ["Root", "2c5aaf4162559d21", "14dd49985aa4f8b6"]]))
    block.append(P(WORKED_CLOSE, extra='<w:spacing w:before="8pt"/>'))

    block.append(heading3("4.4.2 Case Study: Odometer Rollback"))
    block += [P(t) for t in CASE]

    a, _ = para_span(doc, "4.5 Limitations and Future Work")
    doc = doc[:a] + "".join(block) + doc[a:]

    # 5. three new references, appended to the web sources so they number [46]-[48]
    _, b = para_span(doc, "MLX: An array framework for Apple silicon")
    doc = doc[:b] + "".join(reference(r) for r in REFS_NEW) + doc[b:]

    ET.fromstring(doc.encode("utf-8"))
    print(f"document.xml {before} -> {len(doc)} bytes, XML well-formed")

    with zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = doc.encode("utf-8") if item.filename == "word/document.xml" else zin.read(item.filename)
            zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
            zi.compress_type = item.compress_type
            zi.external_attr = item.external_attr
            zout.writestr(zi, data)
    print("wrote", DST)
    print("\ncorrections applied to the humanized text:")
    for c in CORRECTIONS:
        print("  -", c)


if __name__ == "__main__":
    main()
