from __future__ import annotations

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


class ErrorEntry(Static):
    DEFAULT_CSS = """
    ErrorEntry {
        margin: 1 0 0 0;
        padding: 0 1;
        color: $error;
        background: $error 15%;
        border-left: thick $error;
        text-style: bold;
    }
    """

    def __init__(self, message: str) -> None:
        super().__init__(f"✗ 错误：{message}", markup=False)
        self.message = message


class Conversation(VerticalScroll):
    DEFAULT_CSS = """
    Conversation {
        height: 1fr;
        padding: 0 1;
    }
    """

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

    async def add_error(self, message: str) -> ErrorEntry:
        entry = ErrorEntry(message)
        await self.mount(entry)
        self.scroll_end(animate=False)
        return entry


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
