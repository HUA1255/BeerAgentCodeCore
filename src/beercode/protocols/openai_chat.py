from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence

from openai import AsyncOpenAI

from beercode.config import Provider
from beercode.messages import Message, ReplyComplete, StreamEvent, TextDelta

MAX_TOKENS = 8192
TIMEOUT_SECONDS = 120.0


class OpenAIChatClient:
    def __init__(self, provider: Provider, headers: Mapping[str, str]) -> None:
        self._provider = provider
        self._client = AsyncOpenAI(
            api_key=provider.api_key,
            base_url=provider.base_url,
            default_headers=dict(headers),
            timeout=TIMEOUT_SECONDS,
            max_retries=0,
        )

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
        async for chunk in response:
            if not chunk.choices:
                continue
            content = chunk.choices[0].delta.content
            if content:
                parts.append(content)
                yield TextDelta(content)
        yield ReplyComplete(Message("assistant", "".join(parts)))
