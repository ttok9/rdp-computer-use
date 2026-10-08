# Publishing checklist

Publish **only this standalone directory**, not its parent development workspace.
Start a new repository history after inspection; do not push private prototype
history. This document is a release gate, not a claim that publication occurred.

## Prepared locally

- [x] MIT license for project code and separate third-party notices.
- [x] English/Korean README, source-level architecture, static and interactive diagrams.
- [x] Placeholder configuration, offline demo, harmless example scenarios.
- [x] Deterministic core/adapter regression tests and CI configuration.
- [x] Contributor/security guidance, issue/PR templates, dependency-update configuration.
- [x] Allowlisted source-archive tooling and heuristic release-content checks.

## Owner checks before upload

- [ ] Confirm permission to publish employer/client-related work and all original contributions.
- [ ] Review third-party and transitive dependency licenses for the intended distribution.
- [ ] Rotate any credentials exposed in the private prototype; inspect all proposed files.
- [ ] Verify the release ZIP contains only intended public files and no old Git history.
- [ ] Run an independent secret scanner; inspect generated documents and images manually.
- [ ] Create a public repository and enable private vulnerability reporting.
- [ ] Set repository URLs in `pyproject.toml` after the real URL exists.
- [ ] Enable branch protection and allow CI to run; inspect every job result.
- [ ] Re-run clean-VM RDP smoke and a harmless model-guided scenario; record failures honestly.

An experimental alpha may be shared with outstanding live-validation gaps clearly
disclosed. Do not call it production-ready or fully E2E-tested until those gates pass.

## Build from this directory

```bash
python -m pip install -e '.[all,dev]'
python -m unittest discover -s tests -v
python tools/check_release.py
python -m build
python -m twine check dist/*
python tools/package_source.py --output ../rdp-computer-use-source.zip
```

The source ZIP is allowlisted, refuses overwrites, includes `.github` and docs,
and excludes `.git`, virtual environments, build outputs, credentials, and traces.
Wheel/sdist are separate Python-installation artifacts. Neither option vendors
third-party runtime dependencies.

## Repository presentation

Suggested description:

> GUI-only Windows automation over RDP. Observe, decide, act, and verify with pluggable vision-language models.

Suggested topics: `computer-use`, `rdp`, `windows-automation`, `gui-testing`,
`vision-language-model`, `python`, `test-automation`.

Use `docs/assets/hero.svg` in the README. For a social-preview upload, rasterize it
to PNG/JPEG first. Pin Quickstart, Architecture, and Roadmap links in the repository
description/discussions once their actual public URLs exist.

For the first release, label it `v0.2.0a2` and mark it pre-release. Summarize what is
implemented, exact tests run, and what remains unverified. Attach wheel/sdist and
source ZIP with SHA-256 checksums. Do not upload `.env` or real desktop captures.

## A credible demo is more useful than extra badges

After a real run succeeds, record a short clean-VM demo: problem → goal → visible
action → verification result → limits. Label any mock clearly. Publish a small
reproducible setup and real failures, not unmeasured productivity claims. Invite
specific contributions; do not promise stars or manufacture engagement.
