# Your first contribution

Start with one reproducible observation. No contribution requires posting private
desktop content, credentials, or an employer's internal workflow. These are
suggested tasks, not assigned issues or promises that a feature already exists.

## 1. Check the released demo instructions

**Needs:** Python 3.11 or 3.12; no Windows VM, RDP account, or model key.

Follow the three commands in the [README](../README.md#try-the-loop-without-a-server)
from a clean directory. Record your OS and Python version, the command that failed
or confused you, and the smallest corrected instruction. A useful documentation
PR leaves both English and Korean instructions consistent and preserves the
scripted/offline label. Expected demo output: `status: "succeeded"`, two steps.

## 2. Report one authorized Windows smoke test

**Needs:** your disposable Windows VM and a permitted private RDP connection.

Follow the [setup guide](QUICKSTART.md). Run `rdp-cua smoke-rdp --env-file .env`
before attempting a model task. Report Windows/controller OS, Python and package
versions, display size, keyboard layout, whether a frame arrived, and the result
of disconnecting. A failed attempt is useful evidence too. Redact hostnames,
addresses, account identifiers, and desktop content before posting.

A smoke pass is not a model-guided task pass. If you later run Notepad, state the
goal, model, attempt count, elapsed time, and what a human independently observed.

## 3. Add one keyboard or input regression

**Needs:** Python and optional adapter dependencies; a real RDP session is not
required for a fake-connection regression test.

Read [the adapter](../src/rdp_cua/adapters/aardwolf_driver.py) and
[adapter tests](../tests/test_optional_adapters.py). Describe a concrete input
case, then add a synthetic test that fails for the bug and passes with its fix.
Check cleanup and bounded execution. Keep the change focused; discuss a new
dependency or public API before implementing it.

## Share what you found

- [Report a reproducible problem](https://github.com/ttok9/rdp-computer-use/issues/new?template=bug_report.yml).
- [Propose a use case or design](https://github.com/ttok9/rdp-computer-use/issues/new?template=feature_request.yml).
- Follow the [contributor guide](../CONTRIBUTING.md) for validation and PR scope.

한국어로 재현 과정과 사용 사례를 작성해도 좋습니다. 실제 환경에서 확인한 사실과
아직 확인하지 못한 부분을 나눠 적어주세요.
