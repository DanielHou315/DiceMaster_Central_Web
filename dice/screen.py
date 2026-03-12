"""Screen control — set content on dice faces."""
from dice._bridge import get_bridge


def set_text(screen_id: int, path: str) -> None:
    get_bridge().send({"type": "screen.set_text", "screen_id": screen_id, "path": path})


def set_image(screen_id: int, path: str) -> None:
    get_bridge().send({"type": "screen.set_image", "screen_id": screen_id, "path": path})


def set_gif(screen_id: int, path: str) -> None:
    get_bridge().send({"type": "screen.set_gif", "screen_id": screen_id, "path": path})
