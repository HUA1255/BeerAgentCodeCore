from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from typing import Protocol

from beercode.config import Provider
from beercode.messages import Message, StreamEvent


class ProtocolClient(Protocol):
    def stream(self, system: str, history: Sequence[Message]) -> AsyncIterator[StreamEvent]: ...


ClientFactory = Callable[[Provider, Mapping[str, str]], ProtocolClient]


def _openai_factory(provider: Provider, headers: Mapping[str, str]) -> ProtocolClient:
    from beercode.protocols.openai_chat import OpenAIChatClient

    return OpenAIChatClient(provider, headers)


def _anthropic_factory(provider: Provider, headers: Mapping[str, str]) -> ProtocolClient:
    from beercode.protocols.anthropic_messages import AnthropicMessagesClient

    return AnthropicMessagesClient(provider, headers)


FACTORIES: dict[str, ClientFactory] = {
    "openai": _openai_factory,
    "anthropic": _anthropic_factory,
}


def create_client(provider: Provider, headers: Mapping[str, str]) -> ProtocolClient:
    return FACTORIES[provider.protocol](provider, headers)
