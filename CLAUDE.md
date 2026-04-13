# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Install the package in editable mode (no external dependencies — stdlib only):
```bash
pip install -e .
```

Run tests (live network calls against the real API):
```bash
pytest test_versions.py
```

Run a single test:
```bash
pytest test_versions.py::test_get_currencies
```

Lint (errors only, then warnings):
```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
```

CI matrix: Python 3.8–3.12.

## Architecture

This is a single-class library. `FrankfurterEngine` in `frankfurter/engine.py` is the entire public surface — all user-facing methods live there. The package exposes only that class via `__init__.py`.

**Request flow:** All HTTP is done through the private `__api_call` method using stdlib `urllib` (no third-party HTTP library). It builds a URL from `BASE_URL`/`BASE_HEADERS` in `utils.py`, fires a GET, and returns parsed JSON. HTTP errors surface as `FrankfurterCallFailedException`.

**Currency validation:** Every public method that accepts `base` or `symbols` calls `_check_valid_currency`, which in turn calls `fetch_currencies()`. `fetch_currencies()` is decorated with `@lru_cache`, so the currencies list is fetched once per `FrankfurterEngine` instance and reused for all subsequent validation calls.

**Exceptions:** `FrankfurterCallFailedException` (HTTP/API failures) and `UnknownCurrencyException` (unknown currency code) are defined in `exceptions.py`. Note that `FrankfurterCallFailedException.__init__` raises immediately — it does not return an instance.

**Tests are integration tests** — they call the live `api.frankfurter.dev` endpoint. There is no mocking layer.
