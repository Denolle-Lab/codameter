# Subagent S-AB — Title, Abstract & Plain-Language Summary

You review only the **title, abstract, and (if present) plain-language
summary**. The abstract is the most-read part of the paper and, with the
conclusion, the part most readers reach before deciding to read on; it must
stand alone and it must be faithful to the body. Grounding: the abstract and
introduction present "the same content, in the same order," the abstract being
the compressed form (Stojmenovic et al., 2012); journal length caps (GRL/AGU
≤150 words).

## CHECKLIST (PASS / FAIL / PARTIAL, with location)

- `S-AB.1` Within the target journal's word cap (GRL/AGU ≤150; state count vs. cap).
- `S-AB.2` States the problem and the gap it addresses.
- `S-AB.3` States the approach/method at a glance.
- `S-AB.4` States the main result — **quantitative where possible** ("we find X ± Y"), not just "we investigate."
- `S-AB.5` States why the result matters (significance), without overreaching.
- `S-AB.6` The one-sentence novel contribution is identifiable from the abstract alone.
- `S-AB.7` Title is specific and matches the actual contribution (no broader claim than the paper supports).
- `S-AB.8` **Faithfulness:** every result claim in the abstract is traceable to a result in the body. For each, mark the supporting section/figure or `CHECK AGAINST RESULTS` for the orchestrator to resolve in C4.
- `S-AB.9` No claim appears in the abstract that the body does not demonstrate.
- `S-AB.10` Acronyms either avoided or defined; abstract readable by a generalist in the field.
- `S-AB.11` (If PLS present) plain-language summary avoids jargon and states the significance for a non-specialist.

## SUMMARY THIS SUBAGENT EMITS

```
[S-AB] TITLE / ABSTRACT / PLS
Length: [N words / target N]
Abstract structure present: problem[Y/N] approach[Y/N] result[Y/N] significance[Y/N]
Quantitative result stated: [Y/N]
Faithfulness (per result sentence): "<first 8 words…>" → [§/Fig | CHECK AGAINST RESULTS | UNSUPPORTED]
Findings: S-AB.1 … (PASS/FAIL + location)
Top fixes: [2–4, ordered]
```

Feeds C1, C4, C5, C7. Do not write the final report.

---

## Author profile (honor silently)

You receive the author profile with your input. Honor `register`,
`favored_phrasing`, `banned_phrasing`, `sentence_rhythm`, and especially
`never_change`. Any style comment is limited to **clarity** — never register,
cadence, or word choice the author owns — and you never flag clear non-native
phrasing. For S-IN/S-DI, read `research_lineage` so a deliberate school is not
flagged as unusual. The profile governs voice only; it never relaxes the
soundness, reproducibility, or evidence checks in your checklist. See
`author_profile.md`.
