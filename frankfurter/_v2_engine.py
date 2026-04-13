from ._base_engine import BaseEngine
from .exceptions import UnknownCurrencyException
from .models import v2
from .utils import BASE_URL, normalise_symbols, parse_date


class FrankfurterV2Engine(BaseEngine):
    def __init__(self, quiet_mode: bool = True, timeout: float = 10.0) -> None:
        super().__init__(
            base_url=f"{BASE_URL}/v2",
            quiet_mode=quiet_mode,
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_valid_currency(self, currency: str) -> None:
        if currency not in self.fetch_currencies().currencies:
            raise UnknownCurrencyException(f"Unknown Currency : {currency}")

    def _validate_quotes(self, quotes: str) -> str:
        quotes = normalise_symbols(quotes)
        for code in quotes.split(","):
            self._check_valid_currency(code)
        return quotes

    @staticmethod
    def _parse_rates(raw: list) -> list[v2.RateEntry]:
        return [
            v2.RateEntry(date=e["date"], base=e["base"], quote=e["quote"], rate=e["rate"])
            for e in raw
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_currencies(self, scope: str | None = None) -> v2.CurrenciesResult:
        if self._currencies_cache is None:
            raw = self._api_call("currencies", {"scope": scope})
            # API returns a flat array of currency objects
            self._currencies_cache = v2.CurrenciesResult(
                currencies={
                    entry["iso_code"]: v2.CurrencyInfo(
                        iso_code=entry["iso_code"],
                        name=entry["name"],
                        symbol=entry.get("symbol", ""),
                        iso_numeric=entry.get("iso_numeric", ""),
                        start_date=entry.get("start_date", ""),
                        end_date=entry.get("end_date", ""),
                    )
                    for entry in raw
                }
            )
        return self._currencies_cache

    def fetch_latest_data(
        self,
        base: str | None = None,
        quotes: str | None = None,
    ) -> list[v2.RateEntry]:
        if quotes:
            quotes = self._validate_quotes(quotes)
        if base:
            self._check_valid_currency(base)
        raw = self._api_call("rates", {"base": base, "quotes": quotes})
        return self._parse_rates(raw)

    def fetch_data_for_date(
        self,
        date: str,
        base: str | None = None,
        quotes: str | None = None,
    ) -> list[v2.RateEntry]:
        parse_date(date, "date")
        if quotes:
            quotes = self._validate_quotes(quotes)
        if base:
            self._check_valid_currency(base)
        raw = self._api_call("rates", {"base": base, "quotes": quotes, "date": date})
        return self._parse_rates(raw)

    def fetch_time_series_data(
        self,
        start_date: str,
        base: str | None = None,
        quotes: str | None = None,
        end_date: str | None = None,
        group: str | None = None,
    ) -> list[v2.RateEntry]:
        parse_date(start_date, "start_date")
        if end_date:
            parse_date(end_date, "end_date")
        if quotes:
            quotes = self._validate_quotes(quotes)
        if base:
            self._check_valid_currency(base)
        raw = self._api_call(
            "rates",
            {"base": base, "quotes": quotes, "from": start_date, "to": end_date, "group": group},
        )
        return self._parse_rates(raw)

    def fetch_rate(self, base: str, quote: str) -> v2.SingleRateResult:
        self._check_valid_currency(base)
        self._check_valid_currency(quote)
        raw = self._api_call(f"rate/{base}/{quote}")
        return v2.SingleRateResult(
            base=raw["base"],
            quote=raw["quote"],
            rate=raw["rate"],
            date=raw["date"],
        )

    def fetch_currency_detail(self, code: str) -> v2.CurrencyDetailResult:
        self._check_valid_currency(code)
        raw = self._api_call(f"currency/{code}")
        return v2.CurrencyDetailResult(
            code=raw["code"],
            name=raw["name"],
            providers=raw.get("providers", []),
        )

    def fetch_providers(self) -> v2.ProvidersResult:
        raw = self._api_call("providers")
        # API returns a flat array of provider objects
        return v2.ProvidersResult(
            providers=[
                v2.Provider(
                    key=p["key"],
                    name=p["name"],
                    country_code=p.get("country_code"),
                    rate_type=p.get("rate_type", ""),
                    pivot_currency=p.get("pivot_currency", ""),
                    data_url=p.get("data_url"),
                    terms_url=p.get("terms_url"),
                    start_date=p.get("start_date", ""),
                    end_date=p.get("end_date", ""),
                    currencies=p.get("currencies", []),
                )
                for p in raw
            ]
        )
