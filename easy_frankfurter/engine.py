from ._v1_engine import FrankfurterV1Engine
from ._v2_engine import FrankfurterV2Engine


def FrankfurterEngine(
    api_version: str = "v1",
    quiet_mode: bool = True,
    timeout: float = 10.0,
) -> FrankfurterV1Engine | FrankfurterV2Engine:
    """
    Factory function that returns the appropriate engine for the requested API version.

    Parameters:
        api_version (str): API version to use — 'v1' or 'v2'. Defaults to 'v1'.
        quiet_mode (bool): Suppress info logging when True. Defaults to True.
        timeout (float): HTTP request timeout in seconds. Defaults to 10.0.

    Returns:
        FrankfurterV1Engine for api_version='v1', FrankfurterV2Engine for api_version='v2'.

    Raises:
        ValueError: If api_version is not 'v1' or 'v2'.
    """
    if api_version == "v1":
        return FrankfurterV1Engine(quiet_mode=quiet_mode, timeout=timeout)
    if api_version == "v2":
        return FrankfurterV2Engine(quiet_mode=quiet_mode, timeout=timeout)
    raise ValueError(f"Unknown api_version: {api_version!r}. Expected 'v1' or 'v2'.")
