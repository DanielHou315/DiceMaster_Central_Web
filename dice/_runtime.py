"""Internal runtime management — NOT exposed to students."""

from dice._bridge import get_bridge


def teardown() -> None:
    get_bridge().reset()
