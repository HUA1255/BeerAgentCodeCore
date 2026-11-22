import pytest

from support.mock_llm import Reply

pytestmark = pytest.mark.parametrize("protocol", ["openai", "anthropic"])

API_KEY = "sk-e2e-secret-998877"


def start(beercode, protocol):
    return beercode([{"name": "Local Mock", "protocol": protocol, "model": "mock-model", "api_key": API_KEY}])


def error_lines(screen: str) -> list[str]:
    return [line for line in screen.splitlines() if "✗ 错误：" in line]


@pytest.mark.parametrize(
    ("reply", "message"),
    [
        (Reply.error(401), "鉴权失败（401）"),
        (Reply.error(404), "模型或接口不存在（404）"),
        (Reply.error(429), "请求过于频繁或额度不足（429）"),
        (Reply.text("半截回复内容", chunk_size=1, chunk_delay=0.05, disconnect=True), "连接中断，本轮回复不完整，未计入对话历史"),
    ],
    ids=["401", "404", "429", "disconnect"],
)
def test_request_failure_shows_marked_chinese_error_and_keeps_running(beercode, mock_llm, protocol, reply, message):
    mock_llm.enqueue(reply)
    term = start(beercode, protocol)

    term.submit("触发错误")
    screen = term.wait_for_text(message)

    assert any(message in line for line in error_lines(screen))
    assert API_KEY not in screen
    assert "Mock error" not in screen
    term.submit("再试一次")
    term.wait_for_text("mock reply")


def test_conversation_continues_without_the_failed_turn(beercode, mock_llm, protocol):
    mock_llm.enqueue("你好，Ada。", Reply.error(429), Reply.text("断开的半截", disconnect=True), "你叫 Ada。")
    term = start(beercode, protocol)

    term.submit("我叫 Ada")
    term.wait_for_text("你好，Ada。")
    term.submit("限流轮")
    term.wait_for_text("（429）")
    term.submit("断开轮")
    term.wait_for_text("连接中断")
    term.submit("我叫什么？")
    term.wait_for_text("你叫 Ada。")

    last = mock_llm.wait_for_requests(4)[3]
    assert last.conversation == [
        {"role": "user", "content": "我叫 Ada"},
        {"role": "assistant", "content": "你好，Ada。"},
        {"role": "user", "content": "我叫什么？"},
    ]


def test_disconnect_keeps_partial_reply_and_says_it_is_not_in_history(beercode, mock_llm, protocol):
    mock_llm.enqueue(Reply.text("半截回复内容", chunk_size=1, chunk_delay=0.05, disconnect=True))
    term = start(beercode, protocol)

    term.submit("触发断开")
    screen = term.wait_for_text("未计入对话历史")

    assert "半截回复内容" in screen
    assert "已丢弃" not in screen
