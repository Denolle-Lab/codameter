# Live review ledger

`codameter-gji.review.json` is the manifest the pre-submission-reviewer skill reads at Step 0.5 and rewrites at Step 5. It is the live state of the review loop: iteration count, readiness, and the per-finding ledger with reconciliation verdicts.

It was converted on 2026-09-10 from Astra's iteration-1 manifest at `review/codameter-gji.review.json`, which stays frozen as the original record together with the three reports and the evidence directory. The converter is not checked in; the `conversion_note` field lists exactly what was added (section, scope, plan_package, hash_method, manuscript_ref, open) and what was renamed (verification to execution_evidence). No finding text, tier, status, or ID was changed.

Running iteration 2:

- The skill needs a diff of the manuscript against the reviewed version. Produce it with `git diff b6dbbd0 -- paper/manuscript_marine.qmd`, or a before/after pair from `git show b6dbbd0:paper/manuscript_marine.qmd`.
- `manuscript_hash` is the sha256 of the raw file bytes, no normalization. Recompute the same way.
- The `scope` field names the subagents that own each finding, so unchanged scopes carry their verdicts forward and changed ones are re-dispatched.
- Closure evidence for code findings is a re-run of `review/evidence/audit_probes.py` and `downstream_probes.py`; their committed JSON is the before state.
- Do not hand-edit statuses. A C2/C3/C4 finding closes only when changed text or code demonstrably fixes it.

The local skill is v2.5; the review ran under v2.4. Expect new register findings in an `INTRODUCED-BY-RECALIBRATION` bucket rather than as regressions.
