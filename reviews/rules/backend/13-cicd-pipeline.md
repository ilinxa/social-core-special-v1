# 13 — CI/CD Pipeline Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 13.1 Pipeline Architecture & Design

| ID | Rule | Verdict |
|----|------|---------|
| 13.1.1 | FAIL if no CI/CD pipeline exists (no .github/workflows/, .gitlab-ci.yml, Jenkinsfile) | PASS/FAIL |
| 13.1.2 | INFO if pipeline config not reviewed — N/A if no CI | PASS/INFO |
| 13.1.3 | WARN if pipeline stages not clearly separated | PASS/WARN |
| 13.1.4 | INFO if stages not ordered by speed — N/A if no CI | PASS/INFO |
| 13.1.5 | WARN if pipeline doesn't run on every PR and push to main | PASS/WARN |
| 13.1.6 | INFO if no branch-specific behavior defined | PASS/INFO |
| 13.1.7 | INFO if idempotency not verified | PASS/INFO |
| 13.1.8 | INFO if pipeline time not monitored | PASS/INFO |
| 13.1.9 | WARN if no failure notifications configured | PASS/WARN |
| 13.1.10 | INFO if pipeline history not retained | PASS/INFO |

## 13.2 Continuous Integration Triggers

| ID | Rule | Verdict |
|----|------|---------|
| 13.2.1 | WARN if CI doesn't run on every PR | PASS/WARN |
| 13.2.2 | WARN if CI doesn't run on pushes to protected branches | PASS/WARN |
| 13.2.3 | INFO if dependency update PRs not tested in CI | PASS/INFO |
| 13.2.4 | INFO if draft PRs trigger full pipeline | PASS/INFO |
| 13.2.5 | INFO if no path filters in monorepo CI | PASS/INFO |
| 13.2.6 | INFO if CI not re-triggered on new commits | PASS/INFO |
| 13.2.7 | INFO if no merge queue — acceptable for small teams | PASS/INFO |
| 13.2.8 | WARN if CI results not visible in PR interface | PASS/WARN |
| 13.2.9 | WARN if no required status checks on protected branches | PASS/WARN |
| 13.2.10 | WARN if force push to protected branches is allowed | PASS/WARN |

## 13.3 Code Quality Gates

| ID | Rule | Verdict |
|----|------|---------|
| 13.3.1 | WARN if no linting in CI (ruff or flake8) | PASS/WARN |
| 13.3.2 | WARN if no formatting check in CI (black --check) | PASS/WARN |
| 13.3.3 | WARN if no import sorting check in CI (isort --check) | PASS/WARN |
| 13.3.4 | WARN if no type checking in CI (mypy/pyright) | PASS/WARN |
| 13.3.5 | INFO if mypy config not strict — acceptable for gradual adoption | PASS/INFO |
| 13.3.6 | INFO if bandit not in CI — acceptable for early stage | PASS/INFO |
| 13.3.7 | INFO if no circular import detection in CI | PASS/INFO |
| 13.3.8 | INFO if django-upgrade not in CI | PASS/INFO |
| 13.3.9 | WARN if quality gates can be bypassed | PASS/WARN |
| 13.3.10 | PASS if quality gate errors are actionable | PASS |

## 13.4 Test Execution in CI

| ID | Rule | Verdict |
|----|------|---------|
| 13.4.1 | WARN if full test suite doesn't run on every PR | PASS/WARN |
| 13.4.2 | WARN if CI tests run against SQLite instead of PostgreSQL | PASS/WARN |
| 13.4.3 | WARN if CI tests don't use Redis | PASS/WARN |
| 13.4.4 | INFO if CI doesn't use service containers | PASS/INFO |
| 13.4.5 | PASS if pytest is the test runner | PASS |
| 13.4.6 | INFO if pytest-xdist not used for parallelization | PASS/INFO |
| 13.4.7 | INFO if test output not published as artifacts | PASS/INFO |
| 13.4.8 | INFO if flaky tests not tracked | PASS/INFO |
| 13.4.9 | INFO if test order not randomized | PASS/INFO |
| 13.4.10 | INFO if test duration not tracked | PASS/INFO |
| 13.4.11 | WARN if migration chain not verified in CI | PASS/WARN |
| 13.4.12 | WARN if unapplied migration check not in CI | PASS/WARN |
| 13.4.13 | WARN if missing migration check not in CI | PASS/WARN |

## 13.5 Code Coverage

| ID | Rule | Verdict |
|----|------|---------|
| 13.5.1 | WARN if coverage not generated in CI | PASS/WARN |
| 13.5.2 | INFO if coverage not published to PR interface | PASS/INFO |
| 13.5.3 | PASS if coverage threshold is configured locally (usable in CI) | PASS |
| 13.5.4 | INFO if no per-file coverage thresholds | PASS/INFO |
| 13.5.5 | INFO if coverage delta not reported on PRs | PASS/INFO |
| 13.5.6 | INFO if no Codecov/Coveralls integration | PASS/INFO |
| 13.5.7 | INFO if no branch coverage measurement | PASS/INFO |
| 13.5.8 | PASS if coverage excludes migrations/settings/manage.py | PASS |
| 13.5.9 | PASS if test quality is high (not gaming coverage) | PASS |
| 13.5.10 | INFO if critical path coverage not enforced | PASS/INFO |

## 13.6 Security Scanning in CI

| ID | Rule | Verdict |
|----|------|---------|
| 13.6.1 | WARN if pip-audit not in CI | PASS/WARN |
| 13.6.2 | INFO if bandit not in CI — acceptable for early stage | PASS/INFO |
| 13.6.3 | WARN if no secret detection in CI (detect-secrets/gitleaks) | PASS/WARN |
| 13.6.4 | WARN if no Docker image scanning in CI | PASS/WARN |
| 13.6.5 | INFO if no SAST (semgrep) in CI | PASS/INFO |
| 13.6.6 | INFO if no license scanning in CI | PASS/INFO |
| 13.6.7 | INFO if scan results not published as artifacts | PASS/INFO |
| 13.6.8 | WARN if critical findings don't block merge | PASS/WARN |
| 13.6.9 | INFO if suppressions not reviewed | PASS/INFO |
| 13.6.10 | WARN if manage.py check --deploy not in CI | PASS/WARN |

## 13.7 Build & Image Pipeline

| ID | Rule | Verdict |
|----|------|---------|
| 13.7.1 | WARN if Docker image not built in CI | PASS/WARN |
| 13.7.2 | INFO if no layer caching in CI builds | PASS/INFO |
| 13.7.3 | WARN if image not tagged with Git SHA | PASS/WARN |
| 13.7.4 | INFO if :latest tag strategy not defined | PASS/INFO |
| 13.7.5 | INFO if no private registry configured | PASS/INFO |
| 13.7.6 | INFO if image digest not captured | PASS/INFO |
| 13.7.7 | PASS if Dockerfile builds successfully (verified locally/Makefile) | PASS |
| 13.7.8 | PASS if no secrets in build args | PASS |
| 13.7.9 | WARN if no image scanning before deploy | PASS/WARN |
| 13.7.10 | INFO if image size not reported | PASS/INFO |

## 13.8 Continuous Deployment to Staging

| ID | Rule | Verdict |
|----|------|---------|
| 13.8.1 | INFO if no auto-deploy to staging — N/A without CI | PASS/INFO |
| 13.8.2 | INFO if staging pipeline differs from production | PASS/INFO |
| 13.8.3 | PASS if migrations run in deploy (entrypoint handles this) | PASS |
| 13.8.4 | INFO if no smoke tests after staging deploy | PASS/INFO |
| 13.8.5 | INFO if no auto-rollback on staging | PASS/INFO |
| 13.8.6 | INFO if staging not periodically reset | PASS/INFO |
| 13.8.7 | INFO if staging not production-equivalent | PASS/INFO |
| 13.8.8 | INFO if no feature flags for staging | PASS/INFO |
| 13.8.9 | INFO if no staging deploy notifications | PASS/INFO |
| 13.8.10 | INFO if staging deploy duration not tracked | PASS/INFO |

## 13.9 Production Deployment

| ID | Rule | Verdict |
|----|------|---------|
| 13.9.1 | INFO if production deploy not via tag/manual — N/A without CI | PASS/INFO |
| 13.9.2 | INFO if no approval gate on production deploy | PASS/INFO |
| 13.9.3 | INFO if no zero-downtime deploy strategy | PASS/INFO |
| 13.9.4 | PASS if migrations run before traffic shift (entrypoint.sh) | PASS |
| 13.9.5 | INFO if no canary releases | PASS/INFO |
| 13.9.6 | INFO if no one-command rollback | PASS/INFO |
| 13.9.7 | INFO if rollback not tested | PASS/INFO |
| 13.9.8 | INFO if deployment not logged | PASS/INFO |
| 13.9.9 | INFO if no post-deploy smoke tests | PASS/INFO |
| 13.9.10 | INFO if error rate not monitored after deploy | PASS/INFO |
| 13.9.11 | INFO if no CHANGELOG maintained | PASS/INFO |
| 13.9.12 | INFO if no Git tag on production deploy | PASS/INFO |

## 13.10 Environment & Secret Management in CI

| ID | Rule | Verdict |
|----|------|---------|
| 13.10.1 | PASS if no secrets in committed pipeline files (N/A — no pipeline files) | PASS |
| 13.10.2 | INFO if CI secret scoping not configured — N/A | PASS/INFO |
| 13.10.3 | INFO if no environment-separated secrets — N/A | PASS/INFO |
| 13.10.4 | INFO if secret persistence not verified — N/A | PASS/INFO |
| 13.10.5 | INFO if secret masking not configured — N/A | PASS/INFO |
| 13.10.6 | INFO if no short-lived credentials — N/A | PASS/INFO |
| 13.10.7 | INFO if CI least privilege not applied — N/A | PASS/INFO |
| 13.10.8 | INFO if secret rotation requires pipeline changes — N/A | PASS/INFO |
| 13.10.9 | INFO if CI env vars not documented — N/A | PASS/INFO |
| 13.10.10 | INFO if CI secret access not audited — N/A | PASS/INFO |

## 13.11 Pipeline Reliability & Maintenance

| ID | Rule | Verdict |
|----|------|---------|
| 13.11.1 | INFO if flaky tests not tracked — N/A without CI | PASS/INFO |
| 13.11.2 | INFO if flaky tests not quarantined — N/A | PASS/INFO |
| 13.11.3 | INFO if CI runner capacity not monitored — N/A | PASS/INFO |
| 13.11.4 | INFO if pipeline deps not pinned — N/A | PASS/INFO |
| 13.11.5 | INFO if 3rd-party actions not pinned — N/A | PASS/INFO |
| 13.11.6 | INFO if pipeline config not DRY — N/A | PASS/INFO |
| 13.11.7 | INFO if CI costs not monitored — N/A | PASS/INFO |
| 13.11.8 | INFO if pipeline changes not reviewed — N/A | PASS/INFO |
| 13.11.9 | INFO if CI/CD docs not maintained — N/A | PASS/INFO |
| 13.11.10 | INFO if failure triage not documented — N/A | PASS/INFO |

## 13.12 Pre-commit Hooks

| ID | Rule | Verdict |
|----|------|---------|
| 13.12.1 | WARN if no .pre-commit-config.yaml exists | PASS/WARN |
| 13.12.2 | WARN if pre-commit hooks don't include linting and formatting | PASS/WARN |
| 13.12.3 | INFO if hook versions not pinned — N/A without pre-commit | PASS/INFO |
| 13.12.4 | INFO if pre-commit install not documented | PASS/INFO |
| 13.12.5 | INFO if pre-commit not run in CI | PASS/INFO |
| 13.12.6 | INFO if hooks are slow | PASS/INFO |
| 13.12.7 | INFO if hooks not periodically updated | PASS/INFO |
| 13.12.8 | INFO if hooks inconsistent with CI | PASS/INFO |
| 13.12.9 | PASS if slow checks reserved for CI (mypy, full tests) | PASS |
| 13.12.10 | INFO if no commit-msg hook | PASS/INFO |

## 13.13 Local CI Parity & Developer Experience (Added)

| ID | Rule | Verdict |
|----|------|---------|
| 13.13.1 | PASS if make check or equivalent runs same checks as would be in CI | PASS |
| 13.13.2 | PASS if local check is fast (under 2 minutes) | PASS |
| 13.13.3 | PASS if CI-equivalent environment reproducible via Docker Compose | PASS |
| 13.13.4 | INFO if no local CI runner (act or equivalent) | PASS/INFO |
| 13.13.5 | INFO if CI-only failures not documented | PASS/INFO |
| 13.13.6 | INFO if env differences not listed | PASS/INFO |
| 13.13.7 | INFO if onboarding docs don't include CI instructions | PASS/INFO |

## 13.14 Pipeline Observability & Metrics (Added)

| ID | Rule | Verdict |
|----|------|---------|
| 13.14.1 | INFO if pipeline success rate not tracked — N/A without CI | PASS/INFO |
| 13.14.2 | INFO if pipeline duration not tracked per stage — N/A | PASS/INFO |
| 13.14.3 | INFO if test suite duration not trending — N/A | PASS/INFO |
| 13.14.4 | INFO if flaky test rate not tracked — N/A | PASS/INFO |
| 13.14.5 | INFO if CI resource usage not monitored — N/A | PASS/INFO |
| 13.14.6 | INFO if queue wait time not tracked — N/A | PASS/INFO |
| 13.14.7 | INFO if pipeline metrics not dashboarded — N/A | PASS/INFO |
| 13.14.8 | INFO if cost per pipeline not tracked — N/A | PASS/INFO |
