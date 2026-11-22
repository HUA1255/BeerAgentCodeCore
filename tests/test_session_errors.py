import pytest

from beercode.config import Provider
from beercode.errors import RequestFailed
from beercode.session import Session
from support.mock_llm import Reply

API_KEY = "sk-secret-123456"

pytestmark = pytest.mark.parametrize("protocol", ["openai", "anthropic"])


def provider(mock_llm, protocol, **overrides) -> Provider:
    fields = dict(name="Mock", protocol=protocol, model="mock-model", base_url=mock_llm.base_url(protocol), api_key=API_KEY)
    fields.update(overrides)
    return Provider(**fields)


async def collect(stream) -> list[str]:
    return [delta async for delta in stream]


async def failure(session: Session, text: str = "hi") -> RequestFailed:
    with pytest.raises(RequestFailed) as info:
        await collect(session.send(text))
    return info.value


@pytest.mark.parametrize(
    ("status", "keyword"),
    [(401, "鉴权失败"), (404, "模型或接口不存在"), (429, "请求过于频繁")],
)
async def test_http_errors_become_chinese_messages(mock_llm, protocol, status, keyword):
    mock_llm.enqueue(Reply.error(status))
    session = Session(provider(mock_llm, protocol))

    error = await failure(session)

    assert keyword in str(error)
    assert str(status) in str(error)
    assert API_KEY not in str(error)


async def test_disconnect_mid_stream_is_reported(mock_llm, protocol):
    mock_llm.enqueue(Reply.text("半截回复", chunk_size=1, disconnect=True))
    session = Session(provider(mock_llm, protocol))

    error = await failure(session)

    assert "连接中断，本轮回复不完整，未计入对话历史" in str(error)


async def test_unreachable_server_is_reported(mock_llm, protocol):
    session = Session(provider(mock_llm, protocol, base_url="http://127.0.0.1:1"))

    error = await failure(session)

    assert "网络连接失败" in str(error)
    assert API_KEY not in str(error)


async def test_failed_turn_is_left_out_of_history(mock_llm, protocol):
    mock_llm.enqueue("第一轮回复", Reply.error(429), Reply.text("断开的回复", disconnect=True), "第三轮回复")
    session = Session(provider(mock_llm, protocol))

    await collect(session.send("第一轮"))
    await failure(session, "失败轮")
    await failure(session, "断开轮")
    await collect(session.send("第三轮"))

    assert mock_llm.requests[-1].conversation == [
        {"role": "user", "content": "第一轮"},
        {"role": "assistant", "content": "第一轮回复"},
        {"role": "user", "content": "第三轮"},
    ]
