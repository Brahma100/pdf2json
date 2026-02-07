# Publishing to PyPI (Trusted Publishing)

This project is configured to publish with GitHub Actions + PyPI Trusted Publishing.

## Repository values

- GitHub owner: `Brahma100`
- GitHub repo: `pdf2json`
- Workflow file: `publish-pypi.yml`
- Workflow path: `.github/workflows/publish-pypi.yml`
- GitHub environment: `pypi`

## 1) One-time setup

### PyPI
1. Create/sign in to your PyPI account.
2. Go to **Publishing** -> **Add a new pending publisher**.
3. Set:
   - Owner: `Brahma100`
   - Repository: `pdf2json`
   - Workflow name: `publish-pypi.yml`
   - Environment name: `pypi`

Note: pending publisher does **not** reserve package name until first successful publish.

### GitHub
1. Repo Settings -> Environments -> New environment: `pypi`
2. No secrets required for Trusted Publishing (OIDC).

## 2) Release process

1. Update `version` in `pyproject.toml` (example: `0.1.1`).
2. Commit and push.
3. Create and push tag:
   - `git tag v0.1.1`
   - `git push origin v0.1.1`
4. Publish a GitHub Release for that tag.
5. GitHub Action `Publish to PyPI` runs and uploads package.

## 3) Local preflight checks

```powershell
python -m pip install --upgrade pip build twine
python -m build
python -m twine check dist/*
python -m pytest tests/test_golden_regression.py -q
```

## 4) Verify install from PyPI

```powershell
py -3.10 -m venv .venv-test
.\.venv-test\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install invoice-ocr
invoice-ocr sample_invoice.pdf -o out.json
```
