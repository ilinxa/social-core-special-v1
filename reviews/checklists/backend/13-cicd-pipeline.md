# 13 — CI/CD Pipeline Checklist

## 13.1 Pipeline Architecture & Design

- [ ] CI/CD pipeline is defined **entirely as code** — `.github/workflows/`, `.gitlab-ci.yml`, or `Jenkinsfile` committed to version control
- [ ] Pipeline configuration is **reviewed like application code** — changes go through PR review
- [ ] Pipeline has **clearly separated stages** — lint → type check → test → security scan → build → deploy → smoke test
- [ ] Stages are **ordered by fastest feedback first** — linting fails before waiting for slow tests
- [ ] Pipeline runs on **every PR and every push to main** — no gaps in coverage
- [ ] **Branch-specific behavior** is explicit — PRs run tests, merges to main trigger deploy to staging, tags trigger production deploy
- [ ] Pipeline is **idempotent** — running it twice produces the same result
- [ ] Pipeline completion time is **monitored** — target under 10 minutes for full PR pipeline
- [ ] **Pipeline notifications** are sent on failure — Slack, email, or equivalent — reaching the right people
- [ ] Pipeline history is **retained and auditable** — who triggered what run, when, with what result

## 13.2 Continuous Integration Triggers

- [ ] CI runs automatically on **every pull request** — no manual trigger required
- [ ] CI runs on **every push to protected branches** — main, develop, release branches
- [ ] CI runs on **dependency update PRs** — Dependabot and Renovate PRs are fully tested
- [ ] **Draft PRs** do not trigger the full pipeline — only required checks, saving CI minutes
- [ ] **Path filters** are used in monorepos — backend CI only triggers on backend file changes
- [ ] CI is **re-triggered on new commits** to an open PR — stale green checks from an earlier commit do not count
- [ ] **Merge queue** is used for high-traffic repos — preventing merge races on main
- [ ] CI results are **visible in the PR interface** — pass/fail visible before review is completed
- [ ] **Required status checks** are enforced via branch protection — PRs cannot merge with failing CI
- [ ] **Force push to protected branches is disabled** — history is immutable after merge

## 13.3 Code Quality Gates

- [ ] **`ruff` linting** runs as the first step — fastest feedback on style and obvious bugs
- [ ] **`black` formatting check** runs in CI — `black --check .` fails on unformatted code
- [ ] **`isort` check** runs in CI — `isort --check-only .` fails on unsorted imports
- [ ] **`mypy` type checking** runs in CI — static type errors fail the build
- [ ] **`mypy` configuration** is strict — `disallow_untyped_defs = true` at minimum
- [ ] **`bandit`** security linting runs in CI — catching common security anti-patterns in Python code
- [ ] **`import-linter`** or **`pydeps`** runs in CI — detecting circular imports between apps
- [ ] **`django-upgrade --check`** runs if upgrading Django — catching deprecated patterns automatically
- [ ] All quality gates are **required** — cannot be skipped or bypassed for a merge
- [ ] Quality gate failures produce **actionable error messages** — not cryptic exit codes

## 13.4 Test Execution in CI

- [ ] **Full test suite runs** on every PR — no subset-only runs in CI
- [ ] Tests run against **PostgreSQL** in CI — not SQLite, matching production database
- [ ] Tests run against **Redis** in CI — not mocked, matching production cache and broker
- [ ] CI uses **Docker Compose or service containers** to spin up dependencies — not mocked external services
- [ ] **`pytest`** is used as the test runner — with CI-appropriate flags (`--tb=short`, `--no-header`)
- [ ] **`pytest-xdist`** parallelizes tests in CI — `-n auto` distributes across available CPUs
- [ ] **Test output** is captured and published as CI artifacts — accessible for debugging failures
- [ ] **Flaky tests** are tracked and quarantined — not blocking CI on intermittently failing tests
- [ ] **`pytest-randomly`** randomizes test order in CI — detecting hidden test interdependencies
- [ ] Test run duration is **tracked over time** — growing test time triggers investigation and optimization
- [ ] **`manage.py migrate`** runs from zero in CI — verifying migration chain is intact
- [ ] **`manage.py migrate --check`** runs in CI — fails if unapplied migrations exist in the branch
- [ ] **`manage.py makemigrations --check`** runs in CI — fails if model changes lack a migration

## 13.5 Code Coverage

- [ ] **`pytest-cov`** generates coverage reports in CI — `coverage.xml` produced for every run
- [ ] Coverage report is **published to CI interface** — visible in PR without downloading artifacts
- [ ] **Coverage threshold is enforced** — build fails if total coverage drops below configured minimum (e.g. 80%)
- [ ] **Per-file coverage thresholds** are considered — critical files like `services.py` require higher coverage
- [ ] **Coverage delta is reported on PRs** — showing if a PR increases or decreases overall coverage
- [ ] Coverage is reported to **Codecov, Coveralls, or equivalent** — historical trends tracked
- [ ] **Branch coverage** is measured — not just line coverage, which can miss untested code paths
- [ ] Coverage reports **exclude non-testable files** — `migrations/`, `settings/`, `manage.py` excluded from metrics
- [ ] Coverage is not **gamed** — tests exist to verify behavior, not just to touch lines
- [ ] Coverage gaps in **critical paths** (auth, billing, permissions) trigger mandatory review comments

## 13.6 Security Scanning in CI

- [ ] **`pip-audit`** runs in CI — failing on known CVEs in direct and transitive dependencies
- [ ] **`bandit`** runs in CI — Python security linting catching injection risks, hardcoded passwords, weak crypto
- [ ] **`detect-secrets`** or **`gitleaks`** runs in CI — failing if secrets are detected in any committed file
- [ ] **Docker image vulnerability scanning** runs in CI — Trivy or Snyk scanning the built image before push
- [ ] **SAST (Static Application Security Testing)** runs in CI — `semgrep` with Django/Python rulesets
- [ ] **Dependency license scanning** runs in CI — `pip-licenses` failing on disallowed licenses
- [ ] Security scan results are **published as CI artifacts** — full reports downloadable for review
- [ ] **Critical and high severity findings block the merge** — medium and low are warnings
- [ ] Security scan suppressions are **code-reviewed** — not silently added to ignore lists
- [ ] **`manage.py check --deploy`** runs in CI — verifying Django's own security checklist passes

## 13.7 Build & Image Pipeline

- [ ] **Docker image is built in CI** on every PR — verifying the Dockerfile is not broken
- [ ] Image build uses **layer caching** — CI caches Docker layers to speed up repeated builds
- [ ] Built image is **tagged with the Git SHA** — `registry/app:abc1234` enabling exact version tracing
- [ ] Image is also tagged with **`latest`** only on main branch merges — PRs do not pollute the `latest` tag
- [ ] Built image is **pushed to a private registry** — not Docker Hub public by default
- [ ] **Image digest** is captured and stored — enabling reproducible deployments from exact image content
- [ ] Image build **fails the pipeline** if it fails — not silently ignored
- [ ] **Build arguments** (`ARG`) do not contain secrets — build-time secrets use `--secret` mount
- [ ] **`docker scout` or Trivy** scans the pushed image — blocking deployment of vulnerable images
- [ ] Image **size is reported** in CI — growing image size is flagged for investigation

## 13.8 Continuous Deployment to Staging

- [ ] **Every merge to main** automatically deploys to staging — no manual step required
- [ ] Staging deployment uses the **same pipeline** as production — no special-case staging scripts
- [ ] Staging deployment runs **database migrations** automatically — before traffic is shifted
- [ ] **Smoke tests run automatically** after staging deployment — verifying critical paths work
- [ ] Staging deployment **automatically rolls back** if smoke tests fail — not requiring manual intervention
- [ ] Staging environment is **reset periodically** — data does not accumulate indefinitely
- [ ] Staging uses **production-equivalent infrastructure** — same instance types, same services, smaller scale
- [ ] **Feature flags** allow testing unreleased features in staging — without affecting production
- [ ] Staging deployment **notifications** are sent to the team — success and failure both communicated
- [ ] Staging deployment **duration is tracked** — growing deploy time is investigated

## 13.9 Production Deployment

- [ ] **Production deployment is triggered manually or via tag** — not automatically on every merge to main
- [ ] Production deployments require **explicit approval** — a human gates the release
- [ ] Production uses **blue-green or rolling deployment** — zero downtime, no dropped requests
- [ ] **Database migrations run before** new code receives traffic — backwards-compatible migrations enforced
- [ ] **Canary releases** are considered for high-risk changes — small percentage of traffic before full rollout
- [ ] **Rollback is one command** — `deploy rollback` restores the previous known-good version
- [ ] Rollback is **tested regularly** — not just theoretically possible
- [ ] **Deployment is logged** — who deployed, what version, when, with a link to the pipeline run
- [ ] **Post-deploy smoke tests** run automatically — verifying production is healthy after deploy
- [ ] **Error rate is monitored** immediately after deploy — automatic rollback if error rate spikes
- [ ] **`CHANGELOG.md` is updated** as part of the release process — not left to memory
- [ ] **Git tag is created** for every production deploy — `v1.2.3` tag on the exact commit deployed

## 13.10 Environment & Secret Management in CI

- [ ] **No secrets in pipeline YAML files** — all secrets injected via CI environment variables or secret store
- [ ] CI secrets are **scoped to the minimum necessary** — deploy keys only have deploy permissions
- [ ] **Separate secret sets** per environment — staging secrets do not grant production access
- [ ] CI runners do **not persist secrets between jobs** — secrets are injected fresh per run
- [ ] **Secrets are masked in CI logs** — never printed even in verbose mode
- [ ] **Short-lived credentials** are used where possible — OIDC-based AWS/GCP auth instead of long-lived keys
- [ ] CI service account permissions follow **least privilege** — cannot access resources beyond what the pipeline needs
- [ ] **Secret rotation** does not require pipeline changes — externalized via secret manager references
- [ ] CI environment variables are **documented** — `CONTRIBUTING.md` lists required CI secrets for new contributors setting up forks
- [ ] **CI secret access is audited** — who has access to configure CI secrets is reviewed quarterly

## 13.11 Pipeline Reliability & Maintenance

- [ ] **Flaky tests are tracked** in a dedicated issue — not left to silently fail and be re-run
- [ ] Flaky tests are **quarantined** — marked and excluded from blocking CI until fixed
- [ ] **CI runner capacity** is monitored — jobs not queuing for more than 2 minutes during peak hours
- [ ] **Pipeline dependencies are pinned** — GitHub Actions versions, Docker images used in CI are pinned to digests
- [ ] **Third-party GitHub Actions are forked or pinned** — not trusting `@main` of external actions
- [ ] Pipeline configuration is **DRY** — shared steps use reusable workflows or templates, not copy-pasted
- [ ] **CI costs are monitored** — unnecessary long-running jobs or redundant pipelines are optimized
- [ ] Pipeline definition is **reviewed on significant changes** — not just rubber-stamped
- [ ] **CI/CD documentation** is maintained — onboarding guide explains how the pipeline works
- [ ] **Pipeline failure triage process** is documented — who investigates, how quickly, escalation path

## 13.12 Pre-commit Hooks

- [ ] **`pre-commit`** is configured — `.pre-commit-config.yaml` committed to the repo
- [ ] Pre-commit hooks run — `ruff`, `black`, `isort`, `detect-secrets`, `trailing-whitespace`, `end-of-file-fixer`
- [ ] Pre-commit hook versions are **pinned** — `rev:` uses an exact tag or commit hash
- [ ] **`pre-commit install`** is documented in the onboarding guide — every developer installs it on clone
- [ ] **`pre-commit run --all-files`** runs in CI — ensuring hooks pass on the full codebase, not just staged files
- [ ] Pre-commit hooks are **fast** — total hook runtime under 30 seconds to not frustrate developers
- [ ] **`pre-commit autoupdate`** is run periodically — keeping hook versions current
- [ ] Pre-commit hooks are **consistent with CI checks** — hooks never pass locally while CI fails on the same check
- [ ] Hooks that are **slow** (mypy, full test suite) are not in pre-commit — reserved for CI
- [ ] **`commit-msg`** hook enforces conventional commit format if commit conventions are adopted

## 13.13 Local CI Parity & Developer Experience (Added)

- [ ] **`make check`** or equivalent runs the same checks as CI — developers can verify before pushing
- [ ] Local check command is **fast** — under 2 minutes for full lint + test suite
- [ ] CI environment is **reproducible locally** — Docker Compose or similar spins up identical dependencies
- [ ] **`act`** or equivalent allows running GitHub Actions locally — debugging CI failures without pushing
- [ ] CI-only failures are **rare** — local and CI environments produce the same results
- [ ] **Environment parity** is documented — known differences between local and CI are listed
- [ ] Developer onboarding docs include **CI setup instructions** — how to configure, run, and debug locally

## 13.14 Pipeline Observability & Metrics (Added)

- [ ] Pipeline **success rate** is tracked — target >95% on main branch
- [ ] Pipeline **duration** is tracked per stage — identifying bottlenecks
- [ ] **Test suite duration** trends are monitored — alerts if test time increases >20%
- [ ] **Flaky test rate** is tracked — percentage of pipeline runs that fail then pass on retry
- [ ] CI **resource usage** is monitored — CPU, memory, disk per job
- [ ] **Queue wait time** is tracked — jobs waiting for available runners
- [ ] Pipeline metrics are **dashboarded** — Grafana, Datadog, or CI-native analytics
- [ ] **Cost per pipeline run** is tracked — cloud CI billing is understood and optimized
