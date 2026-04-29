r"""
Coupling decision tree.

Combines the per-tier diagnostics into an overall recommendation about
whether to use the linear superposition (Eq. 6) or escalate to a coupled
inversion (Eq. 19). All thresholds are exposed as module-level constants
that can be overridden.

Per the build plan §"Five technical risks", we ship two-tier diagnostics:

- **Soft warning** on Pe in [0.3, 3]
- **Hard escalate** on Pe in [0.1, 10]

In v0.1, only Tier 1 is wired up. The decision tree records which tiers it
*could not evaluate* so users know what's pending.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .tier1_poroelastic import drainage_peclet, frequency_dependent_beta_eff


# Default thresholds (can be overridden via Site config in future versions)
PE_SOFT_LOW = 0.3
PE_SOFT_HIGH = 3.0
PE_HARD_LOW = 0.1
PE_HARD_HIGH = 10.0


@dataclass
class CouplingReport:
    """Output of :func:`diagnose_all_tiers`."""

    tier1: dict[str, Any] = field(default_factory=dict)
    tier2: dict[str, Any] = field(default_factory=dict)
    tier3: dict[str, Any] = field(default_factory=dict)
    tier4: dict[str, Any] = field(default_factory=dict)
    soft_warnings: list[str] = field(default_factory=list)
    hard_escalations: list[str] = field(default_factory=list)
    deferred_tiers: list[str] = field(default_factory=list)

    @property
    def escalate(self) -> bool:
        """True if any tier triggered a hard escalation."""
        return len(self.hard_escalations) > 0

    @property
    def warn(self) -> bool:
        """True if any tier raised a soft warning."""
        return len(self.soft_warnings) > 0 or self.escalate

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier1": self.tier1,
            "tier2": self.tier2,
            "tier3": self.tier3,
            "tier4": self.tier4,
            "soft_warnings": self.soft_warnings,
            "hard_escalations": self.hard_escalations,
            "deferred_tiers": self.deferred_tiers,
            "escalate": self.escalate,
        }

    def __str__(self) -> str:
        lines = ["Coupling diagnostic report:"]
        lines.append(f"  Tier 1 (poroelastic): {self.tier1.get('status', 'n/a')}")
        for name in ("tier2", "tier3", "tier4"):
            t = getattr(self, name)
            status = t.get("status", "deferred")
            lines.append(f"  {name.title()}: {status}")
        if self.soft_warnings:
            lines.append("  Soft warnings:")
            for w in self.soft_warnings:
                lines.append(f"    - {w}")
        if self.hard_escalations:
            lines.append("  Hard escalations:")
            for e in self.hard_escalations:
                lines.append(f"    - {e}")
        lines.append(
            f"  Recommendation: "
            f"{'use Eq. 19 (coupled)' if self.escalate else 'use Eq. 6 (linear)'}."
        )
        return "\n".join(lines)


def escalation_decision(
    peclet: float,
    *,
    pe_soft_low: float = PE_SOFT_LOW,
    pe_soft_high: float = PE_SOFT_HIGH,
    pe_hard_low: float = PE_HARD_LOW,
    pe_hard_high: float = PE_HARD_HIGH,
) -> str:
    """Translate a single Pe value into an escalation level.

    Returns one of ``"safe"``, ``"warn"``, ``"escalate"``.
    """
    if pe_hard_low <= peclet <= pe_hard_high and not (
        pe_soft_low <= peclet <= pe_soft_high
    ):
        # Outer band but not inner: could still be safe; the convention
        # below treats the inner band [soft_low, soft_high] as warn,
        # the outer band [hard_low, hard_high] minus inner as escalate.
        return "escalate"
    if pe_soft_low <= peclet <= pe_soft_high:
        return "warn"
    if pe_hard_low <= peclet <= pe_hard_high:
        return "escalate"
    return "safe"


def diagnose_all_tiers(
    *,
    forcing_period_s: float,
    diffusion_length_m: float,
    diffusivity_m2_s: float,
    beta_drained: float,
    alpha_B_skempton: float,
    tidal_dvv: pd.Series | None = None,
    tidal_strain: pd.Series | None = None,
    earthquake_catalog: pd.DataFrame | None = None,
) -> CouplingReport:
    """Run all available tier diagnostics and combine into a report.

    Tiers 2--4 are deferred in v0.1 (see the per-tier modules). They are
    listed in :attr:`CouplingReport.deferred_tiers` so users know what
    additional information could be extracted in future versions.

    Parameters
    ----------
    forcing_period_s
        Dominant forcing period (s) — used for the drainage Péclet number.
    diffusion_length_m
        Kernel peak depth (m).
    diffusivity_m2_s
        Hydraulic diffusivity from Phase 1 (m^2/s).
    beta_drained
        Drained acoustoelastic coefficient from Phase 1.
    alpha_B_skempton
        Prior on alpha_B * B (typically 0.4--0.8).
    tidal_dvv, tidal_strain
        Optional sub-daily series for the tidal-:math:`\\beta` test.
    earthquake_catalog
        Optional catalog (deferred to v0.3 for Tier 2).

    Returns
    -------
    CouplingReport
    """
    report = CouplingReport()

    # ---------------- Tier 1 ----------------
    pe = drainage_peclet(forcing_period_s, diffusion_length_m, diffusivity_m2_s)
    decision = escalation_decision(pe)
    omega_drain = diffusivity_m2_s / diffusion_length_m**2  # rad/s
    omega_forc = 2.0 * 3.141592653589793 / forcing_period_s
    beta_eff_at_forc = float(
        frequency_dependent_beta_eff(
            omega_forc,
            beta_drained=beta_drained,
            alpha_B_skempton=alpha_B_skempton,
            omega_drain=omega_drain,
        )[0]
    )
    report.tier1 = {
        "status": decision,
        "drainage_peclet": float(pe),
        "omega_drain_rad_s": float(omega_drain),
        "beta_eff_at_forcing": beta_eff_at_forc,
        "beta_drained": float(beta_drained),
        "ratio_eff_to_drained": float(beta_eff_at_forc / beta_drained)
        if beta_drained != 0
        else None,
    }
    if decision == "warn":
        report.soft_warnings.append(
            f"Tier 1: Pe = {pe:.2f} in soft-warning band — frequency-dependent "
            f"beta_eff differs from beta_drained by "
            f"{abs(beta_eff_at_forc / beta_drained - 1):.0%}"
        )
    elif decision == "escalate":
        report.hard_escalations.append(
            f"Tier 1: Pe = {pe:.2f} in hard-escalation band — use "
            f"frequency-dependent beta_eff(omega) in Phase 4 inversion"
        )

    # Optional tidal beta
    if tidal_dvv is not None and tidal_strain is not None:
        try:
            from .tier1_poroelastic import tidal_beta_estimate

            beta_tide, sigma = tidal_beta_estimate(tidal_dvv, tidal_strain)
            ratio = beta_tide / beta_drained if beta_drained != 0 else None
            report.tier1["beta_tidal"] = float(beta_tide)
            report.tier1["beta_tidal_sigma"] = float(sigma)
            report.tier1["tidal_to_drained_ratio"] = (
                float(ratio) if ratio is not None else None
            )
            if ratio is not None and ratio > 1.5:
                report.soft_warnings.append(
                    f"Tier 1 tidal test: |beta_tidal|/|beta_drained| = "
                    f"{ratio:.2f} > 1.5 — undrained response active at tidal "
                    f"frequencies; implies alpha_B * B = {1 - 1 / ratio:.2f}"
                )
        except Exception as exc:  # pragma: no cover
            report.tier1["tidal_test_error"] = str(exc)

    # ---------------- Tiers 2-4: deferred ----------------
    report.deferred_tiers.extend(["tier2", "tier3", "tier4"])
    report.tier2 = {"status": "deferred (v0.3)"}
    report.tier3 = {"status": "deferred (v0.3)"}
    report.tier4 = {"status": "deferred (v0.4)"}

    return report
