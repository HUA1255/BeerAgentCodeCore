from textual.app import App, ComposeResult

from beercode.tui.widgets import AssistantEntry, Conversation


class ConversationApp(App):
    def compose(self) -> ComposeResult:
        yield Conversation()


async def test_error_entry_is_styled_apart_from_assistant_reply():
    app = ConversationApp()
    async with app.run_test() as pilot:
        conversation = app.query_one(Conversation)
        reply = await conversation.add_assistant()
        reply.append("普通回复")
        error = await conversation.add_error("出错了")
        await pilot.pause()

        assert isinstance(reply, AssistantEntry)
        assert error.styles.border_left[0] != "" and reply.styles.border_left[0] == ""
        assert error.styles.color != reply.styles.color
        assert error.styles.background != reply.styles.background
        assert "✗ 错误：出错了" in str(error.render())
