# Review manifest — provenance & iteration state

This file documents the **review manifest**: the JSON record that makes the
Pre-Submission Reviewer *stateful across drafts*. It is loaded in `SKILL.md`
Step 0.5, consumed throughout reconciliation mode, and rewritten in Step 5. It is
**not** a subagent — it has no `S-` ID and no checklist. It is the spine that lets
every iteration be a strict improvement on the last, and the provenance record
that lets us trace what was reviewed, by which version, and what changed.

---

## Why it exists

A stateless reviewer re-derives findings from scratch each run and surfaces a
different subset every time. That makes "every iteration is an improvement" and
"never raise issues not raised before" impossible to honor. The manifest fixes
this by persisting the **Issue Ledger** (the closed set of findings, keyed by
durable IDs) plus **provenance** (version, model, iteration, hash) so the next
run *reconciles* the prior findings instead of re-discovering them.

---

## Location & naming

By default one manifest per manuscript:

```
reviews/<manuscript-id>.review.json
```

`<manuscript-id>` is a stable slug the author chooses (e.g. `denolle2026-tremor`).
The orchestrator looks here in Step 0.5; if absent, this is iteration 1.

---

## Schema

```json
{
  "manuscript_id": "denolle2026-tremor",
  "title": "Deep tremor migration beneath the Olympic Peninsula",
  "skill_version": "2.3",
  "skill_commit": "59cc06b",
  "model": "claude-opus-4-8",
  "profile": "default",
  "target_journal": "GRL",
  "manuscript_type": "research article",
  "iteration": 3,
  "manuscript_hash": "sha256:1f3a…",
  "created": "2026-05-01",
  "updated": "2026-06-24",

  "history": [
    {"iteration": 1, "date": "2026-05-01", "model": "claude-opus-4-8", "skill_commit": "59cc06b",
     "readiness": "Major revision required", "open": 22, "manuscript_hash": "sha256:9b0c…"},
    {"iteration": 2, "date": "2026-06-10", "model": "claude-opus-4-8", "skill_commit": "59cc06b",
     "readiness": "Revise before submission", "open": 9, "manuscript_hash": "sha256:c44e…"}
  ],

  "ledger": [
    {
      "id": "S-ME.11",
      "criterion": "C2",
      "tier": "Fair",
      "status": "PARTIALLY ADDRESSED",
      "summary": "Sampling rate and taper for the cross-correlation are unstated.",
      "location": "Methods ¶3",
      "first_seen": 1,
      "last_changed": 3,
      "bucket": null
    },
    {
      "id": "S-RP.4",
      "criterion": "C3",
      "tier": "Fatal",
      "status": "NOT ADDRESSED",
      "summary": "No DOI for the processing code; 'available upon request' is non-compliant at AGU.",
      "location": "Data Availability",
      "first_seen": 1,
      "last_changed": 1,
      "bucket": null
    },
    {
      "id": "S-DI.7",
      "criterion": "C4",
      "tier": "Good",
      "status": "INTRODUCED-IN-REVISION",
      "summary": "New paragraph claims a depth dependence not shown in any figure.",
      "location": "Discussion ¶5 (added this revision)",
      "first_seen": 2,
      "last_changed": 2,
      "bucket": "INTRODUCED-IN-REVISION"
    }
  ]
}
```

### Field notes

- **`skill_version` / `model` / `profile` / `target_journal` / `manuscript_type`**
  — the provenance four-plus. If any changed since the last run, the orchestrator
  says so (a changed journal re-calibrates the bar; a changed profile changes
  voice handling).
- **`skill_commit`** — the short git SHA of the source commit (in the
  `academic-practice-agents` repo) the run's skill was loaded from
  (`git rev-parse --short HEAD` in that checkout, or read the `INSTALLED_FROM`
  file a deployed copy carries). `skill_version` says *what* release;
  `skill_commit` pins *exactly which bytes*, closing the gap when files were
  edited without bumping the version. The two together resolve to the release tag
  `presub-reviewer/v<skill_version>`. Record it at top level and in every
  `history` entry (a re-review may run under a newer commit). `"unknown"` is
  acceptable when the skill was not loaded from a git checkout (e.g. a stateless
  browser upload).
- **`iteration`** — monotonically increasing; incremented at Step 0.5 on every
  reconciliation run.
- **`manuscript_hash`** — `sha256` of the normalized manuscript text. Used to (a)
  confirm the draft actually changed, and (b) match a "current vs. prior" diff
  when the author supplies no explicit diff.
- **`history`** — append-only; one entry per past iteration with the readiness
  verdict and open-finding count, so the trajectory (22 → 9 → …) is visible.
- **`ledger`** — the closed set of findings. IDs are the same durable handles the
  subagents emit (`S-IN.4`, `C2.4`, `S-RP.4`). Each finding carries its current
  `status` and the iteration it was `first_seen` / `last_changed`.

### Status values (reconciliation verdicts)

| Status | Meaning |
|---|---|
| `OPEN` | First-review finding, not yet revised against |
| `RESOLVED` | Changed text demonstrably fixes it |
| `PARTIALLY ADDRESSED` | Improved but not closed |
| `NOT ADDRESSED` | Unchanged since raised |
| `REGRESSED` | Was better before; the revision worsened it |
| `INTRODUCED-IN-REVISION` | New defect in changed text (quarantine bucket) |
| `INTRODUCED-BY-RECALIBRATION` | New issue only because the target journal changed |

---

## Lifecycle

**Iteration 1 (no manifest).** Run the full review. Build the complete Issue
Ledger from the subagent findings, every item `OPEN`. Write the manifest with
`iteration: 1`, the provenance block, and the manuscript hash.

**Iteration N≥2 (manifest present).** Load it. Run Step 1.5 change detection.
For each ledger finding, assign a reconciliation verdict, citing changed text for
RESOLVED / REGRESSED. Add new findings only from changed spans, into the two
quarantine buckets. Apply the **monotonicity rule**: a finding may not move to a
worse tier than it held last iteration unless tied to changed text; the open set
should shrink or hold, not grow, except via the buckets. Append to `history`,
bump `iteration`, update `manuscript_hash` and `updated`, write back.

**Integrity guard.** A C2/C3/C4 finding is `RESOLVED` only when changed text fixes
it — never because an author asserts it or hand-edits the manifest. (Governance
rules 6–7.)

---

## Relationship to `changes.json`

`scripts/detect_changes.py` produces a `changes.json` (changed sections, changed
spans, `references_changed` / `methods_or_data_changed`, recommended re-dispatch
list). Step 1.5 consumes it to decide which subagents re-run. `changes.json` is
transient per-iteration scratch; the manifest is the durable record. Keep them
side by side (e.g. `reviews/<id>.changes.json` and `reviews/<id>.review.json`).

---

## AI-review disclosure stamp (in-paper)

Step 5 emits this for the manuscript's AI-use / Acknowledgments statement. It
records **process, not endorsement**. Fill the bracketed fields from the manifest:

> This manuscript was checked with the Denolle Group Pre-Submission Reviewer
> (v[skill_version], model [model]), an advisory AI tool, through [iteration]
> review iteration(s) prior to submission. All findings were reviewed and
> adjudicated by the authors. The tool does not run code, resolve links, or
> confirm results, and it does not endorse the manuscript's validity.

Do not reword this into a quality claim ("vetted," "validated," "approved"). It
attests only that the draft passed through the tool. **`skill_commit` is always
recorded in the manifest, but keep the in-paper stamp version-only for
readability** — the version maps to the release tag `presub-reviewer/v[skill_version]`,
and a reader who needs the exact bytes finds the SHA in the retained manifest.
(If a co-author wants it inline, `v[skill_version], commit [skill_commit]` is fine.)

---

## Author Verification log (`reviews/<id>.verification.json`)

The optional **Author Verification** pass (`S-AV`, SKILL Step 6) writes its own
record — a **sibling** of the review manifest, in the same provenance family but a
separate file, because it is a different axis (accountability, not quality) and
must never be mistaken for a quality score. One per manuscript:

```
reviews/<manuscript-id>.verification.json
```

It is a **transcript**, not a ledger: it records what was asked and answered, not
a set of findings to reconcile. It certifies **process, not competence** — see
governance rules 8–9. Schema:

```json
{
  "manuscript_id": "denolle2026-tremor",
  "skill_version": "2.4",
  "skill_commit": "7e5ab41",
  "model": "claude-opus-4-8",
  "manuscript_hash": "sha256:1f3a…",
  "mode": "LIVE",
  "answering_authors": ["A. Student"],
  "adjudicator": "M. Denolle",
  "grounded_in": "review iteration 2 inventory",
  "date": "2026-07-02",
  "coverage": {
    "workflow": true, "method": true, "claims": true, "interpretation": true,
    "limitations": true, "novelty": true, "figures": true
  },
  "topics": [
    {
      "id": "AV.1",
      "topic": "bandpass filter — phase choice",
      "location": "Methods ¶3",
      "covers": ["S-RP.R2", "S-ME.3"],
      "question": "You use a 2–8 Hz zero-phase bandpass. Why zero-phase and not causal here, and what happens to your arrival-time picks if you'd used causal?",
      "answer_verbatim": "…",
      "probe": null,
      "engagement": "ANSWERED-IN-OWN-WORDS"
    }
  ],
  "deferred_or_uncovered": [
    {"topic": "velocity-model choice", "route_to": "co-author B. Postdoc"}
  ]
}
```

### Field notes

- **`mode`** — `LIVE` (human-conducted oral exam, high integrity) or
  `TYPED` (degraded — answers entered in-session where a model could generate
  them). Never present `TYPED` as equivalent to `LIVE`.
- **`answering_authors` / `adjudicator`** — named humans. The adjudicator judges
  adequacy by reading the transcript; the agent never does. `adjudicator` may be
  `"self-attested"` when no separate human reviews it (weaker).
- **`grounded_in`** — the review iteration whose inventory seeded the questions, or
  `"standalone"` (thinner coverage; no prior review).
- **`skill_commit`** — same meaning as in the review manifest: the short source
  SHA the pass ran from, pinning the exact skill bytes to the tag
  `presub-reviewer/v<skill_version>`.
- **`engagement`** — one of `ANSWERED-IN-OWN-WORDS` / `PARTIAL` /
  `DEFERRED→<name>` / `DECLINED` / `DID-NOT-ADDRESS-Q`. This records **whether the
  question was answered, not whether the answer is correct**. There is no
  correctness or competence field, by design.

Unlike the review manifest, there is no reconciliation — an examination is a
point-in-time record. A new examination replaces the last; keep prior ones as
`reviews/<id>.verification.<date>.json` if a history is wanted.

---

## Author Verification Statement (in-paper)

Step 6 emits this for the manuscript's AI-use / Acknowledgments statement. Like
the AI-review disclosure stamp, it records **process, not competence** — that an
examination happened, never that the authors understand the work. Fill the
bracketed fields from the verification log:

> The authors completed a structured author-verification examination of this
> manuscript's data-processing, signal-processing, and interpretation choices
> (Denolle Pre-Submission Reviewer, Author Verification pass v[skill_version],
> [N] topics, [date], [live / typed]). The examination records the authors' own
> account of these choices for internal accountability; it does not certify their
> correctness and is not an endorsement of the manuscript.

Do not reword this into a competence or quality claim ("verified understanding,"
"authors demonstrated mastery," "human-validated"). It attests only that the
examination took place and that a record of the answers is retained. Whether to
include it in the paper at all is the authors' choice — the internal log stands on
its own. The `verification.json` records `skill_commit`; as with the review
stamp, keep the in-paper wording version-only and let the retained log carry the
exact SHA.

---

## Ledger for next iteration (copy-paste fallback)

Step 5 also prints the full ledger as a fenced block. In a CLI run this is
redundant with the JSON manifest, but it is the **only** way to carry state in a
session with no filesystem. Format:

```
LEDGER  (manuscript_id=denolle2026-tremor  iteration=3  skill=v2.3  model=claude-opus-4-8)
S-ME.11 | C2 | Fair | PARTIALLY ADDRESSED | Methods ¶3 | sampling rate/taper unstated
S-RP.4  | C3 | Fatal | NOT ADDRESSED      | Data Avail. | no code DOI
S-DI.7  | C4 | Good | INTRODUCED-IN-REVISION | Disc. ¶5 | unshown depth dependence
```

---

## Browser caveat (read this)

This reviewer is built for a **CLI / filesystem-backed agent** (Claude Code,
Codex, Cursor) because iteration requires persisting the manifest between runs.
**It is not meant for a stateless browser session (claude.ai Skills) past
iteration 1**: there is nowhere to store the ledger, so the no-new-issues and
monotonicity guarantees cannot be enforced automatically. If someone must use the
browser, the only path is to manually paste the *Ledger for next iteration* block
back in each time — treat that as a degraded fallback, not the supported workflow.
