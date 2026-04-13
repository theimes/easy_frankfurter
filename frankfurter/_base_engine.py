import json
import socket
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError

from .exceptions import FrankfurterCallFailedException
from .logger import Logger
from .utils import BASE_HEADERS


class BaseEngine:
    def __init__(self, base_url: str, quiet_mode: bool = True, timeout: float = 10.0) -> None:
        self.quiet_mode = quiet_mode
        self._timeout = timeout
        self._currencies_cache = None
        self._base_url = base_url
        self._base_headers = BASE_HEADERS
        if not quiet_mode:
            Logger.info("Currency Engine Initialized")

    def _api_call(self, path: str, params: dict | None = None) -> dict | list:
        """Fire a GET request and return the parsed JSON body (dict or list)."""
        params = params or {}
        params_str = urlencode({k: v for k, v in params.items() if v is not None})
        url = f"https://{self._base_url}/{path}"
        if params_str:
            url = f"{url}?{params_str}"
        request = Request(url=url, method="GET", headers=self._base_headers)
        try:
            with urlopen(request, timeout=self._timeout) as response:
                if not self.quiet_mode:
                    Logger.info("Found the Forex data successfully")
                return json.loads(response.read().decode())
        except HTTPError as e:
            raise FrankfurterCallFailedException(e.code, e.msg)
        except (URLError, socket.timeout) as e:
            raise FrankfurterCallFailedException(0, str(e))
