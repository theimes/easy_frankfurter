import json
import pytest
from unittest.mock import patch, MagicMock

from frankfurter import FrankfurterEngine
from frankfurter._v1_engine import FrankfurterV1Engine
from frankfurter._v2_engine import FrankfurterV2Engine
from frankfurter.models import v1, v2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

V1_CURRENCIES_RAW = {"EUR": "Euro", "USD": "US Dollar", "GBP": "Pound Sterling"}

# v2 /currencies returns a flat array
V2_CURRENCIES_RAW = [
    {"iso_code": "EUR", "name": "Euro", "symbol": "€", "iso_numeric": "978",
     "start_date": "1999-01-04", "end_date": "2026-04-13"},
    {"iso_code": "USD", "name": "US Dollar", "symbol": "$", "iso_numeric": "840",
     "start_date": "1999-01-04", "end_date": "2026-04-13"},
    {"iso_code": "GBP", "name": "Pound Sterling", "symbol": "£", "iso_numeric": "826",
     "start_date": "1999-01-04", "end_date": "2026-04-13"},
]

V1_RATES_RAW = {"base": "EUR", "date": "2026-04-10", "rates": {"USD": 1.085, "GBP": 0.872}}

V2_RATES_RAW = [
    {"date": "2026-04-10", "base": "EUR", "quote": "USD", "rate": 1.085},
    {"date": "2026-04-10", "base": "EUR", "quote": "GBP", "rate": 0.872},
]

V2_SINGLE_RATE_RAW = {"base": "EUR", "quote": "USD", "rate": 1.085, "date": "2026-04-10"}

# v2 /providers returns a flat array
V2_PROVIDERS_RAW = [
    {
        "key": "ECB", "name": "European Central Bank", "country_code": "EU",
        "rate_type": "reference rate", "pivot_currency": "EUR",
        "data_url": "https://ecb.europa.eu", "terms_url": None,
        "start_date": "1999-01-04", "end_date": "2026-04-13",
        "currencies": ["USD", "GBP", "JPY"],
    }
]

# Seeded v2 cache for tests that need valid currency lookups
V2_CURRENCIES_CACHE = v2.CurrenciesResult(
    currencies={
        "EUR": v2.CurrencyInfo("EUR", "Euro", "€", "978", "1999-01-04", "2026-04-13"),
        "USD": v2.CurrencyInfo("USD", "US Dollar", "$", "840", "1999-01-04", "2026-04-13"),
        "GBP": v2.CurrencyInfo("GBP", "Pound Sterling", "£", "826", "1999-01-04", "2026-04-13"),
    }
)


def mock_urlopen(response_data):
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(response_data).encode()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)
    return MagicMock(return_value=mock_response)


PATCH = "frankfurter._base_engine.urlopen"


# ---------------------------------------------------------------------------
# Factory — tests 1-3
# ---------------------------------------------------------------------------

def test_factory_default_returns_v1_engine():
    assert isinstance(FrankfurterEngine(), FrankfurterV1Engine)


def test_factory_v2_returns_v2_engine():
    assert isinstance(FrankfurterEngine(api_version="v2"), FrankfurterV2Engine)


def test_factory_unknown_version_raises_value_error():
    with pytest.raises(ValueError):
        FrankfurterEngine(api_version="v3")


# ---------------------------------------------------------------------------
# v1 engine — tests 4-8
# ---------------------------------------------------------------------------

def test_v1_fetch_currencies_returns_currencies_result():
    engine = FrankfurterV1Engine()
    with patch(PATCH, mock_urlopen(V1_CURRENCIES_RAW)):
        result = engine.fetch_currencies()
    assert isinstance(result, v1.CurrenciesResult)
    assert isinstance(result.currencies, dict)
    assert isinstance(result.currencies["EUR"], str)


def test_v1_fetch_latest_data_returns_rates_result():
    engine = FrankfurterV1Engine()
    engine._currencies_cache = v1.CurrenciesResult(currencies=V1_CURRENCIES_RAW)
    with patch(PATCH, mock_urlopen(V1_RATES_RAW)):
        result = engine.fetch_latest_data()
    assert isinstance(result, v1.RatesResult)
    assert result.base == "EUR"
    assert result.date == "2026-04-10"
    assert isinstance(result.rates, dict)
    assert isinstance(result.rates["USD"], float)


def test_v1_fetch_latest_data_url_uses_latest_path_and_symbols_param():
    engine = FrankfurterV1Engine()
    urlopen_mock = mock_urlopen(V1_RATES_RAW)
    with patch(PATCH, urlopen_mock):
        engine._currencies_cache = v1.CurrenciesResult(currencies=V1_CURRENCIES_RAW)
        engine.fetch_latest_data(base="EUR", symbols="USD,GBP")
    called_url = urlopen_mock.call_args[0][0].full_url
    assert "/v1/latest" in called_url
    assert "symbols=" in called_url
    assert "quotes=" not in called_url


def test_v1_fetch_time_series_url_uses_path_range():
    engine = FrankfurterV1Engine()
    time_series_raw = {
        "base": "EUR",
        "start_date": "2026-04-07",
        "end_date": "2026-04-10",
        "rates": {
            "2026-04-07": {"USD": 1.08},
            "2026-04-10": {"USD": 1.09},
        },
    }
    urlopen_mock = mock_urlopen(time_series_raw)
    with patch(PATCH, urlopen_mock):
        engine._currencies_cache = v1.CurrenciesResult(currencies=V1_CURRENCIES_RAW)
        engine.fetch_time_series_data(start_date="2026-04-07", end_date="2026-04-10")
    called_url = urlopen_mock.call_args[0][0].full_url
    assert "2026-04-07..2026-04-10" in called_url
    assert "/v1/" in called_url


def test_v1_convert_currency_returns_float():
    engine = FrankfurterV1Engine()
    urlopen_mock = mock_urlopen(V1_RATES_RAW)
    with patch(PATCH, urlopen_mock):
        engine._currencies_cache = v1.CurrenciesResult(currencies=V1_CURRENCIES_RAW)
        result = engine.convert_currency(100, "EUR", "USD")
    assert isinstance(result, float)
    assert result == pytest.approx(108.5)


# ---------------------------------------------------------------------------
# v2 engine — tests 9-15
# ---------------------------------------------------------------------------

def test_v2_fetch_currencies_returns_currencies_result_with_currency_info():
    engine = FrankfurterV2Engine()
    with patch(PATCH, mock_urlopen(V2_CURRENCIES_RAW)):
        result = engine.fetch_currencies()
    assert isinstance(result, v2.CurrenciesResult)
    assert isinstance(result.currencies["EUR"], v2.CurrencyInfo)
    assert result.currencies["EUR"].name == "Euro"
    assert result.currencies["EUR"].iso_code == "EUR"


def test_v2_fetch_latest_data_returns_list_of_rate_entries():
    engine = FrankfurterV2Engine()
    with patch(PATCH, mock_urlopen(V2_RATES_RAW)):
        engine._currencies_cache = V2_CURRENCIES_CACHE
        result = engine.fetch_latest_data()
    assert isinstance(result, list)
    assert all(isinstance(e, v2.RateEntry) for e in result)
    entry = result[0]
    assert hasattr(entry, "date")
    assert hasattr(entry, "base")
    assert hasattr(entry, "quote")
    assert hasattr(entry, "rate")


def test_v2_fetch_latest_data_url_uses_rates_path_and_quotes_param():
    engine = FrankfurterV2Engine()
    urlopen_mock = mock_urlopen(V2_RATES_RAW)
    with patch(PATCH, urlopen_mock):
        engine._currencies_cache = V2_CURRENCIES_CACHE
        engine.fetch_latest_data(base="EUR", quotes="USD")
    called_url = urlopen_mock.call_args[0][0].full_url
    assert "/v2/rates" in called_url
    assert "quotes=" in called_url
    assert "symbols=" not in called_url


def test_v2_fetch_time_series_url_uses_from_and_to_query_params():
    engine = FrankfurterV2Engine()
    v2_time_series_raw = [
        {"date": "2026-04-07", "base": "EUR", "quote": "USD", "rate": 1.08},
        {"date": "2026-04-10", "base": "EUR", "quote": "USD", "rate": 1.09},
    ]
    urlopen_mock = mock_urlopen(v2_time_series_raw)
    with patch(PATCH, urlopen_mock):
        engine._currencies_cache = V2_CURRENCIES_CACHE
        engine.fetch_time_series_data(start_date="2026-04-07", end_date="2026-04-10")
    called_url = urlopen_mock.call_args[0][0].full_url
    assert "/v2/rates" in called_url
    assert "from=" in called_url
    assert "to=" in called_url
    assert ".." not in called_url


def test_v2_fetch_rate_returns_single_rate_result():
    engine = FrankfurterV2Engine()
    with patch(PATCH, mock_urlopen(V2_SINGLE_RATE_RAW)):
        engine._currencies_cache = V2_CURRENCIES_CACHE
        result = engine.fetch_rate("EUR", "USD")
    assert isinstance(result, v2.SingleRateResult)
    assert result.base == "EUR"
    assert result.quote == "USD"
    assert isinstance(result.rate, float)


def test_v2_fetch_providers_returns_providers_result():
    engine = FrankfurterV2Engine()
    with patch(PATCH, mock_urlopen(V2_PROVIDERS_RAW)):
        result = engine.fetch_providers()
    assert isinstance(result, v2.ProvidersResult)
    assert len(result.providers) > 0
    assert isinstance(result.providers[0], v2.Provider)
    assert result.providers[0].key == "ECB"


def test_v2_engine_has_no_convert_currency():
    engine = FrankfurterV2Engine()
    assert not hasattr(engine, "convert_currency")
