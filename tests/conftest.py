import pytest
from dice._bridge import Bridge


class MockBridge:
    """Test double for the JS bridge."""

    def __init__(self):
        self.sent: list[dict] = []
        self._inbound_handlers: dict[str, list] = {}

    def send(self, message: dict) -> None:
        self.sent.append(message)

    def on(self, msg_type: str, handler) -> None:
        self._inbound_handlers.setdefault(msg_type, []).append(handler)

    def receive(self, message: dict) -> None:
        msg_type = message["type"]
        for handler in self._inbound_handlers.get(msg_type, []):
            handler(message)

    def assert_sent(self, expected: dict) -> None:
        assert expected in self.sent, f"Expected {expected} in {self.sent}"

    def reset(self):
        self.sent.clear()
        self._inbound_handlers.clear()


@pytest.fixture(autouse=True)
def mock_bridge(monkeypatch):
    """Replace the global bridge with a mock for every test."""
    mock = MockBridge()
    import dice._bridge as bridge_module
    monkeypatch.setattr(bridge_module, "_instance", mock)
    from dice import _runtime
    _runtime.teardown()
    yield mock
