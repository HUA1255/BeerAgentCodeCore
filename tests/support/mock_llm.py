from __future__ import annotations

import json
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Iterator


@dataclass(frozen=True)
class Text:
    text: str


@dataclass(frozen=True)
class Thinking:
    text: str


@dataclass(frozen=True)
class Pause:
    seconds: float


Event = Text | Thinking | Pause


@dataclass
class Reply:
    events: list[Event] = field(default_factory=list)
    chunk_delay: float = 0.0

    @classmethod
    def text(cls, text: str, *, thinking: str | None = None, chunk_size: int = 2, chunk_delay: float = 0.0) -> "Reply":
        events: list[Event] = []
        if thinking:
            events.extend(Thinking(part) for part in _split(thinking, chunk_size))
        events.extend(Text(part) for part in _split(text, chunk_size))
        return cls(events=events, chunk_delay=chunk_delay)

    @property
    def full_text(self) -> str:
        return "".join(e.text for e in self.events if isinstance(e, Text))


@dataclass(frozen=True)
class RecordedRequest:
    protocol: str
    path: str
    headers: dict[str, str]
    body: dict


def _split(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]


def _sse(data: dict | str, event: str | None = None) -> bytes:
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    head = f"event: {event}\n" if event else ""
    return f"{head}data: {payload}\n\n".encode()


def encode_openai(reply: Reply, model: str) -> Iterator[bytes | Pause]:
    base = {"id": "chatcmpl-mock", "object": "chat.completion.chunk", "created": int(time.time()), "model": model}

    def chunk(delta: dict, finish: str | None = None) -> bytes:
        return _sse({**base, "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]})

    yield chunk({"role": "assistant", "content": ""})
    for event in reply.events:
        if isinstance(event, Pause):
            yield event
        elif isinstance(event, Thinking):
            yield chunk({"reasoning_content": event.text})
        else:
            yield chunk({"content": event.text})
    yield chunk({}, "stop")
    yield _sse("[DONE]")


Encoder = Callable[[Reply, str], Iterator[bytes | Pause]]

ROUTES: dict[str, tuple[str, Encoder]] = {
    "/chat/completions": ("openai", encode_openai),
}


class MockLLMServer:
    def __init__(self, default_reply: str = "mock reply") -> None:
        self.requests: list[RecordedRequest] = []
        self._script: deque[Reply] = deque()
        self._default_reply = default_reply
        self._lock = threading.Lock()
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), self._handler_class())
        self._httpd.daemon_threads = True
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        host, port = self._httpd.server_address[:2]
        return f"http://{host}:{port}"

    def base_url(self, protocol: str) -> str:
        return f"{self.url}/v1" if protocol == "openai" else self.url

    def enqueue(self, *replies: Reply | str) -> None:
        with self._lock:
            self._script.extend(Reply.text(r) if isinstance(r, str) else r for r in replies)

    def requests_for(self, protocol: str) -> list[RecordedRequest]:
        return [r for r in self.requests if r.protocol == protocol]

    def wait_for_requests(self, count: int, timeout: float = 10.0) -> list[RecordedRequest]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if len(self.requests) >= count:
                return list(self.requests)
            time.sleep(0.05)
        raise AssertionError(f"期望至少 {count} 个请求，实际 {len(self.requests)} 个")

    def start(self) -> "MockLLMServer":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()

    def __enter__(self) -> "MockLLMServer":
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()

    def _next_reply(self) -> Reply:
        with self._lock:
            return self._script.popleft() if self._script else Reply.text(self._default_reply)

    def _handler_class(self) -> type[BaseHTTPRequestHandler]:
        server = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args: object) -> None:
                pass

            def do_POST(self) -> None:
                length = int(self.headers.get("content-length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")
                route = next((r for suffix, r in ROUTES.items() if self.path.endswith(suffix)), None)
                if route is None:
                    self.send_response(404)
                    self.send_header("content-length", "0")
                    self.end_headers()
                    return
                protocol, encoder = route
                headers = {k.lower(): v for k, v in self.headers.items()}
                with server._lock:
                    server.requests.append(RecordedRequest(protocol, self.path, headers, body))
                reply = server._next_reply()
                self.send_response(200)
                self.send_header("content-type", "text/event-stream")
                self.send_header("cache-control", "no-cache")
                self.send_header("connection", "close")
                self.end_headers()
                self.close_connection = True
                try:
                    for piece in encoder(reply, body.get("model", "mock-model")):
                        if isinstance(piece, Pause):
                            time.sleep(piece.seconds)
                            continue
                        self.wfile.write(piece)
                        self.wfile.flush()
                        if reply.chunk_delay:
                            time.sleep(reply.chunk_delay)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        return Handler
