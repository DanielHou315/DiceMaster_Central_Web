"""Orientation — track which screen faces up/down."""
from dice._bridge import get_bridge

_change_handlers: list = []
_top: int = 1
_bottom: int = 6
_polling_registered: bool = False
_dispatch_registered: bool = False


def on_change(handler) -> None:
    global _dispatch_registered
    _change_handlers.append(handler)
    if not _dispatch_registered:
        get_bridge().on("orientation.change", _dispatch_change)
        _dispatch_registered = True


def top() -> int:
    _register_polling()
    return _top


def bottom() -> int:
    _register_polling()
    return _bottom


def _register_polling(bridge=None) -> None:
    global _polling_registered
    if _polling_registered:
        return
    b = bridge or get_bridge()
    b.on("orientation.change", _update_state)
    _polling_registered = True


def _dispatch_change(message: dict) -> None:
    t = message.get("top", 1)
    b = message.get("bottom", 6)
    for handler in _change_handlers:
        handler(t, b)


def _update_state(message: dict) -> None:
    global _top, _bottom
    _top = message.get("top", 1)
    _bottom = message.get("bottom", 6)


def _reset() -> None:
    global _top, _bottom, _polling_registered, _dispatch_registered
    _change_handlers.clear()
    _top = 1
    _bottom = 6
    _polling_registered = False
    _dispatch_registered = False
