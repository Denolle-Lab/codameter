# Hiding the golden set (private evaluation corpus)

The golden dv/v benchmark is **generated**, not stored. That has a consequence
most benchmark-privacy advice gets wrong here:

> Hiding the arrays, or the seeds, hides nothing.

A case's ground-truth `dv/v(t)` is a pure function of its `amp` numbers
(amplitude, phase, drop, healing timescale, trend, event onset). In the public
package those come from the published `golden.AMP` table, so the truth is
reconstructible from public source alone. The seed only randomizes the coda and
the measurement noise:

```python
days = golden._days(case["years"])
guess = golden.MOTIF[case["motif"]](days, golden.AMP[case["use_case"]])
np.allclose(guess, golden.generate(case["id"])["truth"])   # True, no seed used
```

So privacy rests on three things, in this order.

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
python scripts/make_private_golden.py \
    --secret "$CODAMETER_GOLDEN_SECRET" \
    --out ./hidden-golden
# -> hidden-golden/cases.json      (recipes, each with its secret `amp`)
# -> hidden-golden/manifest.json   (frozen expected metrics for those recipes)
```

The secret is the only thing you must protect: the same secret reproduces the
same hidden corpus, a different one gives a different corpus. `--jitter` sets the
spread on the amplitudes; the seasonal phase and the event onset are fully
randomized, so even *when* the earthquake happens is unknown.

## 3. Keep the recipes out of the public repo

The recipes **are** the dataset. The repo ships only a small public sample
(`golden.PUBLIC_SAMPLE_IDS`: one case per grade) for development, tests,
tutorials and the paper figures. The evaluation corpus lives elsewhere and is
swapped in by pointing codameter at it:

```bash
huggingface-cli download <org>/codameter-golden-private \
    --repo-type dataset --local-dir ./hidden-golden
export CODAMETER_GOLDEN_DIR=$PWD/hidden-golden

python -c "from codameter import golden; print(len(golden.CASES), golden.IS_HIDDEN_SET)"
# 27 True
```

`load_cases()` uses `<CODAMETER_GOLDEN_DIR>/cases.json` when present, else the
public sample. No new dependency: the HF CLI does the fetch, codameter just reads
a directory. A private S3 prefix or a private git repo works identically -- sync
it to a directory and set the variable.

## Where to publish what

| Artifact | Where | Why |
| --- | --- | --- |
| Public sample (3 cases) + its manifest | in-repo, and Zenodo for a DOI | citable for the paper; enough to develop and run the tests against |
| Hidden corpus (`cases.json` + `manifest.json`) | **private** HF dataset (token-gated) | the recipes are the dataset; token in CI secrets |
| The secret | a secrets manager / CI secret | reproduces the corpus; losing it means regenerating it |

Do **not** put the hidden corpus on Zenodo: it is an open archive, and its
restricted-access mode is awkward to consume from CI.

## Caveats, stated plainly

- The 30 cases released in **v0.2.1 are already public**, seeds and `AMP` table
  included. They cannot be made private retroactively. A genuinely hidden set
  must be a *fresh* corpus with secret parameters, which is what
  `make_private_golden.py` builds.
- Secret parameters stop reconstruction, not exfiltration. If the agent can run
  arbitrary code with the private dir mounted, it can read `cases.json`. Isolate
  the sandbox from the golden dir.
- The *structure* stays public (motifs, depth bands, the grade taxonomy). That is
  intentional: the task is to measure dv/v well, not to guess the corpus.
