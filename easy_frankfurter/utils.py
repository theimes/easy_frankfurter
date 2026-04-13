from datetime import date as _date

BASE_URL = "api.frankfurter.dev"
BASE_HEADERS = {"Accept": "*/*", "User-Agent": "Python Package"}


def normalise_symbols(symbols: str) -> str:
    return ",".join(s.strip() for s in symbols.split(","))


def parse_date(value: str, param_name: str) -> str:
    try:
        _date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"'{param_name}' must be in YYYY-MM-DD format, got: {value!r}")
    return value
