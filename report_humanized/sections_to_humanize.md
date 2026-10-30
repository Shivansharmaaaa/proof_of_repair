# Replacement sections to humanize

Each block is under 500 words. Run one at a time, then send it back and I will swap it into the document.


**Do not let the tool alter these:** 0x5FbDB2315678afec, chain id 31337, Solidity 0.8.20, 721/86/163, n=57, n=163, n=106, 98.3%, 93.0%, 43.6%, 32.5%, 75.8%, 37.5%, 56%-60%, ROUGE-L 0.13-0.24, 1,966 bytes. Last time it split digits ("2. 45 million") and broke file paths.


---

## R1 — 4.1.1 The Proof-of-Repair Leaf  (replaces the current 4.1.1)
*467 words*

The leaf is the unit of commitment, and its contents are fixed by the implementation rather than chosen for presentation. Eleven fields enter the hashed payload: a proof identifier, the vehicle identification number, the vehicle description, the odometer reading, the event type, the issuing workshop, the sealing timestamp, the digest of the repair report, the content identifier of the stored evidence, a model provenance record, and an open extension map. Everything a later dispute might turn on is therefore inside a single digest, and nothing that would identify a person is.

Three of these deserve comment. The event type is drawn from a closed set of five values covering diagnosis, repair, parts replacement, pre-purchase inspection and fault-code clearance, so a diagnosis cannot later be presented as a completed repair. The vehicle identification number is converted to upper case before hashing, which removes a trivial source of disagreement between two parties who recorded the same vehicle differently. The extension map is included in the payload even when empty, so that a record cannot be augmented after sealing without the augmentation being visible.

Model provenance is the field with no counterpart in a paper service book. It records the base model, the adapter version, a digest of the adapter weights themselves, and a Merkle root computed over the training dataset manifest. A sealed diagnosis is therefore attributable not only to a model by name but to the exact parameters that produced it and the exact corpus those parameters were trained on. If a model version is later found to systematically mislabel a family of fault codes, every record produced by it can be located and re-examined, which is a property the diagnostic layer cannot provide on its own.

The report and the evidence are both reduced before they enter the leaf. The repair report is serialised canonically and hashed, and the evidence is written to a content-addressed store whose identifier is the digest of the stored bytes. The leaf therefore commits to a diagnosis of several hundred words and to invoices and photographs of arbitrary size through two fixed-length values. In the record examined later in this chapter, a report of nine fields and an evidence payload of 1,966 bytes are represented by thirty-two bytes each.

The practical consequence is that the leaf stays small enough to batch cheaply and to publish without exposing anything. A workshop discloses a leaf without disclosing what it contains; a buyer who is shown the underlying report can confirm that it is the report the leaf committed to; and a party holding neither can still confirm that the leaf was included in a published batch. These are three different levels of disclosure supported by one structure, which is why the commitment is made over a canonical encoding rather than over the documents themselves.


---

## R2 — 4.1.3 Smart Contract and On-Chain Anchoring  (replaces the current 4.1.3)
*458 words*

The anchoring contract is deliberately small. It is written in Solidity for the 0.8.20 compiler series and stores one record type: a root, the block timestamp at which it was accepted, the batch identifier it belongs to, a metadata reference, and the address that submitted it. Two mappings index that record, one from root to anchor and one from batch identifier to root, so that a batch can be located either by the commitment it produced or by the name under which it was sealed.

A single external function performs the anchoring, and it enforces four conditions before writing anything. The root must be non-zero, the batch identifier must be non-empty, the root must not already be present, and the batch identifier must not already be bound to a different root. The third and fourth conditions are what prevent reuse: a root cannot be anchored twice, and a batch identifier cannot be quietly re-pointed at a new root after the fact. An attempt to do either reverts, which is the behaviour the verification path depends on when it treats a recorded anchor as final.

Each accepted anchor emits an event carrying the root, the batch identifier, the metadata reference, the submitting address and the timestamp, with the root and the submitter indexed. An observer who never queries the contract state can therefore reconstruct the full anchoring history from logs alone, which matters for a verifier who holds only a record and a root and wants to establish when that root first appeared.

One property should be stated plainly rather than discovered by a reader of the source. Anchoring is permissionless. The contract carries an owner and an ownership transfer function, but the anchoring function is not restricted to the owner, so any address may anchor any root. The submitting address recorded alongside the root is therefore a claim about who sealed a batch, not an authorisation to seal it. Establishing that a particular workshop made that claim requires an identity layer the prototype does not implement, and the recorded address should be read accordingly. The guarantee the contract does provide is narrower and still useful: that a given root was present at a given block time and has not been replaced since.

The deployment used for this work is a local development chain with chain identifier 31337, with the contract deployed at 0x5FbDB2315678afec. Four batches were anchored through it during interactive testing, each returning a transaction hash that the registry stores alongside the batch. This exercises the complete path, including rejection of duplicate roots, but confers no public persistence: a root anchored on a development chain is only as durable as that chain, which is why the same roots are submitted in parallel to a public timestamping service.


---

## R3 — 2.1.9 Synthesis  (replaces the current 2.1.9; use as the closing paragraphs of Related Work)
*405 words*

Read together, the reviewed work supplies every component this problem needs and never assembles them. Vehicle diagnosis research produces fault inferences and remaining-life estimates, and stops when the inference is produced. Transparency-log and timestamping research produces mechanisms for proving that a record existed and has not changed, and treats the content of that record as given. Parameter-efficient adaptation makes it affordable to specialise a language model to a narrow technical vocabulary, and says nothing about what should be done with the output. Each line of work is mature on its own terms.

The gap is the join. A diagnosis is useful to a buyer only if it is bound to a particular vehicle at a particular odometer reading, with the evidence that the recommended work was actually carried out, in a form that a stranger can check without trusting the garage that produced it or the database that stored it. None of the reviewed systems binds those four things together. Blockchain-based vehicle proposals typically anchor telemetry or ownership transfer rather than repair events and their supporting documents. Diagnostic systems produce text and leave its custody unaddressed. Transparency logs are built for certificates, where the committed object is already a structured artefact with an established meaning.

Two consequences follow for the design. First, the committed object has to be defined before anything can be anchored, because a commitment is only as meaningful as the thing it commits to; this is why the leaf specification precedes the anchoring mechanism in the chapter that follows. Second, the roles of the two technologies must be separated without ambiguity. The adapted language model converts diagnostic context into a structured record and offers no guarantee that the record is correct. The cryptographic layer guarantees that whatever was recorded cannot be altered afterwards and offers no opinion on whether it was right. Conflating these produces the common and mistaken claim that putting a diagnosis on a chain makes the diagnosis trustworthy.

Stating the separation also makes the evaluation obligations clear. The diagnostic layer must be measured on whether it identifies the correct fault and emits a record that survives downstream processing, and must be reported honestly when it fails. The attestation layer must be demonstrated by showing that an altered record is detected, rather than asserted by describing the construction. The chapters that follow address these separately, and the limitations of each are reported without appeal to the strengths of the other.


---

## R4 — 4.4 Results  (replaces the current 4.4 Implementation Status and Preliminary Results)
*462 words*

The diagnostic layer was evaluated on a split that is disjoint by fault code, so that no code seen during training appears at evaluation. The corpus divides into 721 training, 86 validation and 163 test cases under a fixed seed, and the manifest describing it is itself hashed, with the resulting root recorded in the provenance field of every sealed record.

On the primary hold-out of 57 real OBD cases, the 4-bit Mistral path adapted with MLX identified the correct fault code in 98.3% of cases and emitted a schema-complete record in 98.3%, failing outright once. The TinyLlama path with the automotive adapter reached 93.0% on fault code while emitting a valid record every time. The contrast matters more than the gap: a pipeline that must hash its output treats an unparsable response as a repair that cannot be sealed, so perfect structural validity on a weaker model is not obviously worse than one failure on a stronger one.

Both figures fall away under conditions the models were not adapted for. Across the full 163-case profile, fault-code accuracy drops to 43.6% for Mistral and 32.5% for TinyLlama. On the 106 free-text owner complaints drawn from the national defects database, which describe symptoms without quoting a diagnostic code, fault-code accuracy is zero. The models learned to map codes to procedures, not to infer codes from prose, and nothing in the training data asked them to. Reported alone, the 98.3% figure would misrepresent the system.

Severity classification is weak throughout, between 56% and 60%, and overlap with reference repair steps is low, with ROUGE-L between 0.13 and 0.24. Both are expected where several phrasings of a procedure are equally correct, and neither is a safety claim. Within the hold-out, performance also splits by origin: Mistral labels every case from the instruction-tuned subset correctly but is better calibrated on severity for the real workshop subset, at 75.8% against 37.5%, which suggests the two corpora teach different things and should not be pooled when reporting.

The attestation layer is reported differently because it does not have an accuracy. It either detects an alteration or it does not. Four batches were sealed, anchored on the development chain and timestamped, and every verification run over the stored records reproduced the committed digests. Every alteration attempted against them was detected, as the worked example that follows sets out in full.

One deployment condition is reported rather than concealed. On a fresh checkout the sealing path fails before reaching the model, because the trained adapter is not fetched into the adapter directory by the repository itself. This is a packaging gap in that working copy, not a defect in either layer, and it means the complete workflow including live inference has not been demonstrated end to end on that machine.
