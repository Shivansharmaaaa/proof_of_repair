"""Humanized Proof-of-Repair report — content source.

Append new sections to BLOCKS as they are drafted, then run build_report.py.
Block kinds: h1, h2, h3, body, keywords, bullet
"""

BLOCKS = [
    ("h1", "Abstract"),

    ("body",
     "The resale value and safety of a used vehicle are heavily influenced by its repair "
     "history, which is typically documented only through paper invoices, workshop stamps, "
     "and unsigned PDF service reports. These documents can be altered, back-dated, or "
     "selectively withheld, leaving buyers, dealers, or insurers with little reliable proof "
     "that a declared repair actually occurred, that it was performed at the stated odometer "
     "reading, or that the supporting paperwork remains unchanged."),

    ("body",
     "This project develops a cloud-based Proof-of-Repair system that creates a verifiable, "
     "tamper-evident repair history linked to a vehicle identification number (VIN). The "
     "workshop-captured data, including the VIN, vehicle details, OBD-II diagnostic trouble "
     "codes, symptoms, sensor notes, and odometer reading, is processed by a large language "
     "model fine-tuned with parameter-efficient LoRA for automotive fault diagnosis, which "
     "outputs a structured diagnosis and a ranked repair procedure. Supporting evidence, "
     "including invoices, photographs, and reports, is stored off-chain, while only digests "
     "and content identifiers are retained. Each repair is recorded as a Proof-of-Repair leaf "
     "associated with the vehicle identification number, vehicle details, odometer reading, "
     "report hash, evidence identifier, and model provenance. Leaves are organized into a "
     "Merkle tree, with its root secured by an EVM-compatible smart contract and "
     "independently timestamped via OpenTimestamps, ensuring that any alteration to a "
     "committed record invalidates its digest, updates the recomputed root, and triggers "
     "detection. A buyer, dealer, or insurer checks the repair timeline for a vehicle "
     "identification number and verifies the sealing status of every event."),

    ("body",
     "Two fine-tuned models were evaluated on a real-world OBD hold-out set containing 57 "
     "cases, achieving fault-code accuracy rates of 93. 0% and 98. 3%. This system is a "
     "research prototype that operates on a local EVM development chain, uses synthetic data "
     "for demonstration, and defers physical OBD-II integration, production deployment, and "
     "large-scale field validation to future work."),

    ("keywords",
     "The keywords include proof of repair, second-hand vehicles, vehicle repair history, "
     "VIN, OBD-II diagnostic trouble codes, large language models, LoRA fine-tuning, Merkle "
     "tree, blockchain anchoring, OpenTimestamps, data integrity, and content-addressed "
     "evidence."),

    ("h1", "1. Introduction"),

    ("body",
     "The used vehicle market is one of the world's largest consumer markets, and in most "
     "countries it significantly exceeds the new vehicle market in terms of unit volume. "
     "However, a used vehicle is an unusually opaque product. Two vehicles of the same make, "
     "model, year, and mileage can vary drastically in condition depending on whether a "
     "transmission has been rebuilt, if structural damage from an accident was properly "
     "repaired, or if recurring electronic issues have been managed only with temporary "
     "fixes. The seller typically possesses extensive knowledge of the product's history, "
     "whereas the buyer usually lacks such information, representing the classic condition of "
     "information asymmetry documented in economic literature regarding markets for goods of "
     "uncertain quality [1]. When buyers cannot tell the difference between a well-maintained "
     "vehicle and a poorly maintained one, the price offered tends to converge toward the "
     "value of an average or below-average example, which penalizes honest sellers and "
     "rewards concealment [1], [2]."),

    ("body",
     "In practice, repair history is communicated through service booklets, printed workshop "
     "invoices, stamped maintenance schedules, and increasingly, PDF job cards sent via "
     "email. All of these are standard documents. A PDF can be regenerated with a new date, a "
     "booklet stamp can be applied out of sequence, an invoice can be discarded if it records "
     "an inconvenient repair, and a scanned report can be edited before being forwarded to a "
     "prospective buyer. The document itself provides no evidence of its creation date or "
     "whether it has been altered since. While centralized commercial vehicle-history "
     "services offer a partial solution, they rely on selective reporting from participating "
     "garages and insurers, vary significantly in coverage across countries, and ultimately "
     "require consumers to trust the database operator rather than verify the information "
     "independently."),

    ("body",
     "Two distinct technical capabilities are needed to address this issue, and it is crucial "
     "not to conflate them. The first step is interpretation, which involves converting raw "
     "diagnostic signals from a vehicle—primarily the OBD-II diagnostic trouble codes "
     "standardized in [29] and [30], along with symptoms and sensor observations—into a "
     "structured and consistent statement identifying the problem and the necessary repairs. "
     "This language and reasoning problem is addressed in the project by a large language "
     "model adapted to the automotive diagnostic domain using low-rank adaptation [10]. The "
     "second capability is integrity, which ensures that once a repair is recorded, neither "
     "the workshop nor any subsequent party can silently alter the record or the supporting "
     "evidence. This cryptographic problem is addressed using content-addressed evidence, "
     "Merkle-tree commitments [20], and public anchoring [23], [24], [35]."),

    ("body",
     "The system outlined in this report maintains a strict separation between these two "
     "roles. The artificial intelligence component interprets diagnostic data and produces "
     "structured repair information, offering no security guarantees at all. The blockchain "
     "and timestamping features ensure that recorded data cannot be altered, but they do not "
     "verify the clinical accuracy of the diagnosis."),

    ("h2", "1.1 Background"),

    ("body",
     "Modern vehicles are equipped with a wide array of instruments. On-board diagnostics "
     "standards establish a unified set of emission-related diagnostic services and a shared "
     "vocabulary of diagnostic trouble codes, enabling scan tools from any manufacturer to "
     "retrieve fault information from any compliant vehicle [29], [30]. Consequently, raw "
     "fault data is readily accessible in workshops. The most challenging part is the step "
     "following retrieval: connecting a code to the likely cause, the specific repair needed, "
     "and the associated parts and labor. This interpretive knowledge is primarily stored in "
     "the experience of technicians and in proprietary service manuals."),

    ("body",
     "Regardless, cryptography has long supplied the essential components required to make "
     "records tamper-evident. Merkle trees condense large collections of records into a single "
     "hash value [20], transparency logs leverage this structure to ensure that append-only "
     "claims are auditable [32], [33], and timestamping schemes enable a party to demonstrate "
     "that data existed at a specific time [5], [35]. Public blockchains offer a "
     "cost-effective platform for publishing such commitments, where no single participant has "
     "control over the record [23], [24]. This project combines these two established areas of "
     "expertise to demonstrate what was repaired on a specific vehicle."),

    ("h2", "1.2 Motivation"),

    ("body",
     "The project was driven by the common challenges buyers encounter when inspecting used "
     "cars. The buyer is presented with a folder of invoices and is asked to accept them as "
     "stated. If a major repair was performed poorly or if the odometer was rolled back to "
     "make the repair appear to have occurred at a lower mileage, the buyer has no practical "
     "way of detecting this before purchasing the vehicle. The same challenge impacts dealers "
     "evaluating trade-ins and insurers reviewing claims histories."),

    ("body",
     "An honest workshop is equally disadvantaged. A garage that meticulously documents its "
     "work and photographs replaced parts cannot prove the authenticity of its records, as a "
     "dishonest garage could easily create documents that appear identical. A mechanism that "
     "transforms meticulous documentation into verifiable evidence thereby rewards "
     "participants who exhibit good behavior."),

    ("body",
     "Finally, the recent availability of open-weight language models that can be adapted "
     "cost-effectively to narrow domains [10], [26], [27] makes it realistic for a student "
     "project to build a domain-specific diagnostic rather than merely propose one. "
     "Integrating this with cryptographic anchoring transforms a standard maintenance record "
     "into a document that can be verified by a third party."),

    ("h2", "1.3 Scope of the Project"),

    ("body", """The project delivers a functional prototype that spans the entire workflow from diagnostic input to buyer-facing verification. The system includes a workshop interface accepting VIN, vehicle details, diagnostic trouble codes, symptoms, sensor notes, and odometer readings; an AI diagnostic layer based on LoRA-adapted language models that provides structured diagnosis and repair data; off-chain evidence storage with hash and content identifier generation; construction of VIN-bound Proof-of-Repair leaves; Merkle-tree batching; a Solidity smart contract anchoring Merkle roots on an EVM-compatible chain; OpenTimestamps submission of those roots; a SQLite-backed VIN registry with a verification API."""),

    ("body", """Beyond the current scope are direct electronic data acquisition from OBD-II hardware installed in physical vehicles, integration with commercial workshop management systems, ingestion of verified commercial invoices, deployment to a public blockchain network in production, and the implementation of a production-grade identity, authentication, and access control framework. The evidence presented in the demonstrations is synthetic. The prototype is designed to demonstrate technical feasibility and reveal design trade-offs, rather than to function as a commercial vehicle history service."""),

    ("h1", "2. Project Description and Goals"),

    ("body", """This chapter surveys the existing research and engineering efforts that form the foundation of the project, pinpoints the specific gap it aims to fill, formally defines the problem and objectives, and outlines the strategy for executing the work."""),

    ("h2", "2.1 Literature Review"),

    ("body", """The literature relevant to this project can be broadly categorized into three largely independent areas: vehicle diagnosis and health monitoring, the efficient adaptation of large language models to specialized domains, and cryptographic integrity, provenance, and public anchoring. The review below is organized by theme rather than by individual paper, and concludes by explaining how these currents are integrated here."""),

    ("h3", "2.1.1 Information Asymmetry and Used-Vehicle History"),

    ("body", """The economic case for verifiable repair history is well established. Akerlof's analysis of markets where sellers possess superior knowledge of product quality reveals that the inability of buyers to distinguish between high and low-quality units leads to depressed prices and the exclusion of superior goods from the market [1]. Notheisen et al. This paper examines the problem in the context of used cars, arguing that a shared, tamper-resistant record of a vehicle's history reduces the uncertainty driving the market effect, using the automobile market as a motivating case for trust-free transaction systems [2]. These works motivate the objective of the present project but do not address how repair evidence is produced or how it is linked to a specific vehicle."""),

    ("h3", "2.1.2 On-Board Diagnostics and Fault Interpretation"),

    ("body", """Diagnostic trouble codes and the services used to retrieve them are standardized [29], [30], while vehicle identification numbers are standardized independently [28]. Because these identifiers are stable and machine-readable, they serve as natural keys for a repair registry. However, the standards define only the vocabulary and do not address the mapping from a code to a repair. In workshop practice, this mapping is heuristic, often specific to a particular model and engine family, and serves as a recurring cause of unnecessary component replacements."""),

    ("h3", "2.1.3 Data-Driven Vehicle and Machine Health"),

    ("body", """A significant amount of research addresses degradation and failure as prediction problems. The NASA C-MAPSS turbofan degradation simulation datasets, introduced by Saxena et al. [18] became the standard benchmark for remaining useful life estimation, and Lei et al. Survey the entire pipeline from data acquisition to remaining-useful-life prediction that has developed around such benchmarks [7]. In industrial applications, Matzka's AI4I 2020 dataset offers labeled failure modes encompassing tool wear, heat dissipation, power supply, and overstrain conditions, making it a widely adopted resource for explainable predictive maintenance studies [19]. Theissler and colleagues. This review focuses on predictive maintenance in the automotive industry, highlighting that the main challenges are the lack of labeled real-world failure data and the difficulty of transferring models across different vehicle fleets [8]. While this literature supports the health-related datasets used in this project with a focus on predicting future failures, the current work focuses on verifying repairs that have already been completed."""),

    ("h3", "2.1.4 Language Models for Structured Domain Reasoning"),

    ("body", """Transformer-based language models [13] have proven effective at transforming unstructured technical descriptions into structured outputs, especially when fine-tuned to match a specific response format [16]. Open toolchains like the Transformers library and PyTorch have made such adaptation routine. Two limitations are pertinent in this context. First, generated text may be fluent yet incorrect, as noted in the survey by Ji et al. Given that document hallucination is a persistent failure mode in natural language generation [9], the model outputs in this project are treated as assistive diagnostic suggestions rather than authoritative facts. Second, output format reliability is as critical as content accuracy in an automated pipeline, since the downstream hashing and commitment stage depends on parseable structured records. This is why JSON output validity is reported alongside fault-code accuracy in the evaluation."""),

    ("h3", "2.1.5 Parameter-Efficient Fine-Tuning"),

    ("body", """Full fine-tuning of a large model exceeds the resources available for a student project. Adapter-based transfer learning demonstrated that inserting a small number of trainable parameters into a frozen network can achieve performance comparable to full fine-tuning [11]. Low-Rank Adaptation (LoRA) refines this approach by freezing pre-trained weights and training low-rank update matrices, which drastically reduces the number of trainable parameters and storage requirements per task without increasing inference latency once merged [10]. QLoRA extends the approach to quantized backbones, enabling the adaptation of larger models on a single accelerator [12]. Compact open models like TinyLlama [26] and Mistral 7B [27] serve as appealing backbones for this type of adaptation, while the PEFT library [44] and the MLX framework for Apple silicon [45] render both approaches practical. The current project adheres precisely to this approach by adapting two open-source models for automotive diagnosis using LoRA, instead of training a model from scratch."""),

    ("h3", "2.1.6 Blockchain-Based Integrity and Provenance"),

    ("body", """Public blockchains offer an append-only ledger with no single point of control [23], while programmable chains expand this capability to include arbitrary state transitions defined by smart contracts [24], [22]. Field surveys outline both the capabilities and well-known limitations of on-chain storage, particularly its high costs and constrained throughput [6]. In the automotive sector specifically, Dorri et al. Propose a blockchain-based architecture for vehicular security and privacy, including maintenance and update records [3], and Cebe et al. We present Block4Forensic, a lightweight blockchain framework that leverages vehicle data and maintenance history to support forensic analysis following an incident [4]. These works demonstrate the feasibility of vehicle-related ledgers. However, they do not address the generation of the repair content itself, nor do they combine a domain-adapted diagnostic model with the attestation layer."""),

    ("h3", "2.1.7 Merkle Trees, Transparency Logs and Anchoring"),

    ("body", """The Merkle tree serves as the standard mechanism for summarizing numerous records with a single hash while preserving the ability to verify the membership of any individual record [20]. Certificate Transparency extends this construction to the internet scale to ensure certificate issuance is auditable, while precisely defining the log and proof structures [32], [33]. More recent standardization efforts by the IETF on supply-chain integrity and transparency extend this pattern to signed statements regarding artifacts and receipts generated by transparency services [34]. The properties of the underlying hash function used in all these constructions are defined in [31]. This body of work establishes the design pattern used here: commit numerous repair records into a tree, publish only the root, and maintain the ability to verify that a specific repair belongs to that root."""),

    ("h3", "2.1.8 Timestamping and Off-Chain Evidence"),

    ("body", """Haber and Stornetta demonstrated how documents can be timestamped to prove their existence at a specific moment without relying on the trustworthiness of the timestamping authority [5]. OpenTimestamps realizes this concept by leveraging the Bitcoin blockchain as an attestation mechanism, where numerous submissions are consolidated into one on-chain commitment, and receipts are initially marked as pending before being upgraded once the aggregating transaction is confirmed [35]. Regarding the evidence itself, content-addressed storage as described for IPFS identifies data by its cryptographic hash rather than by location, meaning a short identifier is sufficient to detect any modification of a large file [25]. Together, these two ideas enable bulky evidence to remain off-chain while keeping the on-chain footprint small."""),

    ("h3", "2.1.9 Synthesis"),

    ("body", """When these strands are combined, all the elements needed for a reliable repair record are already present in their individual forms: standardized vehicle and fault identifiers, efficient domain adaptation of language models, Merkle-based commitments, public anchoring with independent timestamping, and content-addressed evidence. What is comparatively rare is an end-to-end process where a diagnosis from a domain-adapted model, the subsequent repair, and the supporting evidence are cryptographically bound to a single vehicle identification number, publicly anchored, and then presented to a non-technical buyer as a readable timeline with a verification status. This project's contribution lies in constructing and evaluating that path. Table 1 summarizes the themes and their relevance."""),

    ("caption", "Table 1. Thematic summary of the reviewed literature and its relevance to the project"),

    ("table", [
        ["Theme", "Representative works", "Relevance to this project"],
        ["Used-vehicle information asymmetry", "[1], [2]", "Establishes the economic need for verifiable repair history"],
        ["OBD-II diagnostics and vehicle identifiers", "[28], [29], [30]", "Supplies the standard input vocabulary and the VIN key"],
        ["Vehicle and machine health analytics", "[7], [8], [18], [19]", "Source of degradation and failure-mode datasets used in training"],
        ["Language models and structured output", "[9], [13], [14], [15], [16]", "Basis of the diagnostic layer and of its reliability caveats"],
        ["Parameter-efficient fine-tuning", "[10], [11], [12], [26], [27]", "Method used to adapt open models to automotive diagnosis"],
        ["Blockchain integrity and vehicular ledgers", "[3], [4], [6], [22], [23], [24]", "Justifies on-chain anchoring and the smart-contract design"],
        ["Merkle trees and transparency logs", "[20], [31], [32], [33], [34]", "Provides the batching and membership-proof construction"],
        ["Timestamping and content-addressed storage", "[5], [25], [35]", "Enables off-chain evidence with independent timestamps"],
    ]),

    ("h2", "2.2 Research Gap"),

    ("body", """The reviewed work identifies a specific gap. Current research in automotive diagnostics primarily focuses on inferring faults and predicting remaining useful life, typically terminating once a diagnosis or prediction is generated, without addressing whether the resulting data can be trusted by third parties later. Current research on blockchain-based vehicular systems primarily focuses on ledger architecture, privacy, and forensic reconstruction, typically assuming that trustworthy repair content is available as an input without addressing how such content is generated or standardized. Work on transparency logs, Merkle anchoring, and timestamping is domain-neutral and provides mechanisms rather than applications."""),

    ("body", """Three additional specific shortfalls arise from this separation. First, few systems bind a diagnostic result, the repair performed in response to it, and the evidence of that repair to a single vehicle identifier within one cryptographic commitment; without this binding, an authentic invoice can be presented against the wrong vehicle. Second, the provenance of the diagnostic model itself is rarely recorded, meaning a stored diagnosis cannot later be linked to the specific model version that generated it. Third, the verification path is rarely designed for the actual end user, as proofs are described in developer-friendly terms rather than presented as a readable timeline with a clear verification status for a buyer standing in a forecourt."""),

    ("body", """This project bridges that gap by unifying AI-driven automotive diagnostics, evidence hashing, VIN binding, Merkle-proof construction, blockchain anchoring with independent timestamping, and buyer-facing verification into a single streamlined workflow."""),

    ("h2", "2.3 Objectives"),

    ("body", """The objectives of Project-I are listed below. Each is formulated so that its completion can be evaluated against an observable artifact in the implementation."""),

    ("num", """Create a VIN-bound repair attestation model where every sealed repair is linked to a single vehicle identification number and cannot be applied to another vehicle without being detected."""),
    ("num", """Integrate an AI diagnostic module that ingests diagnostic trouble codes, symptoms, sensor data, odometer readings, and vehicle specifications to deliver a structured diagnosis and prioritized repair plan in a machine-readable format."""),
    ("num", """Generate cryptographic commitments for repair evidence so that invoices, photographs, and reports are represented by digests and content identifiers instead of file copies."""),
    ("num", """Construct Merkle trees over batches of Proof-of-Repair leaves and generate membership proofs for individual repairs."""),
    ("num", """Anchor Merkle roots via an EVM-compatible smart contract that logs the root, batch identifier, timestamp, metadata reference, and submitting address, while preventing the re-anchoring of any root or batch that has already been recorded."""),
    ("num", """Support the submission of the same Merkle roots via OpenTimestamps to establish an independent timestamping path that does not rely on the EVM deployment."""),
    ("num", """Provide VIN-based verification for buyers, dealers, and insurers, which returns a repair timeline along with the anchoring and verification status of each event."""),
    ("num", """Evaluate the fine-tuned diagnostic models on a held-out set of real OBD cases, reporting both fault-code accuracy and structured-output validity."""),
    ("num", """Demonstrate the full workflow via a web interface, including workshop-side sealing and anchoring, as well as buyer-side lookup and verification."""),

    ("h2", "2.4 Problem Statement"),

    ("body", """A vehicle is identified by its vehicle identification number v, and throughout its lifetime, a series of repair events is carried out by one or more workshops. Each event generates descriptive content, including the diagnostic codes observed, the diagnosis reached, the work performed, and the odometer reading at the time, along with supporting evidence such as invoices, photographs, and technical reports. Currently, this information is stored as ordinary documents held by the workshop or the current owner."""),

    ("body", """The issue this project addresses is that parties who did not witness the repair—such as prospective buyers, dealers, or insurers—cannot verify whether the provided records are complete, accurately reflect the vehicle in question, have been altered after the fact, or were created at the correct time. Formally, given a repair record and its supporting evidence, there is no efficiently verifiable proof that the record was created before the transaction and remained unchanged, nor is there any binding link between the record and v that persists after the underlying documents are copied."""),

    ("h2", "3.2 Feasibility Study"),

    ("body", """Feasibility is evaluated based on the resources realistically available to a student project and the conditions that would apply if the prototype were later deployed in service."""),

    ("h3", "3.2.1 Technical Feasibility"),

    ("body", """Every component of the system is constructed using mature, openly available technology. Adapting language models using LoRA is a well-established approach that is deliberately efficient in terms of trainable parameters, and open-source backbones of appropriate sizes are readily available. The construction of Merkle trees and the implementation of the SHA-2 family of hash functions are both standardized and cost-effective when done correctly [20], [31]. EVM-compatible development environments enable developers to compile, test, and deploy Solidity contracts on a local chain before going live on a public network [39], [40]. The primary technical risks lie not within individual components but at their interfaces: the diagnostic model must generate output that parses reliably, as the commitment stage cannot hash unparsable records, and the canonical serialization used to construct a leaf must be standardized, since different serializations of the same repair would yield different digests and be mistaken for distinct records. Both risks are mitigated in the design by validating structured output before sealing and by establishing a single canonical leaf encoding."""),

    ("h3", "3.2.2 Economic Feasibility"),

    ("body", """Development expenses are minimal. The datasets are publicly available, the model is deliberately designed for parameter efficiency and can run on a single consumer accelerator or Apple Silicon, and all backend, database, and frontend components are open source. Operationally, the design minimizes recurring costs by anchoring a Merkle root for an entire batch instead of per transaction, which reduces the on-chain cost per repair as batch size grows, while keeping bulky evidence off-chain where storage is cheaper. OpenTimestamps aggregation provides independent timestamping at a negligible marginal cost [35]. The primary costs in a production deployment are not blockchain fees, but rather standard cloud hosting, secure evidence storage with durable backups, and the human resources required to onboard and verify workshops."""),

    ("h3", "3.2.3 Social Feasibility"),

    ("body", """Adoption relies on the incentives provided to the participants. Buyers and insurers benefit directly because they receive verifiable evidence they can review. Honest workshops can demonstrate the authenticity of their documentation, providing a competitive advantage. Workshops that depend on ambiguity have no incentive to participate, so the system must remain useful even with partial adoption: an unverified gap in a timeline is informative on its own, as long as the interface treats a lack of evidence as a lack of proof rather than as evidence of wrongdoing. Two issues need attention. The first principle is privacy: since repair history is tied to a vehicle and, by extension, its owners, the design ensures that personal data remains outside the committed leaf and any on-chain payload, publishing only digests instead. The second risk is that an AI-generated diagnosis may be treated as authoritative; since generative models can produce fluent yet incorrect outputs [9], the interface presents the diagnosis as an assistive suggestion linked to a specific model version, leaving the technician ultimately responsible for the repair actually performed."""),

    ("h2", "3.3 System Specification"),

    ("body", """The specification below outlines the environment in which the prototype was developed and where it can be replicated. It is defined as a class of machines rather than as a single fixed configuration."""),

    ("h1", "4. Design Approach and Details"),

    ("body", """This chapter outlines the system architecture, the design artifacts defining its behavior, the datasets and model development underpinning the diagnostic layer, the current implementation status along with preliminary results, and the remaining limitations."""),

    ("h2", "4.1 System Architecture"),

    ("body", """The architecture is organized as a pipeline of layers, as illustrated in Figure 2. Raw diagnostic data from the vehicle enters at the top and exits at the bottom as a verifiable timeline presented to the buyer. The color coding distinguishes the four types of components: ordinary off-chain cloud services, the AI diagnostic layer, storage, and the on-chain and public-timestamp layer."""),

    ("figure", ("figures/fig2_architecture.png", 5.70)),
    ("caption", "Fig. 2. System architecture of the cloud-based Proof-of-Repair system"),

    ("body", """The data input layer receives the VIN, vehicle details, diagnostic trouble codes, reported symptoms, sensor notes, and odometer reading via the workshop bay form, which then sends this information to the FastAPI backend. The AI diagnosis layer forwards this context to a LoRA-adapted language model, which returns a structured diagnosis including the identified fault, its likely cause, and a prioritized repair procedure. The repair attestation layer integrates the diagnosis with the technician's actual work, linking it to the vehicle identification number, odometer reading, workshop identity, and the provenance of the model that generated the diagnosis."""),

    ("body", """Evidence follows a separate path. Invoices, photographs, and reports are stored off-chain, while only a summary of the repair report and a content identifier for each evidence item proceed to the commitment stage. The Proof-of-Repair leaf is subsequently formed. Leaves are accumulated into a pending batch; once the batch is anchored, a Merkle tree is constructed over it and its root is submitted to both the smart contract and OpenTimestamps. The VIN registry stores repair events, leaves, batches, and anchoring metadata, and delivers them via the verification API to the buyer-facing interface."""),

    ("body", """It is important to emphasize the separation of responsibilities between the two main technologies, as this distinction is often unclear in descriptions of such systems. The language model interprets diagnostic data to generate structured repair instructions, yet it plays no role in security; if the model is compromised or erroneous, it will output a faulty diagnosis that the system will faithfully execute. The cryptographic and blockchain components ensure that committed records are tamper-evident, but they do not enhance diagnostic quality and cannot detect instances where a technician records a repair that never occurred. The combination provides a consistently structured record that, once sealed, cannot be altered without detection."""),

    ("h3", "4.1.1 The Proof-of-Repair Leaf"),

    ("body", """The leaf represents the unit of commitment. It is a canonical encoding of a small, fixed set of fields that collectively identify what was repaired, on which vehicle, at what stage in the vehicle's life, and based on what evidence. Table 7 lists the committed fields."""),

    ("caption", "Table 7. Fields committed in a buyer-facing Proof-of-Repair leaf"),

    ("table", [
        ["Field", "Description", "Why it is committed"],
        ["VIN", "Standard vehicle identification number of the repaired vehicle [28]", "Binds the repair to one vehicle so that a record cannot be presented against another"],
        ["Vehicle", "Make, model, year and related particulars", "Detects substitution of a different vehicle sharing a similar description"],
        ["Odometer", "Reading recorded at the time of the repair", "Fixes the point in the vehicle's life; a later inconsistent reading becomes visible"],
        ["Report hash", "Digest of the canonical repair report", "Any edit to the report changes the digest and breaks the proof"],
        ["Evidence CID", "Content identifier of the stored evidence [25]", "Detects modification or substitution of invoices, photographs or reports"],
        ["Model provenance", "Identifier of the diagnostic model and adapter used", "Allows a stored diagnosis to be attributed to the model version that produced it"],
    ]),

    ("body", """Because the leaf commits only to a digest of the report and a content identifier of the evidence rather than to the documents themselves, it remains small and contains no personal data while still being sufficient to detect any changes to the underlying material."""),

    ("h3", "4.1.2 Merkle Tree and Root"),

    ("body", """Individual leaves are paired and hashed sequentially using a cryptographic hash function until only a single value, known as the Merkle root, remains [20], [31]. The root serves as a compact commitment to the entire batch, representing a fixed-size value that remains constant regardless of the number of repairs contained within. Two features make this construction particularly useful in this context. First, modifying any committed repair or evidence file alters the corresponding leaf digest, which cascades through every internal node on the path to the root, thereby changing the root; because the root was previously published, this alteration is detectable. Second, membership of a single repair can be verified without revealing the rest of the batch by providing only the sibling hashes along the path from that leaf to the root. A verifier independently recalculates the leaf from the provided record, applies the given path, and verifies that the resulting root matches the anchored root. This is the same construction that underlies transparency logs [32], [33]."""),

    ("h3", "4.1.3 Smart Contract and On-Chain Anchoring"),

    ("body", """The Solidity contract is located in the contracts/ProofOfRepair directory. Sol anchors the Merkle roots of batched, VIN-bound Proof-of-Repair records on an EVM-compatible chain [21], [22], [37]. Its state and operations are summarized in Table 8. Only roots and small metadata references are stored on-chain, while invoices, photographs, and reports are never."""),

    ("caption", "Table 8. On-chain anchor record and contract operations"),

    ("table", [
        ["Element", "Kind", "Description"],
        ["Merkle root", "Stored value", "Commitment to the batch of Proof-of-Repair leaves"],
        ["Timestamp", "Stored value", "Block time at which the root was anchored"],
        ["Batch identifier", "Stored value", "Identifier of the batch to which the root corresponds"],
        ["Metadata URI", "Stored value", "Reference to off-chain metadata describing the batch"],
        ["Submitting address", "Stored value", "Account that submitted the anchor, establishing who made the claim"],
        ["Anchor a Merkle root", "Operation", "Records a new root together with its batch identifier and metadata reference"],
        ["Check whether a root is anchored", "Operation", "Returns whether a given root has already been committed"],
        ["Retrieve anchor information", "Operation", "Returns the stored record associated with a root"],
        ["Prevent reuse", "Operation", "Rejects an attempt to anchor a root or batch identifier that has already been recorded"],
    ]),

    ("body", """The current implementation is designed to operate on a local Hardhat development network [40]. This is sufficient to exercise the full anchoring path, including transaction submission, event handling, and the rejection of duplicate roots, but it is not a public deployment: a root anchored on a local chain is only as persistent as that local chain. Deployment to a public testnet or main network is considered an optional subsequent step and is included in the future work section."""),

    ("h3", "4.1.4 OpenTimestamps"),

    ("body", """OpenTimestamps offers an independent timestamping path for the identical Merkle root [5], [35]. It is not a duplicate of the EVM anchor and should not be mistaken for one; instead, submissions are aggregated by public calendar servers into a commitment that is later included in the Bitcoin blockchain, while the receipt sent to the submitter remains pending until the aggregating transaction is confirmed, at which point it becomes a complete proof. The value of this second path lies in the redundancy of trust. If the EVM deployment used for anchoring were abandoned or its history disputed, the OpenTimestamps receipt would still demonstrate that the root existed at the recorded time, and vice versa."""),

    ("h3", "4.1.5 Off-Chain Evidence and Storage"),

    ("body", """Raw evidence remains stored off-chain in the evidence store under the artifacts/evidence/ directory and is represented in the commitment solely through digests and content identifiers [25]. Four factors motivate this. Storing files on a public blockchain would be prohibitively expensive and would waste shared capacity for data relevant only to a small number of parties. The limited throughput of the ledger constrains scalability, as bulky payloads exacerbate this issue [6]. Publishing invoices and photographs on an immutable public ledger would permanently expose commercially and personally sensitive information. Finally, no integrity is compromised by storing them off-chain, as comparing the digest of a retrieved file with the committed one detects any modifications."""),

    ("body", """The application state is stored in a SQLite database located at artifacts/por_registry. Sqlite3 [43], which stores repair records, leaves, batches, roots, and anchoring metadata. SQLite is well-suited for a prototype because it eliminates the need for a separate server process, stores the entire registry in a single portable file, and allows the system to be easily reproduced from a fresh checkout. Its limitations are equally evident: it is not designed to handle many concurrent writers distributed across multiple application instances. A production deployment would migrate the registry to a networked relational database and the evidence store to durable object storage without altering the proof structure, as neither the leaf encoding nor the anchoring path relies on the specific database choice."""),

    ("h3", "4.1.6 Backend and Frontend"),

    ("body", """The backend is a Python service exposed via FastAPI and served by Uvicorn. Cloud. Api:app [41], [42]. It links the web interface to the diagnostic model, evidence store, proof generator, registry, and anchoring path, while exposing the verification route GET /api/vin/{vin} that returns the repair timeline for a vehicle. The frontend, hosted locally at http://127. 0. 0. 1:8000, serves as the workshop bay for entering diagnostic context, diagnosing and sealing repairs by VIN, anchoring pending batches, verifying the final proof, and accessing buyer and dealer lookup views."""),

    ("h2", "4.2 Design"),

    ("body", """The design is documented using a context and level-1 data flow diagram, a use-case diagram, a conceptual class model, and two sequence diagrams that cover the sealing and verification processes."""),

    ("h3", "4.2.1 Data Flow Diagram"),

    ("body", """Figure 3 presents the context diagram. The system operates as a single process that exchanges data with three external entities: the workshop submitting diagnostic and repair details, the buyer, dealer, or insurer providing a VIN and receiving a verified timeline, and the external blockchain and timestamping services that accept Merkle roots and issue receipts."""),

    ("figure", ("figures/fig3_dfd0.png", 6.10)),
    ("caption", "Fig. 3. Level-0 (context) data flow diagram"),

    ("figure", ("figures/fig4_dfd1.png", 6.00)),
    ("caption", "Fig. 4. Level-1 data flow diagram of the Proof-of-Repair system"),

    ("body", """The diagram clearly delineates the boundary between on-chain and off-chain operations. Only the data flow between process 4. 0 and the external chain crosses the boundary, carrying exclusively the root, batch identifier, and metadata reference, while all other flows, including evidence, remain contained within the system."""),

    ("h3", "4.2.2 Use Case Diagram"),

    ("body", """Figure 5 displays the actors and the use cases they trigger. The workshop or mechanic submits vehicle details and diagnostic trouble codes, documents repairs with supporting evidence, seals the repairs to a specific VIN, and secures pending batches. Buyers, dealers, and insurers share the same two verification use cases because their needs differ in purpose rather than in operation. A system administrator is responsible for managing workshop accounts and the keys used for anchoring."""),

    ("figure", ("figures/fig5_usecase.png", 5.90)),
    ("caption", "Fig. 5. Use case diagram"),

    ("body", """Three inclusion relationships are depicted. Submitting vehicle details involves running an AI diagnosis, as submissions without a diagnosis cannot be sealed; recording a repair entails generating the evidence hash and content identifier; and sealing a repair requires constructing the Merkle tree entry that will later be included in the batch."""),

    ("h3", "4.2.3 Class Diagram"),

    ("body", """Figure 6 illustrates a conceptual class and data model instead of a direct copy of the implementation classes. It describes the entities the system reasons about and their relationships, while the running code organizes some of these as modules, tables, or serialized records instead of as classes with exactly those names."""),

    ("figure", ("figures/fig6_class.png", 6.10)),
    ("caption", "Fig. 6. Conceptual class and data model"),

    ("body", """A vehicle, uniquely identified by its VIN, is associated with multiple repair records. Each RepairRecord is generated with the help of a single DiagnosticResult, which includes the diagnostic codes, the likely cause, the ranked repair options, and the model that produced it. Each RepairRecord is committed as a single ProofLeaf, which references the Evidence items via their content identifiers. Leaves are grouped into a MerkleTree to generate a root, which is then anchored by a single MerkleAnchor containing the transaction reference, the metadata URI, the OpenTimestamps receipt, and the anchoring timestamp. The VINRegistry indexes repair events and anchors to enable VIN-based lookups that assemble the timeline and verify each entry, while the Workshop entity records who sealed the repair and under which signing address."""),

    ("h3", "4.2.4 Sequence Diagram"),

    ("body", """Figure 7 illustrates the workshop journey. The mechanic initiates the diagnostic process within the workshop bay, prompting the backend to request a diagnosis from the LoRA-adapted model, store the resulting evidence along with its content identifier, and instruct the proof generator to create a VIN-bound leaf that is then persisted alongside the repair event. In the second phase, the mechanic requests that the pending batch be anchored by assembling the Merkle tree, submitting its root to both the smart contract and OpenTimestamps, and then storing the resulting anchor record and receipts."""),

    ("figure", ("figures/fig7_seq_seal.png", 6.10)),
    ("caption", "Fig. 7. Sequence diagram for diagnosis, sealing and batch anchoring"),

    ("figure", ("figures/fig8_seq_verify.png", 6.10)),
    ("caption", "Fig. 8. Sequence diagram for VIN-based buyer verification"),

    ("body", """The comparison step is where the guarantee is actually delivered. If a repair report or evidence file is modified after sealing, the recomputed leaf and root will differ, and the resulting mismatch with the anchored root will be reported to the user."""),

    ("h2", "4.3 Dataset Description and Model Development"),

    ("body", """The diagnostic layer is trained and evaluated using a documented collection of automotive and machine-health datasets, which are stored in the repository along with a dataset manifest. Their roles are summarized in Table 9."""),

    ("caption", "Table 9. Datasets documented in the project repository"),

    ("table", [
        ["Dataset", "Role in the project"],
        ["MechanicDB OBD-II repair sample", "Real diagnostic trouble codes mapped to ranked repair procedures with labour and parts information"],
        ["Automotive DTC fine-tuning dataset", "Instruction-response pairs for supervised fine-tuning of automotive diagnosis"],
        ["NHTSA ODI complaints [36]", "Real vehicle-owner complaints for popular used models, providing natural symptom language"],
        ["NASA C-MAPSS FD001-FD004 [18], [37]", "Engine degradation trajectories and remaining useful life information for powertrain health context"],
        ["UCI AI4I 2020 [19], [38]", "Labelled failure modes covering tool wear, heat dissipation, power and overstrain conditions"],
    ]),

    ("body", """Model development employs parameter-efficient LoRA fine-tuning instead of full fine-tuning, ensuring that adaptation stays within the project's compute budget and the resulting adapters remain compact enough to be stored and versioned alongside the code [10], [44]. Two model paths are documented. The first approach adapts TinyLlama using an automotive and DTC-focused LoRA adapter [26]. The second approach adapts a 4-bit Mistral model using the MLX framework on Apple silicon [27], [45], following the quantized adaptation method [12]. Both paths are trained to output structured JSON diagnoses because the downstream commitment stage requires a parseable record, and the provenance of the model that generated a diagnosis is logged in the corresponding Proof-of-Repair leaf."""),

    ("h2", "4.4 Implementation Status and Preliminary Results"),

    ("body", """The diagnostic models were evaluated using a real-world OBD hold-out set comprising 57 cases. Two metrics are reported: fault-code accuracy, defined as the proportion of cases where the model correctly identified the fault code, and JSON output accuracy, defined as the proportion of responses that were emitted as valid structured records suitable for downstream processing. The results documented in the repository are presented in Table 10."""),

    ("caption", "Table 10. Diagnostic model evaluation results reported in the project repository"),

    ("table", [
        ["Model", "Evaluation set", "Fault-code accuracy", "JSON output accuracy"],
        ["TinyLlama with automotive LoRA", "Real OBD hold-out, n = 57", "93.0%", "100%"],
        ["Mistral 4-bit / MLX with LoRA", "Real OBD hold-out, n = 57", "98.3%", "98.3%"],
    ]),

    ("body", """These results, documented in the project repository from the fine-tuning experiments described above, were not regenerated for this report. Two observations follow. The Mistral path achieves higher fault-code accuracy, consistent with its larger backbone. While the TinyLlama path achieves perfect structured-output validity, the Mistral path does not; consequently, for any pipeline that must hash the output, an occasional unparsable response represents a genuine operational cost rather than a mere rounding error, as such a response must be rejected and regenerated before a repair can be finalized. Given the small size of the hold-out set, which contains only 57 cases, these figures should be interpreted as indicative of feasibility rather than as a precise measure of accuracy."""),

    ("body", """Table 11 summarizes the implementation status of each component. The distinction lies between what is deployed in the repository and what has been fully validated end-to-end in the author's local environment."""),

    ("caption", "Table 11. Implementation status of the system components"),

    ("table", [
        ["Component", "Status", "Notes"],
        ["Project architecture and datasets", "Implemented", "Layered design and dataset manifest documented"],
        ["LoRA fine-tuning pipeline", "Implemented", "Two documented model paths with reported evaluation results"],
        ["DTC diagnosis workflow", "Implemented", "Structured diagnosis produced from the submitted context"],
        ["Repair-proof data structure", "Implemented", "Canonical leaf over VIN, vehicle, odometer, report hash, CID and provenance"],
        ["Evidence hashing and content identifiers", "Implemented", "Evidence retained off-chain under artifacts/evidence/"],
        ["Merkle tree and proof mechanism", "Implemented", "Batch root construction and membership proofs"],
        ["Solidity smart contract", "Implemented", "contracts/ProofOfRepair.sol anchoring and duplicate rejection"],
        ["EVM integration", "Local only", "Exercised on a local Hardhat chain; no public deployment"],
        ["OpenTimestamps integration", "Implemented", "Receipts stored; Bitcoin inclusion is pending until confirmation"],
        ["VIN registry and verification API", "Implemented", "SQLite registry with GET /api/vin/{vin}"],
        ["Frontend web interface", "Implemented", "Loads successfully and reaches the backend in local testing"],
        ["Local AI inference on a fresh checkout", "Not validated locally", "Sealing returned a missing-adapter error because the trained adapter artefact was absent from the local copy"],
        ["Physical OBD-II hardware integration", "Not implemented", "Diagnostic context is entered manually in the prototype"],
        ["Production cloud deployment", "Not implemented", "Future work"],
    ]),

    ("body", """One point in Table 11 warrants explanation. During local testing, the frontend loaded correctly and the backend was accessible, but invoking the seal action resulted in a diagnosis failure indicating that the TinyLlama adapter was missing from the expected adapter path. This represents a deployment condition specific to that particular working copy, where a trained adapter artifact was not fetched into the artifacts/adapters/ directory, rather than a defect within the diagnostic pipeline or the attestation layer, both of which are implemented in the repository and were evaluated as reported in Table 10. The conclusion of this report is limited: the entire workflow, including live AI inference, has not been demonstrated end-to-end on that machine, and no contradictory claim is made here."""),

    ("h2", "4.5 Limitations and Future Work"),

    ("body", """As a research prototype, the system has limitations that must be clearly stated."""),

    ("bullet", """Deployment completeness was not achieved because the trained adapter artifact was missing from the local working copy, preventing end-to-end live AI inference in that environment."""),
    ("bullet", """No physical OBD-II integration is present; diagnostic data is entered manually instead of being read from a scan tool connected to a vehicle, meaning no measurements in the prototype are machine-verified at the time of capture."""),
    ("bullet", """The evidence used in the demonstrations consists of prototypes and synthetic data; no verified commercial workshop invoices have been ingested, and no workshop partnerships have been established."""),
    ("bullet", """Local blockchain only: anchoring is performed on a local EVM development chain, meaning the persistence and public verifiability offered by a production deployment are not yet available."""),
    ("bullet", """The validation scale employs a hold-out set of 57 real OBD cases, which is sufficient to demonstrate feasibility but inadequate for characterizing behavior across manufacturers, model years, and fault families."""),
    ("bullet", """Diagnostic reliability is compromised because generative models can generate fluent yet incorrect diagnoses, and while cryptographic anchoring ensures records are tamper-evident, the system still commits whatever is recorded, rendering the anchoring ineffective for guaranteeing truth."""),
    ("bullet", """Data quality is limited because the training data comes from public datasets that have uneven coverage across manufacturers and fault types."""),
    ("bullet", """Privacy: A VIN-linked repair history is indirectly tied to vehicle owners; while the design ensures personal data remains out of committed leaves and off-chain payloads, a deployed service would require a carefully considered policy regarding data retention and disclosure."""),
    ("bullet", """Identity and access control: the prototype lacks a production-grade scheme for verifying a workshop's identity and does not implement a full role-based access control model."""),
    ("bullet", """SQLite and a local evidence directory are suitable for a prototype but not for concurrent multi-tenant operations."""),

    ("body", """The corresponding future work follows directly from these limitations. The most immediate steps are to package the trained adapters so that a fresh checkout can run inference without manual retrieval, and to deploy the anchoring contract to a public testnet so that roots become independently verifiable outside the development environment. Furthermore, sourcing data directly from OBD-II hardware would eliminate manual entry from the capture process; collaborating with workshops and incorporating verified digital invoices would substitute synthetic evidence; and transitioning to a managed database and object storage system would enable concurrent usage."""),

    ("body", """From a diagnostic perspective, the most impactful improvement is expanding and diversifying the training and evaluation datasets, followed by anchoring the model's outputs in retrieved service documentation to enable diagnoses to cite their sources, similar to retrieval-augmented generation [17]. On the verification side, a mobile or QR-based lookup would enable buyers to check a vehicle at the point of inspection, while automatically updating OpenTimestamps receipts once Bitcoin inclusion is confirmed would allow the interface to distinguish between a pending timestamp and a completed one. Finally, workshop identity, role-based access control, monitoring, and key management must all be implemented before the system can be operated as a service instead of merely demonstrated as a prototype."""),

    ("pagebreak", None),

    ("h1", "5. References"),

    ("refgroup", 'Journals'),
    ("ref", ['1', 'G. A. Akerlof, “The market for lemons: Quality uncertainty and the market mechanism,” The Quarterly Journal of Economics, vol. 84, no. 3, pp. 488–500, 1970.']),
    ("ref", ['2', 'B. Notheisen, J. B. Cholewa, and A. P. Shanmugam, “Trading real-world assets on blockchain: An application of trust-free transaction systems in the market for lemons,” Business & Information Systems Engineering, vol. 59, no. 6, pp. 425–440, 2017.']),
    ("ref", ['3', 'A. Dorri, M. Steger, S. S. Kanhere, and R. Jurdak, “BlockChain: A distributed solution to automotive security and privacy,” IEEE Communications Magazine, vol. 55, no. 12, pp. 119–125, 2017.']),
    ("ref", ['4', 'M. Cebe, E. Erdin, K. Akkaya, H. Aksu, and S. Uluagac, “Block4Forensic: An integrated lightweight blockchain framework for forensics applications of connected vehicles,” IEEE Communications Magazine, vol. 56, no. 10, pp. 50–57, 2018.']),
    ("ref", ['5', 'S. Haber and W. S. Stornetta, “How to time-stamp a digital document,” Journal of Cryptology, vol. 3, no. 2, pp. 99–111, 1991.']),
    ("ref", ['6', 'Z. Zheng, S. Xie, H.-N. Dai, X. Chen, and H. Wang, “Blockchain challenges and opportunities: A survey,” International Journal of Web and Grid Services, vol. 14, no. 4, pp. 352–375, 2018.']),
    ("ref", ['7', 'Y. Lei, N. Li, L. Guo, N. Li, T. Yan, and J. Lin, “Machinery health prognostics: A systematic review from data acquisition to RUL prediction,” Mechanical Systems and Signal Processing, vol. 104, pp. 799–834, 2018.']),
    ("ref", ['8', 'A. Theissler, J. Pérez-Velázquez, M. Kettelgerdes, and G. Elger, “Predictive maintenance enabled by machine learning: Use cases and challenges in the automotive industry,” Reliability Engineering & System Safety, vol. 215, art. 107864, 2021.']),
    ("ref", ['9', 'Z. Ji, N. Lee, R. Frieske, T. Yu, D. Su, Y. Xu, E. Ishii, Y. J. Bang, A. Madotto, and P. Fung, “Survey of hallucination in natural language generation,” ACM Computing Surveys, vol. 55, no. 12, pp. 1–38, 2023.']),

    ("refgroup", 'Conferences'),
    ("ref", ['10', 'E. J. Hu, Y. Shen, P. Wallis, Z. Allen-Zhu, Y. Li, S. Wang, L. Wang, and W. Chen, “LoRA: Low-rank adaptation of large language models,” in Proc. International Conference on Learning Representations (ICLR), 2022.']),
    ("ref", ['11', 'N. Houlsby, A. Giurgiu, S. Jastrzebski, B. Morrone, Q. de Laroussilhe, A. Gesmundo, M. Attariyan, and S. Gelly, “Parameter-efficient transfer learning for NLP,” in Proc. 36th International Conference on Machine Learning (ICML), 2019, pp. 2790–2799.']),
    ("ref", ['12', 'T. Dettmers, A. Pagnoni, A. Holtzman, and L. Zettlemoyer, “QLoRA: Efficient finetuning of quantized LLMs,” in Advances in Neural Information Processing Systems (NeurIPS), 2023.']),
    ("ref", ['13', 'A. Vaswani, N. Shazeer, N. Parmar, J. Uszkoreit, L. Jones, A. N. Gomez, L. Kaiser, and I. Polosukhin, “Attention is all you need,” in Advances in Neural Information Processing Systems (NIPS), 2017, pp. 5998–6008.']),
    ("ref", ['14', 'T. Wolf et al., “Transformers: State-of-the-art natural language processing,” in Proc. Conference on Empirical Methods in Natural Language Processing: System Demonstrations (EMNLP), 2020, pp. 38–45.']),
    ("ref", ['15', 'A. Paszke et al., “PyTorch: An imperative style, high-performance deep learning library,” in Advances in Neural Information Processing Systems (NeurIPS), 2019, pp. 8026–8037.']),
    ("ref", ['16', 'L. Ouyang et al., “Training language models to follow instructions with human feedback,” in Advances in Neural Information Processing Systems (NeurIPS), 2022.']),
    ("ref", ['17', 'P. Lewis et al., “Retrieval-augmented generation for knowledge-intensive NLP tasks,” in Advances in Neural Information Processing Systems (NeurIPS), 2020.']),
    ("ref", ['18', 'A. Saxena, K. Goebel, D. Simon, and N. Eklund, “Damage propagation modeling for aircraft engine run-to-failure simulation,” in Proc. International Conference on Prognostics and Health Management (PHM), 2008, pp. 1–9.']),
    ("ref", ['19', 'S. Matzka, “Explainable artificial intelligence for predictive maintenance applications,” in Proc. 3rd International Conference on Artificial Intelligence for Industries (AI4I), 2020, pp. 69–74.']),
    ("ref", ['20', 'R. C. Merkle, “A digital signature based on a conventional encryption function,” in Advances in Cryptology — CRYPTO ’87, Lecture Notes in Computer Science, vol. 293, Springer, 1988, pp. 369–378.']),

    ("refgroup", 'Books'),
    ("ref", ['21', 'A. Narayanan, J. Bonneau, E. Felten, A. Miller, and S. Goldfeder, Bitcoin and Cryptocurrency Technologies: A Comprehensive Introduction. Princeton, NJ: Princeton University Press, 2016.']),
    ("ref", ['22', 'A. M. Antonopoulos and G. Wood, Mastering Ethereum: Building Smart Contracts and DApps. Sebastopol, CA: O’Reilly Media, 2018.']),

    ("refgroup", 'Standards, Specifications and Technical Reports'),
    ("ref", ['23', 'S. Nakamoto, “Bitcoin: A peer-to-peer electronic cash system,” white paper, 2008.']),
    ("ref", ['24', 'G. Wood, “Ethereum: A secure decentralised generalised transaction ledger,” Ethereum Project Yellow Paper, 2014.']),
    ("ref", ['25', 'J. Benet, “IPFS — Content addressed, versioned, P2P file system,” arXiv preprint arXiv:1407.3561, 2014.']),
    ("ref", ['26', 'P. Zhang, G. Zeng, T. Wang, and W. Lu, “TinyLlama: An open-source small language model,” arXiv preprint arXiv:2401.02385, 2024.']),
    ("ref", ['27', 'A. Q. Jiang et al., “Mistral 7B,” arXiv preprint arXiv:2310.06825, 2023.']),
    ("ref", ['28', 'ISO 3779:2009, Road vehicles — Vehicle identification number (VIN) — Content and structure, International Organization for Standardization, Geneva, Switzerland.']),
    ("ref", ['29', 'ISO 15031-5:2015, Road vehicles — Communication between vehicle and external equipment for emissions-related diagnostics — Part 5: Emissions-related diagnostic services, International Organization for Standardization, Geneva, Switzerland.']),
    ("ref", ['30', 'SAE J1979, E/E Diagnostic Test Modes, SAE International, Warrendale, PA.']),
    ("ref", ['31', 'Secure Hash Standard (SHS), FIPS PUB 180-4, National Institute of Standards and Technology, Gaithersburg, MD, 2015.']),
    ("ref", ['32', 'B. Laurie, A. Langley, and E. Kasper, “Certificate Transparency,” RFC 6962, Internet Engineering Task Force, 2013.']),
    ("ref", ['33', 'B. Laurie, E. Messeri, and R. Stradling, “Certificate Transparency version 2.0,” RFC 9162, Internet Engineering Task Force, 2021.']),
    ("ref", ['34', 'IETF Supply Chain Integrity, Transparency and Trust (SCITT) Working Group, “An architecture for trustworthy and transparent digital supply chains,” Internet-Draft, work in progress.']),

    ("refgroup", 'Web and Official Technical Sources'),
    ("ref", ['35', 'P. Todd, “OpenTimestamps: Scalable, trustless, distributed timestamping with Bitcoin.” [Online]. Available: https://opentimestamps.org']),
    ("ref", ['36', 'National Highway Traffic Safety Administration, “Office of Defects Investigation (ODI) complaints database.” [Online]. Available: https://www.nhtsa.gov']),
    ("ref", ['37', 'NASA Prognostics Center of Excellence, “Turbofan engine degradation simulation data set (C-MAPSS),” NASA Prognostics Data Repository, NASA Ames Research Center, Moffett Field, CA.']),
    ("ref", ['38', 'S. Matzka, “AI4I 2020 predictive maintenance dataset,” UCI Machine Learning Repository, 2020. [Online]. Available: https://archive.ics.uci.edu']),
    ("ref", ['39', 'Ethereum Foundation, “Solidity documentation.” [Online]. Available: https://docs.soliditylang.org']),
    ("ref", ['40', 'Nomic Foundation, “Hardhat: Ethereum development environment.” [Online]. Available: https://hardhat.org']),
    ("ref", ['41', 'S. Ramírez, “FastAPI documentation.” [Online]. Available: https://fastapi.tiangolo.com']),
    ("ref", ['42', 'Encode, “Uvicorn: An ASGI web server implementation for Python.” [Online]. Available: https://www.uvicorn.org']),
    ("ref", ['43', 'SQLite, “SQLite documentation.” [Online]. Available: https://www.sqlite.org/docs.html']),
    ("ref", ['44', 'Hugging Face, “PEFT: Parameter-efficient fine-tuning.” [Online]. Available: https://huggingface.co/docs/peft']),
    ("ref", ['45', 'Apple, “MLX: An array framework for Apple silicon.” [Online]. Available: https://github.com/ml-explore/mlx']),
]
