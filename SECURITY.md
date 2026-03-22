# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest  | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

### How to Report

1. Email the security team with:
   - Description of the vulnerability
   - Steps to reproduce
   - Affected components (backend, frontend, infrastructure)
   - Severity assessment (if possible)

2. You will receive an acknowledgment within **48 hours**.

3. We will investigate and provide a timeline for a fix within **5 business days**.

### What to Expect

- Confirmation of receipt within 48 hours
- Assessment and severity classification within 5 business days
- A fix or mitigation plan communicated privately
- Credit in release notes (if desired) after the fix is deployed

## Security Practices

This project implements:

- JWT authentication with short-lived access tokens (15 min) and refresh tokens (7 days)
- Progressive account lockout after repeated failed login attempts
- Role-based access control (RBAC) with permission-level enforcement
- Input validation via DRF serializers and custom validators
- HTML sanitization (nh3) for rich text content
- Rate limiting on authentication endpoints
- HSTS, CSRF protection, and secure cookie settings in production
- Secret detection via pre-commit hooks (detect-secrets)
- Dependency auditing via pip-audit in CI
- Automated security scanning in GitHub Actions
