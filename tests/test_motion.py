from dice import motion


def test_on_shake_callback(mock_bridge):
    called = []
    motion.on_shake(lambda intensity: called.append(intensity))
    mock_bridge.receive({"type": "motion.shake", "intensity": 0.8})
    assert called == [0.8]


def test_multiple_shake_callbacks(mock_bridge):
    a, b = [], []
    motion.on_shake(lambda i: a.append(i))
    motion.on_shake(lambda i: b.append(i))
    mock_bridge.receive({"type": "motion.shake", "intensity": 0.5})
    assert a == [0.5]
    assert b == [0.5]


def test_is_shaking_default(mock_bridge):
    assert motion.is_shaking() is False


def test_is_shaking_after_shake(mock_bridge):
    motion._register_polling(mock_bridge)
    mock_bridge.receive({"type": "motion.shake", "intensity": 0.8})
    assert motion.is_shaking() is True


def test_shake_intensity_default(mock_bridge):
    assert motion.shake_intensity() == 0.0


def test_shake_intensity_after_shake(mock_bridge):
    motion._register_polling(mock_bridge)
    mock_bridge.receive({"type": "motion.shake", "intensity": 0.6})
    assert motion.shake_intensity() == 0.6


def test_is_shaking_resets_on_still(mock_bridge):
    motion._register_polling(mock_bridge)
    mock_bridge.receive({"type": "motion.shake", "intensity": 0.8})
    mock_bridge.receive({"type": "motion.still"})
    assert motion.is_shaking() is False
    assert motion.shake_intensity() == 0.0
