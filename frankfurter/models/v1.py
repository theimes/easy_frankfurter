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
