# Contributing to Titan

Contributions are welcome.

The [Titan Ledger](CONTRIBUTORS.md) records the people and work that have
given the project its lasting shape. It is not a popularity list or a
commit-count export; it is maintained as part of Titan's history.

## Before You Open a PR

- Check that your change does not break any existing tests: `pytest`
- Check that your change does not alter the public API without a corresponding update to `CONTRACT.md`
- Keep changes focused — one concern per PR

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```

## Reporting Issues

Open a GitHub issue with a minimal reproducible example.

## Recognition

Titan recognizes more than runtime code. Tests, documentation, architectural
investigations, ADRs, reviews, and useful issue reports can all be meaningful
contributions. If accepted work leaves a durable mark, it belongs in the
[Titan Ledger](CONTRIBUTORS.md).

## Philosophy

Titan is stability-driven. New features are only considered if they preserve full backward compatibility and fit within the existing contract. When in doubt, read `CONTRACT.md` first.
