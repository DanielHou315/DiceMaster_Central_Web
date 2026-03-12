"""Logging — send debug messages to the web UI console."""
from dice._bridge import get_bridge


def log(message: str) -> None:
    get_bridge().send({"type": "log", "message": message})
