# DiceMaster Central Web — `dice` Package Design

## Overview

A pure-Python package called `dice` that provides the student-facing API for the DiceMaster web simulator. It mirrors the function signatures of the real `dice` package in `DiceMaster_Central` (which wraps ROS2), but routes all calls through a Pyodide JS bridge (`postMessage`) to the Next.js UI.

The two packages are completely independent — same name, same signatures, different implementations, never coexist at runtime.

## Student-Facing API

```python
# --- Screens ---
from dice import screen
screen.set_text(1, "assets/question.json")
screen.set_image(1, "assets/cat.jpg")
screen.set_gif(1, "assets/anim.gif.d")

# --- Motion (callbacks + polling) ---
from dice import motion
motion.on_shake(my_func)          # my_func(intensity: float)
motion.is_shaking()               # bool
motion.shake_intensity()          # float 0.0-1.0

# --- Orientation (callbacks + polling) ---
from dice import orientation
orientation.on_change(my_func)    # my_func(top: int, bottom: int)
orientation.top()                 # int — current top screen ID
orientation.bottom()              # int — current bottom screen ID

# --- Timers ---
from dice import timer
tid = timer.set(2.0, my_func)    # periodic
timer.once(5.0, my_func)         # one-shot
timer.cancel(tid)

# --- Utilities ---
from dice import log
log("debug message")

from dice import assets
assets.get("cat.jpg")             # returns path in virtual FS
assets.list()                     # all asset paths
```

### Strategy Class

```python
from dice import screen, motion, assets
from dice.strategy import BaseStrategy

class ShakeQuizlet(BaseStrategy):
    _strategy_name = "shake_quizlet"

    def start_strategy(self):
        self.idx = 0
        self.show_question(0)
        motion.on_shake(self.next_question)

    def stop_strategy(self):
        pass

    def next_question(self, intensity):
        self.idx += 1
        self.show_question(self.idx)

    def show_question(self, idx):
        screen.set_text(1, assets.get(f"q{idx}.json"))
```

## Architecture

Two independent repos, same package name:

| Repo | Package | Backend |
|---|---|---|
| DiceMaster_Central | `dice` | Wraps ROS2 (rclpy) — single node, lazy pub/sub |
| DiceMaster_Central_Web | `dice` | Wraps Pyodide JS bridge (postMessage) |

### Real hardware (`dice` in DiceMaster_Central)

- Single ROS2 node, single thread
- Lazy: importing `dice.motion` does nothing; calling `motion.on_shake(fn)` subscribes to `/imu/motion`
- Tracks all active pubs/subs/timers/callbacks per game round
- Game manager (internal only) calls `_runtime.teardown()` to clean up between games
- `teardown()` is NOT exposed to students

### Web simulator (`dice` in DiceMaster_Central_Web)

- Runs in Pyodide Web Worker
- All `dice.*` calls translate to JSON messages via `postMessage`
- Inbound messages from JS trigger registered callbacks

## JS Bridge Protocol

### Outbound (Python → JS)

```json
{"type": "screen.set_text", "screen_id": 1, "path": "assets/question.json"}
{"type": "screen.set_image", "screen_id": 1, "path": "assets/cat.jpg"}
{"type": "screen.set_gif", "screen_id": 1, "path": "assets/anim.gif.d"}
{"type": "log", "message": "debug info"}
{"type": "error", "message": "NameError: ...", "lineno": 12, "traceback": "..."}
```

### Inbound (JS → Python)

```json
{"type": "motion.shake", "intensity": 0.8}
{"type": "orientation.change", "top": 1, "bottom": 6}
```

This protocol is the contract the web team must implement on the JS side.

## Error Handling

- No validation in `dice` — just pass through to the bridge
- Python exceptions from student code are caught by the runner, serialized with traceback/line number, and sent as `error` messages to the UI
- Callback errors are caught and reported without crashing the simulator

## Testing

Mock the JS bridge, run with pytest in regular Python:

```python
def test_set_image(mock_bridge):
    screen.set_image(1, "assets/cat.jpg")
    mock_bridge.assert_sent({"type": "screen.set_image", "screen_id": 1, "path": "assets/cat.jpg"})

def test_on_shake(mock_bridge):
    called = []
    motion.on_shake(lambda i: called.append(i))
    mock_bridge.receive({"type": "motion.shake", "intensity": 0.8})
    assert called == [0.8]
```

## File Upload / Assets

Left to the web team. The `dice` package assumes assets are loaded into Pyodide's virtual filesystem before student code runs. `dice.assets.get("name")` returns a path in the virtual FS.

## Existing Code Violations

The current example strategies in DiceMaster_Central use raw ROS2 calls (`create_publisher`, `create_subscription`) which will be stripped from the student environment. Flagged:
- `examples/strategies/shake_quizlet/shake_quizlet.py`
- `examples/strategies/pipeline_test/pipeline_test.py`

These must be migrated to the `dice.*` API.
