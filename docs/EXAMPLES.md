# Examples: start small, inspect the result

The live recipes below are **scenario templates** to adapt to your Windows environment.
Run only against a disposable VM. Do not include private data in tasks or screenshots.

| Recipe | Purpose | Expected visible evidence |
| --- | --- | --- |
| [Offline demo result](../examples/demo-result.json) | Reproduce the core loop without network/SDKs | Scripted JSON success, two steps |
| [Notepad JSON](../examples/scenarios/notepad.json) / [Markdown](../examples/scenarios/notepad.md) | Simple cross-window navigation and text entry | Public demo text in an editor |
| [Calculator JSON](../examples/scenarios/calculator.json) | A small GUI task with a checkable expected value | Calculator displays 42 |

## Reproduce the offline result

```bash
rdp-cua demo
python tools/render_demo.py
```

The second command regenerates the public demo JSON and static terminal card
from the real scripted runner output. It does not control or depict a Windows VM.

## Live lab recipe

```bash
rdp-cua doctor --require-adapters
rdp-cua scenario-check examples/scenarios/calculator.json
rdp-cua smoke-rdp --env-file .env
rdp-cua run --env-file .env --scenario examples/scenarios/calculator.json --output result-calculator.json
```

Inspect the desktop yourself. A model's `succeeded` status is not independent proof
that Calculator or a more complex validation procedure behaved correctly. The
scenario steps are prompt guidance, not forced execution. Do not start a second
runner or manually interfere with the same session while evaluating a run.

## Turn a workflow into a useful public example

Define a harmless goal, explicit starting state, and a visible success condition.
Report all attempts, including failures. Record controller OS/Python, target OS,
display dimensions, model identifier, wall-clock duration, and final state. Avoid
claiming speed, savings, or accuracy from a single hand-picked run. See the
[launch/evaluation plan](LAUNCH_PLAYBOOK.md) for a reproducible demo checklist.
