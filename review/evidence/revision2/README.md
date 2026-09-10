# Revision-pass evidence

This directory records the Codex reconciliation after `62b63b5`.
It preserves earlier evidence under `review/evidence/closure/` and the
iteration-1 reports rather than replacing their outputs.

- `reconciliation.json`: all 37 findings with bounded assessments and limits.
- `code_changes.diff`: zero-context changes in this pass, relative to its starting HEAD.
- `manuscript_changes.diff`: zero-context manuscript changes since the original audit.
- `locked_calibration_checks.json`: hashes and summaries of the three locked
  200-realization runs; every recorded missing fraction is zero.
- `pytest.log`, `pytest.xml`: complete-suite execution on the revised source.
- `pre_commit.log`: configured formatter, linter and typing checks.
- `paper_build.log`: Quarto PDF rebuild, reusing committed figure assets.
- `manuscript_layout.txt`: text extracted from the final rendered PDF.
- `page_*.png`: selected full pages inspected for abstract typography,
  covariance wording, calibration-table readability, running headers and
  availability/end matter.
- `verification.json`: final checks, versions and source hashes.

Initial focused check: 32 passed in 154.97 seconds. The later full suite
includes the subsequently added moving-reference gate and geometry-cache
regressions. No locked 200-realization experiment was repeated in this pass;
those archived values were checked for compatibility with the missingness
correction. No raw field waveform or external figure was regenerated.

The formal reviewer manifest remains at iteration 1. This is a bounded
reconciliation, not a completed second nine-scope manuscript review.

Logs and extracted text have trailing whitespace normalized by repository hooks.
