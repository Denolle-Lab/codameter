# Report format

Emit a compact, reproducible recommendation. Plain voice, no emojis, no
em-dashes. Use the numbers you actually got in Step 3; do not round away a real
difference or invent one that is not there.

## Structure

1. **Use case** — one line naming the resolved application and the key fields the
   user gave.

2. **Recommended config** — the dict and a YAML block:

   ```yaml
   estimator: stretching (TS)
   band: [0.4, 1.0]        # Hz
   window: [10, 30]        # s lapse
   stack: 10               # days
   reference: fixed
   gate: true
   eps_max: 0.06           # stretching search half-width
   ```

3. **Why** — one line per axis, each with its driver and a citation from
   `USE_CASES[key]`. Name the one or two axes that matter most for this use case.

4. **Validation** — the table from Step 3:

   | Config | RMS vs truth | Recovered signal |
   | --- | --- | --- |
   | recommended | 0.024 % | drop -0.40 % (true -0.40 %) |
   | user / naive | 0.31 % | drop -0.18 % |

   State the ratio and what it means in one sentence. If a factorial was run, add
   the top variance-driving axis.

5. **Reproduce** — a short snippet the user can paste:

   ```python
   from codameter import use_cases as uc, golden
   from codameter.deviations import run_pipeline
   key = "volcano"
   d = golden.generate(golden.MAINSTREAM_BY_USE_CASE[key])
   dvv, valid = run_pipeline(d["ccfs"], d["t"], d["fs"],
                             uc.recommend(key), eps_max=uc.eps_max(key))
   ```

6. **One caveat** — the `key_rule` for this use case, verbatim in substance (for
   example, for a volcano: correct for rainfall before reading a pre-eruptive
   signal).

## Tone

The user is a scientist tuning their own pipeline, not being graded. Give the
recommendation as a defensible default plus the evidence, and be explicit that
they should cross-check on their own data with more than one estimator.
