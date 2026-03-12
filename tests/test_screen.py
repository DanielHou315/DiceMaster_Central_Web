from dice import screen


def test_set_text(mock_bridge):
    screen.set_text(1, "assets/question.json")
    mock_bridge.assert_sent({"type": "screen.set_text", "screen_id": 1, "path": "assets/question.json"})


def test_set_image(mock_bridge):
    screen.set_image(2, "assets/cat.jpg")
    mock_bridge.assert_sent({"type": "screen.set_image", "screen_id": 2, "path": "assets/cat.jpg"})


def test_set_gif(mock_bridge):
    screen.set_gif(3, "assets/anim.gif.d")
    mock_bridge.assert_sent({"type": "screen.set_gif", "screen_id": 3, "path": "assets/anim.gif.d"})
