# Setup and configuration

## 1. Prove the local installation first

Use Python 3.11 or 3.12 on the controller. Newer Python versions may lack binary
wheels for the pinned RDP dependency and require a native build toolchain.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
rdp-cua doctor
rdp-cua demo
```

PowerShell activation: `.venv\Scripts\Activate.ps1`. You can also invoke
`.venv\Scripts\python.exe -m rdp_cua demo` without changing execution policy.
The base demo is scripted and offline. This repository is not yet a published
PyPI release; install from the checked-out directory, not by guessing a PyPI name.

## 2. Prepare an authorized Windows lab

- Use a disposable VM with a supported RDP server and a dedicated low-privilege account.
- Make RDP reachable from the controller over a private network/VPN. Do not expose it to the public Internet.
- Prepare a single interactive desktop with Notepad and no sensitive documents.
- Keep a normal RDP client available for recovery; concurrent human/agent input can interfere.
- Obtain an image-capable OpenAI-compatible Chat Completions endpoint. Text-only models do not work.

Install `python -m pip install -e '.[all]'`, then run
`rdp-cua doctor --require-adapters`. `aardwolf==0.2.13` is intentionally pinned;
this is not a claim that it is the latest release or free of vulnerabilities.

## 3. Set configuration without executing a shell file

Copy `.env.example` to `.env` and edit placeholders. The CLI loads it only when
`--env-file .env` is provided. Values are literal single-line `KEY=value` pairs:
whole-value quotes are removed, but variable expansion, command substitution,
inline comments, and multiline values are not supported. Existing environment
variables take precedence. Use your secret manager in preference to a file when available.

| Variable | Default | Meaning |
| --- | --- | --- |
| `RDP_HOST` | required | Hostname or IP, without scheme or path |
| `RDP_PORT` | `3389` | RDP TCP port |
| `RDP_USERNAME`, `RDP_PASSWORD` | required | Dedicated authorized test account |
| `RDP_DOMAIN` | empty | Domain, when applicable |
| `RDP_AUTH` | `ntlm` | NLA/HYBRID; `tls` is an explicit legacy alternative |
| `RDP_WIDTH`, `RDP_HEIGHT` | `1920`, `1080` | Requested display size; input mapping uses actual frame size |
| `CUA_VISION_BASE_URL` | `http://127.0.0.1:8000/v1` | Compatible API root |
| `CUA_VISION_MODEL` | required for `run` | Image-capable model identifier |
| `CUA_VISION_API_KEY` | `not-required` | Endpoint credential; placeholder only for endpoints that allow it |
| `CUA_MAX_STEPS` | `30` | Maximum decision iterations |
| `CUA_ACTION_TIMEOUT_SECONDS` | `30` | Per-action deadline |
| `CUA_REPEAT_ACTION_LIMIT` | `2` | Consecutive identical actions allowed |
| `CUA_OBSERVATION_TIMEOUT_SECONDS` | `15` | Per-capture deadline |
| `CUA_MODEL_TIMEOUT_SECONDS` | `60` | Per-decision/per-verification deadline |
| `CUA_SETTLE_SECONDS` | `0.3` | Delay before post-action capture |

Do not disable NLA on a real system just to make a demo work. `tls` mode is for
an already-authorized isolated legacy test configuration. The adapter does not
expose a verified certificate-pinning policy; network isolation remains essential.

## 4. Receive a frame, then run a harmless goal

```bash
rdp-cua smoke-rdp --env-file .env --frame-timeout 30
rdp-cua run --env-file .env --goal "Open Notepad and type Hello" --output result.json
```

The smoke test logs in, receives a frame, and disconnects. It sends no input and
does not save the screenshot. Login can still change session state.
`--frame-timeout` is applied separately to connection and frame arrival, not as
a single total wall-clock limit. Disconnect has its own bound.

`run` controls the desktop. Use an unused output path whose parent directory exists.
Results include `status`, `reason`, `step_count`, and completed step records.
An action interrupted before verification is not included as a completed record;
the result is not a complete forensic input log.

Exit codes: `0` success, `1` unsuccessful task/required-adapter check, `2`
configuration or execution error, `130` keyboard interruption. Ctrl+C cancels the
CLI task and attempts cleanup; it cannot undo remote input.

## Scenarios

```bash
rdp-cua scenario-check examples/scenarios/notepad.md
rdp-cua run --env-file .env --scenario examples/scenarios/notepad.md
```

JSON and Markdown describe the same guidance. Expected conditions become part of
the prompt; the model can skip or misjudge them. Use an independent verifier for
hard assertions. See [architecture](ARCHITECTURE.md) for the extension contracts.

## Troubleshooting

| Symptom | First checks |
| --- | --- |
| Optional adapter import fails | Correct venv, Python 3.11/3.12, install `.[all]`, run `python -m pip check` |
| RDP timeout | VPN/route, firewall, enabled RDP, port; verify with a normal RDP client |
| Authentication fails | Username/domain, account policy, NLA support; do not publish credential logs |
| No frame | Session readiness and display settings; increase smoke timeout for a slow lab |
| Decision/verification error | Endpoint image support, model ID, strict JSON booleans and one-action schema |
| Wrong click | Correct target display, no concurrent operator, inspect actual frame size |
| Repeated-action stop | Investigate a stale screen or ineffective action before increasing limits |
| Typing/shortcut mismatch | Keyboard layout, IME, unsupported key; use the documented action subset |

Top-level errors intentionally report type/stage rather than raw SDK exceptions.
Upstream dependency logging can still reveal details. Inspect diagnostics locally
and redact them before creating an issue.
