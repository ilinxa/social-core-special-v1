# 14 — Documentation Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 14.1 README.md

| ID | Rule | Verdict |
|----|------|---------|
| 14.1.1 | FAIL if no README.md at project root | PASS/FAIL |
| 14.1.2 | WARN if README has no project description | PASS/WARN |
| 14.1.3 | WARN if tech stack not listed in README | PASS/WARN |
| 14.1.4 | INFO if no architecture overview | PASS/INFO |
| 14.1.5 | WARN if prerequisites not documented | PASS/WARN |
| 14.1.6 | WARN if no local dev setup instructions | PASS/WARN |
| 14.1.7 | INFO if setup not verified regularly | PASS/INFO |
| 14.1.8 | WARN if README doesn't explain how to run tests | PASS/WARN |
| 14.1.9 | WARN if README doesn't explain linting/formatting | PASS/WARN |
| 14.1.10 | WARN if no env var reference or link to .env.example | PASS/WARN |
| 14.1.11 | INFO if common tasks not documented | PASS/INFO |
| 14.1.12 | INFO if no links to further docs | PASS/INFO |
| 14.1.13 | WARN if README is demonstrably outdated | PASS/WARN |
| 14.1.14 | INFO if no last verified date | PASS/INFO |

## 14.2 API Documentation

| ID | Rule | Verdict |
|----|------|---------|
| 14.2.1 | WARN if no auto-generated OpenAPI schema | PASS/WARN |
| 14.2.2 | PASS if schema served at accessible URL | PASS |
| 14.2.3 | PASS if Swagger UI available in dev | PASS |
| 14.2.4 | PASS if ReDoc available | PASS |
| 14.2.5 | WARN if API docs publicly accessible in production settings | PASS/WARN |
| 14.2.6 | WARN if most endpoints lack summaries | PASS/WARN |
| 14.2.7 | INFO if endpoints lack detailed descriptions | PASS/INFO |
| 14.2.8 | INFO if response codes not exhaustively documented | PASS/INFO |
| 14.2.9 | INFO if request body schemas lack descriptions | PASS/INFO |
| 14.2.10 | INFO if query params not documented | PASS/INFO |
| 14.2.11 | WARN if auth requirements not clear in schema | PASS/WARN |
| 14.2.12 | INFO if enum values not shown | PASS/INFO |
| 14.2.13 | INFO if no example requests/responses | PASS/INFO |
| 14.2.14 | INFO if deprecated endpoints not marked | PASS/INFO |
| 14.2.15 | INFO if schema drift not detected in CI | PASS/INFO |
| 14.2.16 | INFO if no Postman/Bruno collection | PASS/INFO |

## 14.3 Architecture Decision Records (ADRs)

| ID | Rule | Verdict |
|----|------|---------|
| 14.3.1 | INFO if no ADR process adopted — acceptable for early stage | PASS/INFO |
| 14.3.2 | INFO if ADRs not in dedicated directory | PASS/INFO |
| 14.3.3 | INFO if no ADR template | PASS/INFO |
| 14.3.4 | WARN if major technology choices not documented anywhere | PASS/WARN |
| 14.3.5 | WARN if architectural patterns not explained anywhere | PASS/WARN |
| 14.3.6 | INFO if rejected alternatives not documented | PASS/INFO |
| 14.3.7 | INFO if ADRs have no status field | PASS/INFO |
| 14.3.8 | INFO if superseded ADRs don't link forward | PASS/INFO |
| 14.3.9 | INFO if ADRs written retroactively | PASS/INFO |
| 14.3.10 | PASS if ADRs are concise | PASS |
| 14.3.11 | INFO if onboarding doesn't reference ADRs | PASS/INFO |
| 14.3.12 | INFO if no ADR index | PASS/INFO |

## 14.4 Code-Level Documentation

| ID | Rule | Verdict |
|----|------|---------|
| 14.4.1 | WARN if most public modules lack docstrings | PASS/WARN |
| 14.4.2 | WARN if most public classes lack docstrings | PASS/WARN |
| 14.4.3 | INFO if most public functions lack docstrings — acceptable if code is self-documenting | PASS/INFO |
| 14.4.4 | INFO if no enforced docstring format | PASS/INFO |
| 14.4.5 | WARN if complex algorithms have no comments | PASS/WARN |
| 14.4.6 | PASS if non-obvious business rules are documented inline | PASS |
| 14.4.7 | INFO if TODO/FIXME/HACK not consistently tagged with issue links | PASS/INFO |
| 14.4.8 | INFO if bare TODOs not linted | PASS/INFO |
| 14.4.9 | PASS if comments explain why, not what | PASS |
| 14.4.10 | WARN if stale/misleading comments found | PASS/WARN |
| 14.4.11 | WARN if unexplained magic numbers found in business logic | PASS/WARN |
| 14.4.12 | INFO if no @deprecated decorator used | PASS/INFO |

## 14.5 Inline Documentation for Configuration

| ID | Rule | Verdict |
|----|------|---------|
| 14.5.1 | PASS if .env.example has inline comments | PASS |
| 14.5.2 | PASS if settings/base.py has comments on non-obvious settings | PASS |
| 14.5.3 | PASS if settings/production.py has security comments | PASS |
| 14.5.4 | INFO if docker-compose.yml lacks comments | PASS/INFO |
| 14.5.5 | INFO if Dockerfile lacks comments | PASS/INFO |
| 14.5.6 | INFO if CI/CD YAML lacks comments — N/A if no CI | PASS/INFO |
| 14.5.7 | PASS if nginx config has comments | PASS |
| 14.5.8 | INFO if pyproject.toml lacks comments | PASS/INFO |
| 14.5.9 | PASS if Makefile targets have ## description comments | PASS |
| 14.5.10 | INFO if pre-commit config lacks comments — N/A if no pre-commit | PASS/INFO |

## 14.6 Onboarding Documentation

| ID | Rule | Verdict |
|----|------|---------|
| 14.6.1 | WARN if no onboarding guide exists | PASS/WARN |
| 14.6.2 | WARN if onboarding doesn't cover dev environment setup | PASS/WARN |
| 14.6.3 | INFO if no codebase structure tour | PASS/INFO |
| 14.6.4 | INFO if no workflow documentation | PASS/INFO |
| 14.6.5 | WARN if onboarding doesn't explain how to run/test/debug | PASS/WARN |
| 14.6.6 | INFO if CI/CD not covered — N/A if no CI | PASS/INFO |
| 14.6.7 | INFO if no team contacts documented | PASS/INFO |
| 14.6.8 | INFO if common pitfalls not documented | PASS/INFO |
| 14.6.9 | INFO if onboarding not validated by new joiners | PASS/INFO |
| 14.6.10 | INFO if onboarding not updated after new hires | PASS/INFO |
| 14.6.11 | INFO if access provisioning not documented | PASS/INFO |
| 14.6.12 | INFO if no onboarding checklist | PASS/INFO |

## 14.7 Runbooks & Operational Documentation

| ID | Rule | Verdict |
|----|------|---------|
| 14.7.1 | INFO if no per-environment runbook — acceptable for early stage | PASS/INFO |
| 14.7.2 | INFO if common failure scenarios not documented | PASS/INFO |
| 14.7.3 | INFO if manual migration procedure not documented | PASS/INFO |
| 14.7.4 | INFO if rollback procedure not documented | PASS/INFO |
| 14.7.5 | INFO if scaling procedure not documented | PASS/INFO |
| 14.7.6 | INFO if log access not documented | PASS/INFO |
| 14.7.7 | INFO if management command access not documented | PASS/INFO |
| 14.7.8 | INFO if DB access procedure not documented | PASS/INFO |
| 14.7.9 | INFO if no incident response runbook | PASS/INFO |
| 14.7.10 | INFO if runbooks not linked from alerts | PASS/INFO |
| 14.7.11 | INFO if runbooks not tested | PASS/INFO |
| 14.7.12 | PASS if runbooks are version-controlled (in docs/ or same repo) | PASS |

## 14.8 CHANGELOG & Release Notes

| ID | Rule | Verdict |
|----|------|---------|
| 14.8.1 | WARN if no CHANGELOG.md exists | PASS/WARN |
| 14.8.2 | INFO if CHANGELOG doesn't follow Keep a Changelog format | PASS/INFO |
| 14.8.3 | INFO if CHANGELOG not updated on PRs | PASS/INFO |
| 14.8.4 | INFO if no [Unreleased] section | PASS/INFO |
| 14.8.5 | INFO if releases don't tag CHANGELOG | PASS/INFO |
| 14.8.6 | INFO if CHANGELOG entries are just commit messages | PASS/INFO |
| 14.8.7 | WARN if security fixes not clearly marked | PASS/WARN |
| 14.8.8 | WARN if breaking changes not marked | PASS/WARN |
| 14.8.9 | INFO if git tags don't match CHANGELOG versions | PASS/INFO |
| 14.8.10 | INFO if CHANGELOG not linked from README | PASS/INFO |

## 14.9 Contributing Guide

| ID | Rule | Verdict |
|----|------|---------|
| 14.9.1 | INFO if no CONTRIBUTING.md — acceptable for small/solo team | PASS/INFO |
| 14.9.2 | INFO if branching strategy not documented | PASS/INFO |
| 14.9.3 | INFO if commit conventions not documented | PASS/INFO |
| 14.9.4 | INFO if PR process not documented | PASS/INFO |
| 14.9.5 | INFO if code style not documented | PASS/INFO |
| 14.9.6 | INFO if test requirements not documented | PASS/INFO |
| 14.9.7 | INFO if dependency addition process not documented | PASS/INFO |
| 14.9.8 | INFO if bug reporting not documented | PASS/INFO |
| 14.9.9 | INFO if feature request process not documented | PASS/INFO |
| 14.9.10 | WARN if no security vulnerability reporting process | PASS/WARN |
| 14.9.11 | INFO if no PR template | PASS/INFO |
| 14.9.12 | INFO if no issue templates | PASS/INFO |

## 14.10 Dependency & License Documentation

| ID | Rule | Verdict |
|----|------|---------|
| 14.10.1 | WARN if no LICENSE file | PASS/WARN |
| 14.10.2 | INFO if third-party licenses not documented | PASS/INFO |
| 14.10.3 | INFO if pip-licenses not used | PASS/INFO |
| 14.10.4 | WARN if license compatibility not considered | PASS/WARN |
| 14.10.5 | INFO if no license review for new deps | PASS/INFO |
| 14.10.6 | INFO if internal packages lack LICENSE | PASS/INFO |
| 14.10.7 | INFO if license not in pyproject.toml | PASS/INFO |

## 14.11 Documentation Infrastructure

| ID | Rule | Verdict |
|----|------|---------|
| 14.11.1 | PASS if docs live in the code repo | PASS |
| 14.11.2 | PASS if docs/ directory exists | PASS |
| 14.11.3 | PASS if docs are in Markdown | PASS |
| 14.11.4 | INFO if no mkdocs/Sphinx — acceptable for early stage | PASS/INFO |
| 14.11.5 | INFO if no auto-deployed doc site | PASS/INFO |
| 14.11.6 | INFO if no broken link check in CI | PASS/INFO |
| 14.11.7 | INFO if no spell check in CI | PASS/INFO |
| 14.11.8 | INFO if docs not searchable | PASS/INFO |
| 14.11.9 | PASS if diagrams stored as code (mermaid, PlantUML, draw.io XML) | PASS |
| 14.11.10 | PASS if diagram sources are version-controlled | PASS |

## 14.12 Documentation Quality Standards

| ID | Rule | Verdict |
|----|------|---------|
| 14.12.1 | WARN if docs demonstrably inaccurate | PASS/WARN |
| 14.12.2 | INFO if inconsistent terminology found | PASS/INFO |
| 14.12.3 | INFO if no glossary | PASS/INFO |
| 14.12.4 | PASS if docs are concise | PASS |
| 14.12.5 | INFO if docs use passive voice heavily | PASS/INFO |
| 14.12.6 | PASS if docs include examples | PASS |
| 14.12.7 | INFO if docs not reviewed in PRs | PASS/INFO |
| 14.12.8 | WARN if stale docs found | PASS/WARN |
| 14.12.9 | INFO if no designated doc owner | PASS/INFO |
| 14.12.10 | INFO if docs not part of definition of done | PASS/INFO |

## 14.13 Internal Technical Documentation (Added)

| ID | Rule | Verdict |
|----|------|---------|
| 14.13.1 | PASS if feature implementation docs exist | PASS |
| 14.13.2 | INFO if data flow not documented | PASS/INFO |
| 14.13.3 | PASS if key design decisions documented within features | PASS |
| 14.13.4 | INFO if integration points not documented | PASS/INFO |
| 14.13.5 | INFO if system boundaries not documented | PASS/INFO |
| 14.13.6 | INFO if no ER diagrams or data model docs | PASS/INFO |
| 14.13.7 | INFO if no service interaction diagrams | PASS/INFO |
| 14.13.8 | INFO if testing strategy not documented per module | PASS/INFO |
| 14.13.9 | INFO if implementation docs not linked from code | PASS/INFO |
| 14.13.10 | WARN if implementation docs demonstrably outdated | PASS/WARN |

## 14.14 Progress Tracking & Project Documentation (Added)

| ID | Rule | Verdict |
|----|------|---------|
| 14.14.1 | PASS if progress tracking system exists | PASS |
| 14.14.2 | PASS if progress entries follow consistent schema | PASS |
| 14.14.3 | PASS if entries capture decisions and rationale | PASS |
| 14.14.4 | PASS if feature planning docs exist | PASS |
| 14.14.5 | PASS if feature description docs exist | PASS |
| 14.14.6 | PASS if planning/description docs organized in docs/ | PASS |
| 14.14.7 | INFO if progress entries not machine-readable | PASS/INFO |
| 14.14.8 | PASS if review/audit history maintained | PASS |
