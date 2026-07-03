# Default author profile

A safe working fallback used when no personal profile is supplied. It preserves
voice and never gatekeeps language; it enables the non-controversial citation
axes and leaves identity inference off.

```yaml
name: default
register: plain; first-person allowed; minimal hedging
favored_phrasing: (none specified)
banned_phrasing: (uses the group plain-voice list)
sentence_rhythm: mixed; do not smooth the author's cadence
never_change: clear non-native phrasing; the author's chosen terms of art
research_lineage: (none specified — do not flag framing as unusual without cause)
novelty_appetite: balanced
citation_values:
  surface_axes: [geographic, temporal, venue, self_citation]
  citation_diversity_statement: optional
  flag_over_self_citation: yes
  surface_underrepresented_group: no
  gender_race_inference: no
audience: specialists in the target journal's community
```
