"""Fill the official Apart sprint template (a public Google Doc exported as .docx) with a paper's content.

  python3 build_template.py <template.docx> <body.tex> <out.docx> --title "..." --author "..." --affil "..." --abstract-from <main.tex>

<body.tex> is a LaTeX file whose sections already follow the template order. pandoc renders it with the template as
reference doc; its body is spliced into a copy of the template after the title block, the template's instruction box
and guidance sections are removed, images are re-linked, and pandoc styles are mapped onto the template's styles.
"""
import argparse
import copy
import re
import subprocess
import tempfile

import docx
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT

STYLE_MAP = {"Heading1": "Heading 2", "Heading2": "Heading 3", "Heading3": "Heading 3", "Heading4": "Heading 3"}


def fix_font_types(path):
    """pandoc copies the template's embedded fonts but not their content types; declare them so the file opens."""
    import shutil
    import zipfile
    tmp = path + ".tmp"
    with zipfile.ZipFile(path) as zi, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
        exts = {n.rsplit(".", 1)[1].lower() for n in zi.namelist() if n.startswith("word/fonts/") and "." in n}
        for item in zi.infolist():
            data = zi.read(item.filename)
            if item.filename == "[Content_Types].xml":
                s = data.decode()
                for e in exts:
                    if f'Extension="{e}"' not in s:
                        s = s.replace("<Types ", "<Types ", 1).replace(
                            "</Types>", f'<Default Extension="{e}" ContentType="application/x-font-{e}"/></Types>')
                data = s.encode()
            zo.writestr(item, data)
    shutil.move(tmp, path)


def set_cell_text(cell, old, new):
    for p in cell.paragraphs:
        for r in p.runs:
            if old in r.text:
                r.text = r.text.replace(old, new)
                return True
    return False


def walk_cells(table):
    for row in table.rows:
        for cell in row.cells:
            yield cell
            for t in cell.tables:
                yield from walk_cells(t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("template"); ap.add_argument("body"); ap.add_argument("out")
    ap.add_argument("--title", required=True); ap.add_argument("--author", required=True)
    ap.add_argument("--affil", required=True); ap.add_argument("--abstract", required=True)
    ap.add_argument("--resource-path", default=".")
    a = ap.parse_args()

    with tempfile.TemporaryDirectory() as td:
        body_docx = f"{td}/body.docx"
        subprocess.run(["pandoc", a.body, "-o", body_docx, f"--reference-doc={a.template}",
                        f"--resource-path={a.resource_path}"], check=True)
        fix_font_types(body_docx)
        src = docx.Document(body_docx)
        doc = docx.Document(a.template)

        # --- title block (table 0): title, authors, abstract
        tb = doc.tables[0]
        for cell in walk_cells(tb):
            set_cell_text(cell, "PROJECT TITLE", a.title)
        # author grid: each cell is one run "Author name N" <br/> "Affiliation"; edit the text nodes directly
        first_aff = True
        for t in tb._tbl.iter(qn("w:t")):
            v = (t.text or "").strip()
            if v == "Author name 1":
                t.text = a.author
            elif re.fullmatch(r"Author name [2-6]", v):
                t.text = "\u00a0" * 24  # keep the column width in every renderer
            elif v == "Affiliation":
                t.text = a.affil if first_aff else "\u00a0"
                first_aff = False
        abstract = open(a.abstract).read().strip()
        for cell in walk_cells(tb):
            if "Summarize your project" in cell.text:
                ps = cell.paragraphs
                ps[0].runs[0].text = abstract
                for r in ps[0].runs[1:]:
                    r.text = ""
                for r in ps[0].runs:
                    r.italic = False
                for p in ps[1:]:
                    p._p.getparent().remove(p._p)
                break

        # --- remove instruction box and every guidance element after the title block
        body = doc.element.body
        kids = list(body.iterchildren())
        start = kids.index(doc.tables[1]._tbl)
        for el in kids[start:]:
            if el.tag != qn("w:sectPr"):
                body.remove(el)
        sect = body.find(qn("w:sectPr"))

        # --- splice pandoc body; re-link images
        for el in list(src.element.body.iterchildren()):
            if el.tag == qn("w:sectPr"):
                continue
            new = copy.deepcopy(el)
            for blip in new.iter(qn("a:blip")):
                rid = blip.get(qn("r:embed"))
                part = src.part.related_parts[rid]
                blip.set(qn("r:embed"), doc.part.relate_to(part, RT.IMAGE))
            sect.addprevious(new)

        # --- map styles: pandoc ids -> template styles
        names = {s.name for s in doc.styles}
        for p in doc.paragraphs:
            sid = p._p.pPr.pStyle.val if p._p.pPr is not None and p._p.pPr.pStyle is not None else None
            if sid is None:
                continue
            if sid in STYLE_MAP and STYLE_MAP[sid] in names:
                p.style = doc.styles[STYLE_MAP[sid]]
            elif sid in ("BodyText", "FirstParagraph", "Compact", "BlockText"):
                p.style = doc.styles["normal"]
            elif sid in ("ImageCaption", "TableCaption", "Caption"):
                p.style = doc.styles["normal"]
                for r in p.runs:
                    r.italic = True
        doc.save(a.out)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
