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

### Modules

| Module | Functions |
|--------|-----------|
| `dice.screen` | `set_text(id, path)`, `set_image(id, path)`, `set_gif(id, path)` |
| `dice.motion` | `on_shake(fn)`, `is_shaking()`, `shake_intensity()` |
| `dice.orientation` | `on_change(fn)`, `top()`, `bottom()` |
| `dice.timer` | `set(interval, fn)`, `once(delay, fn)`, `cancel(id)` |
| `dice.assets` | `get(name)`, `list()` |
| `dice.log` | `log(message)` (imported from `dice` directly) |
| `dice.strategy` | `BaseStrategy` (abstract: `start_strategy()`, `stop_strategy()`) |

## JS Bridge Protocol

### Outbound (Python → JS via postMessage)

| type | fields |
|------|--------|
| `screen.set_text` | `screen_id`, `path` |
| `screen.set_image` | `screen_id`, `path` |
| `screen.set_gif` | `screen_id`, `path` |
| `log` | `message` |

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
