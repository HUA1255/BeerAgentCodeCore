from __future__ import annotations

import secrets
from collections.abc import AsyncIterator

from beercode import __version__
from beercode.config import Provider
from beercode.errors import RequestFailed, describe
from beercode.messages import Message, ReplyComplete, TextDelta
from beercode.protocols import ClientFactory, create_client
from beercode.prompts import SYSTEM_PROMPT

__all__ = ["RequestFailed", "Session", "new_session_id", "request_headers"]


def new_session_id() -> str:
    return f"ses_{secrets.token_hex(12)}"


def request_headers(session_id: str) -> dict[str, str]:
    return {"User-Agent": f"beercode/{__version__}", "x-opencode-session": session_id}


class Session:
    def __init__(self, provider: Provider, client_factory: ClientFactory = create_client) -> None:
        self.provider = provider
        self.session_id = new_session_id()
        self.history: list[Message] = []
        self._client = client_factory(provider, request_headers(self.session_id))

    async def send(self, text: str) -> AsyncIterator[str]:
        user = Message("user", text)
        try:
            async for event in self._client.stream(SYSTEM_PROMPT, [*self.history, user]):
                if isinstance(event, TextDelta):
                    yield event.text
                elif isinstance(event, ReplyComplete):
                    self.history.extend([user, event.message])
        except Exception as error:
            raise RequestFailed(describe(error)) from error
