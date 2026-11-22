import re
import time

from support.mock_llm import Pause, Reply


def delayed(text: str, seconds: float) -> Reply:
    return Reply(events=[Pause(seconds), *Reply.text(text).events])


def test_elapsed_seconds_tick_before_first_delta(beercode, mock_llm):
    mock_llm.enqueue(delayed("late answer", 3.5))
    term = beercode()

    term.submit("slow question")

    term.wait_for(r"Imagining… \(0s\)")
    screen = term.wait_for(r"Imagining… \(2s\)", timeout=5)
    assert "late answer" not in screen
    term.wait_for_text("late answer")


def test_timer_keeps_running_while_streaming_and_settles_on_total(beercode, mock_llm):
    mock_llm.enqueue(Reply(events=[Pause(1.2), *Reply.text("ABCDEFGHIJKLMNOPQRSTUVWXYZ", chunk_size=1).events], chunk_delay=0.1))
    term = beercode()

    term.submit("stream with timing")

    term.wait_until(lambda s: "A" in s.split("stream with timing")[-1] and "(2s)" in s, description="首增量后计时继续")
    screen = term.wait_for(r"Imagined for \d+s")
    assert "ABCDEFGHIJKLMNOPQRSTUVWXYZ" in screen
    assert "Imagining…" not in screen
    assert int(re.search(r"Imagined for (\d+)s", screen).group(1)) in (3, 4)


def test_typing_allowed_but_enter_ignored_until_turn_ends(beercode, mock_llm):
    mock_llm.enqueue(Reply.text("first answer done", chunk_size=1, chunk_delay=0.1), "second answer")
    term = beercode()
    term.submit("first")
    term.wait_for_text("Imagining…")

    term.submit("queued text")

    term.wait_for_text("first answer done")
    screen = term.wait_for(r"Imagined for \d+s")
    assert screen.count("queued text") == 1
    assert "> queued text" not in screen
    assert len(mock_llm.requests) == 1

    term.press("Enter")

    term.wait_for_text("second answer")
    assert mock_llm.wait_for_requests(2)[1].body["messages"][-1]["content"] == "queued text"


def test_exit_command_is_not_accepted_while_busy(beercode, mock_llm):
    mock_llm.enqueue(Reply.text("busy answer finished", chunk_size=1, chunk_delay=0.1))
    term = beercode()
    term.submit("first")
    term.wait_for_text("Imagining…")

    term.submit("/exit")

    screen = term.wait_for(r"Imagined for \d+s")
    assert "busy answer finished" in screen
    assert "/exit" in screen
    assert len(mock_llm.requests) == 1

    term.press("Enter")

    assert term.wait_for_exit() == 0
    assert term.tty_is_sane()


def test_conversation_scrolls_while_waiting_and_streaming(beercode, mock_llm):
    long_reply = "\n\n".join(f"LINE-{i:02d}" for i in range(1, 31))
    mock_llm.enqueue(long_reply, Reply(events=[Pause(2), *Reply.text("Z" * 60, chunk_size=1).events], chunk_delay=0.1))
    term = beercode(height=20)
    term.submit("long please")
    term.wait_for(r"Imagined for \d+s")
    term.submit("slow again")
    term.wait_for_text("Imagining…")

    term.press(*["PageUp"] * 10)
    term.wait_until(lambda s: "LINE-01" in s and "Imagining…" not in s, description="等待期间向上滚动")
    time.sleep(3)
    assert "LINE-01" in term.capture()

    term.press("PageDown", "PageDown", "PageDown", "PageDown", "PageDown", "PageDown", "PageDown", "PageDown")
    screen = term.wait_until(lambda s: "Z" * 20 in s and "LINE-01" not in s, description="向下滚动回到底部")
    assert re.search(r"Imagin(ing… \(\d+s\)|ed for \d+s)", screen)


def test_streaming_reply_stays_in_view_when_not_scrolled(beercode, mock_llm):
    long_reply = "\n\n".join(f"ROW-{i:02d}" for i in range(1, 31))
    mock_llm.enqueue(Reply.text(long_reply, chunk_size=4, chunk_delay=0.02))
    term = beercode(height=20)

    term.submit("follow me")

    screen = term.wait_for(r"Imagined for \d+s")
    assert "ROW-30" in screen
    assert "ROW-01" not in screen
