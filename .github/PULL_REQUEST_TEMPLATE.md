# Pull Request

## Summary

<!-- One or two sentences: what does this PR change, and why? -->

## Type of change

- [ ] Bug fix
- [ ] New feature (forward model, coupling tier, inversion mode, ...)
- [ ] Documentation
- [ ] Tests / CI
- [ ] Refactor / cleanup
- [ ] Breaking change (API, YAML schema, output format)

## Checklist

- [ ] Tests pass locally (`pytest`)
- [ ] Lint passes (`ruff check src/ tests/` and `black --check src/ tests/`)
- [ ] New code has docstrings with citation keys for any physics
- [ ] If a forward model or kernel was added, a sanity test against a
      published value or analytical limit is included
- [ ] If a config-file field was added, `examples/configs/*.yaml` and the
      `Site` dataclass are both updated and round-trip-tested
- [ ] CHANGELOG entry added under `## Unreleased`
- [ ] Documentation under `docs/` updated if user-facing behaviour changed

## Scientific reviewer notes (optional)

<!-- For physics-touching PRs, briefly note what published comparison or
synthetic limit you used to validate the change. Reviewers will check this
against the manuscript framework. -->
