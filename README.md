# frankfurter — Unofficial Lightweight Wrapper for the Frankfurter API

The Frankfurter API tracks foreign exchange reference rates published by the [European Central Bank](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html). The data refreshes around 16:00 CET every working day.

## Installation

**From PyPI** (current stable release):

```bash
pip install frankfurter
uv add frankfurter
```

**From GitHub** (this version, with v1/v2 support):

```bash
# pip
pip install git+https://github.com/theimes/frankfurter.git

# uv
uv add git+https://github.com/theimes/frankfurter.git
```

## Choosing Between v1 and v2

The library supports two API versions with different design goals. **They are not compatible** — pick the one that fits your use case and stay with it.

| | v1 (default) | v2 |
|---|---|---|
| Response shape | Single aggregated object per request | Flat list of individual rate entries |
| Currency metadata | Name only (`"EUR": "Euro"`) | Rich: symbol, ISO numeric, date range |
| Provider metadata | Not available | Available via `fetch_providers()` |
| Currency conversion | `convert_currency()` built-in | Not available |
| Time series format | Path-based (`2024-01-01..2024-12-31`) | Query params (`from=` / `to=`) |
| Target filter param | `symbols=` | `quotes=` |
| Best for | Simple rate lookups, one-off conversions | Analytics, multi-provider setups, data pipelines |

**Use v1 when** you want a simple dict of rates keyed by currency code, or need the built-in `convert_currency()` helper.

**Use v2 when** you need rich currency/provider metadata, want to work with individual rate records (e.g. insert rows into a database), or are building against a multi-provider setup.

## Quick Start

```python
from frankfurter import FrankfurterEngine

# v1 — default
engine = FrankfurterEngine()

# v2
engine = FrankfurterEngine(api_version="v2")
```

Both constructors accept:
- `quiet_mode` (bool, default `True`) — suppress log output
- `timeout` (float, default `10.0`) — HTTP timeout in seconds

---

## v1 API

### Get supported currencies

```python
result = engine.fetch_currencies()
# result.currencies -> {"EUR": "Euro", "USD": "US Dollar", ...}
```

### Latest rates

```python
result = engine.fetch_latest_data(base="USD", symbols="EUR,GBP,JPY")
# result.base   -> "USD"
# result.date   -> "2024-04-10"
# result.rates  -> {"EUR": 0.921, "GBP": 0.789, "JPY": 151.2}
```

Both `base` and `symbols` are optional. Omitting `base` defaults to EUR (API default).

### Historical rates for a specific date

```python
result = engine.fetch_data_for_date(date="2024-01-15", base="USD", symbols="EUR,BRL")
# Returns the same RatesResult shape as fetch_latest_data
```

### Time series

```python
result = engine.fetch_time_series_data(
    start_date="2024-01-01",
    end_date="2024-01-31",
    base="USD",
    symbols="EUR,INR",
)
# result.base        -> "USD"
# result.start_date  -> "2024-01-01"
# result.end_date    -> "2024-01-31"
# result.rates       -> {"2024-01-01": {"EUR": 0.91, "INR": 83.1}, ...}
```

`start_date` is required. `end_date` defaults to today.

### Currency conversion

```python
amount_in_eur = engine.convert_currency(100, base="USD", to="EUR")
# -> float, e.g. 92.1
```

---

## v2 API

### Get supported currencies

```python
result = engine.fetch_currencies()
# result.currencies -> {"EUR": CurrencyInfo(...), "USD": CurrencyInfo(...), ...}

info = result.currencies["EUR"]
# info.iso_code    -> "EUR"
# info.name        -> "Euro"
# info.symbol      -> "€"
# info.iso_numeric -> "978"
# info.start_date  -> "1999-01-04"
# info.end_date    -> "2026-04-13"
```

### Latest rates

```python
entries = engine.fetch_latest_data(base="EUR", quotes="USD,GBP")
# -> list of RateEntry objects

for entry in entries:
    print(entry.date, entry.base, entry.quote, entry.rate)
    # "2024-04-10"  "EUR"  "USD"  1.085
```

The parameter is `quotes=` (not `symbols=`).

### Historical rates for a specific date

```python
entries = engine.fetch_data_for_date(date="2024-01-15", base="EUR", quotes="USD,GBP")
# -> list[RateEntry]
```

### Time series

```python
entries = engine.fetch_time_series_data(
    start_date="2024-01-01",
    end_date="2024-01-31",
    base="EUR",
    quotes="USD",
)
# -> list[RateEntry], one entry per date per quote currency
```

### Single rate lookup

```python
result = engine.fetch_rate("EUR", "USD")
# result.base   -> "EUR"
# result.quote  -> "USD"
# result.rate   -> 1.085
# result.date   -> "2024-04-10"
```

### Providers

```python
result = engine.fetch_providers()
for p in result.providers:
    print(p.key, p.name, p.pivot_currency)
    # "ECB"  "European Central Bank"  "EUR"
```

---

## Error Handling

```python
from frankfurter.exceptions import FrankfurterCallFailedException, UnknownCurrencyException

try:
    result = engine.fetch_latest_data(base="USD")
except FrankfurterCallFailedException as e:
    print(e.status_code, e.reason)
except UnknownCurrencyException as e:
    print(e)
```

`FrankfurterCallFailedException` is raised for HTTP errors and network timeouts. `UnknownCurrencyException` is raised when an unrecognised currency code is passed to any method.

---

## API Documentation

For details on the underlying REST API, visit [frankfurter.dev](https://www.frankfurter.dev/).
