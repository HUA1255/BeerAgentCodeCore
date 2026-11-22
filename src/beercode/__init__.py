from importlib.metadata import version

__version__ = version("beercode")


def main() -> None:
    from beercode.cli import main as cli_main

    cli_main()
