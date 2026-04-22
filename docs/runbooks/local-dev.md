# Local Development Runbook

This document covers how to set up a development environment, run the test suite, and extend the `dice` package with a new API module.

## Prerequisites

- Python 3.11 or later (the project requires `>=3.11` per `pyproject.toml`).
- [`uv`](https://github.com/astral-sh/uv) — the project uses `uv` for dependency management and virtual environment creation.

Install `uv` if you don't have it:

```bash
curl -Lsf https://astral.sh/uv/install.sh | sh
# or on macOS with Homebrew:
brew install uv
```

## Install dependencies

From the repository root (`DiceMaster_Central_Web/`):

```bash
uv sync
```

This creates a `.venv/` virtual environment and installs the `dice` package in editable mode along with the `dev` dependency group (`pytest>=7.0`). You do not need to activate the venv manually — `uv run` handles activation automatically.

To install manually into an existing environment instead:

```bash
pip install -e ".[dev]"
```

## Run the test suite

```bash
uv run pytest tests/ -v
```

All tests run against plain CPython — no browser required. The `conftest.py` fixture replaces the singleton `Bridge` instance with a `MockBridge` before each test, so calls to `screen.set_image` and friends write to an in-memory list rather than calling `postMessage`.

To run a single test file:

```bash
uv run pytest tests/test_screen.py -v
```

To stop on the first failure:

```bash
uv run pytest tests/ -x
```

## Project structure

```
DiceMaster_Central_Web/
├── dice/               # The student-facing Python package
│   ├── __init__.py     # Exports `log`; entry point for `from dice import log`
│   ├── _bridge.py      # Singleton bridge: Python ↔ JS postMessage
│   ├── _log.py         # log() implementation
│   ├── _runtime.py     # teardown() — resets all module state between games
│   ├── assets.py       # Asset path resolution
│   ├── motion.py       # Shake callbacks and polling
│   ├── orientation.py  # Flip callbacks and polling
│   ├── screen.py       # Display commands
│   ├── strategy.py     # BaseStrategy abstract class
│   ├── timer.py        # setInterval / setTimeout wrappers
│   └── py.typed        # PEP 561 marker — package ships inline type hints
├── tests/
│   ├── conftest.py     # MockBridge fixture (autouse, replaces singleton)
│   └── test_*.py       # One file per module + integration test
├── docs/               # This documentation tree
└── pyproject.toml      # Build config (hatchling), project metadata, dev deps
```

## Understanding `pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "dice"
version = "0.1.0"
description = "DiceMaster student SDK — web simulator backend"
requires-python = ">=3.11"

[dependency-groups]
dev = ["pytest>=7.0"]

[tool.hatch.build.targets.wheel]
packages = ["dice"]
```

Key points:

- The package name is `dice` (not `dicemaster-central-web`). Students write `from dice import screen`.
- There are no runtime dependencies outside the standard library. Pyodide itself provides `js` and `pyodide.ffi`; these are only imported inside `try/except ImportError` blocks so the package installs cleanly on plain CPython.
- Dev dependencies are in a `[dependency-groups]` table (PEP 735), which `uv` understands natively. If you use plain `pip`, install `pytest` manually.

## Building the wheel for Pyodide

```bash
pip wheel . -w dist/
```

This produces `dist/dice-0.1.0-py3-none-any.whl`. Copy this file to the web application's `public/wheels/` directory. The web app loads it with:

```js
await micropip.install("/wheels/dice-0.1.0-py3-none-any.whl");
```

Bump the `version` in `pyproject.toml` before building whenever the API surface changes, so the browser does not serve a cached old wheel.

## Adding a new API module

Follow these steps to add a new top-level module, for example `dice.haptics`.

### 1. Create the module file

```
dice/haptics.py
```

Follow the pattern of existing modules:

```python
"""Haptic feedback — trigger vibration patterns on dice faces."""
from dice._bridge import get_bridge

_handlers: list = []
_registered: bool = False


def on_buzz(handler) -> None:
    global _registered
    _handlers.append(handler)
    if not _registered:
        get_bridge().on("haptics.buzz", _dispatch)
        _registered = True


def buzz(screen_id: int, duration: float) -> None:
    get_bridge().send({"type": "haptics.buzz",
                       "screen_id": screen_id,
                       "duration": duration})


def _reset() -> None:
    global _registered
    _handlers.clear()
    _registered = False
```

### 2. Register `_reset` in `_runtime.py`

Open `dice/_runtime.py` and add your module to `teardown()`:

```python
def teardown() -> None:
    from dice import motion, orientation, timer, assets, haptics
    motion._reset()
    orientation._reset()
    timer._reset()
    assets._reset()
    haptics._reset()
    get_bridge().reset()
```

Without this step, handler lists and registered-flag state will survive across game resets.

### 3. Write tests

Create `tests/test_haptics.py`. The `mock_bridge` fixture from `conftest.py` is `autouse=True`, so it is injected into every test automatically — you only need to accept it as a parameter to inspect sent messages:

```python
from dice import haptics


def test_buzz_sends_message(mock_bridge):
    haptics.buzz(2, 0.5)
    mock_bridge.assert_sent({"type": "haptics.buzz", "screen_id": 2, "duration": 0.5})


def test_on_buzz_callback(mock_bridge):
    received = []
    haptics.on_buzz(lambda intensity: received.append(intensity))
    mock_bridge.receive({"type": "haptics.buzz", "intensity": 0.8})
    assert received == [0.8]
```

### 4. Update the hardware package

Because the web package must maintain API parity with `dicemaster_central` (see `docs/decisions/002-api-parity-with-hardware.md`), any new module added here should be proposed to or mirrored in the hardware package. Open an issue or PR on the hardware repository before merging new API surface.

### 5. Update `README.md`

Add the new module to the Modules table in `README.md` so students and educators can discover it.

## Common development tasks

**Check for import errors without running tests:**

```bash
uv run python -c "from dice import screen, motion, orientation, timer, assets, log; from dice.strategy import BaseStrategy; print('OK')"
```

**Run a specific test by keyword:**

```bash
uv run pytest tests/ -k "shake" -v
```

**Inspect what messages a strategy sends (without a browser):**

```python
# scratch.py — run with: uv run python scratch.py
import dice._bridge as bridge_module
from dice._bridge import Bridge

mock = Bridge()       # fresh instance, no js.postMessage
bridge_module._instance = mock

from dice import screen, motion
screen.set_image(1, "/assets/test.jpg")
print(mock.sent)      # [{'type': 'screen.set_image', 'screen_id': 1, 'path': '/assets/test.jpg'}]
```
