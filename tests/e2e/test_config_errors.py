import pytest

from support.beercode_terminal import BeerCodeTerminal, write_config

SECRET = "sk-very-secret-value-123"


@pytest.fixture
def launch(tmp_path):
    terminals: list[BeerCodeTerminal] = []

    def start(env: dict[str, str] | None = None, ready: str | None = None) -> BeerCodeTerminal:
        terminal = BeerCodeTerminal(tmp_path, env=env).start()
        terminals.append(terminal)
        return terminal.launch(ready=ready)

    yield start
    for terminal in terminals:
        terminal.close()


def assert_clean_failure(term: BeerCodeTerminal, expected: str) -> str:
    code = term.wait_for_exit()
    screen = term.capture()
    assert code != 0
    assert expected in screen
    assert "Traceback" not in screen
    assert SECRET not in screen
    assert term.tty_is_sane()
    return screen


def test_missing_config_points_to_example_file(launch):
    term = launch()

    assert_clean_failure(term, "beercode.example.yaml")


def test_malformed_yaml_reports_location(launch, tmp_path):
    (tmp_path / "beercode.yaml").write_text(f"providers:\n  - api_key: {SECRET}\n   bad: : x\n", encoding="utf-8")
    term = launch()

    assert_clean_failure(term, "第 3 行")


def test_missing_field_names_the_field(launch, tmp_path, mock_llm):
    write_config(tmp_path, mock_llm, [{"name": "No Model", "protocol": "openai", "api_key": SECRET}])
    term = launch()

    assert_clean_failure(term, "缺少必填字段 `model`")


def test_unknown_protocol_lists_supported_ones(launch, tmp_path, mock_llm):
    write_config(tmp_path, mock_llm, [{"name": "Gem", "protocol": "gemini", "model": "g", "api_key": SECRET}])
    term = launch()

    assert_clean_failure(term, "仅支持 anthropic、openai")


def test_unset_environment_variable_is_named(launch, tmp_path, mock_llm):
    write_config(tmp_path, mock_llm, [{"name": "Env", "protocol": "openai", "model": "m", "api_key": "${BEERCODE_TEST_UNSET_KEY}"}])
    term = launch()

    assert_clean_failure(term, "BEERCODE_TEST_UNSET_KEY")


def test_api_key_from_environment_is_used_but_never_shown(launch, tmp_path, mock_llm):
    write_config(tmp_path, mock_llm, [{"name": "Env Mock", "protocol": "openai", "model": "mock-model", "api_key": "${BEERCODE_TEST_KEY}"}])
    term = launch(env={"BEERCODE_TEST_KEY": SECRET}, ready="mock-model")

    term.submit("hi")
    screen = term.wait_for_text("mock reply")

    assert mock_llm.wait_for_requests(1)[0].headers["authorization"] == f"Bearer {SECRET}"
    assert SECRET not in screen
