# ADR-002: Keep the Web SDK API Identical to the Hardware Package

## Status

Accepted

## Context

DiceMaster has two runtime targets:

1. **Physical device** — a Raspberry Pi running ROS 2 Humble, with the `dicemaster_central` Python package installed in the ROS workspace. Students run their strategy by launching the ROS node.
2. **Web simulator** — a static web page running Python via Pyodide, backed by the `dice` package in this repository.

Educators write game logic once and want it to work on both targets. The primary workflow is:

1. Educator authors a `BaseStrategy` subclass, tests it in the web simulator during lesson planning.
2. The same file is copied (or `git clone`-d) onto the physical device and run without modification.
3. Students use the web simulator for iteration and take-home experimentation, then demo on the physical device.

Without an explicit parity policy the two APIs will diverge over time as the hardware package evolves independently of the web package, breaking games silently.

## Decision

The `dice` package (web) **must expose the same public API as `dicemaster_central` (hardware)**: identical module names, class names, method names, parameter names, and event semantics. Specifically:

- Module layout: `screen`, `motion`, `orientation`, `timer`, `assets`, `log`, `strategy.BaseStrategy`.
- Method signatures match exactly, including parameter order. For example, `screen.set_image(screen_id, path)` uses the same argument names on both targets.
- `BaseStrategy.__init__` accepts `game_name`, `config`, `assets_path` as positional/keyword arguments on both targets.
- `BaseStrategy` abstract methods are `start_strategy(self)` and `stop_strategy(self)` on both.
- Inbound event callbacks receive the same arguments: `on_shake(intensity: float)`, `on_change(top: int, bottom: int)`.

When the hardware package adds or changes an API, this package must be updated to match before the next release.

## Consequences

**Positive**

- Educators write one game file. No `if running_on_hardware: …` branches in student code.
- The web simulator is a faithful preview of hardware behaviour; surprises at demo time are reduced.
- The test suite for the `dice` package (`tests/`) also validates the API contract. If a refactor breaks the signature, tests catch it before the hardware team notices.
- New educators can learn the API from either the web docs or the hardware docs interchangeably.

**Negative / Trade-offs**

- The web package is a **follower**: it must react to every hardware API change. This introduces a maintenance obligation. The hardware team must notify the web team (or file an issue) when `dicemaster_central` changes its public surface.
- Some hardware capabilities have no meaningful web equivalent (e.g. direct GPIO access, low-level IMU readings). These are not part of the student-facing API on either platform, so the constraint applies only to the student API layer. Internal implementation differences are acceptable.
- The web implementation cannot extend the API with web-only conveniences (such as exposing the browser's `deviceorientation` DOM event directly) without first proposing a matching addition to the hardware package. This keeps the constraint symmetric.

## Alternatives Considered

**Separate web-only API**
Designing a web-first API optimised for browser idioms (Promises, async/await, DOM events) would be more natural for web developers. It was rejected because the target audience is students who already know the hardware API. Requiring them to learn a second vocabulary defeats the purpose of the simulator.

**Automatic shim layer generated from hardware package**
Generating the web stubs automatically from hardware source code or type stubs was considered. It would guarantee parity but adds tooling complexity (a code-generation step in CI) that is disproportionate to a small, stable API surface. A manual parity policy with tests is sufficient for now.
