#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the 6-7 page conference paper from the full report.

Reads report_humanized/Proof_of_Repair_IEEE_v2.docx (the full 12-page report,
which is left untouched) and writes Proof_of_Repair_Conference.docx with:

  1 Introduction            new text (S1)
  2 Related Work            new text (S2), replacing 2.1-2.1.9 and 2.2
  3 System Design           former 4.1.x, renumbered
  4 Attestation Algorithm   former 4.2.3, promoted
  5 Evaluation              former 4.3/4.4/4.4.1/4.4.2, case study trimmed
  6 Limitations             new text (S3)
  7 Conclusion              new text (S4)
  References                on a page of their own

Deleted: 1.1-1.3, 2.3, 2.4, 3.2.x, 3.3, 4.1.6, 4.2, 4.2.1, 4.2.2, 4.3's dataset
paragraph, Tables 1 and 9, and the case study's first three paragraphs (the
odometer-fraud framing now lives in the introduction).
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

SRC = "/Users/shivansh/Desktop/proof of repair/report_humanized/Proof_of_Repair_IEEE_v2.docx"
DST = "/Users/shivansh/Desktop/proof of repair/report_humanized/Proof_of_Repair_Conference.docx"

CORRECTIONS = [
    "S1: run-on before 'Akerlof' split; 'adaption' -> 'adaptation'; stray space before comma",
    "S1: 'guarantyd' -> 'guaranteed'; 'are detected each' -> 'are each detected'",
    "S1: first person 'In this paper we describe ... we contribute' made impersonal",
    "S1: closing sentence was garbled ('what the system provides is a stranger can verify')",
    "S2: opening was 'four bodies of work crossing ... none crossing it'",
    "S2: 'Telemetry or ownership anchors vehicular ledgers' - subject and object inverted",
    "S2: 'The text generation of the diagnostic systems is indifferent to its custody' restored",
    "S2: citation style [13, 14, 15] -> [13], [14], [15]; missing full stop after 'affordable'",
    "S2: 'allows to prove' / 'allows to keep' corrected",
    "S3: 'Anchors to a local development chain' had no subject",
    "S3: future work claimed a larger corpus EXISTS; restored as work still to do",
    "S4: 'If you can't check' second person removed; 'guaranty' -> 'guarantee'",
    "S5: missing full stop; 'which is to nothing that was anchored'; stray spaces; 'can not'",
]

# --------------------------------------------------------------------------- text

INTRO = [
    "Used cars are sold on the basis of documents that cannot be checked. A buyer gets a folder of "
    "invoices, a stamped service book and a printed job card, and is asked to accept that the work "
    "described was done, on this vehicle, at the mileage shown. None of these documents have any "
    "evidence of when it was created or if it has been altered since, and the records that would "
    "contradict them can simply be withheld. Akerlof described this asymmetry as the condition for "
    "markets in goods of uncertain quality [1], and it is still not solved in practice [2].",

    "The price is reflected in odometer tampering. In December 2025, 2.45 million cars on U.S. roads "
    "had odometers which had been rolled back, a 14 percent increase in one year, and buyers of "
    "these cars lost an average of $3,300 each, according to CARFAX estimates [47]. The national "
    "regulator estimates that around 450,000 vehicles are sold each year with faked readings [48]. "
    "Digital instrument clusters can be rewritten with cheap tools, so the falsification leaves no "
    "trace on the instrument that it falsifies [47]. Detection therefore has to come from records "
    "outside the vehicle, and those records are precisely what cannot be trusted at present.",

    "There are two capabilities, and the common mistake is that of confusing the two. The first is "
    "interpretation: taking diagnostic trouble codes, symptoms and sensor observations and turning "
    "them into a structured statement of what is wrong and what needs to be done [29], [30]. The "
    "second is integrity. Once a repair has been sealed, the garage that made it and anyone who "
    "works on it afterward cannot change the record or the evidence that supports it without notice. "
    "The first is a language problem, solved here with a model adapted by low-rank adaptation [10]. "
    "The second is a cryptographic problem, solved using content-addressed evidence, Merkle "
    "commitments [20] and public anchoring [23], [35].",

    "This paper describes a prototype that joins them, and contributes four things. A canonical "
    "Proof-of-Repair leaf hashes together a vehicle identification number, odometer reading, report "
    "digest, evidence identifier and model provenance. A batching path pins those leaves to an EVM "
    "contract and separately to a public time-stamping service. A diagnostic layer for automotive "
    "fault codes is evaluated over real OBD cases, including the failure conditions. Finally, a "
    "demonstration run against the implementation shows that an odometer rollback, an invoice "
    "substitution and the reuse of a record across vehicles are each detected.",

    "The role segregation continues to hold. The model returns records that are not guaranteed to be "
    "accurate. The cryptographic layer does not judge whether the records were right, but makes it "
    "impossible to modify the records after they have been sealed. What the system provides is a "
    "repair history a stranger can verify, not a diagnosis a stranger should trust.",
]

RELATED = [
    "Four bodies of work meet in this problem, and none of them spans it.",

    "The economic case is settled. Akerlof showed that when buyers cannot distinguish the quality, "
    "price tends to the average and honest sellers exit [1]. This argument has been extended to "
    "vehicle markets and trust-free transaction systems [2]. But what the literature lacks is a "
    "mechanism for generating evidence that a buyer can actually verify.",

    "The input vocabulary is vehicle diagnosis. Diagnostic services and trouble codes are "
    "standardized [29], [30], as are vehicle identification numbers [28]. This gives any system a "
    "stable key and a shared fault language. This is extended to prognosis by data-driven work on "
    "run-to-failure datasets and remaining-life estimation [18], [19], with wider surveys of "
    "machinery health and automotive predictive maintenance [7], [8]. That work stops at the "
    "inference; what happens to the inference after that is out of its scope.",

    "The interpretation is provided by language models. Transformer architectures transform "
    "unstructured technical description to structured output [13], [14], [15], and instruction "
    "tuning improves adherence to a requested form [16]. The known weakness is reliability. Fluent "
    "output that is incorrect is a documented failure mode [9], so any system that commits model "
    "output must treat the commitment and the correctness as separate claims. Adapter layers [11], "
    "low-rank adaptation [10] and quantized adaptation [12] train a small set of parameters against "
    "a frozen backbone, making adaptation affordable. Open-weight models of modest size [26], [27] "
    "put this within reach of ordinary hardware.",

    "Integrity adds the missing ingredient. Public ledgers provide an append-only state with no "
    "single controller [23], programmable chains extend this to arbitrary state transitions defined "
    "in code [24], and vehicular proposals apply to telemetry, forensics and ownership [3], [4], "
    "[6], [22]. Merkle trees offer a summary of many records in a single hash while preserving "
    "membership proofs [20], [31], the construction underlying certificate transparency [32], [33] "
    "and supply-chain transparency work [34]. Timestamping makes it possible to prove the existence "
    "of a document at a certain point in time without trusting the timestamping party [5], [35], and "
    "content addressing allows the evidence to stay off-chain but still tamper-evident [25].",

    "The gap is the seam, not any individual part. Diagnostic systems generate text and leave its "
    "custody unaddressed. Vehicular ledgers anchor telemetry or ownership, not repair events and "
    "their supporting documents. Transparency logs assume a committed object with structure and "
    "meaning agreed. No reviewed system commits a diagnosis, the repair performed in response to the "
    "diagnosis, the evidence of the repair, and the vehicle it belongs to in one commitment a "
    "stranger can verify. Thus, the first design problem is to define that committed object, and it "
    "comes before the anchoring mechanism in what follows.",
]

CASE_CLOSE = [
    "The same record was run against two additional scenarios. The substitution of the stored "
    "evidence was detected without reference to the original file. Changing two bytes of the "
    "1,966-byte invoice payload, so that the printed odometer now read 76,000, changed its content "
    "identifier from d6faec167aef4751 to 2c2f8a2364db9ef1, which corresponds to nothing that was "
    "anchored. The same was true for a real record reused on multiple vehicles: changing the Camry "
    "leaf ac512c77df8b6a8b to the Civic identification number, leaving all other fields untouched, "
    "moved the leaf digest to 63ab48af3bdad18c and the recomputed root to cc9b95ac3b703fb0, and the "
    "proof issued for the original leaf failed on replay. Because the vehicle identification number "
    "sits inside the hashed payload, a record cannot be moved between vehicles without the move "
    "becoming evident.",
]

LIMITS = [
    "The prototype limits are provided as they stand. Anchoring runs on a local development chain, "
    "so roots are not publicly persisted and independent timestamps are pending until Bitcoin "
    "inclusion confirms them. The evidence is synthetic. No commercial workshop invoice has been "
    "ingested. No workshop partnership exists. The diagnostic context is entered rather than read "
    "from a scan tool, so the prototype is not recording anything directly from the vehicle. The "
    "evaluation is performed on 57 real OBD cases, sufficient to show feasibility and far too few to "
    "know how the models perform across different makes, production years and classes of fault. The "
    "models fail outright on free-text complaints. The registry is a single SQLite file next to a "
    "local evidence directory, which is fine for one writer and not concurrent multi-tenant "
    "operation. Workshop identity is unverified. Since anchoring is permissionless, the submitting "
    "address records a claim, not an authorization. A vehicle identification number is indirectly "
    "tied to an owner, so a deployed service would require a retention and disclosure policy even if "
    "committed leaves lack personal data.",

    "Each of these leads to the future work. The next steps are to package the trained adapters with "
    "the repository, so that a clone can do inference without manually fetching them, and to publish "
    "the contract on a public test network, so that any party can verify a root without access to "
    "the development machine. Beyond those lie a larger evaluation corpus, grounding diagnoses in "
    "retrieved service documentation [17], pulling diagnostic context directly from OBD-II hardware, "
    "and adding workshop identity with role-based access control, before the system is given to real "
    "users instead of being run in a demonstration.",
]

CONCLUSION = [
    "Repair history is worth little if it cannot be checked. This paper described a prototype to "
    "make it checkable by separating two things that are usually run together. A language model "
    "adapted by low-rank adaptation interprets a diagnostic context and generates a structured "
    "repair record. That record is tied to one vehicle with a cryptographic layer, and any change "
    "after that is obvious. Each sealed repair is a canonical leaf over the vehicle identification "
    "number, the odometer reading, the report digest, the evidence identifier, and the model "
    "provenance, and those leaves are collected into a Merkle tree whose root is then anchored on an "
    "EVM contract and timestamped independently.",

    "The diagnostic layer was able to detect the fault code in 98.3% of real OBD cases, but that "
    "accuracy was completely lost on free-text complaints it had not been adapted for. The "
    "attestation layer successfully identified all attempts to tamper with sealed records, including "
    "a one-kilometre odometer change, a two-byte invoice edit, and the reuse of a record on "
    "different vehicles. The guarantee that accompanies it is deliberately limited: that the record "
    "is the one that was sealed, not that the diagnosis it contains is correct.",
]

# Title, and report/repository phrasing replaced with paper phrasing.
TITLE = ("Proof of Repair: VIN-Bound Tamper-Evident Repair Records "
         "from LLM-Assisted Vehicle Diagnosis")

PHRASING = [
    ("This project develops a cloud-based Proof-of-Repair system",
     "This paper presents a cloud-based Proof-of-Repair system"),
    ("The following example was not manually created for this report; instead, it was generated by "
     "the project\u2019s own batching code executed against the Proof-of-Repair leaves stored in the "
     "registry at artifacts/por_registry.sqlite3, and it can be regenerated using the script located "
     "at scripts/merkle_worked_example.py.",
     "The following example was not manually created for this paper; instead, it was generated by "
     "the proposed mechanism itself, executed against the Proof-of-Repair leaves held in the "
     "registry, and it can be regenerated from the implementation."),
    ("The Merkle tree was computed by the project\u2019s batching code using the four leaves listed",
     "The Merkle tree computed by the proposed mechanism over the four leaves listed"),
    ("ensuring that adaptation stays within the project's compute budget",
     "ensuring that adaptation stays within a modest compute budget"),
    ("Raw evidence remains stored off-chain in the evidence store under the artifacts/evidence/ "
     "directory and is represented",
     "Raw evidence remains stored off-chain in the evidence store and is represented"),
    ("The application state is stored in a SQLite database located at artifacts/por_registry. "
     "Sqlite3 [43], which stores",
     "The application state is stored in a SQLite database [43], which stores"),
    ("allows the system to be easily reproduced from a fresh checkout",
     "allows the system to be reproduced easily from a fresh installation"),
    ("Four batches were anchored through it during interactive testing",
     "Four batches were anchored through it in the demonstration runs"),
    ("The three Civic entries were sealed in separate runs during interactive testing",
     "The three Civic entries were sealed in separate runs during testing"),
    ("during interactive testing, the anchored batches were smaller than the example provided",
     "in the demonstration runs, the anchored batches were smaller than the example provided"),
    ("On a fresh checkout the sealing path fails before it reaches the model, since the trained "
     "adapter is not pulled into the adapter directory by the repository itself.",
     "In a fresh deployment the sealing path fails before it reaches the model, because the trained "
     "adapter is not distributed with the implementation."),
    ("This is a packaging gap in that working copy, not a defect in either layer, and it means the "
     "full workflow, including live inference, has not been shown end to end on that machine.",
     "This is a packaging gap rather than a defect in either layer, and it means the full workflow, "
     "including live inference, has not been shown end to end in that environment."),
    ("The next steps are to package the trained adapters with the repository, so that a clone can do "
     "inference without manually fetching them",
     "The next steps are to distribute the trained adapters with the implementation, so that a new "
     "deployment can perform inference without fetching them manually"),
]


# Author block. Department / institution / city inferred from the e-mail domains
# (vitstudent.ac.in, vit.ac.in) - correct these if they are wrong.
DEPARTMENT = "School of Computer Science and Engineering"
INSTITUTION = "Vellore Institute of Technology"
CITY = "Vellore, India"
# The two-column author section fills column-wise: entries 1-2 go down the left
# column, 3-4 down the right. Listed in this order the printed grid reads
#   Shivansh | Himali
#   Vikash   | Thanuja
# so left-to-right, top-to-bottom the authors are Shivansh, Himali, Vikash, Thanuja.
AUTHORS = [
    ("Shivansh Sharma", "shivansh.sharma2023@vitstudent.ac.in"),
    ("Vikash Dhillan", "vikash.dhillan2023@vitstudent.ac.in"),
    ("Himali Sharma", "himali.sharma2023@vitstudent.ac.in"),
    ("Thanuja R", "thanuja.r@vit.ac.in"),
]


def author_para(name, email):
    def run(text, italic=False, br=True):
        it = "<w:i/>" if italic else ""
        pre = "<w:br/>" if br else ""
        return (f'<w:r><w:rPr>{it}<w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr>'
                f'{pre}<w:t xml:space="preserve">{text}</w:t></w:r>')
    return ('<w:p><w:pPr><w:pStyle w:val="Author"/>'
            '<w:spacing w:before="5pt" w:after="0pt"/></w:pPr>'
            + run(name, br=False) + run(DEPARTMENT, italic=True)
            + run(INSTITUTION, italic=True) + run(CITY) + run(email) + '</w:p>')


# ---------------------------------------------------------------------- xml helpers

H2_PR = ('<w:numPr><w:ilvl w:val="0"/><w:numId w:val="0"/></w:numPr>'
         '<w:ind w:start="0pt" w:firstLine="0pt"/>')
H3_PR = ('<w:numPr><w:ilvl w:val="0"/><w:numId w:val="0"/></w:numPr><w:keepNext/>'
         '<w:spacing w:before="4pt" w:after="2pt"/><w:ind w:start="0pt" w:firstLine="0pt"/>')


FIGURE = "/Users/shivansh/Desktop/proof of repair/report_humanized/figures/fig2_architecture.png"
FIG_RID = "rId100"
FIG_CAPTION = "Figure 1. System architecture."   # the only new words; change freely


def png_size(path):
    import struct
    d = Path(path).read_bytes()
    return struct.unpack(">II", d[16:24])


def drawing_xml(width_in, rid, path):
    px_w, px_h = png_size(path)
    cx = int(width_in * 914400)
    cy = int(cx * px_h / px_w)
    A = "http://purl.oclc.org/ooxml/drawingml/main"
    PIC = "http://purl.oclc.org/ooxml/drawingml/picture"
    return (
        '<w:p><w:pPr><w:pStyle w:val="Normal"/><w:keepNext/>'
        '<w:spacing w:before="6pt" w:after="2pt" w:line="240" w:lineRule="auto"/>'
        '<w:jc w:val="center"/>'
        '<w:ind w:start="0pt" w:firstLine="0pt"/></w:pPr><w:r><w:drawing>'
        f'<wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
        '<wp:docPr id="1" name="Picture 1" descr="System architecture"/>'
        f'<wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="{A}" noChangeAspect="1"/>'
        '</wp:cNvGraphicFramePr>'
        f'<a:graphic xmlns:a="{A}"><a:graphicData uri="{PIC}">'
        f'<pic:pic xmlns:pic="{PIC}">'
        '<pic:nvPicPr><pic:cNvPr id="1" name="architecture.png"/><pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
        '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'
    )


def para_span(s, needle):
    i = s.index(needle)
    return s.rindex("<w:p>", 0, i), s.index("</w:p>", i) + len("</w:p>")


def drop_para(s, needle):
    a, b = para_span(s, needle)
    return s[:a] + s[b:]


def P(text):
    return (f'<w:p><w:pPr><w:pStyle w:val="BodyText"/></w:pPr>'
            f'<w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>')


def heading(text, level=2):
    pr = H2_PR if level == 2 else H3_PR
    return (f'<w:p><w:pPr><w:pStyle w:val="Heading{level}"/>{pr}</w:pPr>'
            f'<w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>')


def replace_between(doc, start_needle, end_needle, new_xml, keep_start=True):
    """Replace content between two headings. keep_start=False drops the first heading too."""
    a0, a1 = para_span(doc, start_needle)
    b0, _ = para_span(doc, end_needle)
    return doc[:(a1 if keep_start else a0)] + new_xml + doc[b0:]


def figcaption(text):
    return (f'<w:p><w:pPr><w:pStyle w:val="figurecaption"/>'
            '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="0"/></w:numPr>'
            '<w:spacing w:before="2pt" w:after="8pt"/>'
            '<w:ind w:start="0pt" w:firstLine="0pt"/></w:pPr>'
            f'<w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>')


def rename_heading(doc, old, new):
    assert old in doc, f"heading not found: {old}"
    return doc.replace(old, new, 1)


def main():
    zin = zipfile.ZipFile(SRC)
    doc = zin.read("word/document.xml").decode("utf-8")
    start_len = len(doc)

    # 1 Introduction -------------------------------------------------------
    doc = replace_between(doc, "1. Introduction", "2. Project Description and Goals",
                          "".join(P(t) for t in INTRO))

    # 2 Related Work -------------------------------------------------------
    doc = replace_between(doc, "2. Project Description and Goals", "3.2 Feasibility Study",
                          "".join(P(t) for t in RELATED))
    doc = rename_heading(doc, "2. Project Description and Goals", "2. Related Work")

    # drop feasibility and system specification entirely
    doc = replace_between(doc, "3.2 Feasibility Study", "4. Design Approach and Details",
                          "", keep_start=False)

    # 3 System Design ------------------------------------------------------
    doc = drop_para(doc, "This chapter outlines the system architecture")
    doc = rename_heading(doc, "4. Design Approach and Details", "3. System Design")
    doc = drop_para(doc, "4.1 System Architecture")
    for old, new in (("4.1.1 The Proof-of-Repair Leaf", "3.1 The Proof-of-Repair Leaf"),
                     ("4.1.2 Merkle Tree and Root", "3.2 Merkle Tree and Root"),
                     ("4.1.3 Smart Contract and On-Chain Anchoring",
                      "3.3 Smart Contract and On-Chain Anchoring"),
                     ("4.1.4 OpenTimestamps", "3.4 OpenTimestamps"),
                     ("4.1.5 Off-Chain Evidence and Storage", "3.5 Off-Chain Evidence and Storage")):
        doc = rename_heading(doc, old, new)

    # drop backend/frontend, the design artefacts and their diagrams
    doc = replace_between(doc, "4.1.6 Backend and Frontend", "4.2.3 Attestation Algorithm",
                          "", keep_start=False)

    # 4 Attestation Algorithm (promote from Heading3) ----------------------
    a0, a1 = para_span(doc, "4.2.3 Attestation Algorithm")
    doc = doc[:a0] + heading("4. Attestation Algorithm", 2) + doc[a1:]

    # 5 Evaluation ---------------------------------------------------------
    doc = drop_para(doc, "The diagnostic layer is trained and evaluated using a")
    doc = drop_para(doc, "Table 9. Datasets documented in the project repository")
    i = doc.index("MechanicDB OBD-II")                      # Table 9 itself
    doc = doc[:doc.rindex("<w:tbl>", 0, i)] + doc[doc.index("</w:tbl>", i) + len("</w:tbl>"):]
    doc = rename_heading(doc, "4.3 Dataset Description and Model Development", "5. Evaluation")

    a0, a1 = para_span(doc, "4.4 Results")                   # demote to a subsection
    doc = doc[:a0] + heading("5.1 Diagnostic Results", 3) + doc[a1:]
    doc = rename_heading(doc, "4.4.1 Worked Merkle Example", "5.2 Worked Merkle Example")
    doc = rename_heading(doc, "4.4.2 Case Study: Odometer Rollback",
                         "5.3 Case Study: Odometer Rollback")

    # trim the case study: the fraud framing now lives in the introduction
    for needle in ("Odometer tampering represents the most obvious example",
                   "The fraud mechanism has evolved in a manner",
                   "The protections typically available to a buyer"):
        doc = drop_para(doc, needle)
    a0, _ = para_span(doc, "Two additional scenarios were executed using the same record")
    _, b1 = para_span(doc, "The second scenario evaluates the reuse of a legitimate record")
    doc = doc[:a0] + "".join(P(t) for t in CASE_CLOSE) + doc[b1:]

    # 6 Limitations, 7 Conclusion -----------------------------------------
    doc = replace_between(doc, "4.5 Limitations and Future Work", "5. References",
                          "".join(P(t) for t in LIMITS))
    doc = rename_heading(doc, "4.5 Limitations and Future Work", "6. Limitations and Future Work")
    b0, _ = para_span(doc, "5. References")
    doc = doc[:b0] + heading("7. Conclusion", 2) + "".join(P(t) for t in CONCLUSION) + doc[b0:]

    doc = doc.replace("As set out in full in the following worked example, every attempted "
                      "alteration against them was detected.",
                      "Every attempted alteration against them was detected.")

    # two paragraphs that restate points already made (deletions only)
    #   - the separation of roles, already stated in 1 and 2
    #   - the leaf disclosure summary, already stated earlier in 3.1
    doc = drop_para(doc, "It is important to emphasize the separation of responsibilities")
    doc = drop_para(doc, "In practice this means the leaf is small enough to batch")

    # Figure 1: the architecture diagram, placed after its first mention
    _, a1 = para_span(doc, "The architecture is organized as a pipeline of layers")
    doc = doc[:a1] + drawing_xml(3.0, FIG_RID, FIGURE) + figcaption(FIG_CAPTION) + doc[a1:]

    # author block: replace the three placeholders with the real authors
    a0, _ = para_span(doc, "[Author 1 Name]")
    _, b1 = para_span(doc, "[Author 3 Name]")
    doc = doc[:a0] + "".join(author_para(n, e) for n, e in AUTHORS) + doc[b1:]
    # four authors sit better in a 2x2 grid than across three columns
    doc = doc.replace('<w:cols w:num="3" w:space="36pt"/>', '<w:cols w:num="2" w:space="36pt"/>')

    # references start on a page of their own ------------------------------
    a0, a1 = para_span(doc, "5. References")
    ref = doc[a0:a1].replace("<w:pPr>", "<w:pPr><w:pageBreakBefore/>", 1).replace(
        "5. References", "References")
    doc = doc[:a0] + ref + doc[a1:]

    # IEEE keyword lines are a bare list, not a sentence (deletion only)
    doc = doc.replace('<w:t xml:space="preserve">The keywords include ',
                      '<w:t xml:space="preserve">')

    # title and paper-appropriate phrasing
    assert "<w:t>Proof of Repair</w:t>" in doc, "title run not found"
    doc = doc.replace("<w:t>Proof of Repair</w:t>",
                      f'<w:t xml:space="preserve">{TITLE}</w:t>', 1)
    for old, new_text in PHRASING:
        assert old in doc, f"phrase not found: {old[:60]}"
        doc = doc.replace(old, new_text)

    # the report said "chapter"; this is a paper
    doc = doc.replace("in this chapter", "in this paper")

    # --- cut to the conference's 4-6 page limit (deletions only, no new text) ---
    # 4 Attestation Algorithm: its content is largely covered by 3.1 and 3.2
    doc = replace_between(doc, "4. Attestation Algorithm", "5. Evaluation", "", keep_start=False)
    # 3.5 Off-Chain Evidence and Storage: implementation detail
    doc = replace_between(doc, "3.5 Off-Chain Evidence and Storage", "5. Evaluation",
                          "", keep_start=False)
    # 4.2 Worked Merkle Example: the case study demonstrates the same property
    doc = replace_between(doc, "5.2 Worked Merkle Example", "5.3 Case Study: Odometer Rollback",
                          "", keep_start=False)
    for old, new_h in (("5. Evaluation", "4. Evaluation"),
                       ("5.1 Diagnostic Results", "4.1 Diagnostic Results"),
                                              ("5.3 Case Study: Odometer Rollback", "4.2 Case Study: Odometer Rollback"),
                       ("6. Limitations and Future Work", "5. Limitations and Future Work"),
                       ("7. Conclusion", "6. Conclusion")):
        doc = doc.replace(old, new_h)

    # figures and tables renumbered after the cuts -------------------------
    doc = doc.replace("Figure 2", "Figure 1").replace("Figure 7", "Figure 2")
    for old, new in (("Table 7", "Table 1"), ("Table 8", "Table 2"), ("Table 10", "Table 3"),
                     ("Table 11", "Table 4"), ("Table 12", "Table 5")):
        doc = doc.replace(old, new)

    ET.fromstring(doc.encode("utf-8"))
    words = len(re.sub(r"<[^>]+>", " ", doc).split())
    print(f"document.xml {start_len} -> {len(doc)} bytes, XML well-formed, ~{words:,} words")

    with zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED) as zout:
        rels = zin.read("word/_rels/document.xml.rels").decode("utf-8")
        rel = (f'<Relationship Id="{FIG_RID}" Type="http://purl.oclc.org/ooxml/officeDocument/'
               'relationships/image" Target="media/architecture.png"/>')
        rels = rels.replace("</Relationships>", rel + "</Relationships>")
        for item in zin.infolist():
            if item.filename == "word/document.xml":
                data = doc.encode("utf-8")
            elif item.filename == "word/_rels/document.xml.rels":
                data = rels.encode("utf-8")
            else:
                data = zin.read(item.filename)
            zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
            zi.compress_type = item.compress_type
            zi.external_attr = item.external_attr
            zout.writestr(zi, data)
        zout.writestr("word/media/architecture.png", Path(FIGURE).read_bytes())
    print("wrote", DST)
    for c in CORRECTIONS:
        print("  -", c)


if __name__ == "__main__":
    main()
