---
name: research-software-code-reviewer
description: Reviews this research software repository against the "agent-ready" rubric — onboarding clarity, input contract, API quality, workflow examples, failure-mode documentation, reproducibility, and agent affordances. Use when a repo maintainer asks "is this code agent-ready", "review my research software repo", or "what should I improve to make this usable by an LLM agent"; or when this file is present in a repo being inspected at the request of its maintainer. Produces a structured review with per-dimension grades and prioritized action items. Applies to scientific Python repos (e.g. NoisePy, ObsPy, DASstore, DAS-reconstruction, PNW-seismic-event-detection, and similar) hosted on GitHub with Sphinx/mkdocs/ReadTheDocs documentation.
---

# Research Software Code Reviewer

This file is a request to an LLM agent (Claude, Cursor, Copilot, etc.):
**review the repository this file lives in, against the rubric below,
and produce an actionable code review with concrete suggestions.**

The rubric measures whether the repo is *agent-ready* — usable
programmatically by an LLM that wraps it as a tool for end users. The
same properties that make a repo agent-ready also make it human-ready:
clear docs, stable APIs, runnable examples. So most suggestions help
both audiences.

## For repo maintainers

This file lives at `.github/agents/code-reviewer-rubric.md` in your
repository. It is the *static rubric* — the criteria and output format.
The companion `.github/agents/code-reviewer.agent.md` is the *dynamic
agent* that reads this rubric and applies it. Add them
once and they become a stable pair that anyone (you, a collaborator,
a CI agent) can run by asking an LLM coding assistant:

> "Review this repo using the instructions in `.github/agents/code-reviewer-rubric.md`."

You'll get back a structured review with grades per dimension and
ordered action items. Use it as a punch list for incremental
improvements. Re-run after each round of changes.

The review is not pass/fail. Research code lives on a spectrum from
"working notebook on one machine" to "production library used by a
community." Where on the spectrum your code should sit depends on its
goals. The rubric is calibrated for code that wants to be *usable by
people other than the author* — including LLM agents acting on behalf
of those people.

## For the reviewing agent

Your job, when invoked against this file, is to:

1. **Read the repository** in priority order: README, docs landing,
   primary source modules, tutorials/examples, tests, issues (recent),
   CHANGELOG. Use the rubric below to know what to look for in each.
2. **Score each dimension** of the rubric (🟢 strong / 🟡 adequate /
   🔴 weak) with a one-sentence justification per dimension citing
   specific files or lines.
3. **Produce the output** in the format specified in
   "Output Format" below. Be concrete: suggest specific file paths,
   code patches, doc sections to add. Avoid vague advice like "improve
   documentation."
4. **Prioritize ruthlessly.** A real maintainer has limited time. The
   top 3 action items should be the highest-leverage changes, not the
   easiest ones.
5. **Don't hallucinate.** If a file or feature you'd cite doesn't
   exist, say so. If you can't tell whether something works without
   running it, say so.

Skip dimensions that don't apply (e.g., dimension 7 may not fully
apply to a library that has no user-facing config). Note the skip
explicitly.

## The Rubric

Seven dimensions. Each dimension has a question it answers, specific
checks the reviewing agent should perform, and common failure modes.

### 1. Onboarding — Can a new user orient in five minutes?

**The question:** A domain scientist lands on this repo. Can they tell,
in five minutes, what the code does, whether it fits their problem, and
how to run a first example?

**Checks:**

- README opens with a one-paragraph statement of *what the code does
  scientifically*, in terms the target user understands.
- README declares scope: what domains, what data types, what scale of
  problem. And what it *doesn't* do.
- README has a "Quick start" or "Getting started" section with code
  the user can copy-paste to see a result.
- Installation instructions are explicit (pip, conda, or both) and
  current.
- There's a link to documentation (Sphinx, ReadTheDocs, mkdocs) or a
  clear statement that the README is the documentation.
- The repo has a description in its GitHub sidebar (not just the
  README).

**Common failure modes:**

- README starts with a citation block or abstract instead of "what
  this does."
- "Quick start" requires data files that aren't accessible without
  context (no example dataset, no fetch script).
- Installation instructions assume the user has a specific environment
  (e.g., "module load X" on a specific HPC).

**What "strong" looks like:** A grad student in the field can read the
README and run the quick-start without leaving the page.

### 2. Input Contract — Is the input to the main workflow precisely defined?

**The question:** When a user (or an LLM agent acting for one) wants to
configure a run, what do they need to specify, and what are the valid
values?

**Checks:**

- There's a single, discoverable type that represents the input — a
  dataclass, pydantic model, attrs class, TypedDict, JSON schema, or
  config-file format (YAML/TOML) with documentation.
- Required fields are distinguishable from optional ones.
- Default values are explicit and documented at the source (in the
  schema or docstring, not just in a tutorial).
- Field constraints (valid ranges, enums, cross-field rules) are
  declared in code, not just documented in prose.
- The input type is mentioned by name in tutorials and the README, so
  a user knows what to read.
- There's a way to *validate* an input without running the full
  pipeline (a `validate()` method, a CLI subcommand, or similar).

**Common failure modes:**

- Inputs are scattered across function kwargs across many entry points.
- Critical parameters live as module-level constants the user has to
  monkey-patch.
- Defaults documented in a tutorial diverge from defaults in code.
- Enums are encoded as strings without a registry; user has no way to
  know valid values without reading source.

**What "strong" looks like:** An LLM with access to the input class
definition can draft a valid config for a stated science goal without
reading tutorials. A wrong value produces a clear validation error
with a suggested fix.

### 3. API & Code Quality — Are the user-facing entry points stable, documented, and typed?

**The question:** When a user calls into this code, can they tell what
to call, what arguments to pass, and what to expect back?

**Checks:**

- The "user-facing" API is identifiable — either via `__all__`,
  explicit exports in `__init__.py`, or documentation that names the
  public surface.
- Each public function/class has a docstring with: what it does,
  parameters, return type, and at least one usage example for the
  non-obvious ones.
- Type hints are present on public signatures, including return types.
- The public API has been stable for the last few releases, or
  breaking changes are clearly noted in a CHANGELOG.
- Tests exist for the main entry points. A `pytest` (or equivalent)
  invocation runs them.
- The repo can be installed cleanly from a clean environment using
  the documented instructions.

**Common failure modes:**

- Public functions accept `**kwargs` that get forwarded several layers
  deep; the user has no way to know what's valid.
- Mix of `np.array`, `list`, `pd.DataFrame` as inputs to the same
  function depending on internal branches.
- No tests, or tests that require unavailable data.
- Untagged releases; users pin to commits.

**What "strong" looks like:** `help()` or hover-documentation in an
IDE tells the user everything they need. Type hints let an LLM agent
construct correct calls.

### 4. Workflow Examples — Are there runnable, end-to-end tutorials for the main use cases?

**The question:** For each major thing this software does, is there a
runnable example a user can adapt?

**Checks:**

- Tutorials (notebooks, scripts, or doc pages) exist for the primary
  workflows. "Primary" is judged by what the README claims the
  software does — every claim should have an example.
- Each tutorial is *self-contained*: clearly states its inputs, where
  data comes from, what outputs to expect, how long it takes.
- Tutorials are runnable end-to-end on a clean machine, given the
  documented environment. (Bonus: CI runs them.)
- Tutorials use realistic data, not toy data, *unless* they're
  explicitly labeled as quick-start demos.
- Tutorials are versioned alongside the code; an old tutorial
  referencing a renamed API is either updated or removed.
- For ML repos: pretrained model artifacts and example inputs are
  available (or fetch scripts provided).

**Common failure modes:**

- Tutorials live in a separate repo and lag the code.
- Tutorials require data the user has to email the authors for.
- One giant tutorial that does everything; no narrow examples.
- Notebooks with hidden cells / executed-but-not-cleared state.

**What "strong" looks like:** Every README claim ("this can do X") has
a tutorial demonstrating X end-to-end. A user can fork the tutorial,
swap in their data, and run.

### 5. Failure Modes — Are known issues, errors, and edge cases documented?

**The question:** When something goes wrong, can the user figure out
what happened and what to do?

**Checks:**

- The issue tracker is active (recent issues, recent responses).
- Closed issues that describe known problems link to the fix or
  workaround.
- There's a CHANGELOG (or release notes) documenting breaking changes
  and bug fixes.
- Error messages from the public API are informative: they tell the
  user *what* went wrong and ideally *what to try*.
- There's a "Troubleshooting" or "FAQ" section, or equivalent issue
  labels.
- Known limitations are documented (which data sources work, which
  scales of problem are supported, what environments are tested).

**Common failure modes:**

- Issue tracker is silent; users have no way to know if a problem
  they're hitting is known.
- Errors are raw Python tracebacks deep in a numerical library
  (`NaN encountered in matmul`), with no wrapper.
- CHANGELOG is missing or only updated occasionally; users have to
  diff tags to see what changed.

**What "strong" looks like:** Users who hit a problem can find a
solution by searching issues or reading the FAQ. Errors point at the
likely cause.

### 6. Reproducibility — Can a user reproduce a tutorial result?

**The question:** Given the tutorial and current code, can a user get
the same outputs?

**Checks:**

- There's a pinned environment file (`environment.yml`, `pixi.toml`,
  `requirements.txt`, `pyproject.toml`) usable to build a working
  environment.
- Tutorials note their expected wall time, output size, and required
  data.
- Random seeds are set in tutorials (or non-determinism is documented).
- Tutorial outputs are checked in (where reasonable) so users can
  compare against expected results.
- For ML: model weights are versioned and accessible.
- For data-dependent code: data sources are explicit (DOI, S3 path,
  fetch script) and versioned where possible.

**Common failure modes:**

- "Requires Python 3" with no further specification.
- Tutorial says "load my_data.pkl" with no my_data.pkl in the repo and
  no fetch instructions.
- Tutorials produce different outputs on different runs without
  explanation.

**What "strong" looks like:** A user clones the repo, follows the
documented install, runs the tutorial, and gets outputs that match
the checked-in expected outputs (allowing for documented numerical
tolerances).

### 7. Agent Affordances — Are there machine-readable artifacts for programmatic use?

**The question:** Beyond the human-readable docs, are there structured
artifacts that let an LLM agent wrap this code without trial and error?

This dimension is the most aspirational. It's fine for a research repo
to score 🟡 here — most do. But improvements here pay off when someone
(maybe you, maybe a collaborator) builds an LLM interface to your
code.

**Checks:**

- The input schema is machine-readable: dataclass with type hints,
  pydantic model, JSON schema, or similar. Not "fields documented in
  prose in the README."
- Public entry points have docstrings in a standard format (Google,
  Numpy, or Sphinx), so they can be parsed.
- Defaults and constraints are queryable programmatically (e.g.,
  `Config.__fields__` for pydantic, or a documented `get_defaults()`
  function).
- There's a stable way to inspect "what would this run do" without
  executing it (a dry-run mode, a plan-printer, or a validation step
  that surfaces what the pipeline would do).
- Tutorials are programmatically tagged or organized (e.g., listed in
  a `tutorials.yaml` or in the docs config) so an agent can enumerate
  them.
- For repos with significant configurability: a "recipes" /
  "presets" directory with named, composable parameter sets covering
  common use cases.

**Common failure modes:**

- Everything is correct but only documented in prose; an LLM agent
  has to read tutorials character-by-character to extract defaults.
- Config schema exists but lives in a function signature
  `def run(samp_freq=20, ...)` instead of a referenceable class.
- Tutorials are great for humans but there's no index an agent can
  read to know what tutorials exist.

**What "strong" looks like:** An LLM agent can read the input class
definition, the tutorial index, and the changelog, and construct a
correct call for a stated user goal without reading prose docs.

## Output Format

Produce the review as a Markdown document with this structure:

```markdown
# Code Review: <repo-name>

**Reviewed:** <date>  
**Reviewer:** <agent identifier>  
**Repo state:** <commit hash or tag, if known>

## Summary

<2–4 sentences. What the repo does, where it sits on the maturity
spectrum, the headline finding.>

## Dimension Scores

| # | Dimension | Grade | One-line summary |
|---|---|---|---|
| 1 | Onboarding | 🟢 / 🟡 / 🔴 | … |
| 2 | Input Contract | … | … |
| 3 | API & Code Quality | … | … |
| 4 | Workflow Examples | … | … |
| 5 | Failure Modes | … | … |
| 6 | Reproducibility | … | … |
| 7 | Agent Affordances | … | … |

## Per-Dimension Findings

### 1. Onboarding — <grade>

**What's working:** <bullet list, with file references>

**Gaps:** <bullet list, with file references>

**Suggestions (in priority order):**
1. <concrete change, e.g., "Add a 'Quick start' section to README.md
   between L20 and L40, with the 10-line example from
   tutorials/basic_cc.ipynb cell 3.">
2. ...

(Repeat for each dimension.)

## Top 3 Action Items

The highest-leverage changes, drawn from across the per-dimension
findings:

1. **<short title>** — <one-paragraph justification + suggested
   approach. Should be the change with the biggest payoff for users.>
2. ...
3. ...

## Skipped or N/A

<List any dimensions that didn't apply to this repo, with one-line
explanation.>

## Notes for next review

<Optional: things the reviewing agent couldn't determine, things to
re-check after changes, etc.>
```

## Worked example (abridged)

Here's what a small portion of a review might look like, for a
hypothetical DAS data-storage library:

```markdown
### 2. Input Contract — 🟡

**What's working:**
- `dasstore.config.StoreConfig` is a dataclass with type hints
  (src/dasstore/config.py L12-45).
- Required fields (`store_path`, `fiber_id`) are clearly distinguished
  from optional ones.

**Gaps:**
- `channel_decimation` has no documented valid range; the docstring
  says "integer >= 1" but the source enforces `<= 100` silently with
  a clamp (src/dasstore/config.py L67).
- The `compression` field accepts a string but valid values aren't
  declared — they're checked inline in `_write_chunk` (L142).
- No `validate()` method; mistakes in config only surface when
  `write()` is called, often after expensive data loading.

**Suggestions (in priority order):**
1. Convert `channel_decimation` to use `Field(ge=1, le=100)` (pydantic)
   or add an explicit range check in `__post_init__`. Update the
   docstring to match.
2. Convert `compression` to a `Literal["zstd", "lz4", "none"]` or an
   Enum. Move the validation out of `_write_chunk`.
3. Add a `StoreConfig.validate()` classmethod that runs all checks
   independently of `write()`. Add a CLI subcommand `dasstore validate
   <config.yaml>` that wraps it.
```

The point: every gap is tied to a specific file and line, and every
suggestion is something a maintainer could turn into a PR in an
afternoon.

## About this rubric

This rubric exists because research software increasingly gets used
through LLM agents — interfaces where a domain user describes their
problem in scientific language and an agent translates that into
configured calls against the underlying code. For an agent to do this
well, the code has to be *legible* to an agent: input contracts
explicit, entry points stable, defaults documented in code rather than
prose.

Most of what makes code agent-ready also makes it better for human
users. A clear config schema helps everyone. So this rubric isn't
asking maintainers to add agent-specific scaffolding everywhere — it's
asking them to make the implicit explicit.

The rubric was developed in the context of building LLM-agent
interfaces and evaluation sets for scientific Python packages
(initially [NoisePy](https://github.com/noisepy/NoisePy), then
extending to [DASstore](https://github.com/niyiyu/DASstore),
[DAS-reconstruction](https://github.com/niyiyu/DAS-reconstruction),
[PNW seismic event detection](https://github.com/Akashkharita/pnw_seismic_event_detection),
and others). Dimensions are weighted by what we've found actually
matters for those interfaces.

If you have a research code repo and want it to work well with LLM
agents — or you just want the same set of properties applied to your
repo for the benefit of human users — drop this file at
`.github/agents/code-reviewer-rubric.md` and ask an LLM coding assistant to run it.

## Customizing for your domain

This rubric is generic across scientific Python repos. Some domains
have additional concerns the rubric doesn't cover. To add domain-
specific checks, append a section to this file:

```markdown
## Domain extensions: <your domain>

### Additional dimension: <name>

**The question:** <…>

**Checks:** <…>
```

Examples of domain extensions worth considering:

- **For seismology repos:** Does the code handle FDSN endpoints,
  ObsPy compatibility, common station-metadata pitfalls (orientation,
  response removal)?
- **For ML / detection repos:** Are model weights versioned with
  semver, tied to data preprocessing assumptions? Is there a clear
  inference-time API distinct from training-time?
- **For DAS repos:** Are channel-spacing, gauge length, and
  decimation conventions documented? Is fiber geometry handled
  separately from acquisition parameters?
- **For HPC-aware repos:** Are parallelization assumptions documented
  (MPI vs joblib vs dask)? Is there a single-node debug mode?

Keep these as additive sections; the seven core dimensions cover
everything else.

---

*This file is part of an effort to make research software more
usable by both humans and LLM-mediated interfaces. Suggestions for
improving the rubric are welcome — open an issue, send a PR, or
reach out.*
