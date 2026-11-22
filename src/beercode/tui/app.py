from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding

from beercode.errors import RequestFailed
from beercode.session import Session
from beercode.tui.widgets import Conversation, PromptBox, PromptInput, StatusBar

EXIT_COMMAND = "/exit"


class BeerCodeApp(App):
    TITLE = "BeerCode"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True, show=False),
        Binding("pageup", "scroll_conversation(-1)", priority=True, show=False),
        Binding("pagedown", "scroll_conversation(1)", priority=True, show=False),
    ]

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        self.busy = False

    def compose(self) -> ComposeResult:
        yield Conversation(id="conversation")
        yield PromptBox()
        yield StatusBar(self.session.provider)

    def on_mount(self) -> None:
        self.query_one(PromptInput).focus()

    def action_scroll_conversation(self, direction: int) -> None:
        conversation = self.query_one(Conversation)
        step = conversation.scrollable_content_region.height * direction
        conversation.scroll_to(y=conversation.scroll_y + step, animate=False, immediate=True)

    async def on_prompt_input_submitted(self, message: PromptInput.Submitted) -> None:
        text = message.text
        if self.busy:
            return
        if text == EXIT_COMMAND:
            self.exit()
            return
        if not text.strip():
            return
        self.query_one(PromptInput).clear()
        self.busy = True
        self.run_worker(self._reply(text), exclusive=True)

    async def _reply(self, text: str) -> None:
        conversation = self.query_one(Conversation)
        await conversation.add_user(text)
        entry = await conversation.add_assistant()
        timer = await conversation.add_timer()
        try:
            async for delta in self.session.send(text):
                entry.append(delta)
            entry.finish()
        except RequestFailed as error:
            if not entry.text:
                await entry.remove()
            await conversation.add_error(str(error))
        finally:
            timer.stop()
            self.busy = False
