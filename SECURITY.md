# Security policy

This alpha can send real mouse and keyboard input. Use only authorized, disposable
test desktops with a dedicated least-privileged account. Do not use it to approve
payments, administer production, handle confidential desktops, or make irreversible
changes without an external human-controlled gate.

## Reporting vulnerabilities

Use **Security → Report a vulnerability** on the repository when private reporting
is enabled. If it is unavailable, ask the maintainer for a private contact without
including exploit details, credentials, or affected target addresses in a public
issue. The publishing checklist requires enabling that private channel first.
Only the latest alpha revision receives fixes; no response-time SLA is promised.

## Trust boundaries

- Restrict RDP and the model service to a private network/VPN. Keep remote systems patched.
- Use authenticated HTTPS for non-loopback model endpoints. The endpoint receives desktop images and task/action content.
- The adapter requests NLA by default, but does not expose an independently verified certificate-pinning policy. Do not interpret encryption or NLA alone as a complete transport-security audit.
- A desktop can contain malicious instructions. The system prompt says to ignore them; that is a mitigation, not a reliable prompt-injection defense.
- Action schemas, repetition limits, and timeouts are correctness guards, not authorization or destructive-action policy.
- Do not expose a web/API control plane without separate authentication, authorization, audit, and request-protection design.

## Secrets and records

Keep `.env`, screenshots, runtime results, and traces out of commits. Environment
values are literal and never shell-executed. Public examples use documentation
addresses and placeholder credentials. Structured results avoid raw SDK exception
messages and omit typed action parameters, but model reasons and upstream library
logs can still reveal sensitive content. No automatic comprehensive redaction exists.

Rotate credentials exposed in the original development workspace before publishing
anything derived from it. A clean release folder does not sanitize old Git history.
Repository scans are heuristics, not proof that all secrets have been removed.

## Operational limits

Cancellation is cooperative and cannot undo input. Held keys are released on a
best-effort basis; network loss can prevent cleanup. There is no automatic
reconnect, full input-event audit trail, rollback, or independent success proof.
Human approval before high-impact actions is not implemented in this core.
