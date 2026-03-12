# `dice` Web Package Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the `dice` Python package for the DiceMaster web simulator — same API as the real hardware package, backed by a Pyodide JS bridge.

**Architecture:** Pure Python package with modules (`screen`, `motion`, `orientation`, `timer`, `assets`, `strategy`). Each module delegates to a singleton `_bridge` that sends/receives JSON messages via Pyodide's `postMessage`. A `_runtime` module provides internal teardown for the game manager.

**Tech Stack:** Python 3.11+, pytest, Pyodide JS FFI (import target only — tests mock the bridge)

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `dice/__init__.py`
- Create: `dice/py.typed`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

**Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "dice"
version = "0.1.0"
description = "DiceMaster student SDK — web simulator backend"
requires-python = ">=3.11"

[project.optional-dependencies]
dev = ["pytest>=7.0"]

[tool.setuptools.packages.find]
include = ["dice*"]
```

**Step 2: Create `dice/__init__.py`**

```python
"""DiceMaster student SDK."""
```

**Step 3: Create `dice/py.typed`**

Empty file (PEP 561 marker).

**Step 4: Create `tests/__init__.py`**

Empty file.

**Step 5: Create `tests/conftest.py` with mock bridge fixture**

This fixture is used by ALL subsequent tests. The mock bridge captures outbound messages and can inject inbound messages.

```python
import pytest
from dice._bridge import Bridge


class MockBridge:
    """Test double for the JS bridge. Captures outbound messages, injects inbound."""

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
    # Also reset all module state so tests are isolated
    from dice import _runtime
    _runtime.teardown()
    yield mock
```

**Step 6: Verify project structure**

Run: `cd /Users/danielhou/Code/DiceMaster/DiceMaster_Central_Web && find . -type f | grep -v .git | sort`
Expected: All files listed above present.

**Step 7: Commit**

```bash
git add pyproject.toml dice/ tests/
git commit -m "feat: scaffold dice package with pyproject.toml and test fixtures"
```

---

### Task 2: Bridge Module

The bridge is the single point of contact between Python and JS. All other modules use it. On the web it calls `postMessage` via Pyodide FFI. In tests it's replaced by `MockBridge`.

**Files:**
- Create: `dice/_bridge.py`
- Create: `tests/test_bridge.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/danielhou/Code/DiceMaster/DiceMaster_Central_Web && python3 -m pytest tests/test_bridge.py -v`
Expected: FAIL — `dice._bridge` does not exist yet.

**Step 3: Write minimal implementation**

```python
"""JS bridge — sends/receives JSON messages via postMessage (Pyodide) or mock (tests)."""

from __future__ import annotations

_instance: Bridge | None = None


class Bridge:
    """Singleton bridge to JavaScript main thread."""

    def __init__(self):
        self.sent: list[dict] = []
        self._inbound_handlers: dict[str, list] = {}
        self._js_post: callable | None = None
        try:
            from js import postMessage  # type: ignore[import]
            self._js_post = postMessage
        except ImportError:
            pass  # Running outside Pyodide (tests) — send() just logs

    def send(self, message: dict) -> None:
        """Send a message to the JS main thread."""
        if self._js_post is not None:
            from pyodide.ffi import to_js  # type: ignore[import]
            self._js_post(to_js(message, dict_converter=lambda x: x))
        self.sent.append(message)

    def on(self, msg_type: str, handler) -> None:
        """Register a handler for inbound messages of a given type."""
        self._inbound_handlers.setdefault(msg_type, []).append(handler)

    def receive(self, message: dict) -> None:
        """Dispatch an inbound message to registered handlers."""
        msg_type = message.get("type", "")
        for handler in self._inbound_handlers.get(msg_type, []):
            handler(message)

    def reset(self):
        """Clear all state (used by _runtime.teardown)."""
        self.sent.clear()
        self._inbound_handlers.clear()


def get_bridge() -> Bridge:
    """Get or create the singleton bridge instance."""
    global _instance
    if _instance is None:
        _instance = Bridge()
    return _instance
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/danielhou/Code/DiceMaster/DiceMaster_Central_Web && python3 -m pytest tests/test_bridge.py -v`
Expected: 3 PASSED

**Step 5: Commit**

```bash
git add dice/_bridge.py tests/test_bridge.py
git commit -m "feat: add JS bridge module with send/receive/singleton"
```

---

### Task 3: Screen Module

**Files:**
- Create: `dice/screen.py`
- Create: `tests/test_screen.py`

**Step 1: Write the failing tests**

```python
from dice import screen


def test_set_text(mock_bridge):
    screen.set_text(1, "assets/question.json")
    mock_bridge.assert_sent({
        "type": "screen.set_text",
        "screen_id": 1,
        "path": "assets/question.json",
    })


def test_set_image(mock_bridge):
    screen.set_image(2, "assets/cat.jpg")
    mock_bridge.assert_sent({
        "type": "screen.set_image",
        "screen_id": 2,
        "path": "assets/cat.jpg",
    })


def test_set_gif(mock_bridge):
    screen.set_gif(3, "assets/anim.gif.d")
    mock_bridge.assert_sent({
        "type": "screen.set_gif",
        "screen_id": 3,
        "path": "assets/anim.gif.d",
    })
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/danielhou/Code/DiceMaster/DiceMaster_Central_Web && python3 -m pytest tests/test_screen.py -v`
Expected: FAIL — `dice.screen` has no `set_text`.

**Step 3: Write minimal implementation**

```python
"""Screen control — set content on dice faces."""

from dice._bridge import get_bridge


def set_text(screen_id: int, path: str) -> None:
    """Set a screen to display text from a JSON file."""
    get_bridge().send({"type": "screen.set_text", "screen_id": screen_id, "path": path})


def set_image(screen_id: int, path: str) -> None:
    """Set a screen to display an image."""
    get_bridge().send({"type": "screen.set_image", "screen_id": screen_id, "path": path})


def set_gif(screen_id: int, path: str) -> None:
    """Set a screen to display a GIF animation."""
    get_bridge().send({"type": "screen.set_gif", "screen_id": screen_id, "path": path})
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/danielhou/Code/DiceMaster/DiceMaster_Central_Web && python3 -m pytest tests/test_screen.py -v`
Expected: 3 PASSED

**Step 5: Commit**

```bash
git add dice/screen.py tests/test_screen.py
git commit -m "feat: add screen module (set_text, set_image, set_gif)"
```

---

### Task 4: Motion Module

**Files:**
- Create: `dice/motion.py`
- Create: `tests/test_motion.py`

**Step 1: Write the failing tests**

```python
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


def test_is_shaking_resets_on_no_motion(mock_bridge):
    motion._register_polling(mock_bridge)
    mock_bridge.receive({"type": "motion.shake", "intensity": 0.8})
    mock_bridge.receive({"type": "motion.still"})
    assert motion.is_shaking() is False
    assert motion.shake_intensity() == 0.0
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/danielhou/Code/DiceMaster/DiceMaster_Central_Web && python3 -m pytest tests/test_motion.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
"""Motion detection — shake callbacks and polling."""

from dice._bridge import get_bridge

_shake_handlers: list = []
_shaking: bool = False
_intensity: float = 0.0
_polling_registered: bool = False


def on_shake(handler) -> None:
    """Register a callback for shake events. handler(intensity: float)."""
    _shake_handlers.append(handler)
    bridge = get_bridge()
    bridge.on("motion.shake", _dispatch_shake)


def is_shaking() -> bool:
    """Return whether the device is currently being shaken."""
    return _shaking


def shake_intensity() -> float:
    """Return current shake intensity (0.0-1.0)."""
    return _intensity


def _register_polling(bridge=None) -> None:
    """Register internal handlers for polling state updates."""
    global _polling_registered
    if _polling_registered:
        return
    b = bridge or get_bridge()
    b.on("motion.shake", _update_state_shake)
    b.on("motion.still", _update_state_still)
    _polling_registered = True


def _dispatch_shake(message: dict) -> None:
    intensity = message.get("intensity", 0.0)
    for handler in _shake_handlers:
        handler(intensity)


def _update_state_shake(message: dict) -> None:
    global _shaking, _intensity
    _shaking = True
    _intensity = message.get("intensity", 0.0)


def _update_state_still(message: dict) -> None:
    global _shaking, _intensity
    _shaking = False
    _intensity = 0.0


def _reset() -> None:
    """Clear all state (called by _runtime.teardown)."""
    global _shaking, _intensity, _polling_registered
    _shake_handlers.clear()
    _shaking = False
    _intensity = 0.0
    _polling_registered = False
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/danielhou/Code/DiceMaster/DiceMaster_Central_Web && python3 -m pytest tests/test_motion.py -v`
Expected: 7 PASSED

**Step 5: Commit**

```bash
git add dice/motion.py tests/test_motion.py
git commit -m "feat: add motion module (on_shake, is_shaking, shake_intensity)"
```

---

### Task 5: Orientation Module

**Files:**
- Create: `dice/orientation.py`
- Create: `tests/test_orientation.py`

**Step 1: Write the failing tests**

```python
from dice import orientation


def test_on_change_callback(mock_bridge):
    called = []
    orientation.on_change(lambda top, bottom: called.append((top, bottom)))
    mock_bridge.receive({"type": "orientation.change", "top": 1, "bottom": 6})
    assert called == [(1, 6)]


def test_top_default(mock_bridge):
    assert orientation.top() == 1  # default: screen 1 on top


def test_bottom_default(mock_bridge):
    assert orientation.bottom() == 6  # default: screen 6 on bottom


def test_top_after_change(mock_bridge):
    orientation._register_polling(mock_bridge)
    mock_bridge.receive({"type": "orientation.change", "top": 3, "bottom": 4})
    assert orientation.top() == 3
    assert orientation.bottom() == 4
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/danielhou/Code/DiceMaster/DiceMaster_Central_Web && python3 -m pytest tests/test_orientation.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
"""Orientation — track which screen faces up/down."""

from dice._bridge import get_bridge

_change_handlers: list = []
_top: int = 1
_bottom: int = 6
_polling_registered: bool = False


def on_change(handler) -> None:
    """Register a callback for orientation changes. handler(top: int, bottom: int)."""
    _change_handlers.append(handler)
    get_bridge().on("orientation.change", _dispatch_change)


def top() -> int:
    """Return the screen ID currently facing up."""
    return _top


def bottom() -> int:
    """Return the screen ID currently facing down."""
    return _bottom


def _register_polling(bridge=None) -> None:
    global _polling_registered
    if _polling_registered:
        return
    b = bridge or get_bridge()
    b.on("orientation.change", _update_state)
    _polling_registered = True


def _dispatch_change(message: dict) -> None:
    t = message.get("top", 1)
    b = message.get("bottom", 6)
    for handler in _change_handlers:
        handler(t, b)


def _update_state(message: dict) -> None:
    global _top, _bottom
    _top = message.get("top", 1)
    _bottom = message.get("bottom", 6)


def _reset() -> None:
    global _top, _bottom, _polling_registered
    _change_handlers.clear()
    _top = 1
    _bottom = 6
    _polling_registered = False
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/danielhou/Code/DiceMaster/DiceMaster_Central_Web && python3 -m pytest tests/test_orientation.py -v`
Expected: 4 PASSED

**Step 5: Commit**

```bash
git add dice/orientation.py tests/test_orientation.py
git commit -m "feat: add orientation module (on_change, top, bottom)"
```

---

### Task 6: Timer Module

**Files:**
- Create: `dice/timer.py`
- Create: `tests/test_timer.py`

**Step 1: Write the failing tests**

```python
import time
from dice import timer


def test_set_periodic(mock_bridge):
    called = []
    tid = timer.set(0.05, lambda: called.append(1))
    time.sleep(0.18)
    timer.cancel(tid)
    assert len(called) >= 2  # should fire ~3 times in 0.18s


def test_once(mock_bridge):
    called = []
    timer.once(0.05, lambda: called.append(1))
    time.sleep(0.15)
    assert called == [1]  # fires exactly once


def test_cancel(mock_bridge):
    called = []
    tid = timer.set(0.05, lambda: called.append(1))
    timer.cancel(tid)
    time.sleep(0.15)
    assert called == []


def test_cancel_invalid_id(mock_bridge):
    timer.cancel(9999)  # should not raise
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/danielhou/Code/DiceMaster/DiceMaster_Central_Web && python3 -m pytest tests/test_timer.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
"""Timers — periodic and one-shot callbacks."""

from __future__ import annotations
import threading

_timers: dict[int, threading.Timer | threading.Event] = {}
_next_id: int = 0
_lock = threading.Lock()


def set(interval: float, callback) -> int:
    """Start a periodic timer. Returns timer ID for cancel()."""
    global _next_id
    with _lock:
        tid = _next_id
        _next_id += 1
    stop_event = threading.Event()
    _timers[tid] = stop_event

    def loop():
        while not stop_event.is_set():
            stop_event.wait(interval)
            if not stop_event.is_set():
                callback()

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return tid


def once(delay: float, callback) -> int:
    """Fire callback once after delay. Returns timer ID for cancel()."""
    global _next_id
    with _lock:
        tid = _next_id
        _next_id += 1
    t = threading.Timer(delay, callback)
    t.daemon = True
    _timers[tid] = t
    t.start()
    return tid


def cancel(timer_id: int) -> None:
    """Cancel a timer by ID. No-op if ID is invalid."""
    obj = _timers.pop(timer_id, None)
    if obj is None:
        return
    if isinstance(obj, threading.Event):
        obj.set()
    elif isinstance(obj, threading.Timer):
        obj.cancel()


def _reset() -> None:
    """Cancel all timers (called by _runtime.teardown)."""
    global _next_id
    for tid in list(_timers.keys()):
        cancel(tid)
    _timers.clear()
    _next_id = 0
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/danielhou/Code/DiceMaster/DiceMaster_Central_Web && python3 -m pytest tests/test_timer.py -v`
Expected: 4 PASSED

**Step 5: Commit**

```bash
git add dice/timer.py tests/test_timer.py
git commit -m "feat: add timer module (set, once, cancel)"
```

---

### Task 7: Assets Module

**Files:**
- Create: `dice/assets.py`
- Create: `tests/test_assets.py`

**Step 1: Write the failing tests**

```python
import os
import tempfile
from dice import assets


def test_get_existing(mock_bridge, tmp_path, monkeypatch):
    (tmp_path / "cat.jpg").touch()
    monkeypatch.setattr(assets, "_assets_root", str(tmp_path))
    assert assets.get("cat.jpg") == str(tmp_path / "cat.jpg")


def test_get_nested(mock_bridge, tmp_path, monkeypatch):
    (tmp_path / "cats").mkdir()
    (tmp_path / "cats" / "cat1.jpg").touch()
    monkeypatch.setattr(assets, "_assets_root", str(tmp_path))
    assert assets.get("cats/cat1.jpg") == str(tmp_path / "cats" / "cat1.jpg")


def test_list_assets(mock_bridge, tmp_path, monkeypatch):
    (tmp_path / "a.jpg").touch()
    (tmp_path / "b.json").touch()
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.jpg").touch()
    monkeypatch.setattr(assets, "_assets_root", str(tmp_path))
    result = assets.list()
    assert "a.jpg" in result
    assert "b.json" in result
    assert "sub/c.jpg" in result
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/danielhou/Code/DiceMaster/DiceMaster_Central_Web && python3 -m pytest tests/test_assets.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
"""Asset access — resolve paths in the virtual filesystem."""

from __future__ import annotations
import os

_assets_root: str = "/assets"  # Default; set by game runner before student code starts


def configure(root: str) -> None:
    """Set the assets root directory. Called by game runner, not students."""
    global _assets_root
    _assets_root = root


def get(name: str) -> str:
    """Return the full path to an asset file."""
    return os.path.join(_assets_root, name)


def list() -> list[str]:
    """Return all asset paths relative to the assets root."""
    result = []
    for dirpath, _, filenames in os.walk(_assets_root):
        for f in filenames:
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, _assets_root)
            result.append(rel)
    return sorted(result)


def _reset() -> None:
    """Reset to default (called by _runtime.teardown)."""
    global _assets_root
    _assets_root = "/assets"
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/danielhou/Code/DiceMaster/DiceMaster_Central_Web && python3 -m pytest tests/test_assets.py -v`
Expected: 3 PASSED

**Step 5: Commit**

```bash
git add dice/assets.py tests/test_assets.py
git commit -m "feat: add assets module (get, list, configure)"
```

---

### Task 8: Log Function

**Files:**
- Create: `dice/_log.py`
- Modify: `dice/__init__.py`
- Create: `tests/test_log.py`

**Step 1: Write the failing test**

```python
from dice import log


def test_log_sends_message(mock_bridge):
    log("hello world")
    mock_bridge.assert_sent({"type": "log", "message": "hello world"})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/danielhou/Code/DiceMaster/DiceMaster_Central_Web && python3 -m pytest tests/test_log.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

`dice/_log.py`:
```python
"""Logging — send debug messages to the web UI console."""

from dice._bridge import get_bridge


def log(message: str) -> None:
    """Send a log message to the web UI."""
    get_bridge().send({"type": "log", "message": message})
```

`dice/__init__.py`:
```python
"""DiceMaster student SDK."""

from dice._log import log

__all__ = ["log"]
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/danielhou/Code/DiceMaster/DiceMaster_Central_Web && python3 -m pytest tests/test_log.py -v`
Expected: 1 PASSED

**Step 5: Commit**

```bash
git add dice/_log.py dice/__init__.py tests/test_log.py
git commit -m "feat: add log function"
```

---

### Task 9: Runtime Teardown

**Files:**
- Create: `dice/_runtime.py`
- Create: `tests/test_runtime.py`

**Step 1: Write the failing tests**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/danielhou/Code/DiceMaster/DiceMaster_Central_Web && python3 -m pytest tests/test_runtime.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
"""Internal runtime management — NOT exposed to students."""

from dice._bridge import get_bridge


def teardown() -> None:
    """Reset all dice module state. Called by game manager between games."""
    from dice import motion, orientation, timer, assets
    motion._reset()
    orientation._reset()
    timer._reset()
    assets._reset()
    get_bridge().reset()
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/danielhou/Code/DiceMaster/DiceMaster_Central_Web && python3 -m pytest tests/test_runtime.py -v`
Expected: 4 PASSED

**Step 5: Commit**

```bash
git add dice/_runtime.py tests/test_runtime.py
git commit -m "feat: add runtime teardown for game manager"
```

---

### Task 10: BaseStrategy Class

**Files:**
- Create: `dice/strategy.py`
- Create: `tests/test_strategy.py`

**Step 1: Write the failing tests**

```python
from dice.strategy import BaseStrategy


class FakeStrategy(BaseStrategy):
    _strategy_name = "fake"
    started = False
    stopped = False

    def start_strategy(self):
        self.started = True

    def stop_strategy(self):
        self.stopped = True


def test_strategy_name():
    assert FakeStrategy._strategy_name == "fake"


def test_start_strategy(mock_bridge):
    s = FakeStrategy(game_name="test", config={}, assets_path="/tmp")
    s.start_strategy()
    assert s.started


def test_stop_strategy(mock_bridge):
    s = FakeStrategy(game_name="test", config={}, assets_path="/tmp")
    s.stop_strategy()
    assert s.stopped


def test_config_access(mock_bridge):
    s = FakeStrategy(game_name="test", config={"difficulty": "hard"}, assets_path="/tmp")
    assert s.config["difficulty"] == "hard"


def test_game_name(mock_bridge):
    s = FakeStrategy(game_name="my_game", config={}, assets_path="/tmp")
    assert s.game_name == "my_game"


def test_abstract_methods():
    """BaseStrategy cannot be instantiated directly."""
    import pytest
    with pytest.raises(TypeError):
        BaseStrategy(game_name="test", config={}, assets_path="/tmp")
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/danielhou/Code/DiceMaster/DiceMaster_Central_Web && python3 -m pytest tests/test_strategy.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
"""Base strategy — students subclass this to create games."""

from __future__ import annotations
from abc import ABC, abstractmethod

from dice import assets as _assets


class BaseStrategy(ABC):
    """Base class for student game strategies."""

    _strategy_name: str = ""

    def __init__(self, game_name: str, config: dict, assets_path: str, **kwargs):
        self._game_name = game_name
        self._config = config
        self._assets_path = assets_path
        _assets.configure(assets_path)

    @property
    def game_name(self) -> str:
        return self._game_name

    @property
    def config(self) -> dict:
        return self._config

    @abstractmethod
    def start_strategy(self) -> None:
        """Called when the game starts. Set up screens, register callbacks."""
        ...

    @abstractmethod
    def stop_strategy(self) -> None:
        """Called when the game ends. Clean up."""
        ...
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/danielhou/Code/DiceMaster/DiceMaster_Central_Web && python3 -m pytest tests/test_strategy.py -v`
Expected: 6 PASSED

**Step 5: Commit**

```bash
git add dice/strategy.py tests/test_strategy.py
git commit -m "feat: add BaseStrategy class"
```

---

### Task 11: Integration Test — Full Game Simulation

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write a test that simulates a complete game lifecycle**

```python
"""Integration test — simulate a full game round."""

from dice import screen, motion, orientation, log
from dice.strategy import BaseStrategy
from dice._runtime import teardown


class QuizGame(BaseStrategy):
    _strategy_name = "quiz"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.question_idx = 0

    def start_strategy(self):
        self.show_question()
        motion.on_shake(self.next_question)
        orientation.on_change(self.on_flip)

    def stop_strategy(self):
        log("game over")

    def show_question(self):
        screen.set_text(1, f"q{self.question_idx}.json")

    def next_question(self, intensity):
        self.question_idx += 1
        self.show_question()

    def on_flip(self, top, bottom):
        screen.set_image(top, "highlight.jpg")


def test_full_game_lifecycle(mock_bridge):
    # 1. Game manager creates and starts strategy
    game = QuizGame(game_name="quiz", config={}, assets_path="/assets")
    game.start_strategy()

    # Verify initial screen set
    mock_bridge.assert_sent({"type": "screen.set_text", "screen_id": 1, "path": "q0.json"})

    # 2. User shakes the device
    mock_bridge.receive({"type": "motion.shake", "intensity": 0.7})
    mock_bridge.assert_sent({"type": "screen.set_text", "screen_id": 1, "path": "q1.json"})

    # 3. User flips the dice
    mock_bridge.receive({"type": "orientation.change", "top": 3, "bottom": 4})
    mock_bridge.assert_sent({"type": "screen.set_image", "screen_id": 3, "path": "highlight.jpg"})

    # 4. Game manager stops the game
    game.stop_strategy()
    mock_bridge.assert_sent({"type": "log", "message": "game over"})

    # 5. Game manager tears down for next game
    teardown()

    # 6. Verify callbacks no longer fire
    prev_count = len(mock_bridge.sent)
    mock_bridge.receive({"type": "motion.shake", "intensity": 0.5})
    assert len(mock_bridge.sent) == prev_count  # no new messages
```

**Step 2: Run all tests**

Run: `cd /Users/danielhou/Code/DiceMaster/DiceMaster_Central_Web && python3 -m pytest tests/ -v`
Expected: ALL PASSED

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add full game lifecycle integration test"
```

---

### Task 12: README and Protocol Documentation

**Files:**
- Create: `README.md`

**Step 1: Write README**

```markdown
# DiceMaster Central Web — `dice` Package

Python SDK for the DiceMaster web simulator. Provides the same `dice` API as the hardware package, backed by a Pyodide JS bridge.

## Student API

```python
from dice import screen, motion, orientation, timer, assets, log
from dice.strategy import BaseStrategy

class MyGame(BaseStrategy):
    _strategy_name = "my_game"

    def start_strategy(self):
        screen.set_image(1, assets.get("welcome.jpg"))
        motion.on_shake(self.on_shake)
        orientation.on_change(self.on_flip)

    def stop_strategy(self):
        pass

    def on_shake(self, intensity):
        screen.set_text(1, assets.get("next.json"))

    def on_flip(self, top, bottom):
        log(f"Top screen: {top}")
```

## JS Bridge Protocol

### Outbound (Python → JS via postMessage)

| type | fields |
|------|--------|
| `screen.set_text` | `screen_id`, `path` |
| `screen.set_image` | `screen_id`, `path` |
| `screen.set_gif` | `screen_id`, `path` |
| `log` | `message` |
| `error` | `message`, `lineno`, `traceback` |

### Inbound (JS → Python via worker.postMessage)

| type | fields |
|------|--------|
| `motion.shake` | `intensity` (0.0-1.0) |
| `motion.still` | _(none)_ |
| `orientation.change` | `top`, `bottom` (screen IDs) |

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Building for Pyodide

```bash
pip wheel . -w dist/
# Copy dist/dice-0.1.0-py3-none-any.whl to web app's public/wheels/
```
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with student API and bridge protocol"
```
