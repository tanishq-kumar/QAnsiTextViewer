default:
    @just --list

test:
    uv run pytest

test-no-cov:
    uv run pytest -p no:cacheprovider --no-cov -q

demo:
    uv run python demo.py

run:
    uv run python main.py

lint:
    uv run ruff check ansi_text_viewer tests demo.py main.py

audit:
    uv run pip-audit

api-snapshot:
    uv run python tests/test_api_surface.py

typecheck:
    uv run mypy ansi_text_viewer
    uv run ty check ansi_text_viewer

format:
    uv run ruff format ansi_text_viewer tests demo.py main.py

docs:
    uv run mkdocs serve

docs-build:
    uv run mkdocs build

hooks:
    git config core.hooksPath .githooks

cz *args="--help":
    uv run cz {{args}}

changelog:
    uv run cz changelog --dry-run

changelog-cliff:
    git-cliff --unreleased

bump *args="--dry-run":
    uv run cz bump {{args}} && uv lock
