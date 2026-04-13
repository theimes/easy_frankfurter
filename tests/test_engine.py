import json
import socket
import pytest
from unittest.mock import patch, MagicMock
from urllib.error import URLError

from easy_frankfurter import FrankfurterEngine
from easy_frankfurter.exceptions import FrankfurterCallFailedException
from easy_frankfurter.models import v1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CURRENCIES_V1 = {"EUR": "Euro", "USD": "US Dollar", "GBP": "Pound Sterling"}
RATES_RESPONSE = {"base": "EUR", "date": "2024-01-15", "rates": {"USD": 1.085}}


def mock_urlopen(response_data: dict):
    """Return a context-manager mock that yields a response with the given JSON body."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(response_data).encode()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)
    return MagicMock(return_value=mock_response)


# ---------------------------------------------------------------------------
# Item 3 — HTTP timeout
# ---------------------------------------------------------------------------

def test_timeout_is_passed_to_urlopen():
    """urlopen must be called with the timeout value set on the engine."""
    engine = FrankfurterEngine(timeout=7.0)
    urlopen_mock = mock_urlopen(CURRENCIES_V1)
    with patch("easy_frankfurter._base_engine.urlopen", urlopen_mock):
        engine.fetch_currencies()
    _, call_kwargs = urlopen_mock.call_args
    assert call_kwargs.get("timeout") == 7.0


def test_timeout_default_is_applied():
    """The default timeout (10 s) must be forwarded to urlopen."""
    engine = FrankfurterEngine()
    urlopen_mock = mock_urlopen(CURRENCIES_V1)
    with patch("easy_frankfurter._base_engine.urlopen", urlopen_mock):
        engine.fetch_currencies()
    _, call_kwargs = urlopen_mock.call_args
    assert call_kwargs.get("timeout") == 10.0


def test_socket_timeout_raises_call_failed_exception():
    """A socket.timeout from urlopen must surface as FrankfurterCallFailedException."""
    engine = FrankfurterEngine()
    with patch("easy_frankfurter._base_engine.urlopen", side_effect=socket.timeout()):
        with pytest.raises(FrankfurterCallFailedException):
            engine.fetch_currencies()


def test_url_error_raises_call_failed_exception():
    """A URLError from urlopen must surface as FrankfurterCallFailedException."""
    engine = FrankfurterEngine()
    with patch("easy_frankfurter._base_engine.urlopen", side_effect=URLError("connection refused")):
        with pytest.raises(FrankfurterCallFailedException):
            engine.fetch_currencies()


# ---------------------------------------------------------------------------
# Item 2 — currencies cache (replaces lru_cache)
# ---------------------------------------------------------------------------

def test_fetch_currencies_only_calls_api_once():
    """fetch_currencies must issue only one HTTP request regardless of how many times it is called."""
    engine = FrankfurterEngine()
    urlopen_mock = mock_urlopen(CURRENCIES_V1)
    with patch("easy_frankfurter._base_engine.urlopen", urlopen_mock):
        first = engine.fetch_currencies()
        second = engine.fetch_currencies()
    assert urlopen_mock.call_count == 1
    assert first == second


def test_currencies_cache_can_be_invalidated():
    """Setting _currencies_cache = None must trigger a fresh API call."""
    engine = FrankfurterEngine()
    urlopen_mock = mock_urlopen(CURRENCIES_V1)
    with patch("easy_frankfurter._base_engine.urlopen", urlopen_mock):
        engine.fetch_currencies()
        engine._currencies_cache = None
        engine.fetch_currencies()
    assert urlopen_mock.call_count == 2


# ---------------------------------------------------------------------------
# Item 8 — symbols normalisation
# ---------------------------------------------------------------------------

def test_symbols_with_spaces_are_normalised_in_request():
    """'EUR, INR' must reach the API as 'EUR,INR' — spaces stripped."""
    engine = FrankfurterEngine()
    urlopen_mock = mock_urlopen(RATES_RESPONSE)
    with patch("easy_frankfurter._base_engine.urlopen", urlopen_mock):
        # Seed the cache so currency validation doesn't make extra calls
        engine._currencies_cache = v1.CurrenciesResult(
            currencies={**CURRENCIES_V1, "INR": "Indian Rupee"}
        )
        engine.fetch_latest_data(symbols="EUR, INR")
    called_url = urlopen_mock.call_args[0][0].full_url
    assert "EUR%2CINR" in called_url or "symbols=EUR%2CINR" in called_url or "EUR,INR" in called_url
    assert " " not in called_url


# ---------------------------------------------------------------------------
# Item 7 — date validation
# ---------------------------------------------------------------------------

def test_fetch_data_for_date_rejects_invalid_date():
    """fetch_data_for_date must raise ValueError for a malformed date string, before any network call."""
    engine = FrankfurterEngine()
    with patch("easy_frankfurter._base_engine.urlopen") as urlopen_mock:
        with pytest.raises(ValueError):
            engine.fetch_data_for_date("not-a-date")
    urlopen_mock.assert_not_called()


def test_fetch_time_series_rejects_invalid_start_date():
    """fetch_time_series_data must raise ValueError for a malformed start_date, before any network call."""
    engine = FrankfurterEngine()
    with patch("easy_frankfurter._base_engine.urlopen") as urlopen_mock:
        with pytest.raises(ValueError):
            engine.fetch_time_series_data(start_date="2022-13-01")
    urlopen_mock.assert_not_called()


def test_fetch_time_series_rejects_invalid_end_date():
    """fetch_time_series_data must raise ValueError for a malformed end_date, before any network call."""
    engine = FrankfurterEngine()
    with patch("easy_frankfurter._base_engine.urlopen") as urlopen_mock:
        with pytest.raises(ValueError):
            engine.fetch_time_series_data(start_date="2022-01-01", end_date="2022-99-99")
    urlopen_mock.assert_not_called()


# ---------------------------------------------------------------------------
# Item 6 — start_date is required in fetch_time_series_data
# ---------------------------------------------------------------------------

def test_fetch_time_series_requires_start_date():
    """Calling fetch_time_series_data without start_date must raise TypeError, not silently fall back."""
    engine = FrankfurterEngine()
    with pytest.raises(TypeError):
        engine.fetch_time_series_data()
