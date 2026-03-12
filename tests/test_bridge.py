from dice._bridge import get_bridge


def test_bridge_send(mock_bridge):
    bridge = get_bridge()
    bridge.send({"type": "test", "data": 42})
    mock_bridge.assert_sent({"type": "test", "data": 42})


def test_bridge_receive(mock_bridge):
    received = []
    bridge = get_bridge()
    bridge.on("test.event", lambda msg: received.append(msg))
    mock_bridge.receive({"type": "test.event", "value": "hello"})
    assert len(received) == 1
    assert received[0]["value"] == "hello"


def test_bridge_singleton():
    from dice._bridge import get_bridge
    assert get_bridge() is get_bridge()
