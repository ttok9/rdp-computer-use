# Architecture

![Architecture](assets/architecture.png)

[Interactive architecture](visualizations/release.architecture.html) ·
[Interactive sequence](visualizations/control-loop.sequence.html) ·
[Diagram validation receipts](DIAGRAM_VALIDATION.md)

## Goal and boundaries

Keep the Windows target agentless: standard RDP frames and input events cross
the target boundary. Python orchestration and model reasoning run elsewhere.
This is a public core extracted from a larger prototype, not a repackaging of
its private integrations. Teams and the web control plane are not included.

```text
src/rdp_cua/
├── cli.py                 # doctor, demo, smoke-rdp, run, scenario-check
├── config.py              # environment/literal env-file configuration
├── models.py              # validated actions, observations, decisions, results
├── coordinates.py         # normalized 0–1000 → frame pixel coordinates
├── protocols.py           # DesktopDriver / DecisionEngine / Verifier
├── runner.py              # bounded, cooperative observe–act–verify loop
├── scenario.py            # JSON/Markdown → model guidance
└── adapters/
    ├── aardwolf_driver.py # upstream RDP transport integration
    └── openai_vision.py   # compatible image/JSON Chat Completions client
```

## One iteration

1. `DesktopDriver.capture()` returns a PNG `Observation`.
2. `DecisionEngine.decide()` returns either completion or one validated `Action`.
3. The runner checks cancellation and the consecutive-action fingerprint limit.
4. `DesktopDriver.execute()` transmits the requested input.
5. After a settle delay, another capture is passed to `Verifier.verify()`.
6. A completed `StepRecord` is appended; the loop continues or returns a `TaskResult`.

The built-in engine implements both decision and verification. Custom integrations
can use independent implementations. The verifier receives the post-action frame,
goal, action parameters, and prior history; it does not perform a pixel-diff of
before/after images. The RDP adapter reads the latest buffered frame, so freshness
is not guaranteed merely by a second capture.

## Termination and control

| Condition | Result |
| --- | --- |
| Decision says completed | `succeeded` (model judgment) |
| Verifier says goal complete and action succeeded | `succeeded` |
| Verifier says goal complete but action failed | `failed` |
| Too many consecutive identical actions | `failed` |
| Stage timeout or adapter exception | `failed`, stage/type only |
| `TaskControl.cancel()` | `cancelled` after cooperative cleanup |
| Decision budget exhausted | `max_steps` |

A negative verification does not reset the repetition guard. Different actions
can still cycle until the step budget is exhausted. Model-declared completion
can occur without a new action and is not an independently certified success.

`TaskControl` belongs to the same asyncio event loop as its runner. Pause takes
effect at stage boundaries. Cancellation races each operation and cancels its
child task; adapters must cooperate with asyncio cancellation. Blocking synchronous
code or an adapter swallowing cancellation can exceed deadlines. Inputs already
sent cannot be rolled back. Cleanup and interrupted actions may not appear in
the completed-step history.

One runner owns one task; do not concurrently control the same desktop from two
runners. The CLI owns connection and model-client cleanup. Python callers own
those resources themselves.

## Adapter contracts

The base package imports no external RDP/model SDK. Protocols are structural:
implement async `capture`/`execute`, `decide`, or `verify` with the typed models.
Return correctly validated models; do not return arbitrary dictionaries from a
custom decision engine. The built-in model adapter performs JSON parsing.

RDP actions use negotiated frame dimensions. The supported key subset includes
letter keys, Ctrl/Shift/Alt/Win modifiers, Enter/Tab/Escape/Backspace/Space/Delete,
arrows, Home/End/PageUp/PageDown. Digits, function keys, IME and non-BMP Unicode
are not guaranteed by this minimal adapter. Wheel direction uses signed rotation
through the upstream wheel flag path; remote behavior still requires a live test.

## Data and trust

- Credentials stay in configuration/transport clients, not structured results.
- Screenshots, goal, action details, and history cross to the chosen model endpoint.
- Desktop content and model responses are untrusted. Shape validation does not judge intent.
- Result JSON omits raw screenshots and action parameters, but free-form model text can contain sensitive data.
- No human approval gate, remote action allowlist, or tamper-proof audit trail is implemented.

See [SECURITY.md](../SECURITY.md) before adding real targets.
