from beercode import __version__
from support.mock_llm import Reply

MARKDOWN_REPLY = "Here is **bold text** and a list:\n\n- apple\n- banana\n\n```python\nprint('hi')\n```\n\nDone."


def test_startup_shows_banner_with_name_version_and_cwd(beercode, tmp_path):
    term = beercode()

    screen = term.wait_for_text(f"BeerCode v{__version__}")

    assert tmp_path.name in screen
    assert "Ready" in screen


def test_input_box_has_border_prompt_symbol_and_placeholder(beercode):
    term = beercode()

    screen = term.wait_for_text("Send a message...")

    lines = screen.splitlines()
    row = next(i for i, line in enumerate(lines) if "Send a message..." in line)
    assert "❯" in lines[row]
    assert lines[row].lstrip().startswith("│")
    assert lines[row - 1].lstrip().startswith("╭")
    assert lines[row + 1].lstrip().startswith("╰")


def test_alt_enter_inserts_newline_and_enter_submits_then_clears(beercode, mock_llm):
    term = beercode()
    term.wait_for_text("Send a message...")

    term.type("line one")
    term.press("M-Enter")
    term.type("line two")
    screen = term.wait_for_text("line two")
    rows = [i for i, line in enumerate(screen.splitlines()) if "line one" in line or "line two" in line]
    assert len(rows) == 2 and rows[1] == rows[0] + 1
    assert not mock_llm.requests

    term.press("Enter")

    assert mock_llm.wait_for_requests(1)[0].body["messages"][-1]["content"] == "line one\nline two"
    term.wait_for_text("mock reply")
    term.wait_for_text("Send a message...")


def test_reply_is_rendered_as_markdown_after_it_finishes(beercode, mock_llm):
    mock_llm.enqueue(Reply.text(MARKDOWN_REPLY, chunk_size=8, chunk_delay=0.15))
    term = beercode()

    term.submit("show markdown")

    streaming = term.wait_for_text("**bold")
    assert "Done." not in streaming
    screen = term.wait_until(lambda s: "Done." in s and "**" not in s, description="Markdown 定型")
    assert "bold text" in screen
    assert "```" not in screen
    assert "print('hi')" in screen
    assert "• apple" in screen
    assert "• banana" in screen


def test_layout_stays_intact_in_narrow_terminal(beercode, mock_llm, tmp_path):
    mock_llm.enqueue(Reply.text(MARKDOWN_REPLY))
    term = beercode(width=60, height=30)

    term.submit("narrow please")
    screen = term.wait_until(lambda s: "Done." in s and "**" not in s, description="窄屏回复定型")

    lines = screen.splitlines()
    assert all(len(line) <= 60 for line in lines)
    assert f"BeerCode v{__version__}" in screen
    filled = [line for line in lines if line.strip()]
    assert filled[-1].strip().startswith("Mock OpenAI")
    assert filled[-1].strip().endswith("mock-model")
    assert filled[-2].startswith("╰") and filled[-2].endswith("╯")
    assert filled[-3].startswith("│") and filled[-3].endswith("│") and "❯" in filled[-3]
    assert filled[-4].startswith("╭") and filled[-4].endswith("╮")
    banner = [line for line in lines if line.lstrip().startswith("│") and "BeerCode" in line]
    assert banner and banner[0].rstrip().endswith("│")
