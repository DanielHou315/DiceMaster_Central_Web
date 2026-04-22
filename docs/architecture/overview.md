# Architecture Overview: DiceMaster Central Web Simulator

## Summary

The web simulator lets students run Python game strategies in a browser with no backend server. CPython runs inside the browser via Pyodide (WebAssembly). The `dice` Python package is the student-facing API layer; it talks to the surrounding JavaScript UI through a thin message-passing bridge.

## Layers

```
┌──────────────────────────────────────────────────────┐
│  Student code  (Python)                              │
│  from dice import screen, motion, orientation …     │
└───────────────────────┬──────────────────────────────┘
                        │ function calls
┌───────────────────────▼──────────────────────────────┐
│  dice package  (Python, runs in Pyodide worker)      │
│  screen / motion / orientation / timer / assets /    │
│  log / strategy.BaseStrategy                         │
└───────────────────────┬──────────────────────────────┘
                        │ postMessage (JSON)
┌───────────────────────▼──────────────────────────────┐
│  JS bridge  (browser main thread)                    │
│  Receives outbound messages, dispatches inbound      │
│  events back into the Pyodide worker                 │
└───────────────────────┬──────────────────────────────┘
                        │ DOM updates
┌───────────────────────▼──────────────────────────────┐
│  Virtual dice UI  (HTML / CSS / JS)                  │
│  Renders six screen faces, shake/flip controls       │
└──────────────────────────────────────────────────────┘
```

## Runtime Environment

Pyodide compiles CPython to WebAssembly and runs it in a Web Worker, keeping CPU-intensive Python off the main UI thread. The `dice` package is distributed as a pure-Python wheel (`dice-0.1.0-py3-none-any.whl`) that the web app loads into Pyodide with `micropip.install`.

## The Bridge (`dice/_bridge.py`)

`Bridge` is a module-level singleton. Its behavior depends on the runtime:

- **In Pyodide**: `send()` calls `js.postMessage` after converting the Python dict to a JS object via `pyodide.ffi.to_js`. Inbound messages arrive when the JS side calls `worker.postMessage`; the JavaScript host must call `bridge.receive(message)` on the Python side (e.g. via `pyodide.runPython`).
- **In tests / plain CPython**: `send()` appends to `bridge.sent` instead of calling `postMessage`. There is no real JS, so tests import a `MockBridge` from `tests/conftest.py` that replaces the singleton.

## Exposed Modules

| Module | Responsibility |
|--------|---------------|
| `dice.screen` | Send display commands to the virtual dice faces |
| `dice.motion` | Register shake callbacks; poll shake state |
| `dice.orientation` | Register flip callbacks; poll current top/bottom face |
| `dice.timer` | Schedule repeating or one-shot callbacks |
| `dice.assets` | Resolve asset names to paths in the virtual filesystem |
| `dice.log` (`from dice import log`) | Send debug messages to the web UI console panel |
| `dice.strategy.BaseStrategy` | Abstract base class students subclass to create a game |

`dice._bridge`, `dice._log`, and `dice._runtime` are internal modules not intended for student use.

## Message Protocol

### Outbound — Python → JS

Every outbound call serialises a plain dict with a `type` field and is sent via `Bridge.send()`.

| `type` | Additional fields | Produced by |
|--------|-------------------|-------------|
| `screen.set_text` | `screen_id: int`, `path: str` | `screen.set_text()` |
| `screen.set_image` | `screen_id: int`, `path: str` | `screen.set_image()` |
| `screen.set_gif` | `screen_id: int`, `path: str` | `screen.set_gif()` |
| `log` | `message: str` | `log()` |

### Inbound — JS → Python

The JS host delivers events by calling `bridge.receive(message)` inside the worker.

| `type` | Additional fields | Consumed by |
|--------|-------------------|-------------|
| `motion.shake` | `intensity: float` (0.0–1.0) | `motion` (callbacks + state) |
| `motion.still` | _(none)_ | `motion` (state only) |
| `orientation.change` | `top: int`, `bottom: int` | `orientation` (callbacks + state) |

## Data Flow: A Typical Interaction

The following traces what happens when student code calls `screen.set_image(1, assets.get("welcome.jpg"))` after the die is flipped.

```
1. Student code: screen.set_image(1, assets.get("welcome.jpg"))

2. assets.get("welcome.jpg")
   → returns "/assets/welcome.jpg"
      (assets._assets_root is set by BaseStrategy.__init__ to the
       assets_path argument passed when the JS host instantiates the game)

3. screen.set_image(1, "/assets/welcome.jpg")
   → calls Bridge.send({"type": "screen.set_image",
                         "screen_id": 1,
                         "path": "/assets/welcome.jpg"})

4. Bridge.send (Pyodide path)
   → to_js(message, dict_converter=Object.fromEntries)
   → js.postMessage(jsObject)
   → message leaves the Pyodide worker thread

5. JS main thread receives the postMessage event
   → reads message.type === "screen.set_image"
   → looks up screen element with id matching screen_id 1
   → sets src / innerHTML to resolve the asset path from the virtual FS
   → virtual dice UI updates to show welcome.jpg on face 1

6. User clicks the "Flip" button in the UI
   → JS calculates new top/bottom values (e.g. top=3, bottom=4)
   → JS calls worker.postMessage({type: "orientation.change", top: 3, bottom: 4})

7. Inside the Pyodide worker the host calls:
   bridge.receive({"type": "orientation.change", "top": 3, "bottom": 4})

8. Bridge.receive dispatches to registered handlers
   → orientation._dispatch_change(message)
   → calls each handler in _change_handlers with (top=3, bottom=4)

9. Student's on_flip(3, 4) method runs
   → calls screen.set_image(3, assets.get("highlight.jpg"))
   → cycle repeats from step 3
```

## API Parity with Hardware

The `dice` package is an intentional mirror of the `dicemaster_central` hardware package. Class names, method signatures, and event names are kept identical so a strategy written for the web simulator can be dropped onto a physical DiceMaster device without modification. See `docs/decisions/002-api-parity-with-hardware.md` for the rationale.

## Runtime Lifecycle

`BaseStrategy.__init__` calls `assets.configure(assets_path)` to point the virtual filesystem at the game's asset bundle. The JS host is responsible for calling `start_strategy()` to begin execution and `stop_strategy()` when the game ends. After a game ends, `dice._runtime.teardown()` resets all module-level state (handlers, timers, orientation defaults) and clears the bridge queue, making the worker ready for the next game without a full page reload.
