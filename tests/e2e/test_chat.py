from support.mock_llm import Reply


def test_startup_shows_conversation_input_and_status_bar(beercode):
    term = beercode([{"name": "Local Mock", "protocol": "openai", "model": "mock-model"}])

    screen = term.wait_for_text("Local Mock")

    last_line = [line for line in screen.splitlines() if line.strip()][-1]
    assert last_line.strip().startswith("Local Mock")
    assert last_line.strip().endswith("mock-model")


def test_reply_appears_incrementally_while_streaming(beercode, mock_llm):
    mock_llm.enqueue(Reply.text("ABCDEFGHIJKLMNOPQRST", chunk_size=1, chunk_delay=0.15))
    term = beercode()

    term.submit("hello there")

    term.wait_for_text("hello there")
    partial = term.wait_until(lambda s: "ABC" in s and "ABCDEFGHIJKLMNOPQRST" not in s, description="部分回复")
    assert "ABCDEFGHIJKLMNOPQRST" not in partial
    term.wait_for_text("ABCDEFGHIJKLMNOPQRST")


def test_multi_turn_conversation_sends_full_history(beercode, mock_llm):
    mock_llm.enqueue("Nice to meet you, Ada.", "Your name is Ada.")
    term = beercode()

    term.submit("My name is Ada")
    term.wait_for_text("Nice to meet you, Ada.")
    term.submit("What is my name?")
    term.wait_for_text("Your name is Ada.")

    second = mock_llm.wait_for_requests(2)[1].body["messages"]
    assert second[0]["role"] == "system"
    assert second[1:] == [
        {"role": "user", "content": "My name is Ada"},
        {"role": "assistant", "content": "Nice to meet you, Ada."},
        {"role": "user", "content": "What is my name?"},
    ]


def test_reasoning_content_is_hidden_and_not_sent_back(beercode, mock_llm):
    mock_llm.enqueue(Reply.text("Final answer 42", thinking="SECRET-REASONING-TRACE"), "Second answer")
    term = beercode()

    term.submit("Question one")
    screen = term.wait_for_text("Final answer 42")
    assert "SECRET" not in screen
    term.submit("Question two")
    screen = term.wait_for_text("Second answer")

    assert "SECRET" not in screen
    assert "SECRET" not in str(mock_llm.wait_for_requests(2)[1].body)


def test_requests_share_one_session_id_and_identify_beercode(beercode, mock_llm):
    from beercode import __version__

    term = beercode()
    term.submit("one")
    term.wait_for_text("mock reply")
    term.submit("two")
    mock_llm.wait_for_requests(2)

    first, second = (r.headers for r in mock_llm.requests)
    assert first["user-agent"] == second["user-agent"] == f"beercode/{__version__}"
    assert first["x-opencode-session"] == second["x-opencode-session"]
    assert first["x-opencode-session"].startswith("ses_")


def test_exit_command_quits_and_restores_terminal(beercode):
    term = beercode()

    term.submit("/exit")

    assert term.wait_for_exit() == 0
    assert term.tty_is_sane()


def test_exit_requires_exact_command(beercode, mock_llm):
    term = beercode()

    term.submit("/exit now")

    term.wait_for_text("mock reply")
    assert mock_llm.requests[0].body["messages"][-1]["content"] == "/exit now"


def test_ctrl_c_quits_and_restores_terminal(beercode):
    term = beercode()

    term.press("C-c")

    assert term.wait_for_exit() == 0
    assert term.tty_is_sane()


def test_ctrl_c_quits_while_streaming(beercode, mock_llm):
    mock_llm.enqueue(Reply.text("x" * 200, chunk_size=1, chunk_delay=0.1))
    term = beercode()
    term.submit("stream please")
    term.wait_for_text("xxx")

    term.press("C-c")

    term.wait_for_exit()
    assert term.tty_is_sane()
