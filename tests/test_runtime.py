from dice import screen, motion, orientation, timer
from dice._runtime import teardown


def test_teardown_clears_motion_callbacks(mock_bridge):
    called = []
    motion.on_shake(lambda i: called.append(i))
    teardown()
    mock_bridge.receive({"type": "motion.shake", "intensity": 0.5})
    assert called == []


def test_teardown_clears_orientation_callbacks(mock_bridge):
    called = []
    orientation.on_change(lambda t, b: called.append((t, b)))
    teardown()
    mock_bridge.receive({"type": "orientation.change", "top": 3, "bottom": 4})
    assert called == []


def test_teardown_cancels_timers(mock_bridge):
    import time
    called = []
    timer.set(0.05, lambda: called.append(1))
    teardown()
    time.sleep(0.15)
    assert called == []


def test_teardown_resets_orientation_state(mock_bridge):
    orientation._register_polling(mock_bridge)
    mock_bridge.receive({"type": "orientation.change", "top": 3, "bottom": 4})
    teardown()
    assert orientation.top() == 1
    assert orientation.bottom() == 6
