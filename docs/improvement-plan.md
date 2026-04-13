# Improvement Plan

This document lists every identified defect and the planned fix for each. Items are ordered by severity: correctness bugs first, then reliability issues, then API-quality improvements.

---

## 1. Broken exception class (correctness bug)

**File:** `frankfurter/exceptions.py`

**Problem:**  
`FrankfurterCallFailedException.__init__` calls `raise Exception(...)` inside itself. A plain `Exception` is raised instead of the custom type, so `except FrankfurterCallFailedException` never matches. Any caller doing typed error handling silently gets incorrect behaviour.

**Fix:**  
Remove the `raise` inside `__init__`. Call `super().__init__(message)` properly and store structured fields on the instance.

```python
class FrankfurterCallFailedException(Exception):
    def __init__(self, status_code: int, reason: str) -> None:
        self.status_code = status_code
        self.reason = reason
        super().__init__(f"Frankfurter API call failed. Status: {status_code}. Reason: {reason}")
```

**Test to write first:**  
Assert that catching `FrankfurterCallFailedException` (not bare `Exception`) intercepts the error when the API returns a 4xx/5xx.

---

## 2. `@lru_cache` memory leak on instance method (correctness / reliability bug)

**File:** `frankfurter/engine.py`

**Problem:**  
`@lru_cache` on an instance method holds a strong reference to `self`. The `FrankfurterEngine` instance can never be garbage collected for the lifetime of the cache. In long-running services this leaks memory indefinitely.

**Fix:**  
Replace the decorator with an explicit instance-level cache variable.

```python
def __init__(self, ...) -> None:
    ...
    self._currencies_cache: dict | None = None

def fetch_currencies(self) -> dict:
    if self._currencies_cache is None:
        self._currencies_cache = self.__api_call(path_params=["currencies"])
    return self._currencies_cache
```

This also allows callers to invalidate the cache when needed (`engine._currencies_cache = None`), which `lru_cache` makes impossible without reflection.

**Test to write first:**  
Assert that two consecutive calls to `fetch_currencies()` produce the same result but only issue one HTTP request (mock or count calls to `__api_call`).

---

## 3. No HTTP timeout (reliability bug)

**File:** `frankfurter/engine.py`

**Problem:**  
`urlopen(request)` has no timeout. A hung upstream connection blocks the calling thread forever.

**Fix:**  
Add a `timeout` parameter to `FrankfurterEngine.__init__` and pass it through to `urlopen`.

```python
def __init__(self, quiet_mode: bool = True, timeout: float = 10.0) -> None:
    ...
    self._timeout = timeout

# in __api_call:
with urlopen(request, timeout=self._timeout) as response:
```

`urllib.error.URLError` wraps `socket.timeout`; the existing `HTTPError` handler should be extended to also catch `URLError`.

**Test to write first:**  
Assert that a `socket.timeout` raised by `urlopen` surfaces as a `FrankfurterCallFailedException` (or a new `FrankfurterTimeoutException`) rather than propagating as an unhandled `URLError`.

---

## 4. Global logger side effect at import (reliability bug)

**File:** `frankfurter/logger.py`

**Problem:**  
`logging.basicConfig(...)` is called at module import time, which configures the **root logger** for the entire host application. A library must never do this; it can override the host application's logging setup.

**Fix:**  
Use a named, library-scoped logger and do not call `basicConfig`. The host application controls handler and format configuration.

```python
import logging
Logger = logging.getLogger("frankfurter")
# No basicConfig call. Add a NullHandler so the library is silent by default.
Logger.addHandler(logging.NullHandler())
```

**Test to write first:**  
Assert that importing `frankfurter` does not add handlers to the root logger and does not change the root logger's level.

---

## 5. Mutable default arguments and wrong type annotation (code quality)

**File:** `frankfurter/engine.py`

**Problem:**  
```python
def __api_call(self, query_params: dict = {}, path_params: str = [], extra_headers: dict = {})
```
- `dict = {}` and `list = []` are the classic Python mutable-default-argument bug. They are shared across all calls. They do not cause a visible bug here because the defaults are never mutated, but they are a latent defect.
- `path_params: str` is annotated as `str` but used as a `list`.

**Fix:**  
Use `None` as the default and construct the mutable object inside the function body.

```python
def __api_call(
    self,
    query_params: dict | None = None,
    path_params: list[str] | None = None,
    extra_headers: dict | None = None,
) -> dict:
    query_params = query_params or {}
    path_params = path_params or []
    extra_headers = extra_headers or {}
```

---

## 6. Silent fallback in `fetch_time_series_data` (API quality)

**File:** `frankfurter/engine.py`

**Problem:**  
If `start_date` is omitted, `fetch_time_series_data` silently delegates to `fetch_latest_data`. The caller has no indication that a different endpoint was hit. This is surprising and hard to debug.

**Fix:**  
Make `start_date` a required parameter (remove the `None` default) and raise `ValueError` early if it is missing or malformed.

```python
def fetch_time_series_data(
    self,
    start_date: str,
    base: str | None = None,
    symbols: str | None = None,
    end_date: str | None = None,
) -> dict:
```

**Test to write first:**  
Assert that calling `fetch_time_series_data()` without `start_date` raises `TypeError` (missing argument), and that an invalid date string raises `ValueError`.

---

## 7. Date format not validated (API quality)

**Files:** `frankfurter/engine.py`

**Problem:**  
Date strings (`date`, `start_date`, `end_date`) are forwarded to the API without validation. A malformed date produces an opaque HTTP error rather than a clear `ValueError` at the call site.

**Fix:**  
Add a small validator that runs before the network call.

```python
from datetime import date

def _parse_date(value: str, param_name: str) -> str:
    try:
        date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"'{param_name}' must be in YYYY-MM-DD format, got: {value!r}")
    return value
```

Call `_parse_date(date, "date")` at the top of `fetch_data_for_date` and `fetch_time_series_data`.

**Test to write first:**  
Assert that `fetch_data_for_date("not-a-date")` raises `ValueError` before any network call is made.

---

## 8. `symbols` validation/transmission mismatch (correctness bug)

**File:** `frankfurter/engine.py`

**Problem:**  
Validation strips whitespace from individual symbols (`symbol.strip()`), but the original `symbols` string is passed to the API unmodified. `"EUR, INR"` passes validation but may fail at the HTTP layer because of the embedded space.

**Fix:**  
Normalise the symbols string before both validation and transmission.

```python
def _normalise_symbols(symbols: str) -> str:
    return ",".join(s.strip() for s in symbols.split(","))
```

Call this at the top of any method that accepts `symbols`, and use the normalised value everywhere.

**Test to write first:**  
Assert that `fetch_latest_data(symbols="EUR, INR")` produces the same result as `fetch_latest_data(symbols="EUR,INR")`.

---

## 9. Add v1/v2 API version switching (new feature)

### 9.1 API Differences

The two versions are not a simple URL swap — endpoints, parameter names, and response shapes all differ.

| Concern | v1 | v2 |
|---------|----|----|
| Base URL | `api.frankfurter.dev/v1` | `api.frankfurter.dev/v2` |
| Latest rates | `GET /latest` | `GET /rates` |
| Historical rates | `GET /{date}` | `GET /rates?date={date}` |
| Time series | `GET /{start}..{end}` | `GET /rates?from={start}&to={end}` |
| Currencies list | `GET /currencies` | `GET /currencies` |
| Single pair | — | `GET /rate/{base}/{quote}` |
| Currency detail | — | `GET /currency/{code}` |
| Providers | — | `GET /providers` |
| Target currency param | `symbols` | `quotes` |
| Downsampling | — | `group` query param |
| Multi-provider | — | `providers` query param |

**`/currencies` response shape (breaking change):**

v1:
```json
{ "EUR": "Euro", "USD": "US Dollar" }
```

v2:
```json
{
  "currencies": {
    "EUR": { "name": "Euro", "providers": ["ECB"] },
    "USD": { "name": "US Dollar", "providers": ["ECB", "CB"] }
  }
}
```

**`/rates` response shape (breaking change):**

v1 returns a single JSON object — one date applies to all currencies:
```json
{ "base": "EUR", "date": "2026-04-10", "rates": { "AUD": 1.6561, "BRL": 5.9191 } }
```

v2 returns a JSON **array** — one object per currency pair, each with its own date (currencies that have not updated today carry the last available date):
```json
[
  { "date": "2026-04-13", "base": "EUR", "quote": "AED", "rate": 4.2924 },
  { "date": "2026-04-10", "base": "EUR", "quote": "AUD", "rate": 1.6561 }
]
```

Consequences:
- `__api_call` can no longer declare `-> dict`; the return type must be `dict | list`.
- `convert_currency` v2 must scan the list for `entry["quote"] == to` rather than a dict key lookup.
- The v2 `RatesResult` model is a list of `RateEntry` objects, not a single aggregate object.

**New v2-only `/rate/{base}/{quote}` response:**
```json
{ "base": "EUR", "quote": "USD", "rate": 1.085, "date": "2024-01-15" }
```

**New v2-only `/currency/{code}` response:**
```json
{ "code": "EUR", "name": "Euro", "providers": ["ECB", "CB"] }
```

**New v2-only `/providers` response:**
```json
{ "providers": [{ "id": "ECB", "name": "European Central Bank", "url": "..." }] }
```

---

### 9.2 Data Models

Introduce typed dataclasses in a new `frankfurter/models/` subpackage. Raw dicts are not returned to callers — every public method returns a typed model instance.

**`frankfurter/models/v1.py`**
```python
from dataclasses import dataclass

@dataclass
class RatesResult:
    base: str
    date: str
    rates: dict[str, float]

@dataclass
class TimeSeriesResult:
    base: str
    start_date: str
    end_date: str
    rates: dict[str, dict[str, float]]  # date -> { currency -> rate }

@dataclass
class CurrenciesResult:
    currencies: dict[str, str]          # code -> name
```

**`frankfurter/models/v2.py`**
```python
from dataclasses import dataclass

@dataclass
class RateEntry:
    date: str           # per-entry date — may differ across entries
    base: str
    quote: str
    rate: float

# fetch_latest_data and fetch_data_for_date return list[RateEntry]
# fetch_time_series_data also returns list[RateEntry] (multiple dates interleaved)

@dataclass
class CurrencyInfo:
    name: str
    providers: list[str]

@dataclass
class CurrenciesResult:
    currencies: dict[str, CurrencyInfo]  # code -> CurrencyInfo

@dataclass
class CurrencyDetailResult:
    code: str
    name: str
    providers: list[str]

@dataclass
class Provider:
    id: str
    name: str
    url: str

@dataclass
class ProvidersResult:
    providers: list[Provider]
```

---

### 9.3 Architecture

The endpoint paths and parameter names differ enough that a single class with internal `if version == "v2"` branching would become unmaintainable. Instead, use a **base class + two concrete implementations + factory function**:

```
frankfurter/
  models/
    __init__.py
    v1.py
    v2.py
  _base_engine.py     # shared: __api_call, HTTP, timeout, logging
  _v1_engine.py       # v1 endpoints + v1 model construction
  _v2_engine.py       # v2 endpoints + v2 model construction
  engine.py           # FrankfurterEngine factory function (public API)
  exceptions.py
  utils.py
  logger.py
```

**`_base_engine.py`** — contains only the transport layer:
- `__api_call(url: str, params: dict) -> dict` — HTTP, timeout, error handling
- `_currencies_cache` — instance-level cache (from item 2)
- `quiet_mode`, `timeout` constructor params

**`_v1_engine.py`** — `FrankfurterV1Engine(BaseEngine)`:
- Constructs v1 URLs (`/latest`, `/{date}`, `/{start}..{end}`)
- Uses `symbols` query param
- Returns `v1` model instances
- Methods: `fetch_currencies`, `fetch_latest_data`, `fetch_data_for_date`, `fetch_time_series_data`, `convert_currency`

**`_v2_engine.py`** — `FrankfurterV2Engine(BaseEngine)`:
- Constructs v2 URLs (`/rates`, `/rate/{base}/{quote}`, `/currency/{code}`, `/currencies`, `/providers`)
- Uses `quotes` query param (not `symbols`)
- Returns `v2` model instances
- All v1 methods plus: `fetch_rate`, `fetch_currency_detail`, `fetch_providers`

**`engine.py`** — factory that preserves the existing public interface:
```python
def FrankfurterEngine(
    api_version: str = "v1",
    quiet_mode: bool = True,
    timeout: float = 10.0,
) -> FrankfurterV1Engine | FrankfurterV2Engine:
    if api_version == "v1":
        return FrankfurterV1Engine(quiet_mode=quiet_mode, timeout=timeout)
    if api_version == "v2":
        return FrankfurterV2Engine(quiet_mode=quiet_mode, timeout=timeout)
    raise ValueError(f"Unknown api_version: {api_version!r}. Expected 'v1' or 'v2'.")
```

Existing code that does `FrankfurterEngine()` continues to work unchanged and gets a v1 engine.

---

### 9.4 Currency Validation

`_check_valid_currency` currently calls `fetch_currencies()` and checks `.keys()`. In v2 the currencies dict is nested under a `"currencies"` key and values are `CurrencyInfo` objects, not strings. The base class cannot share this logic.

Each version-specific engine overrides `_check_valid_currency` to interrogate its own model:

```python
# v1
def _check_valid_currency(self, currency: str) -> None:
    if currency not in self.fetch_currencies().currencies:
        raise UnknownCurrencyException(f"Unknown currency: {currency!r}")

# v2 — identical logic, different model shape handled transparently
def _check_valid_currency(self, currency: str) -> None:
    if currency not in self.fetch_currencies().currencies:
        raise UnknownCurrencyException(f"Unknown currency: {currency!r}")
```

---

### 9.5 Tests to Write First

**Factory:**
1. `FrankfurterEngine()` (no args) returns a `FrankfurterV1Engine` instance.
2. `FrankfurterEngine(api_version="v2")` returns a `FrankfurterV2Engine` instance.
3. `FrankfurterEngine(api_version="v3")` raises `ValueError`.

**v1 engine:**
4. `fetch_currencies()` returns a `v1.CurrenciesResult` with `currencies: dict[str, str]`.
5. `fetch_latest_data()` returns a `v1.RatesResult` with `base`, `date`, and `rates: dict[str, float]`.
6. URL for `fetch_latest_data()` contains `/v1/latest` and uses query param `symbols`.
7. URL for `fetch_time_series_data()` contains `/v1/{start}..{end}`.

**v2 engine:**
8. `fetch_currencies()` returns a `v2.CurrenciesResult` with `currencies: dict[str, CurrencyInfo]`.
9. `fetch_latest_data()` returns `list[v2.RateEntry]`; each entry has `date`, `base`, `quote`, `rate`.
10. URL for `fetch_latest_data()` contains `/v2/rates` and uses query param `quotes` (not `symbols`).
11. URL for `fetch_time_series_data()` uses `/v2/rates?from=&to=` query params (not path-based range).
12. `convert_currency` finds the rate by scanning the list for the matching `quote` field.

---

## Implementation Order

| # | Item | Effort | Risk if deferred |
|---|------|--------|-----------------|
| 1 | Fix broken exception class | Low | High — typed error handling is silently wrong |
| 4 | Fix logger side effect | Low | High — corrupts host app logging on import |
| 3 | Add HTTP timeout | Low | Medium — hangs in production |
| 8 | Fix symbols mismatch | Low | Medium — intermittent API failures |
| 2 | Replace `lru_cache` | Low | Medium — memory leak in services |
| 7 | Add date validation | Low | Low — fail-fast improvement |
| 5 | Fix mutable defaults + annotation | Low | Low — latent, not currently triggered |
| 6 | Make `start_date` required | Low | Low — API clarity |
| 9 | v1/v2 switching | Medium | N/A — new feature |
