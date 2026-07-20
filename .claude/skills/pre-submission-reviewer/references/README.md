# Subagent registry — orientation

Each file here is the system prompt for one subagent dispatched by `SKILL.md`.
They share one contract: read a defined scope of the manuscript against an
evidence-grounded checklist, emit a single findings block keyed by the
subagent's ID, and **never write the final report** — the orchestrator
synthesizes the blocks into the 8-criterion rubric.

| File | ID | Scope | Evidence base |
|---|---|---|---|
| `section_abstract.md` | S-AB | Title, abstract, plain-language summary | Stojmenovic 2012; journal length caps |
| `section_introduction.md` | S-IN | Introduction | Swales 3-move (Knight 2020; Lam 2012); Zelst 2022; Verdecchia 2025; Neto 2023 |
| `section_methods.md` | S-ME | Methods / Data & Methods | Six-question (Kallet); Zelst 2021/2022; GPF (Gil 2016) |
| `section_results.md` | S-RE | Results | Zelst 2022; IMRAD neutral-reporting guidance |
| `section_discussion.md` | S-DI | Discussion | Discussion moves; Jara 2021; Hillier 2021 |
| `section_conclusions.md` | S-CO | Conclusions | Pols seven elements |
| `section_figures_data.md` | S-FD | Figures, tables, captions, equations (cross-cutting) | Kallestinova; GPF 20 best practices |
| `section_reproducibility.md` | S-RP | Whole computational workflow | NASEM 2019/2022; Tennant & Ross-Hellauer 2020; GPF |
| `section_citation_diversity.md` | S-CD | Whole reference list — citation & idea diversity | Dworkin/Zurn/Bassett 2020; Zurn/Bassett/Rust 2020 (CDS); Teplitskiy 2022; `cleanBib`, OpenAlex |
| `section_prose_register.md` | S-PR | Whole manuscript (prose, captions, titles) — scientific-register / colloquialism scan | complements `plain-voice` skill (LLM-tell lexicon); scoped exception to the anti-homogenization voice-guard |
| `section_author_verification.md` | S-AV | **Interactive examination of the authors** — data/signal-processing choices first, then method, claims, interpretation, limitations, novelty, figures | oral-exam / accountability design; certifies process, not competence |
| `author_profile.md` | — | Per-author voice profile (persona layer) consumed by all subagents | Doshi & Hauser 2024; Padmakumar & He 2024; Agarwal et al. 2025 |
| `review_manifest.md` | — | Provenance + iteration-state schema (Issue Ledger, reconciliation verdicts, disclosure stamp, Author Verification log) read at Step 0.5 / written at Steps 5–6 | not a subagent — the state spine for incremental re-review |

Section subagents are grounded in the ASTA best-practice / evidence-based
guideline reviews for each section (Best_Practices_* and EvidenceBased_*).
S-RP owns Criterion 3 and adds the constructive reproduction dry-run. S-CD
surfaces citation/idea diversity for C6 and the C1 novelty guardrail — it never
scores or quotas. S-PR feeds C5 by flagging colloquial/non-scientific diction as
author-facing candidates (never rewrites, never lowers a tier for a few slips); it
is the one subagent permitted to comment on register, and only from its defined
lexicon. `author_profile.md` and the `profiles/` folder hold the
persona layer; every subagent honors it for voice, and it can never override the
soundness, reproducibility, or evidence checks.

**S-AV is the exception to the contract above.** It is *not* dispatched in the
parallel fan-out, reviews the *authors* rather than the text, feeds no criterion,
and produces a transcript instead of a findings block. It runs interactively at
SKILL Step 6 and certifies process, not competence. Keep it out of the rubric
synthesis.
