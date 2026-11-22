from __future__ import annotations

import sys
from pathlib import Path

from beercode.config import ConfigError, load_providers
from beercode.session import Session
from beercode.tui.app import BeerCodeApp
from beercode.tui.picker import ProviderPicker


def main() -> None:
    try:
        providers = load_providers(Path.cwd())
    except ConfigError as error:
        print(f"配置错误：{error}", file=sys.stderr)
        sys.exit(1)
    provider = providers[0] if len(providers) == 1 else ProviderPicker(providers).run()
    if provider is None:
        return
    session = Session(provider)
    BeerCodeApp(session).run()
