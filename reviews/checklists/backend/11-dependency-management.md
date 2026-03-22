# 11 — Dependency Management Checklist

## 11.1 Dependency File Structure

- [ ] A **single source of truth** exists for dependencies — `pyproject.toml` preferred over multiple `requirements/*.txt` files
- [ ] If using `requirements/` directory, files are clearly split — `base.txt`, `dev.txt`, `prod.txt`, `test.txt`
- [ ] **No duplicate dependency files** at root level — not both `requirements.txt` and `Pipfile` and `pyproject.toml` coexisting without a clear hierarchy
- [ ] `pyproject.toml` is used as the **central configuration file** — consolidating `black`, `ruff`, `mypy`, `pytest`, and dependency config in one place
- [ ] Dependency files are **committed to version control** — never in `.gitignore`
- [ ] A **lockfile exists** — `poetry.lock`, `pip-tools`-generated `requirements.lock`, or `Pipfile.lock` — pinning transitive dependencies
- [ ] The lockfile is **committed to version control** — ensuring reproducible installs across all environments
- [ ] **`pip-tools`** or **`poetry`** is used for dependency management — not manually editing `requirements.txt`
- [ ] Dependency files are **organized logically** — grouped with comments (`# Database`, `# Async`, `# Testing`)
- [ ] A clear process exists for **adding new dependencies** — documented in `CONTRIBUTING.md`

## 11.2 Version Pinning

- [ ] **All direct dependencies are pinned** to exact versions — `django==5.0.3` not `django>=4.0`
- [ ] **All transitive dependencies are pinned** via a lockfile — not just direct dependencies
- [ ] **No unpinned dependencies** with open-ended ranges (`>=`, `~=`, `^`) in production requirements
- [ ] Development-only dependencies are pinned with the same rigor as production — reproducible dev environments matter
- [ ] **No `latest` or unversioned** Docker base images used alongside Python dependencies — full stack is pinned
- [ ] Version constraints in `pyproject.toml` `[tool.poetry.dependencies]` use **exact pins or tight ranges** — not `"*"`
- [ ] Pin rationale is documented for **unusual version constraints** — e.g. `django==4.2.x # LTS, upgrading in Q3`
- [ ] Upper bound pins are **reviewed regularly** — not set-and-forgotten, blocking security updates indefinitely
- [ ] **Python version itself is pinned** — `.python-version` file or `pyproject.toml` `requires-python` field
- [ ] Python version in lockfile matches the version in `Dockerfile` and CI configuration — no silent mismatch

## 11.3 Dependency Separation

- [ ] **Production dependencies** contain only what the running application needs — zero dev/test packages in prod image
- [ ] **Development dependencies** include tooling — `black`, `ruff`, `mypy`, `pytest`, `factory-boy`, `django-debug-toolbar`
- [ ] **Test dependencies** are separate from general dev dependencies where the distinction matters
- [ ] **No test frameworks** (`pytest`, `coverage`) in production requirements — verified in Dockerfile
- [ ] **No debug tools** (`django-debug-toolbar`, `ipdb`, `django-extensions`) in production requirements
- [ ] Production Docker image installs **only production dependencies** — `pip install --no-dev` or equivalent
- [ ] CI installs **all dependency groups** including test — not missing test dependencies causing false passes
- [ ] Optional feature dependencies are clearly labeled — e.g. `# Optional: only needed for PDF generation`
- [ ] **Database driver** (`psycopg2-binary` vs `psycopg2`) choice is documented — binary vs compiled rationale noted
- [ ] **`psycopg2`** (compiled) is used in production — not `psycopg2-binary` which is not recommended for production

## 11.4 Security Vulnerability Scanning

- [ ] **`pip-audit`** runs in CI on every PR — fails build on known vulnerabilities
- [ ] **`safety`** is used as a secondary scanner — different vulnerability database than `pip-audit`
- [ ] Vulnerability scanning results are **reviewed, not just acknowledged** — suppressed CVEs are documented with justification
- [ ] **CVE suppression list** is reviewed quarterly — suppressed vulnerabilities don't accumulate silently
- [ ] **GitHub Dependabot** or **Snyk** is configured — automated PRs for vulnerable dependency updates
- [ ] Security alerts are routed to the **right people** — not silently ignored in a spam folder
- [ ] A **patch SLA is defined** — critical CVEs patched within 24–48 hours, high within 1 week
- [ ] Vulnerability scanning covers **Docker base images** as well — not just Python packages
- [ ] **Transitive dependencies** are scanned — not just direct dependencies listed in requirements
- [ ] The entire **supply chain is considered** — not just vulnerabilities but also dependency trustworthiness

## 11.5 Dependency Updates

- [ ] A **regular update cadence** is defined — weekly, biweekly, or monthly dependency reviews
- [ ] **Dependabot** or **Renovate** is configured for automated update PRs — not manual tracking
- [ ] Automated update PRs run the **full test suite** before merging — not blindly auto-merged
- [ ] **Major version updates** go through a deliberate upgrade process — changelog reviewed, tests run, staged rollout
- [ ] **Django LTS versions** are used — upgrade path to next LTS is planned before EOL
- [ ] Django upgrade uses **`django-upgrade`** tool — automated codemods for deprecated patterns
- [ ] **DRF version** is kept in sync with Django version compatibility matrix
- [ ] Dependency updates are **batched logically** — not one PR per dependency per day
- [ ] A **changelog is reviewed** for every updated dependency — not just bumping versions blindly
- [ ] **Breaking change detection** is part of the update process — API diffs reviewed for major bumps

## 11.6 Unused Dependency Detection

- [ ] **`deptry`** or **`pip-check`** runs periodically — detecting unused or missing dependencies
- [ ] Unused dependencies are **removed promptly** — not kept "just in case"
- [ ] Dependencies imported only in **one place** are evaluated — is a full package needed or can the logic be inlined?
- [ ] **`importlib`** usage is checked — no dynamic imports hiding real dependency usage from static analysis
- [ ] Dependencies used only in **management commands or scripts** are clearly labeled — not appearing to be unused
- [ ] Removed dependencies are verified to be **fully absent** — not still imported somewhere via a transitive path
- [ ] Dev dependencies no longer needed after a refactor are **cleaned up** — not accumulating over time
- [ ] No **vendored copies** of libraries exist alongside the package in `requirements.txt` — one source of truth

## 11.7 Package Trust & Vetting

- [ ] New dependencies are **evaluated before adoption** — not installed from a Stack Overflow snippet without review
- [ ] Package evaluation criteria include: **maintenance activity**, **download count**, **CVE history**, **license compatibility**
- [ ] **License compatibility** is verified for all dependencies — GPL packages not used in proprietary closed-source projects without legal review
- [ ] **`pip-licenses`** runs in CI — producing a license report and failing on disallowed licenses
- [ ] Packages from **unknown or low-reputation publishers** are avoided — PyPI typosquatting is a real threat
- [ ] **Typosquatting checks** are done for any new package — `reqeusts` vs `requests`
- [ ] Packages with **fewer than 1,000 weekly downloads** are flagged for extra scrutiny
- [ ] **Forked or patched packages** are avoided unless the fork is actively maintained and the reason is documented
- [ ] **Internal packages** are published to a private registry — not installed via `git+https://` URLs in requirements
- [ ] `git+https://` URL dependencies in requirements are flagged — pinned to a specific commit hash, not a branch

## 11.8 Virtual Environment Management

- [ ] A **virtual environment is always used** — no global Python package installations for project dependencies
- [ ] Virtual environment is **not committed** to version control — `.venv/` and `venv/` are in `.gitignore`
- [ ] Virtual environment creation is **documented and scripted** — one command to set up from scratch
- [ ] **`python -m venv`** or **`poetry`** is used consistently — not a mix of `virtualenv`, `conda`, and `venv`
- [ ] Virtual environment is **recreated from lockfile** in CI — not cached between runs without verification
- [ ] **Python version** used in virtual environment matches production — documented in `README.md`
- [ ] **`pre-commit`** is installed inside the virtual environment — not globally, to ensure version consistency
- [ ] A **`Makefile` target** (`make install`) sets up the full virtual environment from scratch — documented in onboarding

## 11.9 Docker & Containerized Dependency Management

- [ ] **`pip install`** in Dockerfile uses `--no-cache-dir` — reducing image size
- [ ] **`pip install`** in Dockerfile uses `--require-hashes` — verifying package integrity
- [ ] Dependencies are installed in a **separate `RUN` layer** from the application code — maximizing layer cache reuse
- [ ] **Multi-stage Dockerfile** is used — build dependencies not present in the final production image
- [ ] `pip`, `setuptools`, and `wheel` are **upgraded first** in the Dockerfile — before installing project dependencies
- [ ] **System-level dependencies** (gcc, libpq-dev) installed in Dockerfile are documented — explaining why each is needed
- [ ] System packages in Dockerfile are **pinned where possible** — not `apt-get install libpq-dev` without a version
- [ ] **`apt-get` cache is cleaned** after installation — `rm -rf /var/lib/apt/lists/*` in the same `RUN` layer
- [ ] The production Docker image is **minimal** — Alpine or slim base, no build tools in final image
- [ ] Docker image size is **monitored** — growing image size signals unnecessary dependency accumulation

## 11.10 CI/CD Dependency Hygiene

- [ ] CI caches the virtual environment or pip cache — **speeding up installs** without compromising reproducibility
- [ ] CI cache is **invalidated on lockfile change** — not serving stale cached packages after a dependency update
- [ ] CI installs from the **lockfile** — not from loose requirement files that might resolve differently
- [ ] **Dependency installation step** is separated from test/lint steps in CI — clear failure attribution
- [ ] CI publishes a **dependency diff** on PRs that change requirements — reviewers see what changed
- [ ] **Production image build** is part of CI — verifying the Dockerfile installs correctly on every PR
- [ ] **`pip check`** runs in CI — verifying no dependency conflicts exist in the installed environment
- [ ] CI environment Python version is **explicitly set** — not relying on the default version of the CI runner

## 11.11 Dependency Documentation (Added)

- [ ] A **dependency inventory** exists — listing each direct dependency with its purpose and justification
- [ ] **Why each dependency was chosen** over alternatives is documented — e.g., "nh3 over bleach for HTML sanitization (Rust-backed, faster, actively maintained)"
- [ ] Upgrade notes and **migration guides** for major dependencies are bookmarked or linked
- [ ] **Dependency graph** can be generated — `pipdeptree` or equivalent shows the full tree
- [ ] **Deprecated dependencies** are tracked — packages approaching EOL are flagged for replacement

## 11.12 Reproducibility & Build Determinism (Added)

- [ ] `pip install` from the same requirements file produces **identical results** on any machine — no platform-dependent resolution
- [ ] **No `setup.py install`** or `python setup.py develop` used — only `pip install` for consistency
- [ ] Build artifacts are **deterministic** — same commit produces the same Docker image contents
- [ ] **Offline installation** is possible from a cached wheels directory — useful for air-gapped deployments
- [ ] CI and production use the **same base image** — no "works in CI, fails in prod" due to different system libs
