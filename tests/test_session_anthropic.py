from beercode.config import Provider
from beercode.session import Session
from support.mock_llm import ANTHROPIC_SIGNATURE, Reply


def anthropic_provider(mock_llm, **overrides) -> Provider:
    fields = dict(name="Mock Claude", protocol="anthropic", model="mock-model", base_url=mock_llm.base_url("anthropic"), api_key="sk-ant-test")
    fields.update(overrides)
    return Provider(**fields)


async def collect(stream) -> list[str]:
    return [delta async for delta in stream]


async def test_reply_streams_as_text_deltas(mock_llm):
    mock_llm.enqueue(Reply.text("你好，世界！", chunk_size=2))
    session = Session(anthropic_provider(mock_llm))

    deltas = await collect(session.send("hi"))

    assert deltas == ["你好", "，世", "界！"]
    assert mock_llm.requests[0].protocol == "anthropic"


async def test_second_request_carries_system_prompt_and_previous_turn(mock_llm):
    mock_llm.enqueue("我叫小啤。", "你刚才问了我的名字。")
    session = Session(anthropic_provider(mock_llm))

    await collect(session.send("你叫什么？"))
    await collect(session.send("我刚才问了什么？"))

    second = mock_llm.requests[1]
    assert "中文" in second.system
    assert second.conversation == [
        {"role": "user", "content": "你叫什么？"},
        {"role": "assistant", "content": "我叫小啤。"},
        {"role": "user", "content": "我刚才问了什么？"},
    ]
    assert second.body["model"] == "mock-model"


async def test_request_carries_no_extended_thinking_parameters(mock_llm):
    session = Session(anthropic_provider(mock_llm))

    await collect(session.send("hi"))

    body = mock_llm.requests[0].body
    assert "thinking" not in body
    assert "budget_tokens" not in str(body)


async def test_thinking_block_is_hidden_and_sent_back_verbatim(mock_llm):
    mock_llm.enqueue(Reply.text("答案是 42。", thinking="让我想想这个问题"), "好的")
    session = Session(anthropic_provider(mock_llm))

    deltas = await collect(session.send("问题"))
    await collect(session.send("继续"))

    assert "".join(deltas) == "答案是 42。"
    assistant = mock_llm.requests[1].body["messages"][1]
    assert assistant == {
        "role": "assistant",
        "content": [
            {"type": "thinking", "thinking": "让我想想这个问题", "signature": ANTHROPIC_SIGNATURE},
            {"type": "text", "text": "答案是 42。"},
        ],
    }


async def test_every_request_carries_user_agent_and_stable_session_id(mock_llm):
    from beercode import __version__

    session = Session(anthropic_provider(mock_llm))
    await collect(session.send("一"))
    await collect(session.send("二"))

    first, second = (r.headers for r in mock_llm.requests)
    assert first["user-agent"] == second["user-agent"] == f"beercode/{__version__}"
    assert first["x-opencode-session"] == second["x-opencode-session"] == session.session_id
    assert first["x-opencode-session"].startswith("ses_")
