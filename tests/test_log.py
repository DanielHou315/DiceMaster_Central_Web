from dice import log


def test_log_sends_message(mock_bridge):
    log("hello world")
    mock_bridge.assert_sent({"type": "log", "message": "hello world"})
