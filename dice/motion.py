"""Motion detection — shake callbacks and polling."""
from dice._bridge import get_bridge

_shake_handlers: list = []
_shaking: bool = False
_intensity: float = 0.0
_polling_registered: bool = False
_shake_registered: bool = False


def on_shake(handler) -> None:
    global _shake_registered
    _shake_handlers.append(handler)
    if not _shake_registered:
        get_bridge().on("motion.shake", _dispatch_shake)
        _shake_registered = True


def is_shaking() -> bool:
    _register_polling()
    return _shaking


def shake_intensity() -> float:
    _register_polling()
    return _intensity


def _register_polling(bridge=None) -> None:
    global _polling_registered
    if _polling_registered:
        return
    b = bridge or get_bridge()
    b.on("motion.shake", _update_state_shake)
    b.on("motion.still", _update_state_still)
    _polling_registered = True


def _dispatch_shake(message: dict) -> None:
    intensity = message.get("intensity", 0.0)
    for handler in _shake_handlers:
        handler(intensity)


def _update_state_shake(message: dict) -> None:
    global _shaking, _intensity
    _shaking = True
    _intensity = message.get("intensity", 0.0)


def _update_state_still(message: dict) -> None:
    global _shaking, _intensity
    _shaking = False
    _intensity = 0.0


def _reset() -> None:
    global _shaking, _intensity, _polling_registered, _shake_registered
    _shake_handlers.clear()
    _shaking = False
    _intensity = 0.0
    _polling_registered = False
    _shake_registered = False
