# Frankfurter Response

In `v1`

```json
/* https://api.frankfurter.dev/v1/latest */
{
  "base": "EUR",
  "date": "2026-04-10",
  "rates": {
    "AUD": 1.6561,
    "BRL": 5.9191,
    "CAD": 1.6187,
    "CHF": 0.9241,
    "...": "..."
  }
}
```

In `v2`

```json
/* https://api.frankfurter.dev/v2/rates */
[
  {
    "date": "2026-04-13",
    "base": "EUR",
    "quote": "AED",
    "rate": 4.2924
  },
  {
    "date": "2026-04-10",
    "base": "EUR",
    "quote": "AFN",
    "rate": 75.647
  },
  {
    "date": "2026-04-10",
    "base": "EUR",
    "quote": "ALL",
    "rate": 95.85
  },
  {
    "date": "2026-04-10",
    "base": "EUR",
    "quote": "AMD",
    "rate": 439.48
  },
  "..."
]
```