from __future__ import annotations

from collections.abc import Iterable

from textual import events
from textual._xterm_parser import XTermParser

ALT_ENTER = "alt+enter"
ALT_ENTER_SEQUENCES = frozenset({"\x1b\r", "\x1b\n"})

_original_sequence_to_key_events = XTermParser._sequence_to_key_events


def _sequence_to_key_events(self: XTermParser, sequence: str, alt: bool = False) -> Iterable[events.Key]:
    if sequence in ALT_ENTER_SEQUENCES:
        yield events.Key(ALT_ENTER, None)
        return
    yield from _original_sequence_to_key_events(self, sequence, alt)


def install_alt_enter() -> None:
    XTermParser._sequence_to_key_events = _sequence_to_key_events
