#!/usr/bin/env bash
# Rebuild both papers in the official Apart template (.docx), plus PDF previews via LibreOffice.
#   bash build_apart_docs.sh            (from anywhere; channel-displacement must sit next to agent-channel-audit)
set -euo pipefail
P1="$(cd "$(dirname "$0")" && pwd)"
P2="$P1/../../channel-displacement/paper"
W="$P1/template-build"
mkdir -p "$W/tpl"
cd "$W"
[ -f template.docx ] || curl -sL -o template.docx \
  "https://docs.google.com/document/d/1_1_27EyZriMlc8n8EBE2YScaeyMjm-8xjR097nmHXAE/export?format=docx"

python3 "$P1/prep_docx_tex.py" "$P1/main.tex" docx.tex
python3 "$P1/prep_docx_tex.py" "$P2/main.tex" p2docx.tex
TPL_BUILD="$W" python3 "$P1/make_template_bodies.py"

python3 "$P1/build_template.py" template.docx tpl/p1_body.tex "$P1/apart-template-filled.docx" \
  --title "Agent Channel Audit: Finding Agent Message Boards in Access Logs Without Reading Them" \
  --author "Martin Kaiser" --affil "Independent researcher" --abstract tpl/p1_abstract.txt --resource-path "$P1"
python3 "$P1/build_template.py" template.docx tpl/p2_body.tex "$P2/apart-template-filled.docx" \
  --title "Close the Board, Agents Move: Channel Displacement in LLM Agent Swarms" \
  --author "Martin Kaiser" --affil "Independent researcher" --abstract tpl/p2_abstract.txt --resource-path "$P2"

if command -v soffice >/dev/null; then
  for d in "$P1" "$P2"; do
    soffice --headless --convert-to pdf --outdir "$d" "$d/apart-template-filled.docx" >/dev/null 2>&1
    echo "$d/apart-template-filled.pdf: $(pdfinfo "$d/apart-template-filled.pdf" | awk '/Pages/{print $2}') pages"
  done
fi
