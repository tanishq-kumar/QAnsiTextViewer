# Security Policy

## Supported versions

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |
| older   | :x:                |

Only the latest PyPI release receives security fixes.

## Reporting a vulnerability

Use GitHub's **private vulnerability reporting**
([Security → Report a vulnerability](https://github.com/tanishq-kumar/QAnsiTextViewer/security/advisories/new)).
Include:

- package version and environment (OS, Python, Qt binding),
- a minimal reproduction (log sample or snippet),
- impact you see (e.g. crash, hang, unsafe link handling).

Do not open a public issue. Expect an initial response within 7 days;
fixes ship as patch releases with a changelog entry crediting the reporter
unless anonymity is requested.

## Scope notes

Log content is treated as untrusted input by design (see the
["Untrusted logs" section in the docs](https://tanishq-kumar.github.io/QAnsiTextViewer/)). Resource-exhaustion via huge lines
or cursor jumps is rate-limited by `setMaximumBlocks()` /
`setMaxLineLength()` — bypasses of those limits are in scope.
