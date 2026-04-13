# Feature: v1/v2 API Version Support

## Objective

Expose both the Frankfurter v1 and v2 APIs as first-class, independent engine implementations.

**This is not a compatibility layer.** v1 and v2 are different APIs that serve different purposes and return fundamentally different data models. The breaking changes introduced by the upstream API are passed through directly — callers choose a version at construction time and receive that version's full interface, unmodified. There is no normalisation, no shimming, and no attempt to make v1 and v2 interchangeable.

Callers migrating from v1 to v2 should expect to rewrite their consuming code.

---

## Feature Sets

The two engines are not in a superset/subset relationship. Each exposes the operations that make sense for its data model.

### v1 Engine — `FrankfurterV1Engine`

| Method | Returns |
|--------|---------|
| `fetch_currencies()` | `v1.CurrenciesResult` |
| `fetch_latest_data(base, symbols)` | `v1.RatesResult` |
| `fetch_data_for_date(date, base, symbols)` | `v1.RatesResult` |
| `fetch_time_series_data(start_date, base, symbols, end_date)` | `v1.TimeSeriesResult` |
| `convert_currency(amount, base, to)` | `float` |

`convert_currency` exists **only in v1**. The v1 rates response is a dict keyed by currency code, making the lookup a single key access. The v2 data model (a flat list of `RateEntry` objects) has no equivalent — the closest v2 operation is `fetch_rate(base, quote)`, which is a dedicated endpoint and returns a single rate directly.

### v2 Engine — `FrankfurterV2Engine`

| Method | Returns | v1 equivalent |
|--------|---------|---------------|
| `fetch_currencies(scope)` | `v2.CurrenciesResult` | `fetch_currencies()` — different model |
| `fetch_latest_data(base, quotes)` | `list[v2.RateEntry]` | `fetch_latest_data()` — different model |
| `fetch_data_for_date(date, base, quotes)` | `list[v2.RateEntry]` | `fetch_data_for_date()` — different model |
| `fetch_time_series_data(start_date, base, quotes, end_date, group)` | `list[v2.RateEntry]` | `fetch_time_series_data()` — different model |
| `fetch_rate(base, quote)` | `v2.SingleRateResult` | — |
| `fetch_currency_detail(code)` | `v2.CurrencyDetailResult` | — |
| `fetch_providers()` | `v2.ProvidersResult` | — |

Note: the parameter for target currencies is `quotes` in v2, not `symbols`.

---

## API Differences

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

### `/currencies` response

v1 — flat dict, code → name:
```json
{ "EUR": "Euro", "USD": "US Dollar" }
```

v2 — nested, includes provider metadata per currency:
```json
{
  "currencies": {
    "EUR": { "name": "Euro", "providers": ["ECB"] },
    "USD": { "name": "US Dollar", "providers": ["ECB", "CB"] }
  }
}
```

### `/rates` response

v1 — single object, one date for all currencies:
```json
{ "base": "EUR", "date": "2026-04-10", "rates": { "AUD": 1.6561, "BRL": 5.9191 } }
```

v2 — flat list, one object per currency pair, each with its own date:
```json
[
  { "date": "2026-04-13", "base": "EUR", "quote": "AED", "rate": 4.2924 },
  { "date": "2026-04-10", "base": "EUR", "quote": "AUD", "rate": 1.6561 }
]
```

The per-entry date in v2 reflects that not all currencies update on the same day. v1 presents a snapshot with a single timestamp; v2 presents the most recent known rate per pair. These are a semantic difference, not just a structural one.

Consequence for the transport layer: `_api_call` must return `dict | list` — v2 rate endpoints return a JSON array.

### v2-only responses

`GET /rate/{base}/{quote}`:
```json
{ "base": "EUR", "quote": "USD", "rate": 1.085, "date": "2024-01-15" }
```

`GET /currency/{code}`:
```json
{ "code": "EUR", "name": "Euro", "providers": ["ECB", "CB"] }
```

`GET /providers`:
```json
{ "providers": [{ "id": "ECB", "name": "European Central Bank", "url": "https://..." }] }
```

---

## Data Models

Typed dataclasses in `frankfurter/models/v1.py` and `frankfurter/models/v2.py`. No public method returns a raw `dict` or `list`.

### `frankfurter/models/v1.py`

```python
from dataclasses import dataclass

@dataclass
class RatesResult:
    base: str
    date: str
    rates: dict[str, float]             # currency code -> rate

@dataclass
class TimeSeriesResult:
    base: str
    start_date: str
    end_date: str
    rates: dict[str, dict[str, float]]  # date -> { currency code -> rate }

@dataclass
class CurrenciesResult:
    currencies: dict[str, str]          # currency code -> full name
```

### `frankfurter/models/v2.py`

```python
from dataclasses import dataclass

@dataclass
class RateEntry:
    date: str       # per-entry — may differ across entries in the same response
    base: str
    quote: str
    rate: float

# fetch_latest_data, fetch_data_for_date, and fetch_time_series_data all return list[RateEntry]

@dataclass
class CurrencyInfo:
    name: str
    providers: list[str]

@dataclass
class CurrenciesResult:
    currencies: dict[str, CurrencyInfo]  # currency code -> CurrencyInfo

@dataclass
class SingleRateResult:
    base: str
    quote: str
    rate: float
    date: str

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

## Architecture

```
frankfurter/
  models/
    __init__.py
    v1.py
    v2.py
  _base_engine.py     # HTTP transport only: _api_call, timeout, error handling
  _v1_engine.py       # FrankfurterV1Engine
  _v2_engine.py       # FrankfurterV2Engine
  engine.py           # FrankfurterEngine factory function (public entry point)
  exceptions.py
  utils.py
  logger.py
```

### `_base_engine.py`

Handles the transport layer only. No business logic, no URL construction, no model parsing.

- `_api_call(path: str, params: dict | None) -> dict | list` — builds the full URL from `BASE_URL + version prefix + path`, fires the GET request with `timeout`, catches `HTTPError` / `URLError` / `socket.timeout`, raises `FrankfurterCallFailedException`.
- `_currencies_cache: dict | list | None` — instance-level cache for `fetch_currencies`.
- Constructor params: `base_url`, `quiet_mode`, `timeout`.

### `_v1_engine.py` — `FrankfurterV1Engine(BaseEngine)`

- Constructs v1 paths: `/latest`, `/{date}`, `/{start}..{end}`, `/currencies`.
- Uses `symbols` query param for target currencies.
- Parses raw API responses into `models.v1.*` dataclass instances.
- `_check_valid_currency` checks against `v1.CurrenciesResult.currencies` (a `dict[str, str]`).

### `_v2_engine.py` — `FrankfurterV2Engine(BaseEngine)`

- Constructs v2 paths: `/rates`, `/rate/{base}/{quote}`, `/currency/{code}`, `/currencies`, `/providers`.
- Uses `quotes` query param for target currencies.
- Parses raw API responses into `models.v2.*` dataclass instances.
- `_check_valid_currency` checks against `v2.CurrenciesResult.currencies` (a `dict[str, CurrencyInfo]`).
- Does **not** implement `convert_currency`.

### `engine.py` — factory

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

`FrankfurterEngine()` with no arguments returns a v1 engine — existing code continues to work.

---

## Currency Validation

Both engines validate currency codes against `fetch_currencies()` before making any rates request, but they interrogate different model shapes.

`FrankfurterV1Engine._check_valid_currency`:
```python
if currency not in self.fetch_currencies().currencies:
    raise UnknownCurrencyException(f"Unknown currency: {currency!r}")
```

`FrankfurterV2Engine._check_valid_currency`:
```python
if currency not in self.fetch_currencies().currencies:
    raise UnknownCurrencyException(f"Unknown currency: {currency!r}")
```

The call is identical because both `CurrenciesResult` types expose a `.currencies` dict. The types of the values differ (`str` vs `CurrencyInfo`), but key lookup works the same way.

---

## Tests to Write First

### Factory

1. `FrankfurterEngine()` returns a `FrankfurterV1Engine` instance.
2. `FrankfurterEngine(api_version="v2")` returns a `FrankfurterV2Engine` instance.
3. `FrankfurterEngine(api_version="v3")` raises `ValueError`.

### v1 engine

4. `fetch_currencies()` returns a `v1.CurrenciesResult`; `currencies` values are plain strings.
5. `fetch_latest_data()` returns a `v1.RatesResult` with `base`, `date`, and `rates: dict[str, float]`.
6. Request for `fetch_latest_data()` hits `/v1/latest` with query param `symbols`.
7. Request for `fetch_time_series_data()` hits `/v1/{start}..{end}` as a path segment.
8. `convert_currency(100, "EUR", "USD")` returns a `float`.

### v2 engine

9. `fetch_currencies()` returns a `v2.CurrenciesResult`; each value in `currencies` is a `v2.CurrencyInfo` with `name` and `providers`.
10. `fetch_latest_data()` returns `list[v2.RateEntry]`; each entry has `date`, `base`, `quote`, `rate`.
11. Request for `fetch_latest_data()` hits `/v2/rates` with query param `quotes` (not `symbols`).
12. Request for `fetch_time_series_data()` hits `/v2/rates` with query params `from` and `to`, not a path range.
13. `fetch_rate("EUR", "USD")` returns a `v2.SingleRateResult`.
14. `fetch_providers()` returns a `v2.ProvidersResult` with a `providers` list.
15. `FrankfurterV2Engine` has no `convert_currency` attribute.
