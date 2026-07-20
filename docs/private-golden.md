# Hiding the golden set (private evaluation corpus)

The golden dv/v benchmark is **generated**, not stored. That single fact drives
everything below, and it cuts against the usual advice about private datasets.

> Hiding the arrays, or the seeds, hides nothing.

A case's ground-truth `dv/v(t)` is a pure function of its `amp` numbers
(amplitude, phase, drop, healing timescale, trend, event onset). In the public
package those come from the published `golden.AMP` table, so the truth is
reconstructible from public source alone. The seed only randomizes the coda and
the measurement noise:

```python
days  = golden._days(case["years"])
guess = golden.MOTIF[case["motif"]](days, golden.AMP[case["use_case"]])
np.allclose(guess, golden.generate(case["id"])["truth"])   # True, no seed used
```

Privacy therefore rests on three things, in this order.

---

## 1. Never hand the truth to the model

`golden.generate()` returns `truth` next to the data. That is right for the
scorer and for plotting, and **fatal** for a model under evaluation: on the
`dvv_series` task an agent given `generate()` can just return `d["truth"]` and
score a perfect 1.0.

Anything an agent touches must go through the observables-only view:

```python
golden.observed(case_id)   # {ccfs, t, days, fs, use_case, grade[, channels]}
                           # TRUTH_KEYS are stripped
```

The FrugalMind `dvv_series` prompt points at `observed()`. If you mount codameter
into an eval sandbox, hand it a truth-free artifact, **never** the golden dir.

## 2. Give the hidden cases secret truth parameters

A hidden case carries its own `amp` block, drawn from a **secret**, which
overrides the public table (`golden.amp_for`). Then the reconstruction above
fails and the agent has to actually measure dv/v.

```bash
python -m codameter.private_golden \
    --secret "$CODAMETER_GOLDEN_SECRET" \
    --out ./hidden-golden
# -> hidden-golden/cases.json      (recipes, each with its secret `amp`)
# -> hidden-golden/manifest.json   (frozen expected metrics for those recipes)
```

`--jitter` sets the spread on the amplitudes; the seasonal phase and the event
onset are fully randomized, so even *when* the earthquake happens is unknown.

## 3. Keep the recipes out of the public repo

The recipes **are** the dataset. The repo ships only a small public sample
(`golden.PUBLIC_SAMPLE_IDS`: one case per grade) for development, tests,
tutorials and the paper figures. `load_cases()` uses
`<CODAMETER_GOLDEN_DIR>/cases.json` when present, else the public sample.

---

# Store the secret, not the dataset

Because the corpus is a **pure function of the secret**, you do not need to host
it at all. Regenerate it inside the eval job:

```yaml
# .github/workflows/eval.yml  (excerpt)
on:
  workflow_dispatch:          # never `pull_request` from forks: secrets are
  schedule: [{cron: "0 6 * * 1"}]   # withheld there, and rightly so
  push: {branches: [main]}

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install "codameter>=0.3"

      - name: Materialize the hidden golden set
        env:
          CODAMETER_GOLDEN_SECRET: ${{ secrets.CODAMETER_GOLDEN_SECRET }}
        run: |
          python -m codameter.private_golden \
              --secret "$CODAMETER_GOLDEN_SECRET" \
              --out "$RUNNER_TEMP/hidden-golden"
          echo "CODAMETER_GOLDEN_DIR=$RUNNER_TEMP/hidden-golden" >> "$GITHUB_ENV"

      - name: Run the eval
        run: ...        # the scorer picks up CODAMETER_GOLDEN_DIR
```

One repository secret. No dataset repo, no access token, no bucket.

## Why this is reproducible

`corpus = f(secret, codameter_version)` — a deterministic function, with no
network and no mutable state:

- **Byte-identical.** The same secret and the same codameter version regenerate
  the same `cases.json` and the same expected metrics, on any machine, forever.
  Scores are comparable across runs because the corpus cannot drift.
- **Verifiable, and publishable as a commitment.** You can publish the SHA-256 of
  `cases.json` in the repo *without publishing its contents*. That pins the
  benchmark cryptographically: anyone holding the secret can check you did not
  quietly change the corpus after seeing a model's results. A hosted file gives
  you no such proof unless you separately pin its revision.
- **Version-coupled by construction.** If codameter's synthesis code changes, the
  expected metrics are recomputed in the same job, so the oracle can never go
  stale against the code. A hosted `manifest.json` silently can.

A hosted artifact is reproducible only if it is *immutable and pinned*. Pull it
from `main` and it can change under you without anyone noticing.

## Why this is safe

- **Nothing at rest.** The corpus exists only in the runner's temp directory for
  the life of the job. There is no bucket to misconfigure, no repo to
  accidentally flip public, no `--local-dir` copy left on a laptop.
- **One credential, not two artifacts.** The attack surface is a single secret,
  versus (a long-lived read token) x (a hosted artifact) x (its ACL).
- **Rotation is free.** Change the secret and the corpus is new. With hosting you
  must regenerate, re-upload, and invalidate the old copy and its token.
- **Nothing to cache.** Which is good, because you must **not** cache it (below).

### The rules that matter more than the token scope

1. **Never let the credential into the agent sandbox.** This is the real leak
   vector. A model that can read `CODAMETER_GOLDEN_SECRET` (or an HF token) can
   regenerate or download the hidden corpus and read the truth. The credential
   belongs to the **scorer/orchestrator** process; the sandbox gets only the
   truth-free arrays from `golden.observed()`.
2. **Never run the secret-bearing workflow on untrusted fork PRs.** GitHub
   withholds secrets from fork `pull_request` runs on purpose. Do not "fix" that
   with `pull_request_target`. Gate the eval on `workflow_dispatch`, `schedule`,
   or `push` to a protected branch.
3. **Never cache the generated corpus.** Actions caches are reachable across
   branches, so caching secret-derived data undoes the whole scheme. Regenerating
   costs a few minutes; an eval's model calls cost far more.

## The cost, stated plainly

Regenerating the hidden manifest runs the full pipeline over the hidden cases:
**~2-3 minutes** per eval run. That is the entire price of not hosting anything.

## When you *do* need to host it

The secret-only flow works because this corpus is **cheap to generate and fully
determined by code + secret**. Host the data instead when that stops being true:

| Situation | Why deriving fails | What to do |
| --- | --- | --- |
| The golden data is **real** (field recordings, human labels) | It is not a function of any seed | Host it; pin a revision |
| Generation is **expensive** (long simulations, huge corpora) | Regenerating per run is wasteful or infeasible | Host it; pin a revision |
| The eval runs **outside GitHub** (e.g. AWS Batch) | No Actions secret | Still a *secret*, just in AWS Secrets Manager -- not a hosted dataset |
| **External parties** submit models you score | Someone must hold the corpus | Private HF dataset + a read-only, repo-scoped token |

If you host, the same invariants apply, plus one: **pin the revision**
(`huggingface-cli download --revision <sha>`), or your benchmark can move under
you. See FrugalMind's `docs/golden_data_provisioning.md` for that path.
