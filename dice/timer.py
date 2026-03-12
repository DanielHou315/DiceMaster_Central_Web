"""Timers — periodic and one-shot callbacks.

Uses JavaScript setInterval/setTimeout when running in Pyodide,
falls back to threading for tests.
"""
from __future__ import annotations

_timers: dict[int, object] = {}
_next_id: int = 0
_in_pyodide: bool = False

try:
    from pyodide.ffi import create_proxy  # noqa: F401
    _in_pyodide = True
except ImportError:
    pass


def set(interval: float, callback) -> int:
    global _next_id
    tid = _next_id
    _next_id += 1

    if _in_pyodide:
        from js import setInterval, clearInterval
        from pyodide.ffi import create_proxy
        proxy = create_proxy(callback)
        js_id = setInterval(proxy, int(interval * 1000))
        _timers[tid] = ("interval", js_id, proxy)
    else:
        import threading
        stop_event = threading.Event()
        _timers[tid] = ("thread_event", stop_event)

        def loop():
            while not stop_event.is_set():
                stop_event.wait(interval)
                if not stop_event.is_set():
                    callback()

        t = threading.Thread(target=loop, daemon=True)
        t.start()

    return tid


def once(delay: float, callback) -> int:
    global _next_id
    tid = _next_id
    _next_id += 1

    if _in_pyodide:
        from js import setTimeout
        from pyodide.ffi import create_proxy
        proxy = create_proxy(callback)
        js_id = setTimeout(proxy, int(delay * 1000))
        _timers[tid] = ("timeout", js_id, proxy)
    else:
        import threading
        t = threading.Timer(delay, callback)
        t.daemon = True
        _timers[tid] = ("thread_timer", t)
        t.start()

    return tid


def cancel(timer_id: int) -> None:
    entry = _timers.pop(timer_id, None)
    if entry is None:
        return

    kind = entry[0]
    if kind == "interval":
        from js import clearInterval
        clearInterval(entry[1])
        entry[2].destroy()
    elif kind == "timeout":
        from js import clearTimeout
        clearTimeout(entry[1])
        entry[2].destroy()
    elif kind == "thread_event":
        entry[1].set()
    elif kind == "thread_timer":
        entry[1].cancel()


def _reset() -> None:
    global _next_id
    for tid in list(_timers.keys()):
        cancel(tid)
    _timers.clear()
    _next_id = 0
