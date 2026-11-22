from __future__ import annotations

import time
from dataclasses import dataclass

from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.message import Message
from textual.widgets import Label, Static, TextArea

from beercode.config import Provider


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
        pass


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
    """

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


class PromptInput(TextArea):
    DEFAULT_CSS = """
    PromptInput {
        height: auto;
        max-height: 10;
        min-height: 3;
    }
    """

    @dataclass
    class Submitted(Message):
        text: str

    async def _on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            self.post_message(self.Submitted(self.text))
            return
        await super()._on_key(event)


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
