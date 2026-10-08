# Changelog

## 0.2.0a2 — 2026-10-02

- Reworked the README around the RDP-only use case, first result, user paths, FAQ, and concrete contribution requests.
- Added an actual scripted-demo result/card, Calculator recipe, and source-linked open-source launch guide.
- Added reproducible verification tooling and deterministic source ZIPs with exact-content checks.
- Fixed cancel-then-pause deadlock; reject duplicate JSON keys and nonstandard JSON constants.
- Aligned model action instructions with accepted action fields and supported keys.
- Expanded tests with real SDK HTTP serialization through a mock transport, error propagation, release links/anchors, and artifact identity checks.
- Hardened archive selection against nested environment files and runtime trace directories.

## 0.2.0a1 — 2026-10-02

### Added

- Literal `--env-file` loading, scenario execution guidance, `scenario-check`, and non-overwriting JSON output.
- Observation/model deadlines, post-action settle interval, stronger required-adapter diagnostics.
- NLA/NTLM configuration with an explicit legacy TLS option.
- English/Korean README, Archify architecture and sequence diagrams, security and contributor guidance.
- Release hygiene checks, source ZIP tooling, issue templates, and expanded CI configuration.

### Fixed

- Reject string booleans, invalid coordinates, unknown action fields, and non-finite limits.
- Cancel in-flight cooperative work and check cancellation before sending the next action.
- Preserve repetition protection after failed verification.
- Use actual desktop frame dimensions; send wheel events instead of arrow keys.
- Validate shortcuts before pressing modifiers and release held keys on failure.
- Include action parameters in verification prompts; close model and RDP clients on CLI exit.
- Avoid reflecting raw third-party exceptions in structured task results.

### Known limits

No destructive-action approval, independent success proof, automatic reconnect,
or multi-monitor support. Public CI has not
run yet. This remains an alpha release candidate.

## 0.1.0 — 2026-09-03

Initial sanitized core: pluggable ports/adapters, RDP/VLM integration skeleton,
scripted demo, scenario parsing, and 18 deterministic tests. Prior real RDP smoke
attempt timed out before a connection was established.
