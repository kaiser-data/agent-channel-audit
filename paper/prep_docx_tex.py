"""Make a Word-friendly copy of a paper's main.tex: numbered citations, plain reference list, PNG figures.

  python3 prep_docx_tex.py <main.tex> <out.tex>

pandoc has no BibTeX-style numbering for thebibliography, so \\cite{a,b} becomes "[1, 2]" in bibitem order (the order
LaTeX numbers them), each \\bibitem becomes a paragraph "[n] ...", and PDF figures are swapped for their PNG twins.
"""
import re
import sys

src, out = sys.argv[1], sys.argv[2]
tex = open(src).read()

bib = re.search(r"\\begin\{thebibliography\}\{[^}]*\}(?:\\small)?(.*?)\\end\{thebibliography\}", tex, re.S)
keys = re.findall(r"\\bibitem\{([^}]*)\}", bib.group(1))
num = {k: i + 1 for i, k in enumerate(keys)}


def cite(m):
    missing = [k.strip() for k in m.group(1).split(",") if k.strip() not in num]
    if missing:
        raise KeyError(f"cite without bibitem: {missing}")
    return "[" + ", ".join(str(num[k.strip()]) for k in m.group(1).split(",")) + "]"


tex = re.sub(r"\\cite\{([^}]*)\}", cite, tex)
items = re.split(r"\\bibitem\{[^}]*\}", bib.group(1))[1:]
refs = "\n\n".join(f"[{i + 1}] {t.strip()}" for i, t in enumerate(items))
tex = tex.replace(bib.group(0), "\\section*{References}\n\n" + refs + "\n")
# pandoc's math parser rejects text-mode macros inside \[...\]
tex = re.sub(r"\\\[(.*?)\\\]", lambda m: "\\[" + re.sub(r"\\textsc\{([^}]*)\}", r"\\textrm{\1}", m.group(1)) + "\\]", tex, flags=re.S)
tex = re.sub(r"(\\includegraphics(?:\[[^]]*\])?\{[^}]*)\.pdf\}", r"\1.png}", tex)
open(out, "w").write(tex)
print(f"{out}: {len(keys)} references")
