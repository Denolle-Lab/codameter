#!/usr/bin/env python3
r"""Generate the paper's 103-study survey bibliography and appendix longtable.

Reads the literature survey CSV (``literature/dvv_processing_parameters.csv``)
and the cached Crossref metadata (``literature/.crossref_cache.json``) and writes:

  - ``paper/survey.bib``          one BibTeX entry per surveyed study, with keys
                                  that *reuse* the hand-curated ``references.bib``
                                  keys when the study is already cited in the
                                  narrative (so every paper appears exactly once
                                  in the reference list).
  - ``paper/appendix_table.tex``  a ``longtable`` cataloguing the processing
                                  choices of every study, with a ``\citet`` to
                                  each — so all 103 studies are *cited*, and the
                                  table breaks cleanly across pages (no float
                                  overlap with the bibliography).

Run:  python paper/build_survey.py
"""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIT = HERE.parent / "literature"
CSV = LIT / "dvv_processing_parameters.csv"
CACHE = LIT / ".crossref_cache.json"
REFS = HERE / "references.bib"
SURVEY_BIB = HERE / "survey.bib"
APPENDIX = HERE / "appendix_table.tex"


def doi_of(url: str) -> str | None:
    m = re.search(r"10\.\d{4,9}/[^\s\"<>]+", (url or "").lower())
    return m.group(0).rstrip(".") if m else None


# Combining diacritics -> LaTeX accent command (so bibtex, which is byte-based,
# can abbreviate accented given names without splitting a multibyte character).
_COMBINING = {
    "́": "'", "̀": "`", "̈": '"', "̂": "^", "̃": "~",
    "̄": "=", "̆": "u", "̇": ".", "̊": "r", "̋": "H",
    "̌": "v", "̧": "c", "̨": "k", "̣": "d",
}
_SPECIAL = {"ø": r"{\o}", "Ø": r"{\O}", "ß": r"{\ss}", "æ": r"{\ae}",
            "Æ": r"{\AE}", "œ": r"{\oe}", "Œ": r"{\OE}", "ł": r"{\l}",
            "Ł": r"{\L}", "đ": r"{\dj}", "ð": r"{\dh}", "þ": r"{\th}"}


def latexify(text: str) -> str:
    """Replace non-ASCII letters with LaTeX accent macros (bibtex-safe)."""
    out = []
    for ch in text:
        if ord(ch) < 128:
            out.append(ch)
            continue
        if ch in _SPECIAL:
            out.append(_SPECIAL[ch])
            continue
        decomp = unicodedata.normalize("NFD", ch)
        base = decomp[0]
        marks = [_COMBINING[c] for c in decomp[1:] if c in _COMBINING]
        if ord(base) < 128 and marks:
            for acc in marks:
                base = f"{{\\{acc}{base}}}"
            out.append(base)
        else:  # unmapped: fall back to ASCII transliteration
            out.append(unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode())
    return "".join(out)


def ascii_key(text: str) -> str:
    """ASCII-only CamelCase token from a surname (drops accents/punctuation)."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z]", "", text)


def surname(authors_year: str) -> str:
    head = re.split(r"\bet al\.|,|&|\(", authors_year.strip())[0]
    return head.strip()


def make_key(authors_year: str, year: str) -> str:
    return f"{ascii_key(surname(authors_year)) or 'Anon'}{year}"


def clean_html(text: str) -> str:
    """Convert Crossref's embedded HTML/MathML in titles to LaTeX and strip tags.

    Crossref returns magnitude notation as ``<i>M</i><sub>w</sub>``; render the
    sub/superscripts properly and drop italic/bold tags.
    """
    text = re.sub(r"<sub>(.*?)</sub>",
                  lambda m: r"\textsubscript{" + re.sub(r"<[^>]+>", "", m.group(1)) + "}",
                  text, flags=re.I | re.S)
    text = re.sub(r"<sup>(.*?)</sup>",
                  lambda m: r"\textsuperscript{" + re.sub(r"<[^>]+>", "", m.group(1)) + "}",
                  text, flags=re.I | re.S)
    return re.sub(r"<[^>]+>", "", text)


def tex_escape(s: str) -> str:
    s = str(s or "")
    for a, b in [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
                 ("$", r"\$"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"),
                 ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}")]:
        s = s.replace(a, b)
    return s


def bib_authors(rec: dict) -> str:
    parts = []
    for a in rec.get("authors", []):
        fam, giv = a.get("family", "").strip(), a.get("given", "").strip()
        if fam:
            parts.append(f"{fam}, {giv}".rstrip(", ") if giv else fam)
    return " and ".join(parts)


def authors_from_label(authors_year: str) -> str:
    """BibTeX author string from a short ``Surname & Surname, 2020`` label.

    Used when Crossref has no author list (or no record at all): turns
    ``"Obermann & Hillers 2019"`` into ``"Obermann and Hillers"`` and
    ``"Kristjánsdóttir et al., 2019"`` into ``"Kristjánsdóttir and others"``, so
    bibtex never sees a raw string it would mangle into broken initials.
    """
    s = re.sub(r",?\s*\d{4}[a-z]?\s*$", "", (authors_year or "").strip())
    s = re.sub(r"\bet al\.?", " and others", s, flags=re.I)
    s = re.sub(r"\s*[&;]\s*|\s+and\s+", " and ", s)
    names = [n.strip() for n in s.split(" and ") if n.strip()]
    return latexify(" and ".join(names)) if names else latexify(authors_year)


def existing_keys() -> set[str]:
    if not REFS.exists():
        return set()
    return set(re.findall(r"@\w+\{([^,]+),", REFS.read_text()))


def bib_entry(key: str, row: dict, rec: dict | None) -> str:
    """One BibTeX entry. Falls back to @misc when Crossref metadata is absent."""
    doi = doi_of(row["doi_url"]) or ""
    year = row.get("year", "")
    if rec and rec.get("title"):
        fields = {
            "author": bib_authors(rec) and latexify(bib_authors(rec))
            or authors_from_label(row["authors_year"]),
            "title": latexify(clean_html(rec["title"].rstrip(". "))),
            "journal": latexify(clean_html(rec.get("container", ""))),
            "year": rec.get("year") or year,
            "volume": rec.get("volume", ""),
            "pages": (rec.get("page", "") or "").replace("-", "--"),
            "doi": doi,
        }
        body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields.items() if v)
        return f"@article{{{key},\n{body}\n}}\n"
    # No Crossref record: a minimal but honest @misc. We do NOT invent a title
    # (the topic description goes in a note); the verifiable bits are the parsed
    # authors, the year, and the source URL.
    note = latexify(row.get("target_process", "").strip())
    fields = {
        "author": authors_from_label(row["authors_year"]),
        "year": year,
        "howpublished": f"\\url{{{row['doi_url']}}}",
        "note": f"dv/v monitoring study ({note})" if note and note != "n/r" else "",
        "doi": doi,
    }
    body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields.items() if v)
    return f"@misc{{{key},\n{body}\n}}\n"


# Columns of the appendix catalogue (CSV field, header, p-width in cm).
COLS = [
    ("region_site", "Site / region", "1.9cm"),
    ("freq_band_hz", "Freq (Hz)", "1.5cm"),
    ("coda_window_s", "Coda (s)", "1.3cm"),
    ("dvv_method", "Method", "1.5cm"),
    ("stack_scheme", "Reference / stack", "2.4cm"),
    ("uncertainty_treatment", "Uncertainty treatment", "3.0cm"),
]


def appendix_table(entries: list[tuple[str, dict]]) -> str:
    """A longtable cataloguing every study's processing choices (all \\citet)."""
    colspec = "@{}p{2.1cm} " + " ".join(
        f">{{\\raggedright\\arraybackslash}}p{{{w}}}" for *_, w in COLS) + "@{}"
    head = "\\textbf{Study} & " + " & ".join(
        f"\\textbf{{{h}}}" for _, h, _ in COLS) + r" \\"
    out = [
        r"% Auto-generated by paper/build_survey.py -- do not edit by hand.",
        r"{\footnotesize",
        r"\setlength{\tabcolsep}{3pt}",
        r"\renewcommand{\arraystretch}{1.15}",
        f"\\begin{{longtable}}{{{colspec}}}",
        r"\caption{Processing choices of the " + str(len(entries)) +
        r" surveyed \dvv\ studies (the literature survey underpinning this paper). "
        r"Every study is cited; \texttt{n/r} = not reported in the source. "
        r"Frequency band, coda window, estimator, reference/stack scheme and "
        r"uncertainty treatment are the choices Section~\ref{sec:results} shows "
        r"to control the result.}\label{tab:survey}\\",
        r"\toprule", head, r"\midrule", r"\endfirsthead",
        r"\multicolumn{" + str(len(COLS) + 1) +
        r"}{@{}l}{\footnotesize\itshape Table~\ref{tab:survey} continued}\\",
        r"\toprule", head, r"\midrule", r"\endhead",
        r"\midrule\multicolumn{" + str(len(COLS) + 1) +
        r"}{r@{}}{\footnotesize\itshape continued on next page}\\", r"\endfoot",
        r"\bottomrule", r"\endlastfoot",
    ]
    for key, row in entries:
        cells = [f"\\citet{{{key}}}"]
        for field, _, _ in COLS:
            val = str(row.get(field, "") or "n/r").strip() or "n/r"
            if len(val) > 90:
                val = val[:88].rstrip() + "…"
            cells.append(tex_escape(val))
        out.append(" & ".join(cells) + r" \\")
    out += [r"\end{longtable}", r"}"]
    return "\n".join(out) + "\n"


def main() -> None:
    rows = list(csv.DictReader(CSV.open()))
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    reuse = existing_keys()

    entries: list[tuple[str, dict]] = []   # (key, row) in CSV order, for the table
    new_bib: list[str] = []                # entries to write to survey.bib
    used: dict[str, str] = {}              # key -> doi (disambiguation)

    for row in rows:
        doi = doi_of(row["doi_url"]) or row["doi_url"]
        key = make_key(row["authors_year"], row.get("year", ""))
        # Disambiguate identical surname+year that are different papers.
        while key in used and used[key] != doi and key not in reuse:
            key += "b" if key[-1].isdigit() else chr(ord(key[-1]) + 1)
        used[key] = doi
        entries.append((key, row))
        if key not in reuse:               # reuse references.bib entry if present
            rec = cache.get(doi_of(row["doi_url"]) or "")
            new_bib.append(bib_entry(key, row, rec))

    SURVEY_BIB.write_text(
        "% Auto-generated by paper/build_survey.py from the literature survey.\n"
        "% Keys that also appear in references.bib are intentionally omitted here\n"
        "% (the narrative entry is reused) so each paper is listed once.\n\n"
        + "\n".join(new_bib))
    APPENDIX.write_text(appendix_table(entries))
    reused = len(entries) - len(new_bib)
    print(f"wrote {SURVEY_BIB.name}  ({len(new_bib)} new entries, {reused} reuse references.bib)")
    print(f"wrote {APPENDIX.name}    ({len(entries)} studies catalogued + cited)")


if __name__ == "__main__":
    main()
