from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence

from anthropic import AsyncAnthropic

from beercode.config import Provider
from beercode.errors import IncompleteReply
from beercode.messages import Message, ReplyComplete, StreamEvent, TextDelta
from beercode.protocols.common import MAX_TOKENS, client_options


class AnthropicMessagesClient:
    def __init__(self, provider: Provider, headers: Mapping[str, str]) -> None:
        self._provider = provider
        self._client = AsyncAnthropic(**client_options(provider, headers))

    async def stream(self, system: str, history: Sequence[Message]) -> AsyncIterator[StreamEvent]:
        async with self._client.messages.stream(
            model=self._provider.model,
            system=system,
            messages=[_to_param(m) for m in history],
            max_tokens=MAX_TOKENS,
        ) as response:
            stopped = False
            async for event in response:
                if event.type == "content_block_delta" and event.delta.type == "text_delta":
                    yield TextDelta(event.delta.text)
                stopped = stopped or event.type == "message_stop"
            if not stopped:
                raise IncompleteReply()
            final = await response.get_final_message()
        blocks = [block.model_dump(exclude_none=True) for block in final.content]
        text = "".join(b["text"] for b in blocks if b["type"] == "text")
        yield ReplyComplete(Message("assistant", text, native=blocks))


def _to_param(message: Message) -> dict:
    content = message.native if message.native is not None else message.text
    return {"role": message.role, "content": content}
