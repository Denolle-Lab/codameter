# Author Profile — the persona layer

A shared reviewer model pulls everyone's writing toward one register. The author
profile is the constraint that resists that. It is loaded at Step 0 and passed to
every subagent. It does two jobs:

- **Preserve** — protect the author's voice, phrasing, chosen framing, and
  citation judgment from being flattened toward a house average.
- **Stretch** — apply only the diversity nudges the author opted into.

It governs **voice, register, framing defense, and citation values only**. It can
never relax soundness (C2), reproducibility (C3/S-RP), or evidence–conclusion
alignment (C4). There is no persona that dissolves a REPRODUCTION-STOP.

A profile is opt-in. If none is supplied, use `profiles/default.md` and say so.

---

## Schema

A profile is a short Markdown file with these fields (all optional except a name;
omitted fields fall back to the default):

```yaml
name:                  # author or profile name
register:              # formal | plain | conversational; first-person allowed? hedging level
favored_phrasing:      # phrases / terms of art the author wants kept
banned_phrasing:       # phrases the author never wants (extends the plain-voice list)
sentence_rhythm:       # long-and-complex | short-and-direct | mixed; tolerance for smoothing
never_change:          # things the reviewer must not touch (e.g., clear non-native phrasing)
research_lineage:      # models / papers / groups / methodological schools the author follows
novelty_appetite:      # defend-heterodox-framing | balanced | nudge-toward-conventional
citation_values:       # which S-CD axes to surface; CDS yes/no; flag over-self-citation?;
                       # surface a non-Western / junior-author group when one exists?
                       # enable gender/race inference? (default: NO)
audience:              # who the paper is for; how hard to push accessibility
```

---

## How each subagent consumes it

- **All section subagents (S-AB, S-IN, S-ME, S-RE, S-DI, S-CO, S-FD):** honor
  `register`, `favored_phrasing`, `banned_phrasing`, `sentence_rhythm`, and
  `never_change`. Style comments are limited to *clarity* — never *register* or
  *word choice the author owns*. Never flag clear non-native phrasing.
- **S-IN / S-DI / S-CD:** read `research_lineage` so the author's deliberate
  school is not flagged as "unusual," and `novelty_appetite` to decide how hard
  to defend heterodox framing (feeds the C1 guardrail).
- **S-CD:** read `citation_values` — which axes to surface, whether to run a
  Citation Diversity Statement, whether to flag over-self-citation, and whether
  gender/race inference is enabled (default off).
- **Orchestrator:** records the profile name in the report header and enforces
  the anti-homogenization voice-guard and the persona-cannot-override-integrity
  rule.

---

## Elicitation — the questions to ask a new user

Ask these once; save the answers as `profiles/<name>.md`. One question at a time
is fine; every field has a default, so a partial profile is valid.

1. **Register & tone.** Formal, plain, or conversational? First person allowed?
   How much hedging do you want kept vs. trimmed?
2. **Words you favor.** Phrases or terms of art you want preserved.
3. **Words you ban.** Phrases you never want the reviewer to suggest.
4. **Sentence rhythm.** Long and complex, short and direct, or mixed? How much
   should the reviewer leave your cadence alone?
5. **Never change.** Anything the reviewer must not touch — for example,
   non-native phrasing that is already clear.
6. **Research lineage.** Models, papers, groups, or methodological schools you
   follow and want the reviewer aware of, so your framing isn't flagged as odd.
7. **Novelty appetite.** Should the reviewer defend heterodox framing on your
   behalf, stay balanced, or nudge you toward the conventional core?
8. **Citation values.** Which diversity axes do you want surfaced (geographic,
   temporal, venue, self-citation)? Run a Citation Diversity Statement? Flag
   over-self-citation? Surface a non-Western or junior-author group when one
   exists? Enable gender/race inference (off by default)?
9. **Audience.** Who is the paper for, and how hard should the reviewer push
   accessibility?

---

## Two cautions

- **A profile can entrench an echo chamber** ("only my school"). The *stretch*
  fields (novelty appetite, citation values) are the antidote — the author opts
  into the mirror, not only the shield.
- **A profile is not a shield against rigor.** If a profile is ever read as
  loosening C2/C3/C4, ignore that part and proceed under the integrity rules.
