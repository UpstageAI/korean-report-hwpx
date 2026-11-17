# Contributing to korean-report-hwpx

Thank you for helping improve these Korean official-document (HWPX) tools. 기여해 주셔서 감사합니다. 이슈와 PR은 한국어·영어 모두 환영합니다.

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md). Report security problems privately as described in [SECURITY.md](SECURITY.md).

## Reporting a wrong output or format rule (서식·출력 오류 제보)

Open an issue with the "Wrong result or format rule" form and include:

- **Tool name** (e.g. `build_document`, `check_structure`)
- **Inputs** you passed: the structure JSON, `doc_type`, `ministry` (remove any personal or internal data)
- **Actual result** and **expected result**, with the basis: the official guideline or regulation (name, article or section, and its effective date or edition)
- **Version** (`pip show korean-report-hwpx`), OS, and the viewer you opened the file with (e.g. Hancom Office version)

Do not attach original agency documents; describe the format difference in numbers (font, size, spacing, margins) instead.

## Running tests (테스트 실행)

The same commands CI runs (`.github/workflows/test.yml`, Python 3.10–3.12):

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
python -m pip install ruff && ruff check . --select E9,F821
python -m pytest -q tests
```

Run the full suite locally before opening a pull request.

## Pull request rules

- **Cite the source for every format rule and number.** Give the regulation or guideline name, the article or section, and its 공포번호/시행일 or edition. Where a statute is amended, follow the amendment's effective-date rule (부칙).
- **Expected values in tests are worked out by hand from the source**, not copied from the tool's output, and include boundary cases (page limits, empty fields, longest allowed titles).
- **New or renamed tools must update the README tool tables and tool counts** (`README.md`, `README-EN.md`, `llms.txt`) so documentation and code stay consistent and CI passes.
- **Format data only.** Templates hold format values; do not add original HWP/HWPX files, images, phone numbers, or text taken from agency documents (`tests/test_public_tree.py` enforces this).
- **No secrets.** Never commit API keys (`LAW_OC` or `UPSTAGE_API_KEY`), tokens, or personal data, including in tests and fixtures.
- Docs-only changes do not need a version bump; maintainers handle releases and `CHANGELOG.md`.
- **Releases go through GitHub Actions only.** Maintainers publish with `gh workflow run publish-pypi.yml` (PyPI Trusted Publishing, no API token); the MCP Registry workflow runs after it. Do not upload from a local machine with an API token.

## Review

Every pull request runs the test workflow and an automated CodeSolar review. Address its comments or reply with the reason you disagree; a maintainer merges after both pass.

## Disclaimer (면책)

Generated documents are drafts. The tools do not invent facts, but the author is responsible for reviewing content and format before official use. Tax questions belong to the companion servers, whose results are not tax advice. See the [README](https://github.com/UpstageAI/korean-report-hwpx#readme).
