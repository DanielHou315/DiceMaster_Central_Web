# ADR-001: Use Pyodide to Run Python Game Code in the Browser

## Status

Accepted

## Context

DiceMaster game strategies are written in Python. Students learn the language in class and write subclasses of `BaseStrategy` to define how a game reacts to physical events (shakes, flips, timers). For in-class demonstrations and take-home experimentation we need those same strategies to run in a web browser so that no physical device is required.

The requirements that shaped this decision:

- Students write one Python file. It must run on the physical device **and** in the browser without changes.
- No backend server. The simulator must be a static web page: zero infrastructure, hostable on GitHub Pages or a school file share.
- The Python environment must be close enough to real CPython that standard language constructs (classes, `abc.ABC`, `threading` as fallback, `os.path`) work without a compatibility shim layer in student code.
- The `dice` package must be installable as a normal wheel so the same package can be `pip install`-ed for local testing and loaded into the browser runtime.

## Decision

Run student Python code in a **Pyodide** environment: CPython 3.x compiled to WebAssembly and executed in a browser Web Worker.

The `dice` package is built as a pure-Python wheel (`dice-0.1.0-py3-none-any.whl`). The web app loads Pyodide, then uses `micropip.install` to load the wheel into the Pyodide runtime. From that point, `from dice import screen, motion …` works exactly as it does on the hardware device or a developer's laptop.

Communication between the Pyodide worker thread and the JavaScript main thread uses the standard `postMessage` / `worker.postMessage` channel. The `dice._bridge.Bridge` singleton abstracts this:

- **Outbound** (Python → JS): `Bridge.send(dict)` calls `js.postMessage` via `pyodide.ffi.to_js`.
- **Inbound** (JS → Python): the JS host calls `bridge.receive(message)` inside the worker whenever a hardware event (shake, flip) occurs in the UI.

When Pyodide's `js` module is not present (plain CPython in tests), `Bridge` falls back to an in-memory list, enabling the full test suite to run with `pytest` on a developer machine without a browser.

## Consequences

**Positive**

- Students use the Python they already know. No new language to learn, no syntax restrictions.
- The `BaseStrategy` subclass they write is identical for the browser and the hardware device.
- The `dice` package can be tested locally with `pytest` using the same source; no browser is needed for unit or integration tests.
- The wheel distribution model means the web app can be versioned independently of the `dice` package: bumping the wheel version is enough to update the simulator.

**Negative / Trade-offs**

- Pyodide adds roughly 10 MB to the initial page load (the WebAssembly binary). This is acceptable for a school-network context but would need consideration for low-bandwidth environments.
- Pyodide start-up latency (parsing and instantiating the WASM binary) adds a few seconds before the first game can start. The web app should display a loading indicator.
- Not all CPython standard-library modules are available in Pyodide (notably anything that requires OS-level file descriptors). The `dice` package avoids these; `timer.py` uses `js.setInterval`/`js.setTimeout` in Pyodide and falls back to `threading` only in tests.
- Debugging inside the Pyodide worker is more involved than debugging plain Python: browser devtools show the worker thread but Python tracebacks surface as strings in the console. The `log()` function routes messages to the visible UI console panel to mitigate this.

## Alternatives Considered

**Brython**
Brython transpiles Python to JavaScript at runtime. It has lower start-up overhead than Pyodide but implements a subset of Python; some standard-library modules and `abc.ABC` abstractions behave differently. Strategy code that uses `threading` or `os.path` would need guarding, violating the requirement that student code runs unchanged.

**Skulpt**
Skulpt is a well-established Python-in-browser solution but targets Python 2/early Python 3 semantics. It does not support `__future__` annotations, type hints, or the `abc` module in the form the `dice` package uses. Maintaining a compatibility shim in `BaseStrategy` for Skulpt was considered unacceptable complexity.

**Backend Python server with WebSockets**
Running a real Python process server-side and streaming events over WebSockets would give full CPython fidelity with zero browser compatibility concerns. It was rejected because it requires infrastructure (a server, a domain, TLS), prevents offline use, and introduces latency on every event round-trip. The requirement for a purely static deployment ruled this option out.
