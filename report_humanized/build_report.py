"""Build the humanized Proof-of-Repair report .docx from content.py.

Formatting matches the original BCSE497J report: A4, 1in margins,
Times New Roman 12pt, 1.15 line spacing, justified body.

Block kinds in content.BLOCKS:
    h1 / h2 / h3   -> headings
    body           -> justified paragraph
    keywords       -> italic justified paragraph
    bullet         -> bulleted item
    num            -> numbered item (list restarts after any non-num block)
    caption        -> centred italic caption (table or figure)
    figure         -> ("figure", (path, width_inches))
    table          -> ("table", [[row1...], [row2...], ...])  first row = header
    pagebreak      -> page break
    refgroup       -> bold reference-group label (Journals, Conferences, ...)
    ref            -> ("ref", [number, text])  hanging-indent IEEE entry
"""
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.text import WD_BREAK
from docx.shared import Pt, Mm, Inches, Cm, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from content import BLOCKS

OUT = "Proof_of_Repair_Report_Humanized.docx"
CONTENT_WIDTH_IN = 6.3  # A4 (8.27in) minus 2 x 1in margins


def set_font(style, name="Times New Roman"):
    style.font.name = name
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), name)


def shade(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    el = OxmlElement("w:shd")
    el.set(qn("w:val"), "clear")
    el.set(qn("w:color"), "auto")
    el.set(qn("w:fill"), fill)
    tc_pr.append(el)


def restart_numbering(paragraph):
    """Force a 'List Number' paragraph to restart at 1 via a fresh numId."""
    # python-docx has no first-class API; reuse the style's abstract list with
    # a new concrete num so each list block restarts independently.
    numbering = paragraph.part.numbering_part.element
    abstracts = numbering.findall(qn("w:abstractNum"))
    target = None
    for a in abstracts:
        fmt = a.find(qn("w:lvl") + "/" + qn("w:numFmt"))
        if fmt is not None and fmt.get(qn("w:val")) == "decimal":
            target = a
            break
    if target is None:
        return
    aid = target.get(qn("w:abstractNumId"))
    used = [int(n.get(qn("w:numId"))) for n in numbering.findall(qn("w:num"))]
    new_id = max(used) + 1 if used else 1
    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(new_id))
    ref = OxmlElement("w:abstractNumId")
    ref.set(qn("w:val"), aid)
    num.append(ref)
    numbering.append(num)
    p_pr = paragraph._p.get_or_add_pPr()
    num_pr = p_pr.find(qn("w:numPr"))
    if num_pr is None:
        num_pr = OxmlElement("w:numPr")
        p_pr.append(num_pr)
    for tag, val in (("w:ilvl", "0"), ("w:numId", str(new_id))):
        el = num_pr.find(qn(tag))
        if el is None:
            el = OxmlElement(tag)
            num_pr.append(el)
        el.set(qn("w:val"), val)


doc = Document()

sec = doc.sections[0]
sec.page_width, sec.page_height = Mm(210), Mm(297)
for side in ("top", "bottom", "left", "right"):
    setattr(sec, f"{side}_margin", Mm(25.4))

normal = doc.styles["Normal"]
normal.font.size = Pt(12)
set_font(normal)
normal.paragraph_format.line_spacing = 1.15
normal.paragraph_format.space_after = Pt(6)

for sid, size, italic, before, after in (
    ("Heading 1", 14, False, 18, 12),
    ("Heading 2", 13, False, 14, 8),
    ("Heading 3", 12, True, 12, 7),
):
    st = doc.styles[sid]
    st.font.size = Pt(size)
    st.font.bold = True
    st.font.italic = italic
    st.font.color.rgb = RGBColor(0, 0, 0)
    set_font(st)
    st.paragraph_format.line_spacing = 1.5
    st.paragraph_format.space_before = Pt(before)
    st.paragraph_format.space_after = Pt(after)
    st.paragraph_format.keep_with_next = True

# Chapter headings render in all caps, as in the original report.
doc.styles["Heading 1"].font.all_caps = True

for sid in ("List Bullet", "List Number"):
    st = doc.styles[sid]
    st.font.size = Pt(12)
    set_font(st)
    st.paragraph_format.line_spacing = 1.15
    st.paragraph_format.space_after = Pt(4)

prev_kind = None
for kind, payload in BLOCKS:
    if kind in ("h1", "h2", "h3"):
        doc.add_paragraph(payload, style={"h1": "Heading 1", "h2": "Heading 2",
                                          "h3": "Heading 3"}[kind])

    elif kind == "body":
        p = doc.add_paragraph(payload)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    elif kind == "keywords":
        p = doc.add_paragraph(payload)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.runs[0].italic = True

    elif kind == "bullet":
        p = doc.add_paragraph(payload, style="List Bullet")
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    elif kind == "num":
        p = doc.add_paragraph(payload, style="List Number")
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if prev_kind != "num":
            restart_numbering(p)

    elif kind == "caption":
        p = doc.add_paragraph(payload)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(10)
        p.paragraph_format.keep_with_next = not payload.startswith("Fig")
        r = p.runs[0]
        r.italic = True
        r.font.size = Pt(11)

    elif kind == "figure":
        path, width_in = payload
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        p.add_run().add_picture(path, width=Inches(min(width_in, CONTENT_WIDTH_IN)))

    elif kind == "pagebreak":
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    elif kind == "refgroup":
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        p.add_run(payload).bold = True

    elif kind == "ref":
        num, text = payload
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf = p.paragraph_format
        pf.left_indent = Cm(1.0)
        pf.first_line_indent = -Cm(1.0)
        pf.space_after = Pt(5)
        pf.line_spacing = 1.1
        tabs = pf.tab_stops
        tabs.add_tab_stop(Cm(1.0))
        r = p.add_run(f"[{num}]\t{text}")
        r.font.size = Pt(11)

    elif kind == "table":
        rows = payload
        ncols = len(rows[0])
        t = doc.add_table(rows=0, cols=ncols)
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = True
        for ri, row in enumerate(rows):
            cells = t.add_row().cells
            for ci, text in enumerate(row):
                cell = cells[ci]
                cell.text = ""
                para = cell.paragraphs[0]
                para.paragraph_format.space_after = Pt(2)
                para.paragraph_format.line_spacing = 1.0
                run = para.add_run(str(text))
                run.font.size = Pt(10.5)
                set_font_run = run.font
                set_font_run.name = "Times New Roman"
                if ri == 0:
                    run.bold = True
                    shade(cell, "D9E2F3")
        doc.add_paragraph().paragraph_format.space_after = Pt(2)

    else:
        raise ValueError(f"unknown block kind: {kind}")
    prev_kind = kind

doc.save(OUT)

words = sum(len(t.split()) for k, t in BLOCKS
            if k in ("body", "keywords", "bullet", "num"))
refs = sum(1 for k, _ in BLOCKS if k == "ref")
tables = sum(1 for k, _ in BLOCKS if k == "table")
figs = sum(1 for k, _ in BLOCKS if k == "figure")
print(f"wrote {OUT}: {len(BLOCKS)} blocks, ~{words} words, "
      f"{tables} tables, {figs} figures, {refs} references")
