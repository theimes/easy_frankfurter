from dataclasses import dataclass


@dataclass
class RateEntry:
    date: str       # per-entry — may differ across entries in the same response
    base: str
    quote: str
    rate: float


@dataclass
class CurrencyInfo:
    iso_code: str
    name: str
    symbol: str
    iso_numeric: str
    start_date: str
    end_date: str


@dataclass
class CurrenciesResult:
    currencies: dict[str, CurrencyInfo]  # iso_code -> CurrencyInfo


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
    key: str
    name: str
    country_code: str | None
    rate_type: str
    pivot_currency: str
    data_url: str | None
    terms_url: str | None
    start_date: str
    end_date: str
    currencies: list[str]


@dataclass
class ProvidersResult:
    providers: list[Provider]
