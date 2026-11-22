PROVIDERS = [
    {"name": "Alpha Cloud", "protocol": "openai", "model": "alpha-model"},
    {"name": "Beta Labs", "protocol": "anthropic", "model": "beta-model"},
    {"name": "Gamma AI", "protocol": "openai", "model": "gamma-model"},
]


def line_with(screen: str, text: str) -> str:
    return next(line for line in screen.splitlines() if text in line)


def test_multiple_providers_show_picker_with_names_and_models(beercode):
    term = beercode(PROVIDERS, ready="Gamma AI")

    screen = term.wait_for_text("gamma-model")
    for provider in PROVIDERS:
        assert provider["model"] in line_with(screen, provider["name"])
    assert "Select a provider" in screen


def status_line(screen: str) -> str:
    return [line for line in screen.splitlines() if line.strip()][-1].strip()


def test_arrow_keys_and_enter_choose_active_provider(beercode, mock_llm):
    term = beercode(PROVIDERS, ready="gamma-model")

    term.press("Down")
    term.press("Down")
    term.press("Up")
    term.press("Enter")

    line = status_line(term.wait_until(lambda s: "Select a provider" not in s and "Beta Labs" in s, description="进入对话"))
    assert line.startswith("Beta Labs")
    assert line.endswith("beta-model")
    term.submit("hello beta")
    request = mock_llm.wait_for_requests(1)[0]
    assert request.protocol == "anthropic"
    assert request.body["model"] == "beta-model"


def test_cursor_defaults_to_first_provider(beercode):
    term = beercode(PROVIDERS, ready="gamma-model")

    term.press("Enter")

    line = status_line(term.wait_until(lambda s: "Select a provider" not in s and "alpha-model" in s, description="进入对话"))
    assert line.startswith("Alpha Cloud")
    assert line.endswith("alpha-model")


def test_single_provider_skips_picker(beercode):
    term = beercode([{"name": "Only One", "protocol": "openai", "model": "solo-model"}], ready="solo-model")

    screen = term.capture()
    assert "Select a provider" not in screen
    assert status_line(screen).startswith("Only One")


def test_ctrl_c_on_picker_exits_and_restores_terminal(beercode, mock_llm):
    term = beercode(PROVIDERS, ready="gamma-model")

    term.press("C-c")

    assert term.wait_for_exit() == 0
    assert term.tty_is_sane()
    assert mock_llm.requests == []
