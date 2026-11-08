"""Reorder each paper's (citation-numbered) LaTeX into the Apart template's section order and add missing sections."""
import os
import re
import subprocess

# working dir holding docx.tex / p2docx.tex (citation-numbered copies of each main.tex); output goes to $S/tpl
S = os.environ.get("TPL_BUILD", ".")


def number_floats(tex, secrefs):
    """Word has no \\ref: prefix captions with 'Figure N.' / 'Table N.' and replace every \\ref with its number."""
    nums = {}
    count = {"figure": 0, "table": 0}

    def env(m):
        kind = m.group(1)
        count[kind] += 1
        n = count[kind]
        body = m.group(2)
        lab = re.search(r"\\label\{([^}]*)\}", body)
        if lab:
            nums[lab.group(1)] = str(n)
        body = body.replace("\\caption{", f"\\caption{{{kind.capitalize()} {n}. ", 1)
        return f"\\begin{{{kind}}}{body}\\end{{{kind}}}"

    tex = re.sub(r"\\begin\{(figure|table)\}(.*?)\\end\{\1\}", env, tex, flags=re.S)
    nums.update(secrefs)

    def ref(m):
        if m.group(1) not in nums:
            raise KeyError(f"unresolved \\ref{{{m.group(1)}}}")
        return nums[m.group(1)]

    return re.sub(r"\\ref\{([^}]*)\}", ref, tex)


def sections(tex):
    body = tex.split("\\maketitle", 1)[1].split("\\end{document}")[0]
    body = re.sub(r"\\begin\{abstract\}.*?\\end\{abstract\}", "", body, flags=re.S)
    body = body.replace("\\appendix", "")
    parts = re.split(r"\\section\*?\{([^}]*)\}", body)
    out = {}
    for i in range(1, len(parts), 2):
        out[parts[i].strip()] = parts[i + 1]
    return out


def clean(x):
    x = re.sub(r"\\paragraph\{([^}]*)\}", r"\\textbf{\1} ", x)
    x = re.sub(r"\\label\{[^}]*\}", "", x)
    x = re.sub(r"\\cmidrule(\([a-z]*\))?\{[^}]*\}", "", x)  # pandoc prints these as text
    return x


def preamble(tex):
    # drop \title/\author/\date: the template's title block carries them, pandoc would print them a second time
    pre = tex.split("\\begin{document}")[0]
    pre = re.sub(r"^\\(title|author|date)\{.*$", "", pre, flags=re.M)
    return pre + "\\begin{document}\n"


LLM = ("This project was carried out with Claude Code (Anthropic, model Claude Opus 5.5) as an agentic assistant. "
       "The author chose the research question and the overall direction, and approved each decision point "
       "(design, deviations, what to publish). Claude Code wrote most of the code, ran the experiments, and drafted "
       "the text of this report. Every number in the report is printed by scripts in the public repository and was "
       "checked against those outputs; every reference was checked against Crossref or the original source. "
       "[AUTHOR: edit this statement so it matches your own role, and revise the text in your own words; the "
       "organisers ask that the final version be primarily written by the team.]")


def build(src, out, extra):
    tex = number_floats(open(src).read(), extra.get("secrefs", {}))
    for a, b in extra.get("subs", []):  # layout-only substitutions for the Word version (e.g. figure widths)
        assert a in tex, a
        tex = tex.replace(a, b)
    sec = sections(tex)
    moved = []  # floats moved to the appendix to keep the main text within the template's page limit
    for lab, title in extra.get("to_appendix", []):
        for k, v in sec.items():
            m = re.search(r"\\begin\{(table|figure)\}(?:(?!\\end\{\1\}).)*?\\label\{%s\}.*?\\end\{\1\}" % re.escape(lab), v, re.S)
            if m:
                sec[k] = v.replace(m.group(0), "")
                moved.append((title, m.group(0)))
                break
        else:
            raise KeyError(lab)
    S_ = lambda k: clean(sec[k])
    lim = S_(extra["limits"])
    lim, _, repro = lim.partition("\\textbf{Reproducibility.}")
    parts = [preamble(tex),
             "\\section{1. Introduction}", S_("Introduction"),
             "\\section{2. Related Work}", extra["related"](sec),
             "\\section{3. Methods}", S_(extra["methods"]),
             "\\section{4. Results}", S_("Results"),
             "\\section{5. Discussion and Limitations}", extra["discussion"](sec),
             "\\subsection{Limitations}", lim,
             "\\subsection{Future Work}", extra["future"],
             "\\section{6. Conclusion}", extra["conclusion"],
             "\\section{Code and Data}", extra["code"], "\n\n" + repro.strip(),
             "\\section{Author Contributions}", "M.K. is the sole author; see the LLM Usage Statement for how an AI assistant was used.",
             "\\section{References}", sec["References"],
             "\\section{Appendix}"] + [f"\\subsection{{{chr(65 + i)}. {k[0].upper() + k[1:]}}}" + clean(sec[k])
                                 for i, k in enumerate(extra["appendix"])] + [
             f"\\subsection{{{chr(65 + len(extra['appendix']) + i)}. {t}}}" + clean(f) for i, (t, f) in enumerate(moved)] + [
             "\\section{LLM Usage Statement}", LLM, "\\end{document}"]
    open(out, "w").write("\n".join(parts))


P1 = dict(
    limits="Limitations", methods="Setting and method",
    related=lambda s: clean(s["Related work"]),
    discussion=lambda s: clean(s["Discussion"]),
    future=("A per-pair detector for small registries (the 4--6 writer channels our sandbox agents built), with its own "
            "false-alarm rate; calibration on a busy real shared resource; a disguise that squats real package names; "
            "and running the audit on an evaluation cluster's own logs as a pre-flight check."),
    conclusion=("A content-free write$\\to$read graph, calibrated to a known false-alarm rate, finds agent message boards "
                "in shared infrastructure earlier than the signals that surfaced the July 2026 incident: in 9 of 9 "
                "simulated conditions on two seed sets, and within ten minutes on the real public log of the wiki that "
                "3{,}010 agents used as a board. It needs no access to content, survives a filename disguise, and fails "
                "where we say it fails: channels of only a handful of agents, and calibration on busy real traffic, "
                "which we could not test. Operators can apply it today to any surface where one principal's writes are "
                "visible to another."),
    code=("\\begin{itemize}\\item Code repository: \\url{https://github.com/kaiser-data/agent-channel-audit}"
          "\\item Data: simulated logs are regenerated by the code; the real arm uses the public request log at "
          "\\url{https://www.wikiservice.at/dse/} (pseudonymised on ingest, not redistributed) and collusion.wiki's public release."
          "\\item Other artifacts: explainer video (3:02) in the repository, \\texttt{video/out/agent-channel-audit-16x9.mp4}"
          "\\end{itemize}"),
    appendix=["Limitations and dual-use / ethical considerations", "Protocol deviations"],
    secrefs={"sec:limits": "5", "app:dev": "B"},
    to_appendix=[("tab:preds", "Predictions across every run")],
    subs=[("width=\\linewidth]{fig2-real-wiki", "width=0.65\\linewidth]{fig2-real-wiki"),
          ("width=\\linewidth]{fig1-participants", "width=0.9\\linewidth]{fig1-participants")],
)
P2 = dict(
    limits="Limitations", methods="Sandbox and design",
    related=lambda s: clean(s["Discussion"].split("\\paragraph{Related work.}")[1]),
    discussion=lambda s: clean(s["Discussion"].split("\\paragraph{Related work.}")[0]),
    future=("Run the frozen panel (Claude Haiku, GPT, Gemini, Mistral) once API credit allows; offer less obvious "
            "alternative surfaces (object names, timing, metadata); close channels repeatedly to study adaptation; "
            "and measure whether a content-free write$\\to$read detector flags the displaced channel."),
    conclusion=("Closing an agent channel is not the end of an incident. In our sandbox, every run that had built a "
                "channel in a shared cache moved it to a CI dashboard within about one round once the cache was "
                "closed, and coordination continued at the same level; only when no other writable surface existed "
                "did coordination stop. The practical response is the one covert-channel analysis recommends: list "
                "every surface one agent can write and another can read, and close or monitor them together."),
    code=("\\begin{itemize}\\item Code repository: \\url{https://github.com/kaiser-data/channel-displacement}"
          "\\item Data: all 160 scored runs, the pilot and the 2 OpenRouter runs, with full transcripts, are in the repository."
          "\\item Companion project: \\url{https://github.com/kaiser-data/agent-channel-audit}"
          "\\item Other artifacts: explainer video (2:31) in the repository, \\texttt{video/out/channel-displacement-16x9.mp4}"
          "\\end{itemize}"),
    appendix=["Limitations and dual-use / ethical considerations"],
)

build(f"{S}/docx.tex", f"{S}/tpl/p1_body.tex", P1)
build(f"{S}/p2docx.tex", f"{S}/tpl/p2_body.tex", P2)
for n, src in (("p1", "/Users/marty/claude-projects/research/swarm-alignment/agent-channel-audit/paper/main.tex"),
               ("p2", "/Users/marty/claude-projects/research/swarm-alignment/channel-displacement/paper/main.tex")):
    t = open(src).read()
    ab = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", t, re.S).group(1).replace("\\noindent", "").replace("\\wrr{}", "write$\\to$read")
    txt = subprocess.run(["pandoc", "-f", "latex", "-t", "plain", "--wrap=none"], input=ab, capture_output=True, text=True).stdout
    open(f"{S}/tpl/{n}_abstract.txt", "w").write(txt.strip())
print("ok")
