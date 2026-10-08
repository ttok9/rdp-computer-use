# A focused open-source launch

## Reference review, 2026-10-02

These are presentation references, not evidence that README design causes stars.
Counts are rounded GitHub page snapshots and will change. No code, branding,
screenshots, or promotional copy from these projects was copied.

| Repository | Approximate stars observed | Pattern worth adapting |
| --- | --- | --- |
| [Browser Use](https://github.com/browser-use/browser-use) | 116.9k | Short positioning; separate entry paths; runnable Python example and FAQ |
| [Cua](https://github.com/trycua/cua) | 27.7k | Choose-your-path navigation, visible demo, a concrete first result |
| [Microsoft UFO](https://github.com/microsoft/UFO) | 9.9k | User-oriented paths, architecture explanation, multilingual navigation |
| [Skyvern](https://github.com/Skyvern-AI/skyvern) | 23.1k | Demo next to quickstart, local setup, troubleshooting and examples |

Our interpretation: make the first successful experiment easy, explain the narrow
RDP-only use case, and provide evidence readers can reproduce. Large installed
communities, distribution, product quality, and maintenance matter too. No star
count or growth rate is promised.

## Positioning

**RDP Computer-Use: GUI automation for Windows desktops you cannot instrument.**

Lead with an existing RDP target where an automation agent, application API, or
usable shell is unavailable. Do not position the project as universally better
than APIs, browser automation, hosted VM platforms, or mature RPA suites.

The README now follows: problem → offline first result → choose a path → fit/non-fit
→ architecture → authorized live setup → extension contracts → evidence → contribution.
An actual scripted CLI result is shown instead of a fabricated live demo.

## Publication gates

1. Confirm code ownership and review credentials/history using the [release checklist](OPEN_SOURCE_CHECKLIST.md).
2. Create the repository, configure real metadata URLs, private vulnerability reporting, branch protection, and CI.
3. State the alpha status and link to the test report; add a passing CI badge after CI runs.
4. Use the hero as a social card only after rendering it to an accepted image format.
5. Publish release notes with exact test scope and checksums, not a broad “fully tested” claim.

Suggested About text:

> GUI-only Windows automation over RDP. Pluggable vision models, bounded execution, and inspectable results. No extra target-side agent.

Suggested topics: `computer-use`, `rdp`, `windows-automation`, `gui-testing`,
`vision-language-model`, `test-automation`, `python`.

## The first real demo: 60–90 seconds

- **0–10 s:** Show a clean, disposable Windows desktop and explain the RDP-only constraint.
- **10–20 s:** Show the public task and configuration names, with credentials hidden.
- **20–65 s:** Record the actual run continuously. Mark any sped-up playback clearly.
- **65–80 s:** Show the visible outcome and result JSON; distinguish model judgment from human inspection.
- **80–90 s:** State the alpha limits and link to reproducible setup.

Until this is recorded, retain the offline/demo label. Do not use the illustration
or scripted trace as evidence that a real Windows/model task succeeded.

## Minimum honest evaluation

Pick a small fixed task set and starting snapshots before running it. Record every
attempt. Keep two outcomes: model-reported status and independently checked result.
Report numerator/denominator, setup, model, elapsed time, costs if available, and
failure reasons. A model's own completion claim is not the evaluator.

Include control tests for cancel, frame loss, invalid model output, and timeouts.
Never publish sensitive desktop images or endpoint credentials with the results.

## Invite useful contributions

Start with three scoped issues: a clean-VM compatibility report, an independent
verifier example, and one reproduced keyboard/layout failure. Give acceptance
criteria and a local test command. Label issues only after they actually exist.

When announcing publicly, describe the niche and limitations, link to the demo,
and ask for one specific kind of feedback. Follow each community's posting rules;
avoid automated mass posting, manufactured engagement, or unmeasured claims.

## Launch copy

**English**

I built an MIT-licensed Python core for experimenting with GUI-only Windows
automation over RDP. The controller observes screenshots, asks a vision model
for one action, sends input, and checks the resulting screen. No additional agent
is installed on the target. There is an offline demo and deterministic regression
suite. I would especially
value clean-VM compatibility reports and independent-verifier contributions.

**한국어**

대상 PC에 자동화 에이전트를 설치하거나 CLI/API를 쓰기 어려운 환경을 위해
RDP 기반 GUI 자동화 코어를 만들었습니다. 화면 관찰 → 모델의 단일 행동 판단
→ 원격 입력 → 결과 확인을 반복합니다. MIT로 공개할 수 있도록 오프라인 데모,
회귀 테스트, 구조 문서를 준비했습니다. 격리된 테스트 VM의 호환성 결과와 독립 검증기 기여를
받아 개선하려 합니다.
