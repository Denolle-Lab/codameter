# Making a Review Agent from a Static Rubric

Our group's convention for code review (and any other rubric-driven
check) is to keep two artifacts separate:

- **The rubric** — a *static* document that defines what "good" means.
- **The agent** — a *dynamic* driver that reads the rubric and applies
  it to a live repository or a set of changes.

This is the same principle as separating *data* from *code*: the rubric
is the source of truth that changes slowly and deliberately; the agent
is the thin, swappable layer that changes when the *workflow* changes,
not when the *criteria* change.

## Why split them?

- **Single source of truth.** Update the criteria in one place and every
  agent, CI job, and collaborator picks up the change.
- **Portability.** The rubric is repo-agnostic and travels to any
  project; the agent is the per-repo adapter.
- **Auditability.** `git blame` on the rubric shows *why* a standard
  changed. The agent stays small and stable.
- **Tool-agnostic.** The same rubric can be driven by Copilot, Claude,
  Cursor, or a plain CI script.

> Rule of thumb: if you're editing *what counts as good*, touch the
> rubric. If you're editing *when or how the review runs*, touch the
> agent.

## The two artifacts

| Artifact | File | Role | Changes when… |
|---|---|---|---|
| Rubric | `.github/agents/<topic>-rubric.md` | Defines criteria, scoring, and output format | The *standard* changes |
| Agent | `.github/agents/<topic>.agent.md` | Reads the rubric and applies it to a repo or a diff | The *workflow* changes |

## Step 1 — Write the rubric (static)

A good rubric is self-contained and tool-agnostic. Include:

1. **Purpose** — one paragraph on what this rubric measures and who it's
   for.
2. **Dimensions** — each with: the *question* it answers, concrete
   *checks*, and common *failure modes*.
3. **Scoring scale** — e.g. 🟢 strong / 🟡 adequate / 🔴 weak, with
   what each grade means.
4. **Output format** — the exact Markdown structure a review must
   produce, so results are comparable over time.
5. **Anti-hallucination clause** — "cite file:line; if you can't verify
   something without running it, say so."

Keep it prose and tables only — **no tool calls, no repo-specific
paths**. That is what makes it reusable across repos.

## Step 2 — Write the agent (dynamic)

The agent is a `.agent.md` file with YAML frontmatter and a short body
that *delegates* to the rubric instead of duplicating it.

```markdown
---
description: "Use when the user asks to review the repo, do a code review, or
  review changes before pushing to GitHub. Runs an on-demand full review or a
  pre-push diff gate."
name: code-reviewer
tools: [read, search, execute, web, todo]
argument-hint: "What to review: 'full repo', 'pre-push', or a path/module"
---
You are a systematic reviewer. You report findings; you do not rewrite code or push.

## Mode A — On-demand review
1. Read the rubric in `.github/agents/code-reviewer-rubric.md` and follow it exactly.
2. Score each dimension with file:line citations.
3. Emit the review in the rubric's Output Format.

## Mode B — Pre-push gate
1. Inspect what's about to be pushed (read-only): `git status`,
   `git diff @{upstream}..HEAD`, `git diff --cached`.
2. Check correctness, security, tests, docs, reproducibility, hygiene.
3. Optionally run the test suite.
4. Return a verdict: READY TO PUSH / DO NOT PUSH YET, blocking items first.

## Constraints
- DO NOT edit code or run mutating git (`commit`, `push`, `add`, `reset`, `--force`).
- DO NOT bypass checks or suggest `--no-verify`.
- DO NOT invent files, lines, or results.
```

Design principles (from VS Code's custom-agent guidance):

- **Keyword-rich `description`.** It is the discovery surface — include
  the phrases that should trigger the agent ("review the repo", "before
  I push").
- **Minimal tools.** A reviewer needs `read` and `search`, plus
  `execute` only if it runs a pre-push gate. Nothing else.
- **Clear boundaries.** State what the agent must *never* do (edit,
  push, fabricate).
- **Reference, don't inline.** The agent points at the rubric file
  instead of copying it.

## Step 3 — Wire it into the workflow

- **On demand:** invoke from the agent picker, or as a subagent
  ("review this repo against the rubric").
- **Before pushing:** ask the agent for a pre-push review, or automate
  it with a hook (`.github/hooks/`) on a push lifecycle event so it runs
  as a gate.
- **In CI:** a scheduled job can run the on-demand review and post the
  Markdown report as an artifact or PR comment.

## Step 4 — Maintain them on different cadences

- Treat the **rubric** like an API: version it, change it via pull
  request, and note revisions in a changelog. Re-run reviews after each
  rubric change to recalibrate.
- Treat the **agent** like glue: update its tools, modes, and
  constraints as your dev process evolves. It should rarely need changes
  when only the criteria move.

## Reuse across the group

Because the rubric is repo-agnostic, share **one rubric** across
projects (a vendored copy, a git submodule, or a small internal
package) and give each repo its **own thin agent** that points at it.
New repo = copy the agent, keep the shared rubric.

```text
shared/rubrics/agent-ready.md                  # one source of truth
repoA/.github/agents/code-reviewer.agent.md    # reads shared rubric
repoB/.github/agents/code-reviewer.agent.md    # reads shared rubric
```

## Reference implementation

This repository follows the pattern:

- Rubric: `.github/agents/code-reviewer-rubric.md`
- Agent: `.github/agents/code-reviewer.agent.md`
- Pre-push gate: `.github/hooks/pre-push-review.json` (+
  `.github/hooks/scripts/pre_push_review_gate.py`) intercepts `git push`
  via a `PreToolUse` hook and asks the operator to run the agent's Mode B
  review first. Set `CODAMETER_PREPUSH_GATE=deny` to hard-block instead of
  asking for confirmation.
