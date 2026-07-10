# Contributing to pico-rabbitmq

## Development setup

```bash
git clone https://github.com/dperezcabrera/pico-rabbitmq.git
cd pico-rabbitmq
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Running tests

```bash
pytest tests/ -v
pytest --cov=pico_rabbitmq --cov-report=term-missing tests/
tox
```

## Linting

```bash
ruff check src/ tests/
ruff format src/ tests/
```

## Code style

- Python 3.11+
- See AGENTS.md for conventions
- Single-line commit messages

## What NOT to do

- Don't modify `_version.py` (auto-generated)
- Don't change `version_scheme` in pyproject.toml
- Don't add runtime dependencies without discussion
