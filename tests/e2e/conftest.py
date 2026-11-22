import pytest

from support.beercode_terminal import DEFAULT_PROVIDER, BeerCodeTerminal, tmux_available, write_config


def pytest_collection_modifyitems(items):
    for item in items:
        if "/e2e/" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
            if not tmux_available():
                item.add_marker(pytest.mark.skip(reason="未安装 tmux"))


@pytest.fixture
def protocol() -> str:
    return "openai"


@pytest.fixture
def beercode(tmp_path, mock_llm, protocol):
    terminals: list[BeerCodeTerminal] = []

    def start(providers: list[dict] | None = None, *, width: int = 100, height: int = 30, ready: str | None = "mock-model") -> BeerCodeTerminal:
        if providers is None:
            providers = [{**DEFAULT_PROVIDER, "protocol": protocol}]
        write_config(tmp_path, mock_llm, providers)
        terminal = BeerCodeTerminal(tmp_path, width=width, height=height).start()
        terminals.append(terminal)
        return terminal.launch(ready=ready)

    yield start
    for terminal in terminals:
        terminal.close()
