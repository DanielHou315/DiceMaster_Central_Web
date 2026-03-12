"""Internal runtime management — NOT exposed to students."""
from dice._bridge import get_bridge


def teardown() -> None:
    from dice import motion, orientation, timer, assets
    motion._reset()
    orientation._reset()
    timer._reset()
    assets._reset()
    get_bridge().reset()
