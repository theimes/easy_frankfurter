import pytest
from frankfurter.exceptions import FrankfurterCallFailedException, UnknownCurrencyException


def test_frankfurter_exception_is_catchable_by_type():
    """FrankfurterCallFailedException must be catchable by its own type, not only as Exception."""
    with pytest.raises(FrankfurterCallFailedException):
        raise FrankfurterCallFailedException(404, "Not found")


def test_frankfurter_exception_exposes_status_code():
    """Caught exception must expose status_code as an attribute."""
    with pytest.raises(FrankfurterCallFailedException) as exc_info:
        raise FrankfurterCallFailedException(422, "Unprocessable")
    assert exc_info.value.status_code == 422


def test_frankfurter_exception_exposes_reason():
    """Caught exception must expose reason as an attribute."""
    with pytest.raises(FrankfurterCallFailedException) as exc_info:
        raise FrankfurterCallFailedException(500, "Server error")
    assert exc_info.value.reason == "Server error"


def test_unknown_currency_exception_is_catchable_by_type():
    """UnknownCurrencyException must be catchable by its own type."""
    with pytest.raises(UnknownCurrencyException):
        raise UnknownCurrencyException("Unknown currency: XYZ")
