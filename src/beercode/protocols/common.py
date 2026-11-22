from __future__ import annotations

from collections.abc import Mapping

from beercode.config import Provider

MAX_TOKENS = 8192
TIMEOUT_SECONDS = 120.0


def client_options(provider: Provider, headers: Mapping[str, str]) -> dict:
    return {
        "api_key": provider.api_key,
        "base_url": provider.base_url,
        "default_headers": dict(headers),
        "timeout": TIMEOUT_SECONDS,
        "max_retries": 0,
    }
