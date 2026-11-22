import pytest

from support.mock_llm import MockLLMServer

PROXY_VARS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")


@pytest.fixture(autouse=True)
def _no_proxy(monkeypatch):
    for name in PROXY_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def mock_llm():
    with MockLLMServer() as server:
        yield server
