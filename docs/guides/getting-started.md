# Getting Started: Writing a Game for the Web Simulator

## What you will build

A Python game strategy that reacts to dice shakes and flips, displays content on the virtual dice faces, and runs in the DiceMaster web simulator without any extra software.

## Prerequisites

- A modern browser (Chrome, Firefox, or Safari).
- The DiceMaster web simulator page open (your instructor will provide the URL, or see `docs/runbooks/local-dev.md` to run it locally).
- Basic familiarity with Python classes.

## The `from dice import …` pattern

All student-facing functionality lives in the `dice` package. Import the modules you need at the top of your file:

```python
from dice import screen, motion, orientation, timer, assets, log
from dice.strategy import BaseStrategy
```

You never instantiate these modules yourself. The simulator initialises them when it loads your strategy.

## Anatomy of a strategy

Every game is a class that inherits from `BaseStrategy` and overrides two required methods:

```python
class MyGame(BaseStrategy):
    _strategy_name = "my_game"   # unique identifier, used by the simulator

    def start_strategy(self):
        # Called once when the game starts. Set up your initial screen state
        # and register any event handlers here.
        pass

    def stop_strategy(self):
        # Called once when the game ends. Clean up if needed.
        pass
```

`_strategy_name` must be a non-empty string and unique across games loaded in the same simulator session.

## Displaying content on dice faces

The physical die has six faces, each with a small screen. In the web simulator they are numbered 1–6. Use `screen` to control what is shown:

```python
screen.set_image(1, assets.get("welcome.jpg"))   # show an image on face 1
screen.set_text(1, assets.get("question.json"))  # show text layout on face 1
screen.set_gif(2, assets.get("spinner.gif"))     # show an animation on face 2
```

`assets.get(name)` resolves a filename to its full path inside the game's asset bundle. Always use `assets.get()` rather than hard-coding a path — the bundle location varies between the web simulator and the hardware device.

## Reacting to shake events

Register a callback with `motion.on_shake`. It will be called every time the simulator detects a shake, with the intensity as a float between 0.0 and 1.0:

```python
def start_strategy(self):
    motion.on_shake(self.on_shake)

def on_shake(self, intensity):
    log(f"Shaken with intensity {intensity:.2f}")
    screen.set_image(1, assets.get("result.jpg"))
```

To poll the current shake state instead of using a callback:

```python
if motion.is_shaking():
    intensity = motion.shake_intensity()
```

## Reacting to orientation changes

`orientation.on_change` fires whenever the die is flipped. The callback receives the face numbers of the new top and bottom faces:

```python
def start_strategy(self):
    orientation.on_change(self.on_flip)

def on_flip(self, top, bottom):
    log(f"Face {top} is on top")
    screen.set_image(top, assets.get("highlight.jpg"))
```

To poll orientation:

```python
current_top = orientation.top()
current_bottom = orientation.bottom()
```

## Using timers

`timer.set` schedules a repeating callback (like `setInterval`). `timer.once` fires a callback after a delay (like `setTimeout`). Both return a timer ID you can pass to `timer.cancel`.

```python
def start_strategy(self):
    self._tick_id = timer.set(2.0, self.tick)   # every 2 seconds

def tick(self):
    screen.set_image(1, assets.get("tick.jpg"))

def stop_strategy(self):
    timer.cancel(self._tick_id)
```

## Logging

`log()` sends a string to the simulator's console panel, visible below the dice UI. Use it for debugging:

```python
log("Game started")
log(f"Current top face: {orientation.top()}")
```

## A complete working example

The following game shows a welcome screen on face 1 when it starts. Each shake advances to the next question. Flipping the die highlights the new top face.

```python
from dice import screen, motion, orientation, log, assets
from dice.strategy import BaseStrategy


QUESTIONS = ["q0.json", "q1.json", "q2.json", "q3.json"]


class QuizGame(BaseStrategy):
    _strategy_name = "quiz"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._question_idx = 0

    def start_strategy(self):
        self._show_question()
        motion.on_shake(self._next_question)
        orientation.on_change(self._on_flip)
        log("Quiz started")

    def stop_strategy(self):
        log("Quiz ended")

    def _show_question(self):
        path = assets.get(QUESTIONS[self._question_idx])
        screen.set_text(1, path)

    def _next_question(self, intensity):
        if intensity < 0.3:
            return  # ignore gentle nudges
        self._question_idx = (self._question_idx + 1) % len(QUESTIONS)
        self._show_question()
        log(f"Moved to question {self._question_idx}")

    def _on_flip(self, top, bottom):
        screen.set_image(top, assets.get("highlight.jpg"))
        log(f"Flipped: top={top} bottom={bottom}")
```

## Loading your strategy into the simulator

1. Open the web simulator in your browser.
2. Click "Load Strategy" and select your `.py` file, or paste the code into the editor panel.
3. The simulator installs the `dice` package into Pyodide, imports your module, finds the `BaseStrategy` subclass, and instantiates it.
4. Click "Start" to call `start_strategy()`.
5. Use the on-screen shake and flip controls to trigger events.
6. Click "Stop" to call `stop_strategy()` and reset the simulator.

## Common mistakes

**Forgetting `_strategy_name`** — the simulator uses this to identify your class. If it is missing or empty, loading will fail with a clear error.

**Hard-coding asset paths** — always use `assets.get("filename")` rather than `"/assets/filename"`. The root path is configured by the simulator when it instantiates your class.

**Not calling `super().__init__`** — `BaseStrategy.__init__` configures the asset root. If you override `__init__` and omit the `super()` call, `assets.get()` will return incorrect paths.

**Registering handlers outside `start_strategy`** — callbacks registered at module import time or inside `__init__` may survive across game resets. Register all event handlers inside `start_strategy`.
