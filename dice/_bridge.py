"""JS bridge — sends/receives JSON messages via postMessage (Pyodide) or mock (tests)."""

from __future__ import annotations

_instance: Bridge | None = None


class Bridge:
    """Singleton bridge to JavaScript main thread."""

    def __init__(self):
        self.sent: list[dict] = []
        self._inbound_handlers: dict[str, list] = {}
        self._js_post = None
        try:
            from js import postMessage
            self._js_post = postMessage
        except ImportError:
            pass

    def send(self, message: dict) -> None:
        if self._js_post is not None:
            from pyodide.ffi import to_js
            self._js_post(to_js(message, dict_converter=lambda x: x))
        self.sent.append(message)

    def on(self, msg_type: str, handler) -> None:
        self._inbound_handlers.setdefault(msg_type, []).append(handler)

    def receive(self, message: dict) -> None:
        msg_type = message.get("type", "")
        for handler in self._inbound_handlers.get(msg_type, []):
            handler(message)

    def reset(self):
        self.sent.clear()
        self._inbound_handlers.clear()


def get_bridge() -> Bridge:
    global _instance
    if _instance is None:
        _instance = Bridge()
    return _instance
