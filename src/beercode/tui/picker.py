from __future__ import annotations

from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Label, OptionList
from textual.widgets.option_list import Option

from beercode.config import Provider


def _row(provider: Provider) -> Table:
    table = Table.grid(expand=True)
    table.add_column(ratio=1)
    table.add_column(justify="right")
    table.add_row(Text(provider.name), Text(provider.model, style="dim"))
    return table


class ProviderPicker(App[Provider | None]):
    TITLE = "BeerCode"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [Binding("ctrl+c", "quit", "Quit", priority=True, show=False)]
    CSS = """
    #picker-title {
        padding: 1 1 0 1;
    }
    #providers {
        height: auto;
        max-height: 1fr;
        margin: 1 1;
    }
    """

    def __init__(self, providers: list[Provider]) -> None:
        super().__init__()
        self.providers = providers

    def compose(self) -> ComposeResult:
        yield Label("Select a provider (↑/↓, Enter)", id="picker-title")
        yield OptionList(*(Option(_row(provider)) for provider in self.providers), id="providers")

    def on_mount(self) -> None:
        options = self.query_one(OptionList)
        options.highlighted = 0
        options.focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.exit(self.providers[event.option_index])
