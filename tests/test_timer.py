import time
from dice import timer


def test_set_periodic(mock_bridge):
    called = []
    tid = timer.set(0.05, lambda: called.append(1))
    time.sleep(0.18)
    timer.cancel(tid)
    assert len(called) >= 2


def test_once(mock_bridge):
    called = []
    timer.once(0.05, lambda: called.append(1))
    time.sleep(0.15)
    assert called == [1]


def test_cancel(mock_bridge):
    called = []
    tid = timer.set(0.05, lambda: called.append(1))
    timer.cancel(tid)
    time.sleep(0.15)
    assert called == []


def test_cancel_invalid_id(mock_bridge):
    timer.cancel(9999)  # should not raise
