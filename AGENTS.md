# Notes for agents

- Package lives in `pdfdocument/`; `setup.py` (setuptools, depends on `reportlab`).
- No test suite. Verify changes by generating a PDF in a scratch dir, e.g.
  `uv run --no-project --with reportlab --with . python script.py`, then
  `pdftotext -layout out.pdf -`.
- User-facing changes get an entry under "Next version" in `CHANGELOG.rst`.
- README is reStructuredText; validate with docutils before committing.

## Issue triage (2026-10-25)

- #8 (missing reportlab dependency): already fixed in v4.0 (`install_requires`).
- #9 (speed comparison with PDFlib etc.): not planned.
- #11 (more examples): addressed by README "Examples" section.

## Commits

- Commit feature by feature, minimal commit messages, no attribution lines.
