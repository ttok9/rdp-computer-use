# Roadmap

These are planned work items, not implemented features or delivery commitments.

## Next: earn a reproducible live demo

- Record a clean-VM Notepad run with OS, Python, model, display, and network setup.
- Publish raw attempt counts, failures, elapsed time, and model cost where available.
- Exercise cancel, session loss, stale frames, and reconnect behavior in a real lab.
- Establish Windows/Linux/macOS adapter compatibility through CI and lab evidence.

## Safety and verification

- Add a pre-action policy/approval interface with deny-by-default examples.
- Separate model confidence from independent application-state assertions.
- Add screenshot freshness checks, redaction controls, and structured failure categories.
- Evaluate certificate validation, credential handling, and malicious on-screen instructions.

## Developer experience

- Add more harmless, portable scenarios and a scenario evaluation harness.
- Improve Unicode, keyboard layout, IME, and screen-resize coverage.
- Prototype alternate drivers and policy verifiers without coupling them to the runner.
- Add an opt-in viewer/control plane only after authentication and authorization design.

## Contribution starting points

Small reproducible adapter tests, documentation fixes, and redacted compatibility
reports are welcome. Propose a design before adding new control surfaces or
dependencies. Do not label a feature implemented until code and tests exist.
