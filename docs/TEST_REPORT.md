# Validation report — 0.2.0a2

Date: 2026-10-02. Scope: the public RDP/CUA core, not Teams or the private web UI.

## Local evidence

Deterministic tests exercise the runner, strict input contracts, scenarios,
configuration, RDP adapter behavior with fake connections, and vision parsing
with fake responses. Optional dependencies are installed for the Python 3.11
run. These are not real Windows or live-model task-success measurements.

| Check | Observed result |
| --- | --- |
| Python 3.11.12, macOS ARM, optional adapters installed | 78 tests passed, 0 skipped |
| Python 3.12.14, macOS ARM, core only | 78 discovered, 64 passed, 14 optional-dependency tests skipped |
| `aardwolf==0.2.13`, `openai==2.54.0` imports | Passed in the 3.11 environment |
| `pip check` | No broken requirements in adapter and clean core environments |
| `doctor --require-adapters` | Passed with no adapter import errors |
| Wheel installed in a fresh Python 3.12 venv | Offline demo passed; optional SDKs absent as expected |
| Wheel installed with the 3.11 adapter environment | Version, demo, and Markdown scenario check passed |
| Source distribution extracted outside the workspace | Tests and wheel rebuild checked as part of release packaging |
| Python compile check | Passed for source, tests, and release tools |
| Release-content and local Markdown-link checks | Passed for the allowlisted public tree |
| Wheel/sdist archive inspection | Licenses included; no `.env`, private history, caches, or local user paths found by the checks |
| Real SDK request serialization | Image payload, API path, decision/verification parsing and HTTP 401 propagation passed through an in-process mock HTTP transport; no live service |
| Source ZIP reproducibility | Two builds have identical SHA-256; every member exactly matches the public allowlist and file bytes |
| Markdown/HTML links | Relative links, heading anchors, and embedded README image paths checked against release membership |
| GitHub workflow/issue YAML | Four files parse successfully; this does not prove a GitHub run passed |

Builds used the declared `setuptools.build_meta` backend directly with setuptools
84.0.0 and wheel 0.48.0 because the isolated environment could not download the
`build`/`twine` frontends. Runtime extras were installed offline from already-cached
package wheels. This is not evidence of a fresh online dependency resolution.
`twine check`, public GitHub Actions, and the Linux/Windows CI matrix have **not**
run locally. The workflow configures these checks for the eventual repository.

Content scans are heuristic and do not constitute a security or license audit.

Machine-readable, Python-source-bound receipts:
[Python 3.11](verification/python311.json) · [Python 3.12](verification/python312.json).
These local receipts are reproducibility records, not signed attestations.

Reproduce locally:

```bash
python tools/verify.py --require-adapters
python tools/verify_artifacts.py dist/rdp_computer_use-0.2.0a2-py3-none-any.whl dist/rdp_computer_use-0.2.0a2.tar.gz
```

Omit `--require-adapters` for the dependency-free core environment. The verification
tool performs no live RDP connection or model request. Full branch coverage,
all-platform compatibility, and vulnerability-free dependencies are not claimed.

## Regressions covered

- String booleans cannot accidentally become success through Python truthiness.
- Invalid action fields, non-integer coordinates, and unbounded/non-finite limits are rejected.
- Cancellation during inference cannot lead to a subsequent input action.
- Cooperative in-flight action work is cancelled and cleaned up.
- Failed verification does not reset the identical-action limit.
- Capture and inference deadlines return stage-specific failures.
- Structured result errors do not echo sensitive third-party exception messages.
- Keyboard validation happens before modifier presses; cleanup is attempted on failure.
- Wheel actions use mouse events, and coordinate mapping uses actual frame dimensions.
- Verification prompts include action parameters, not merely the action type.
- Literal env files do not execute commands or overwrite existing environment variables.
- Scenario parsing, packaging hygiene, and documentation links are checked locally.
- Cancel followed by pause cannot leave the task stuck behind a closed resume gate.
- Duplicate JSON keys and nonstandard constants such as `NaN` are rejected.
- Action prompts use the same field restrictions as the parser.
- NLA/legacy settings, connect failure/cancellation cleanup, no-input smoke behavior, capture timeout, and result-file cleanup are exercised with fake connections.
- Nested environment/trace files are excluded from source archives.

## Live-environment gate: NOT PASSED

A previous 2026-09-03 smoke attempt could not establish TCP connectivity to the
configured RDP target before timeout. Authentication, remote frame delivery, and
model-guided GUI completion were therefore not verified. That older attempt is
not a pass for this release.

On 2026-10-02, a fresh **TCP-only** probe of the existing last-used target was
attempted. The execution environment rejected the socket operation with
`PermissionError` (`errno=1`). This is an environment limitation, not a measured
target failure. No authentication, frame capture, model call, or input event was
performed by that probe. Target addresses and credentials are not published.

From an authorized disposable Windows lab, run:

```bash
rdp-cua smoke-rdp --env-file .env
rdp-cua run --env-file .env --scenario examples/scenarios/notepad.json --output live-result.json
```

Record Windows/Python/model versions, display setup, attempt count, raw outcome,
and elapsed time. Exercise cancellation, timeout, and session loss separately.
Redact artifacts before sharing. Model-reported completion is not independent
proof that a validation procedure passed.

## Diagram evidence

Both Archify artifacts pass 9/9 showcase checks. Automated browser inspection
failed due to Chrome process startup; static README previews were visually
inspected separately. See [the detailed receipts](DIAGRAM_VALIDATION.md).
