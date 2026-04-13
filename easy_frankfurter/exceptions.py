class FrankfurterCallFailedException(Exception):
    def __init__(self, status_code: int, reason: str) -> None:
        self.status_code = status_code
        self.reason = reason
        super().__init__(f"easy_frankfurter: API call failed. Status: {status_code}. Reason: {reason}")


class UnknownCurrencyException(Exception):
    pass
