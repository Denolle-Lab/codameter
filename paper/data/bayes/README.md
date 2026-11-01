# Checks of the Bayesian measurement model (audits UQ-03 and UQ-04)

Both files are produced from the manuscript's Fig. 14 realisation
(`codameter.uq_bayes._build_bayes`: seed 55, 2.5 years, SNR 7, 4-day cadence,
12-member ensemble).

- `duplication_check.json`, from `scripts/check_ensemble_duplication.py`: the
  credible band on mu, the C_d scale, s, tau and the share of the precision of
  mu supplied by the smoothness prior, for the ensemble as measured and with
  every member duplicated and quadrupled.
- `cd_whitening.json`, from `scripts/check_cd_whitening.py`: raw and whitened
  lag autocorrelations of the member residuals about mu, the whitened variance
  under the full C_d and under its diagonal alone.

Rerun the two scripts to regenerate; each takes a few minutes.
