# 14 — Documentation Checklist

## 14.1 README.md
- [ ] **`README.md` exists** at the project root — the first thing any developer sees
- [ ] README starts with a **one-paragraph project description** — what the system does, who it is for, why it exists
- [ ] README includes a **technology stack summary** — Python version, Django version, key dependencies listed
- [ ] README includes a **system architecture overview** — high-level diagram or description of major components
- [ ] README includes **prerequisites** — what must be installed before setup (Docker, Python version, etc.)
- [ ] README includes **local development setup** — step-by-step from a clean clone to a running server
- [ ] Setup instructions are **verified regularly** — tested by a new team member or in CI
- [ ] README includes **how to run tests** — single command, with options for running subsets
- [ ] README includes **how to run linting and formatting** — commands and expected output
- [ ] README includes **environment variable reference** — links to `.env.example` with explanation
- [ ] README includes **common development tasks** — running migrations, creating a superuser, loading seed data
- [ ] README includes **links to further documentation** — API docs, architecture docs, deployment guide
- [ ] README is **kept current** — outdated setup instructions are actively harmful, worse than no docs
- [ ] README has a **last verified date** or a CI check that validates setup steps work

## 14.2 API Documentation
- [ ] **OpenAPI 3.0 schema** is auto-generated — `drf-spectacular` or `drf-yasg` integrated
- [ ] Schema is served at **`/api/schema/`** — downloadable YAML or JSON
- [ ] **Swagger UI** is served at `/api/docs/` — interactive exploration in non-production environments
- [ ] **ReDoc** is served at `/api/redoc/` — alternative readable format for non-technical stakeholders
- [ ] API docs are **disabled or access-controlled in production** — not publicly browsable
- [ ] Every endpoint has a **`summary`** — one line describing what it does
- [ ] Every endpoint has a **`description`** — explaining behavior, side effects, and non-obvious details
- [ ] Every endpoint documents **all possible response codes** — `200`, `201`, `400`, `401`, `403`, `404`, `422`, `429`, `500`
- [ ] Every endpoint documents **request body schema** — with field descriptions and examples
- [ ] Every endpoint documents **query parameters** — filter fields, ordering options, pagination params
- [ ] **Authentication requirements** are documented per endpoint — which scheme, what scopes
- [ ] **Enum fields** show all allowed values in the schema — not just `string`
- [ ] **Example requests and responses** are provided — not just schema structure
- [ ] **Deprecated endpoints** are marked with `deprecated: true` — with migration guidance
- [ ] Schema **drift is detected in CI** — generated schema committed and diff checked on every PR
- [ ] **Postman collection or Bruno collection** is maintained — importable for manual testing

## 14.3 Architecture Decision Records (ADRs)
- [ ] **ADR process is adopted** — a template and process exists for recording architectural decisions
- [ ] ADRs are stored in **`docs/adr/`** — numbered sequentially, e.g. `0001-use-postgresql.md`
- [ ] ADR template includes — **title, status, context, decision, consequences, alternatives considered**
- [ ] ADRs exist for all **non-obvious technology choices** — why PostgreSQL over MySQL, why Celery over Django Q
- [ ] ADRs exist for all **architectural patterns** — why service layer pattern, why RBAC over ABAC
- [ ] ADRs exist for all **significant rejected alternatives** — documenting why option X was not chosen
- [ ] ADRs have a **status** — `proposed`, `accepted`, `deprecated`, `superseded`
- [ ] **Superseded ADRs** link to the ADR that replaced them — not just marked deprecated with no context
- [ ] ADRs are **written at decision time** — not reconstructed months later from memory
- [ ] ADRs are **short and readable** — one to two pages, not essays
- [ ] New team members are **directed to read ADRs** — part of onboarding process
- [ ] ADRs are **searchable** — index file or README in `docs/adr/` linking all records

## 14.4 Code-Level Documentation
- [ ] **Every public module** has a module-level docstring — describing its purpose and scope
- [ ] **Every public class** has a class-level docstring — describing its responsibility and usage
- [ ] **Every public function and method** has a docstring — parameters, return value, raised exceptions
- [ ] Docstrings follow a **consistent format** — Google style, NumPy style, or Sphinx — enforced via `pydocstyle` or `ruff`
- [ ] **Complex algorithms** have an explanatory comment — describing the approach, not just the implementation
- [ ] **Non-obvious business rules** are documented inline — `# Per regulation X, amounts must be rounded up to nearest cent`
- [ ] **Workarounds and technical debt** are tagged — `# HACK:`, `# FIXME:`, `# TODO:` with a linked issue number
- [ ] **`TODO` comments without issue links are disallowed** — enforced via `ruff` or custom lint rule
- [ ] Comments explain **why**, not **what** — the code explains what; comments explain reasoning
- [ ] **No misleading or stale comments** — comments that describe what the code used to do are removed
- [ ] **Magic numbers** are replaced with named constants — or at minimum a comment explaining the value
- [ ] **`@deprecated`** decorator or docstring warning is on all deprecated functions — with migration guidance

## 14.5 Inline Documentation for Configuration
- [ ] **`.env.example`** has inline comments for every variable — explaining what it is and valid values
- [ ] **`settings/base.py`** has comments explaining non-obvious settings — not just Django defaults
- [ ] **`settings/production.py`** has comments on security-critical settings — why each is set as it is
- [ ] **`docker-compose.yml`** has comments on non-obvious service configuration
- [ ] **`Dockerfile`** has comments on non-obvious instructions — why a specific base image, what each `RUN` does
- [ ] **CI/CD pipeline YAML** has comments on complex steps — explaining what each job does and why
- [ ] **nginx configuration** has comments on non-standard directives
- [ ] **`pyproject.toml`** tool configurations have comments where configuration choices are non-obvious
- [ ] **`Makefile` targets** have comments — each target has a `## Description` comment for `make help`
- [ ] **`pre-commit-config.yaml`** has comments explaining why specific hooks are excluded or configured unusually

## 14.6 Onboarding Documentation
- [ ] A **dedicated onboarding guide** exists — `docs/onboarding.md` or equivalent
- [ ] Onboarding guide covers **development environment setup** — from zero to running tests in under 30 minutes
- [ ] Onboarding guide covers **codebase structure tour** — where to find things, how apps are organized
- [ ] Onboarding guide covers **development workflow** — branching strategy, PR process, code review expectations
- [ ] Onboarding guide covers **how to run, test, and debug** the application locally
- [ ] Onboarding guide covers **how CI/CD works** — what runs on PRs, what deploys automatically
- [ ] Onboarding guide covers **who owns what** — team contacts, Slack channels, escalation paths
- [ ] Onboarding guide covers **common pitfalls** — things that trip up new developers regularly
- [ ] Onboarding guide is **validated by new joiners** — they follow it on day one and report gaps
- [ ] Onboarding guide is **updated after every new hire** — fresh perspective catches stale instructions
- [ ] Onboarding guide covers **access provisioning** — what accounts and tools need to be set up
- [ ] **Onboarding checklist** exists — new developers check off each step, ensuring nothing is missed

## 14.7 Runbooks & Operational Documentation
- [ ] A **runbook exists for each environment** — how to access, deploy, rollback, and debug
- [ ] Runbooks cover **common failure scenarios** — database connection failures, Redis outages, high error rates
- [ ] Runbooks cover **how to run database migrations manually** — for emergency situations
- [ ] Runbooks cover **how to roll back a deployment** — step-by-step, not theoretical
- [ ] Runbooks cover **how to scale up** — adding workers, increasing instance sizes
- [ ] Runbooks cover **how to access logs** — in each environment, for each service
- [ ] Runbooks cover **how to run management commands** in production — via exec into container or equivalent
- [ ] Runbooks cover **how to connect to the production database** — safely and with minimal access
- [ ] **Incident response runbook** exists — steps to take when something is on fire
- [ ] Runbooks are **linked from monitoring alerts** — responders find them immediately when paged
- [ ] Runbooks are **tested periodically** — fire drills validate they actually work
- [ ] Runbooks are **version-controlled** — same repo as the application code

## 14.8 CHANGELOG & Release Notes
- [ ] **`CHANGELOG.md`** exists at the project root — maintained and current
- [ ] CHANGELOG follows **Keep a Changelog** format — `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`
- [ ] CHANGELOG is **updated on every PR** that introduces user-facing changes — not retroactively reconstructed
- [ ] CHANGELOG has a **`[Unreleased]` section** — accumulating changes before a release
- [ ] **Releases tag the CHANGELOG** — `[Unreleased]` becomes `[1.2.3] - 2024-03-15` on release
- [ ] CHANGELOG entries are **written for humans** — not git commit messages copy-pasted verbatim
- [ ] **Security fixes** are clearly marked in the CHANGELOG — `Security` section prominently placed
- [ ] **Breaking changes** are prominently marked — with migration guidance for API consumers
- [ ] **Git tags match CHANGELOG versions** — `v1.2.3` tag exists for every `[1.2.3]` entry
- [ ] CHANGELOG is **linked from the README** — easy to find for consumers and contributors

## 14.9 Contributing Guide
- [ ] **`CONTRIBUTING.md`** exists — for any project with more than one contributor
- [ ] Contributing guide covers **branching strategy** — `feature/`, `bugfix/`, `hotfix/` conventions
- [ ] Contributing guide covers **commit message conventions** — conventional commits or team standard
- [ ] Contributing guide covers **PR process** — how to open a PR, what the template requires, review expectations
- [ ] Contributing guide covers **code style expectations** — linking to linting and formatting setup
- [ ] Contributing guide covers **test requirements** — new features require tests, coverage expectations
- [ ] Contributing guide covers **how to add a dependency** — review process, approval requirements
- [ ] Contributing guide covers **how to report a bug** — issue template, expected information
- [ ] Contributing guide covers **how to request a feature** — discussion process before implementation
- [ ] Contributing guide covers **security vulnerability reporting** — responsible disclosure process
- [ ] **PR template** exists — `.github/pull_request_template.md` with checklist for authors
- [ ] **Issue templates** exist — separate templates for bug reports and feature requests

## 14.10 Dependency & License Documentation
- [ ] **`LICENSE`** file exists at the project root — correct license for the project type
- [ ] **Third-party licenses** are documented — `THIRD_PARTY_LICENSES.md` or equivalent
- [ ] **`pip-licenses`** output is committed or generated in CI — full dependency license inventory
- [ ] **License compatibility** is verified — GPL dependencies not used in closed-source commercial projects without legal review
- [ ] **New dependency additions** require license review — part of the PR checklist
- [ ] **Internal package licenses** are defined — every internal package has a `LICENSE` file
- [ ] License information is **machine-readable** — `pyproject.toml` `license` field is set correctly

## 14.11 Documentation Infrastructure
- [ ] **Documentation lives close to the code** — in the same repository, not a disconnected wiki
- [ ] A **`docs/`** directory exists — for anything beyond the README
- [ ] Documentation is written in **Markdown** — universally readable, version-controllable, renderable on GitHub
- [ ] **`mkdocs`** or **Sphinx** is used for larger documentation sites — with auto-generated API reference
- [ ] Documentation site is **deployed automatically** — on merge to main via GitHub Pages, ReadTheDocs, or equivalent
- [ ] **Broken links** are detected in CI — `markdown-link-check` or `lychee` runs on every PR
- [ ] **Spelling errors** are checked in CI — `cspell` or `typos` runs on documentation files
- [ ] Documentation is **searchable** — either via MkDocs search or a documentation platform
- [ ] Diagrams are stored as **code** — `mermaid`, `PlantUML`, or `draw.io` XML — not binary image files
- [ ] **Diagram source files are version-controlled** — changes to architecture are tracked and reviewable

## 14.12 Documentation Quality Standards
- [ ] Documentation is **accurate** — reviewed and updated every time the related code changes
- [ ] Documentation is **consistent** — same terminology used throughout, defined in a glossary if needed
- [ ] A **glossary** exists for domain-specific terms — `docs/glossary.md` defining project-specific vocabulary
- [ ] Documentation is **concise** — no padding or unnecessary repetition
- [ ] Documentation uses **active voice** — "Run the migration" not "The migration should be run"
- [ ] Documentation includes **examples** — code snippets, curl commands, screenshots where helpful
- [ ] Documentation is **reviewed in PRs** — doc changes treated as first-class code changes
- [ ] **Stale documentation is removed** — outdated docs are actively harmful, deleted rather than left
- [ ] Documentation has a **designated owner** — someone responsible for keeping it current
- [ ] Documentation quality is part of the **definition of done** — a feature is not complete without updated docs

## 14.13 Internal Technical Documentation (Added)
- [ ] **Feature implementation docs** exist — describing how major features are implemented
- [ ] Implementation docs cover **data flow** — from request through service layer to response
- [ ] Implementation docs cover **key design decisions** within each feature — why this approach was chosen
- [ ] Implementation docs cover **integration points** — how features interact with each other
- [ ] **System boundaries** are documented — what is in scope vs. delegated to external services
- [ ] **Data model documentation** exists — ER diagrams or equivalent showing model relationships
- [ ] **Service interaction diagrams** exist — showing how services call each other
- [ ] **Testing strategy** is documented per module — what is unit tested vs. integration tested
- [ ] Implementation docs are **linked from code** — docstrings reference relevant docs
- [ ] Implementation docs are **updated with the code** — not left to rot after initial feature development

## 14.14 Progress Tracking & Project Documentation (Added)
- [ ] **Progress tracking system** exists — structured entries logging what was built and when
- [ ] Progress entries follow a **consistent schema** — category, description, files changed, decisions made
- [ ] Progress entries capture **key decisions and rationale** — not just what was done but why
- [ ] **Feature planning docs** exist — describing requirements before implementation begins
- [ ] Feature descriptions exist — **what** the feature does, for **whom**, and **why**
- [ ] Planning and description docs live in **`docs/`** — organized by workspace (backend, frontend, etc.)
- [ ] Progress entries are **machine-readable** — JSON or structured format for programmatic access
- [ ] **Review/audit history** is maintained — versioned reports showing code quality over time
