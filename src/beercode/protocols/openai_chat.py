from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence

from openai import AsyncOpenAI

from beercode.config import Provider
from beercode.errors import IncompleteReply
from beercode.messages import Message, ReplyComplete, StreamEvent, TextDelta
from beercode.protocols.common import MAX_TOKENS, client_options


class OpenAIChatClient:
    def __init__(self, provider: Provider, headers: Mapping[str, str]) -> None:
        self._provider = provider
        self._client = AsyncOpenAI(**client_options(provider, headers))

    async def stream(self, system: str, history: Sequence[Message]) -> AsyncIterator[StreamEvent]:
        messages = [{"role": "system", "content": system}]
        messages.extend({"role": m.role, "content": m.text} for m in history)
        response = await self._client.chat.completions.create(
            model=self._provider.model,
            messages=messages,
            max_tokens=MAX_TOKENS,
            stream=True,
        )
        parts: list[str] = []
        finished = False
        async for chunk in response:
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            content = choice.delta.content
            if content:
                parts.append(content)
                yield TextDelta(content)
            finished = finished or choice.finish_reason is not None
        if not finished:
            raise IncompleteReply()
        yield ReplyComplete(Message("assistant", "".join(parts)))
