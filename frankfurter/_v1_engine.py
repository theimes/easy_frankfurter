from ._base_engine import BaseEngine
from .exceptions import FrankfurterCallFailedException, UnknownCurrencyException
from .models import v1
from .utils import BASE_URL, normalise_symbols, parse_date


class FrankfurterV1Engine(BaseEngine):
    def __init__(self, quiet_mode: bool = True, timeout: float = 10.0) -> None:
        super().__init__(
            base_url=f"{BASE_URL}/v1",
            quiet_mode=quiet_mode,
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_valid_currency(self, currency: str) -> None:
        if currency not in self.fetch_currencies().currencies:
            raise UnknownCurrencyException(f"Unknown Currency : {currency}")

    def _validate_symbols(self, symbols: str) -> str:
        symbols = normalise_symbols(symbols)
        for code in symbols.split(","):
            self._check_valid_currency(code)
        return symbols

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_currencies(self) -> v1.CurrenciesResult:
        if self._currencies_cache is None:
            raw = self._api_call("currencies")
            self._currencies_cache = v1.CurrenciesResult(currencies=raw)
        return self._currencies_cache

    def fetch_latest_data(
        self,
        base: str | None = None,
        symbols: str | None = None,
    ) -> v1.RatesResult:
        if symbols:
            symbols = self._validate_symbols(symbols)
        if base:
            self._check_valid_currency(base)
        raw = self._api_call("latest", {"base": base, "symbols": symbols})
        return v1.RatesResult(base=raw["base"], date=raw["date"], rates=raw["rates"])

    def fetch_data_for_date(
        self,
        date: str,
        base: str | None = None,
        symbols: str | None = None,
    ) -> v1.RatesResult:
        parse_date(date, "date")
        if symbols:
            symbols = self._validate_symbols(symbols)
        if base:
            self._check_valid_currency(base)
        raw = self._api_call(date, {"base": base, "symbols": symbols})
        return v1.RatesResult(base=raw["base"], date=raw["date"], rates=raw["rates"])

    def fetch_time_series_data(
        self,
        start_date: str,
        base: str | None = None,
        symbols: str | None = None,
        end_date: str | None = None,
    ) -> v1.TimeSeriesResult:
        parse_date(start_date, "start_date")
        if end_date:
            parse_date(end_date, "end_date")
        if symbols:
            symbols = self._validate_symbols(symbols)
        if base:
            self._check_valid_currency(base)
        path = f"{start_date}..{end_date or ''}"
        raw = self._api_call(path, {"base": base, "symbols": symbols})
        return v1.TimeSeriesResult(
            base=raw["base"],
            start_date=raw.get("start_date", start_date),
            end_date=raw.get("end_date", end_date or ""),
            rates=raw["rates"],
        )

    def convert_currency(self, amount: float, base: str, to: str) -> float:
        self._check_valid_currency(base)
        self._check_valid_currency(to)
        result = self.fetch_latest_data(base=base, symbols=to)
        exchange_rate = result.rates.get(to)
        if exchange_rate:
            return amount * exchange_rate
        raise FrankfurterCallFailedException(404, f"No exchange rate found for {base} to {to}.")
