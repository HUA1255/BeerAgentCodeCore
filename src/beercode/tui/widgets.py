from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from rich.markdown import Markdown
from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Label, Static, TextArea

from beercode import __version__
from beercode.config import Provider
from beercode.tui.keys import ALT_ENTER, install_alt_enter

install_alt_enter()

BEER_ART = "\n".join([
    "  .~~~~.  ",
    "  i====i_ ",
    "  |cccc|_)",
    "  |cccc|  ",
    "  `-==-'  ",
])

READY_TEXT = "Ready. Type a message and press Enter to send."


class Banner(Horizontal):
    DEFAULT_CSS = """
    Banner {
        height: auto;
        border: round $accent;
        padding: 0 1;
    }
    Banner #beer-art {
        width: auto;
        color: $warning;
        margin: 0 2 0 0;
    }
    Banner #banner-info {
        width: 1fr;
        height: auto;
    }
    Banner #app-name {
        text-style: bold;
    }
    Banner #cwd {
        color: $text-muted;
    }
    """

    def __init__(self, cwd: Path | None = None) -> None:
        super().__init__()
        self.cwd = cwd or Path.cwd()

    def compose(self) -> ComposeResult:
        yield Static(BEER_ART, id="beer-art", markup=False)
        with Vertical(id="banner-info"):
            yield Static(f"BeerCode v{__version__}", id="app-name", markup=False)
            yield Static("Claude Code style AI coding assistant", markup=False)
            yield Static(f"cwd: {self.cwd}", id="cwd", markup=False)


class UserEntry(Static):
    DEFAULT_CSS = """
    UserEntry {
        margin: 1 0 0 0;
        color: $text-muted;
    }
    """

    def __init__(self, text: str) -> None:
        super().__init__(f"> {text}", markup=False)


class AssistantEntry(Static):
    DEFAULT_CSS = """
    AssistantEntry {
        margin: 1 0 0 0;
    }
    """

    def __init__(self) -> None:
        super().__init__("", markup=False)
        self.text = ""

    def append(self, delta: str) -> None:
        self.text += delta
        self.update(self.text)

    def finish(self) -> None:
        self.update(Markdown(self.text, code_theme="monokai"))


class TurnTimer(Static):
    DEFAULT_CSS = """
    TurnTimer {
        color: $text-muted;
    }
    """

    FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self) -> None:
        super().__init__("", markup=False)
        self.started = time.monotonic()
        self.frame = 0

    def on_mount(self) -> None:
        self.refresh_label()
        self.ticker = self.set_interval(0.1, self.tick)

    def elapsed(self) -> int:
        return int(time.monotonic() - self.started)

    def tick(self) -> None:
        self.frame = (self.frame + 1) % len(self.FRAMES)
        self.refresh_label()

    def refresh_label(self) -> None:
        self.update(f"{self.FRAMES[self.frame]} Imagining… ({self.elapsed()}s)")

    def stop(self) -> None:
        self.ticker.stop()
        self.update(f"✻ Imagined for {self.elapsed()}s")


class Conversation(VerticalScroll):
    DEFAULT_CSS = """
    Conversation {
        height: 1fr;
        padding: 0 1;
    }
    Conversation #ready {
        margin: 1 0 0 0;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        yield Banner()
        yield Static(READY_TEXT, id="ready", markup=False)

    def on_mount(self) -> None:
        self.anchor()

    async def add_user(self, text: str) -> UserEntry:
        entry = UserEntry(text)
        await self.mount(entry)
        self.scroll_end(animate=False)
        return entry

    async def add_assistant(self) -> AssistantEntry:
        entry = AssistantEntry()
        await self.mount(entry)
        self.scroll_end(animate=False)
        return entry

    async def add_timer(self) -> TurnTimer:
        timer = TurnTimer()
        await self.mount(timer)
        self.scroll_end(animate=False)
        return timer


PLACEHOLDER = "Send a message..."


class PromptInput(TextArea):
    DEFAULT_CSS = """
    PromptInput {
        height: auto;
        max-height: 8;
        border: none;
        padding: 0;
        background: transparent;
    }
    PromptInput:focus {
        border: none;
        background-tint: transparent;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(placeholder=PLACEHOLDER, soft_wrap=True, show_line_numbers=False, highlight_cursor_line=False, compact=True, **kwargs)

    @dataclass
    class Submitted(Message):
        text: str

    async def _on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            self.post_message(self.Submitted(self.text))
            return
        if event.key == ALT_ENTER:
            event.prevent_default()
            event.stop()
            self.insert("\n")
            return
        await super()._on_key(event)


class PromptBox(Horizontal):
    DEFAULT_CSS = """
    PromptBox {
        height: auto;
        border: round $primary;
        padding: 0 1;
    }
    PromptBox #prompt-symbol {
        width: 2;
        color: $primary;
        text-style: bold;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("❯", id="prompt-symbol", markup=False)
        yield PromptInput(id="prompt")


class StatusBar(Horizontal):
    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        padding: 0 1;
    }
    StatusBar #provider-name {
        width: 1fr;
    }
    StatusBar #model-name {
        width: auto;
    }
    """

    def __init__(self, provider: Provider) -> None:
        super().__init__()
        self.provider = provider

    def compose(self) -> ComposeResult:
        yield Label(self.provider.name, id="provider-name", markup=False)
        yield Label(self.provider.model, id="model-name", markup=False)
