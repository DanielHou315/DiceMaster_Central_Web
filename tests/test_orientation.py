from dice import orientation


def test_on_change_callback(mock_bridge):
    called = []
    orientation.on_change(lambda top, bottom: called.append((top, bottom)))
    mock_bridge.receive({"type": "orientation.change", "top": 1, "bottom": 6})
    assert called == [(1, 6)]


def test_top_default(mock_bridge):
    assert orientation.top() == 1


def test_bottom_default(mock_bridge):
    assert orientation.bottom() == 6


def test_state_after_change(mock_bridge):
    orientation._register_polling(mock_bridge)
    mock_bridge.receive({"type": "orientation.change", "top": 3, "bottom": 4})
    assert orientation.top() == 3
    assert orientation.bottom() == 4
