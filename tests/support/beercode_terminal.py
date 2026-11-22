from __future__ import annotations

import shutil
import sys
from pathlib import Path

import yaml

from support.mock_llm import MockLLMServer
from support.tmux import TmuxTerminal

BEERCODE_BIN = Path(sys.executable).with_name("beercode")

DEFAULT_PROVIDER = {"name": "Mock OpenAI", "protocol": "openai", "model": "mock-model", "api_key": "sk-test-key"}


def write_config(directory: Path, mock_llm: MockLLMServer, providers: list[dict] | None = None) -> Path:
    entries = []
    for provider in providers or [DEFAULT_PROVIDER]:
        entry = dict(provider)
        entry.setdefault("api_key", "sk-test-key")
        if entry.get("base_url", ...) is ...:
            entry["base_url"] = mock_llm.base_url(entry["protocol"])
        if entry["base_url"] is None:
            del entry["base_url"]
        entries.append(entry)
    path = Path(directory) / "beercode.yaml"
    path.write_text(yaml.safe_dump({"providers": entries}, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


class BeerCodeTerminal(TmuxTerminal):
    READY_TEXT = "mock-model"

    def launch(self, ready: str | None = None, timeout: float = 15.0) -> "BeerCodeTerminal":
        self.run(str(BEERCODE_BIN))
        if ready is not None:
            self.wait_for_text(ready, timeout)
        return self

    def submit(self, text: str) -> None:
        self.type(text)
        self.press("Enter")

    def wait_for_exit(self, timeout: float = 10.0) -> int:
        self.wait_until(lambda s: s.rstrip().endswith("$"), timeout, "回到 shell 提示符")
        return int(self.shell_value("$?"))

    def tty_is_sane(self) -> bool:
        settings = self.shell_value("$(stty -a | tr '\\n' ' ')")
        tokens = settings.split()
        return all(flag in tokens for flag in ("icanon", "echo", "isig", "icrnl"))


def tmux_available() -> bool:
    return shutil.which("tmux") is not None
