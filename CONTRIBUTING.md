# Contributing

Small reproducible improvements are welcome—especially adapter tests, independent
verification ideas, and clean-VM compatibility reports.

## Local checks

```bash
python -m pip install -e '.[all,dev]'
python -m unittest discover -s tests -v
python tools/verify.py --require-adapters
python -m build
python -m twine check dist/*
```

Use Python 3.11 or 3.12. For core-only changes, `pip install -e .` is enough;
optional-adapter tests skip when their dependencies are missing. The offline demo
must continue to work without a server, credentials, GPU, or network.

## Pull requests

- Explain the problem, behavior change, and how you tested it.
- Add deterministic regression tests; never require a private target in default CI.
- For runner changes, cover cancellation, repetition, deadlines, and result status.
- For adapter changes, state which checks are fakes and which exercised a real server.
- Keep dependencies optional and preserve protocol boundaries.
- Never include credentials, real screenshots, personal data, internal addresses, or proprietary scenarios.
- Do not replace third-party notices with the project license.
- Contributions must be yours to publish and compatible with this project's MIT license.

Use synthetic frames for tests. For live reports, describe OS, Python, model,
display size, and reproduction steps; share redacted evidence only. Read
[SECURITY.md](SECURITY.md) before filing a security-related issue.

Be respectful, assume good intent, and critique code rather than people.
