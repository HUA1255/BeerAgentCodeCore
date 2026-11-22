from beercode.config import Provider
from beercode.session import Session
from support.mock_llm import Reply


def openai_provider(mock_llm, **overrides) -> Provider:
    fields = dict(name="Mock OpenAI", protocol="openai", model="mock-model", base_url=mock_llm.base_url("openai"), api_key="sk-test")
    fields.update(overrides)
    return Provider(**fields)


async def collect(stream) -> list[str]:
    return [delta async for delta in stream]


async def test_reply_streams_as_text_deltas(mock_llm):
    mock_llm.enqueue(Reply.text("你好，世界！", chunk_size=2))
    session = Session(openai_provider(mock_llm))

    deltas = await collect(session.send("hi"))

    assert deltas == ["你好", "，世", "界！"]


async def test_second_request_carries_system_prompt_and_previous_turn(mock_llm):
    mock_llm.enqueue("我叫小啤。", "你刚才问了我的名字。")
    session = Session(openai_provider(mock_llm))

    await collect(session.send("你叫什么？"))
    await collect(session.send("我刚才问了什么？"))

    messages = mock_llm.requests[1].body["messages"]
    assert messages[0]["role"] == "system"
    assert "中文" in messages[0]["content"]
    assert messages[1:] == [
        {"role": "user", "content": "你叫什么？"},
        {"role": "assistant", "content": "我叫小啤。"},
        {"role": "user", "content": "我刚才问了什么？"},
    ]
    assert mock_llm.requests[1].body["model"] == "mock-model"


async def test_reasoning_content_is_neither_streamed_nor_sent_back(mock_llm):
    mock_llm.enqueue(Reply.text("答案是 42。", thinking="让我想想这个问题"), "好的")
    session = Session(openai_provider(mock_llm))

    deltas = await collect(session.send("问题"))
    await collect(session.send("继续"))

    assert "".join(deltas) == "答案是 42。"
    second_request = str(mock_llm.requests[1].body)
    assert "让我想想" not in second_request
    assert "reasoning" not in second_request
    assert {"role": "assistant", "content": "答案是 42。"} in mock_llm.requests[1].body["messages"]


async def test_every_request_carries_user_agent_and_stable_session_id(mock_llm):
    from beercode import __version__

    session = Session(openai_provider(mock_llm))
    await collect(session.send("一"))
    await collect(session.send("二"))
    other = Session(openai_provider(mock_llm))
    await collect(other.send("三"))

    first, second, third = (r.headers for r in mock_llm.requests)
    assert first["user-agent"] == f"beercode/{__version__}"
    assert second["user-agent"] == f"beercode/{__version__}"
    assert first["x-opencode-session"] == second["x-opencode-session"] == session.session_id
    assert first["x-opencode-session"].startswith("ses_") and len(first["x-opencode-session"]) > len("ses_") + 8
    assert third["x-opencode-session"] != first["x-opencode-session"]
