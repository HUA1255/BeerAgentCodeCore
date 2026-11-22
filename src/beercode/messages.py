from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class Message:
    role: Literal["user", "assistant"]
    text: str
    native: Any = None


@dataclass(frozen=True)
class TextDelta:
    text: str


@dataclass(frozen=True)
class ReplyComplete:
    message: Message


StreamEvent = TextDelta | ReplyComplete
