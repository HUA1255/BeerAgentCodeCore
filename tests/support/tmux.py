from __future__ import annotations

import os
import re
import subprocess
import time
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path

PROXY_VARS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")
PROMPT = "__SH__$ "


class TmuxTerminal:
    def __init__(self, cwd: Path, *, width: int = 100, height: int = 30, env: Mapping[str, str] | None = None) -> None:
        self.cwd = Path(cwd)
        self.width = width
        self.height = height
        self.socket = f"beercode-test-{uuid.uuid4().hex[:8]}"
        self.target = "main"
        base = {k: v for k, v in os.environ.items() if k not in PROXY_VARS}
        base.update({"PS1": PROMPT, "BASH_SILENCE_DEPRECATION_WARNING": "1", "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8"})
        base.pop("TMUX", None)
        base.update(env or {})
        self.env = base

    def _tmux(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["tmux", "-L", self.socket, *args], env=self.env, capture_output=True, text=True, check=check)

    def start(self) -> "TmuxTerminal":
        self._tmux(
            "new-session", "-d", "-s", self.target,
            "-x", str(self.width), "-y", str(self.height),
            "-c", str(self.cwd),
            "bash --noprofile --norc",
        )
        self._tmux("set-option", "-t", self.target, "status", "off")
        self.wait_for(re.escape(PROMPT.strip()))
        return self

    def close(self) -> None:
        self._tmux("kill-server", check=False)

    def run(self, command: str) -> None:
        self.type(command)
        self.press("Enter")

    def type(self, text: str) -> None:
        self._tmux("send-keys", "-t", self.target, "-l", text)

    def press(self, *keys: str) -> None:
        self._tmux("send-keys", "-t", self.target, *keys)

    def capture(self) -> str:
        return self._tmux("capture-pane", "-p", "-J", "-t", self.target).stdout

    def wait_until(self, predicate: Callable[[str], bool], timeout: float = 10.0, description: str = "条件") -> str:
        deadline = time.monotonic() + timeout
        screen = ""
        while time.monotonic() < deadline:
            screen = self.capture()
            if predicate(screen):
                return screen
            time.sleep(0.1)
        raise AssertionError(f"等待{description}超时（{timeout}s），当前屏幕：\n{screen}")

    def wait_for(self, pattern: str, timeout: float = 10.0) -> str:
        regex = re.compile(pattern)
        return self.wait_until(lambda s: regex.search(s) is not None, timeout, f" /{pattern}/ ")

    def wait_for_text(self, text: str, timeout: float = 10.0) -> str:
        return self.wait_until(lambda s: text in s, timeout, f"「{text}」")

    def shell_value(self, expression: str, timeout: float = 10.0) -> str:
        marker = uuid.uuid4().hex[:6]
        self.run(f'echo "<""{marker}:{expression}:{marker}>"')
        screen = self.wait_for(rf"<{marker}:.*:{marker}>", timeout)
        return re.search(rf"<{marker}:(.*):{marker}>", screen).group(1)
