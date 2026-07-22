# Contributing to Titan

Contributions are welcome.

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

## Philosophy

Titan is stability-driven. New features are only considered if they preserve full backward compatibility and fit within the existing contract. When in doubt, read `CONTRACT.md` first.
