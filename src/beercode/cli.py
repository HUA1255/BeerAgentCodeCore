from __future__ import annotations

from pathlib import Path

from beercode.config import load_providers
from beercode.session import Session
from beercode.tui.app import BeerCodeApp


def main() -> None:
    providers = load_providers(Path.cwd())
    session = Session(providers[0])
    BeerCodeApp(session).run()
