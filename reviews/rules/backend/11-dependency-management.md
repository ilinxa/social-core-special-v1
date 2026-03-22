# 11 — Dependency Management Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 11.1 Dependency File Structure

| ID | Rule | Verdict |
|----|------|---------|
| 11.1.1 | WARN if no pyproject.toml and only requirements/*.txt — pyproject.toml is modern best practice | PASS/WARN |
| 11.1.2 | PASS if requirements/ directory has clear split (base, local/dev, production) | PASS |
| 11.1.3 | FAIL if multiple conflicting dependency systems coexist without hierarchy | PASS/FAIL |
| 11.1.4 | WARN if pyproject.toml not used as central config — tool configs scattered across files | PASS/WARN |
| 11.1.5 | FAIL if dependency files are in .gitignore | PASS/FAIL |
| 11.1.6 | WARN if no lockfile exists for transitive dependencies | PASS/WARN |
| 11.1.7 | WARN if lockfile not committed to version control | PASS/WARN |
| 11.1.8 | INFO if pip-tools/poetry not used — manual requirements.txt is acceptable if well-maintained | PASS/INFO |
| 11.1.9 | PASS if dependency files have comments grouping related packages | PASS |
| 11.1.10 | INFO if no CONTRIBUTING.md with dependency addition process | PASS/INFO |

## 11.2 Version Pinning

| ID | Rule | Verdict |
|----|------|---------|
| 11.2.1 | FAIL if any direct dependency in production lacks exact version pin (==) | PASS/FAIL |
| 11.2.2 | WARN if transitive dependencies not pinned via lockfile | PASS/WARN |
| 11.2.3 | FAIL if >=, ~=, or ^ used in production requirements | PASS/FAIL |
| 11.2.4 | PASS if dev dependencies also pinned to exact versions | PASS |
| 11.2.5 | WARN if Docker base image uses mutable tag without digest | PASS/WARN |
| 11.2.6 | INFO if pyproject.toml not used — N/A for requirements.txt approach | PASS/INFO |
| 11.2.7 | INFO if pin rationale not documented — acceptable if versions are current | PASS/INFO |
| 11.2.8 | INFO if no regular review process documented | PASS/INFO |
| 11.2.9 | WARN if Python version not pinned (.python-version or requires-python) | PASS/WARN |
| 11.2.10 | PASS if Python version in Dockerfile matches development/CI | PASS |

## 11.3 Dependency Separation

| ID | Rule | Verdict |
|----|------|---------|
| 11.3.1 | PASS if production requirements contain only runtime dependencies | PASS |
| 11.3.2 | PASS if dev/local requirements include tooling | PASS |
| 11.3.3 | INFO if test deps not separated from dev — acceptable if combined as local.txt | PASS/INFO |
| 11.3.4 | FAIL if pytest/coverage in production requirements | PASS/FAIL |
| 11.3.5 | FAIL if debug tools in production requirements | PASS/FAIL |
| 11.3.6 | PASS if Dockerfile installs only production dependencies | PASS |
| 11.3.7 | PASS if test dependencies available in test/CI context | PASS |
| 11.3.8 | INFO if optional deps not labeled — acceptable for small dependency sets | PASS/INFO |
| 11.3.9 | WARN if psycopg2-binary vs psycopg2 choice not documented | PASS/WARN |
| 11.3.10 | WARN if psycopg2-binary used in production — should use compiled psycopg2 | PASS/WARN |

## 11.4 Security Vulnerability Scanning

| ID | Rule | Verdict |
|----|------|---------|
| 11.4.1 | WARN if pip-audit not in CI | PASS/WARN |
| 11.4.2 | INFO if safety not used as secondary scanner | PASS/INFO |
| 11.4.3 | INFO if no CVE suppression documentation | PASS/INFO |
| 11.4.4 | INFO if no quarterly review process | PASS/INFO |
| 11.4.5 | WARN if no Dependabot/Snyk/Renovate configured | PASS/WARN |
| 11.4.6 | INFO if no alert routing configured | PASS/INFO |
| 11.4.7 | INFO if no patch SLA defined | PASS/INFO |
| 11.4.8 | WARN if Docker images not scanned | PASS/WARN |
| 11.4.9 | WARN if only direct deps scanned, not transitive | PASS/WARN |
| 11.4.10 | INFO if supply chain trust not formally assessed | PASS/INFO |

## 11.5 Dependency Updates

| ID | Rule | Verdict |
|----|------|---------|
| 11.5.1 | WARN if no regular update cadence defined | PASS/WARN |
| 11.5.2 | WARN if no Dependabot/Renovate configured | PASS/WARN |
| 11.5.3 | INFO if auto-merge not configured — manual review acceptable | PASS/INFO |
| 11.5.4 | PASS if major updates go through deliberate review | PASS |
| 11.5.5 | PASS if Django version is recent/LTS | PASS |
| 11.5.6 | INFO if django-upgrade not used — manual upgrades acceptable | PASS/INFO |
| 11.5.7 | PASS if DRF version compatible with Django version | PASS |
| 11.5.8 | INFO if no batching strategy — acceptable for small team | PASS/INFO |
| 11.5.9 | INFO if changelogs not formally reviewed — acceptable for patch updates | PASS/INFO |
| 11.5.10 | INFO if no breaking change detection — tests serve this purpose | PASS/INFO |

## 11.6 Unused Dependency Detection

| ID | Rule | Verdict |
|----|------|---------|
| 11.6.1 | WARN if no unused dependency detection tool configured | PASS/WARN |
| 11.6.2 | WARN if obviously unused packages remain in requirements | PASS/WARN |
| 11.6.3 | INFO if single-use deps not evaluated | PASS/INFO |
| 11.6.4 | PASS if no dynamic importlib usage hiding real dependencies | PASS |
| 11.6.5 | INFO if script-only deps not labeled | PASS/INFO |
| 11.6.6 | PASS if no phantom transitive dependencies relied upon directly | PASS |
| 11.6.7 | INFO if no cleanup process for removed deps | PASS/INFO |
| 11.6.8 | PASS if no vendored library copies alongside requirements | PASS |

## 11.7 Package Trust & Vetting

| ID | Rule | Verdict |
|----|------|---------|
| 11.7.1 | PASS if all dependencies are well-known, maintained packages | PASS |
| 11.7.2 | INFO if no formal evaluation criteria documented | PASS/INFO |
| 11.7.3 | WARN if license compatibility not verified | PASS/WARN |
| 11.7.4 | INFO if pip-licenses not in CI | PASS/INFO |
| 11.7.5 | PASS if no obscure/low-reputation packages used | PASS |
| 11.7.6 | PASS if no typosquatting risks in dependency names | PASS |
| 11.7.7 | INFO if download count not checked — acceptable for known packages | PASS/INFO |
| 11.7.8 | PASS if no forked or patched packages used | PASS |
| 11.7.9 | PASS if no git+https:// URL dependencies | PASS |
| 11.7.10 | PASS if no branch-pinned git dependencies | PASS |

## 11.8 Virtual Environment Management

| ID | Rule | Verdict |
|----|------|---------|
| 11.8.1 | PASS if virtual environment is used | PASS |
| 11.8.2 | PASS if venv/ and .venv/ in .gitignore | PASS |
| 11.8.3 | PASS if venv setup is documented/scripted | PASS |
| 11.8.4 | PASS if consistent tool used (venv, poetry, etc.) | PASS |
| 11.8.5 | INFO if CI recreates env from lockfile — no CI yet | PASS/INFO |
| 11.8.6 | WARN if Python version not documented for venv | PASS/WARN |
| 11.8.7 | INFO if pre-commit not installed in venv — no pre-commit configured | PASS/INFO |
| 11.8.8 | PASS if Makefile target exists for env setup | PASS |

## 11.9 Docker & Containerized Dependency Management

| ID | Rule | Verdict |
|----|------|---------|
| 11.9.1 | PASS if --no-cache-dir used in pip install | PASS |
| 11.9.2 | INFO if --require-hashes not used — acceptable for early stage | PASS/INFO |
| 11.9.3 | PASS if dependency install is separate RUN layer from code copy | PASS |
| 11.9.4 | PASS if multi-stage Dockerfile is used | PASS |
| 11.9.5 | PASS if pip/setuptools/wheel upgraded first | PASS |
| 11.9.6 | WARN if system deps not documented in Dockerfile | PASS/WARN |
| 11.9.7 | WARN if system packages not pinned | PASS/WARN |
| 11.9.8 | PASS if apt-get cache cleaned in same RUN layer | PASS |
| 11.9.9 | PASS if slim base image used | PASS |
| 11.9.10 | INFO if image size not monitored | PASS/INFO |

## 11.10 CI/CD Dependency Hygiene

| ID | Rule | Verdict |
|----|------|---------|
| 11.10.1 | INFO if no CI cache — no CI exists | PASS/INFO |
| 11.10.2 | INFO if cache invalidation not configured — no CI | PASS/INFO |
| 11.10.3 | INFO if CI doesn't install from lockfile — no CI | PASS/INFO |
| 11.10.4 | INFO if dep install not separated in CI — no CI | PASS/INFO |
| 11.10.5 | INFO if no dependency diff on PRs — no CI | PASS/INFO |
| 11.10.6 | INFO if no production image build in CI — no CI | PASS/INFO |
| 11.10.7 | WARN if pip check not run anywhere | PASS/WARN |
| 11.10.8 | INFO if CI Python version not set — no CI | PASS/INFO |

## 11.11 Dependency Documentation (Added)

| ID | Rule | Verdict |
|----|------|---------|
| 11.11.1 | WARN if no dependency inventory with purpose descriptions | PASS/WARN |
| 11.11.2 | INFO if alternative choices not documented | PASS/INFO |
| 11.11.3 | INFO if upgrade notes not bookmarked | PASS/INFO |
| 11.11.4 | INFO if dependency graph not generated | PASS/INFO |
| 11.11.5 | WARN if deprecated dependencies not tracked | PASS/WARN |

## 11.12 Reproducibility & Build Determinism (Added)

| ID | Rule | Verdict |
|----|------|---------|
| 11.12.1 | WARN if pip install resolution is non-deterministic (no lockfile) | PASS/WARN |
| 11.12.2 | PASS if only pip install used (no setup.py install) | PASS |
| 11.12.3 | WARN if build not deterministic (no lockfile for transitive deps) | PASS/WARN |
| 11.12.4 | INFO if offline installation not possible | PASS/INFO |
| 11.12.5 | PASS if CI and production use same base image | PASS |
