#!/usr/bin/env python3
"""Pre-push review gate for the `code-reviewer` agent (Mode B).

This is a VS Code Copilot `PreToolUse` hook. Before any tool call that runs
`git push`, it interrupts and requires a pre-push review to have been done,
pointing the operator at the `code-reviewer` agent's Mode B (pre-push gate).

Behaviour:
- Reads the hook payload as JSON on stdin.
- If the tool about to run is a `git push`, it returns a `PreToolUse`
  permission decision of `ask` (confirm) — or `deny` (hard block) when the
  environment variable `CODAMETER_PREPUSH_GATE=deny` is set.
- For every other tool call it allows execution and stays silent.

It is intentionally read-only and deterministic: it never runs git itself,
never edits files, and fails open (allows the push) if the payload cannot be
parsed, so a malformed payload can't wedge the workflow.
"""

from __future__ import annotations

import json
import os
import re
import sys

# Matches `git push`, `git  push`, `git -C <dir> push`, etc. Word-bounded so
# it won't trip on substrings like "git pushd" or a file named "git push".
_GIT_PUSH = re.compile(r"\bgit\b[^\n;|&]*\bpush\b")

_REASON = (
    "Pre-push review required. Run the `code-reviewer` agent in Mode B "
    "(pre-push gate) and confirm a 'READY TO PUSH' verdict before pushing. "
    "Mode B reviews the staged/unstaged diff for correctness, security, "
    "tests, docs, reproducibility, and hygiene. "
    "See .github/agents/code-reviewer.agent.md."
)


def _iter_strings(value):
    """Yield every string found anywhere in a nested JSON structure."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)


def _is_git_push(payload: dict) -> bool:
    """True if the pending tool call appears to run `git push`."""
    return any(_GIT_PUSH.search(text) for text in _iter_strings(payload))


def _allow() -> None:
    # Stay silent and let the tool run.
    json.dump({"continue": True}, sys.stdout)


def _gate() -> None:
    decision = "deny" if os.environ.get("CODAMETER_PREPUSH_GATE") == "deny" else "ask"
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
                "permissionDecisionReason": _REASON,
            },
            "systemMessage": _REASON,
        },
        sys.stdout,
    )


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        # Fail open: don't block work just because we couldn't parse input.
        _allow()
        return 0

    if isinstance(payload, dict) and _is_git_push(payload):
        _gate()
    else:
        _allow()
    return 0


if __name__ == "__main__":
    sys.exit(main())
