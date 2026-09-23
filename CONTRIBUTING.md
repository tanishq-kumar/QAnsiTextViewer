# Contributing

## Setup

```bash
uv sync --group dev
just test
```

Requires Python `>=3.11`. GUI tests run headless (`QT_QPA_PLATFORM=offscreen`
is set by CI; export it locally if you have no display).

## Workflow

- Branch from `develop`; `main` is PR-only with required checks.
- Commits follow [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`, `ci:`, `test:`, `chore:` …) — releases and the
  changelog are generated from them, so `feat:`/`fix:` wording shows up publicly.
- Before pushing: `just test`, `just lint`, `just typecheck`.

## PR gate

Every PR runs `static` (ruff, ty, audit, strict docs build) first;
the OS × Python matrix (12 legs) only runs after it passes, and merging
requires all of them green.

## API changes

`AnsiTextViewer`'s public surface is pinned by `tests/api_surface.txt`.
If your change intentionally alters it, run `just api-snapshot` and commit
the updated baseline in the same PR.

## Security

Report vulnerabilities privately — see [SECURITY.md](SECURITY.md).
Never open a public issue for a suspected security bug.
