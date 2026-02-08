# Definition of Done (DOD) Checklist - TITAN-OMNI

## 1. Supply Chain Hardening
- [x] `requirements.in` reflects current dependencies.
- [x] `requirements.txt` generated via `pip-compile --generate-hashes`.
- [x] No `pip install` commands exist without `--require-hashes`.
- [x] Local installation verifies successfully.

### Approved Exceptions
> [!WARNING]
> - **Package**: `pandas-ta==0.4.71b0`
> - **Reason**: No stable release available on PyPI.
> - **Mitigation**: SHA256 pinned in `requirements.txt`. Monitor for stable release.

## 2. CI/CD Pipeline
- [ ] Workflow yaml syntax validated.
- [ ] Deterministic environment (locked python version).
- [ ] Secrets injected via environment variables.
- [ ] Artifact upload configured for logs.
- [ ] "Fail-Closed" behavior verified (pipeline fails on error).

## 3. Code Integrity
- [ ] No hardcoded credentials in source code.
- [ ] `.gitignore` excludes sensitive files (`.env`, `*.log`).
- [ ] `main.py` handles signals (SIGTERM) gracefully.
- [ ] Idempotency logic (`cycle_id`) implemented and tested.

## 4. Documentation
- [ ] `MASTER_ARCHITECTURE.md` updated.
- [ ] `MASTER_DEPLOYMENT.md` updated.
- [ ] `MASTER_DATABASE.md` updated.
- [ ] `MASTER_OPERATIONS.md` updated.

## 5. Security
- [ ] No secrets in logs (`blackbox.log`).
- [ ] Database credentials isolated.
- [ ] Least privilege access for API keys.
