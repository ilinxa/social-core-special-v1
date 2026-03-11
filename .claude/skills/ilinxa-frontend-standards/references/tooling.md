# Tooling: Dev Environment, CI/CD, and Deployment

## Table of Contents
1. [Dev Environment](#dev-environment)
2. [CI/CD Pipeline](#cicd-pipeline)
3. [Deployment](#deployment)

---

## Dev Environment

### Node.js

Use `.nvmrc` at project root to pin version:
```
22
```

```bash
nvm use   # reads .nvmrc
```

Package manager: **npm** (default). Use `package-lock.json`, commit it.

### VS Code

Workspace settings (`.vscode/settings.json`):
```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.codeActionsOnSave": { "source.fixAll.eslint": "explicit" },
  "typescript.tsdk": "node_modules/typescript/lib",
  "typescript.enablePromptUseWorkspaceTsdk": true,
  "[typescript]": { "editor.defaultFormatter": "esbenp.prettier-vscode" },
  "[typescriptreact]": { "editor.defaultFormatter": "esbenp.prettier-vscode" }
}
```

Recommended extensions (`.vscode/extensions.json`):
```json
{
  "recommendations": [
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint",
    "bradlc.vscode-tailwindcss",
    "formulahendry.auto-rename-tag",
    "mikestead.dotenv"
  ]
}
```

### Environment Variables

```
.env                  # shared defaults (committed if no secrets)
.env.local            # local overrides (gitignored)
.env.development      # dev-specific
.env.production       # prod-specific (gitignored)
```

Rules:
- Vite: prefix with `VITE_` for client exposure. Next.js: prefix with `NEXT_PUBLIC_`.
- Never commit real secrets. Use `.env.local` or CI secrets.
- Document all required vars in `.env.example` (committed, no real values).

---

## CI/CD Pipeline

GitHub Actions, two workflows:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push to any branch, PRs to `develop`/`main` | Lint, typecheck, test, build |
| `deploy.yml` | Push to `main` | Deploy to production |

### CI Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [develop, main]
  pull_request:
    branches: [develop, main]

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version-file: ".nvmrc"
          cache: "npm"

      - run: npm ci

      - name: Lint
        run: npm run lint

      - name: Type Check
        run: npm run typecheck

      - name: Test
        run: npm run test -- --coverage

      - name: Build
        run: npm run build

      - name: Upload Coverage
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage
          path: coverage/
```

### Branch Protection

Required for `develop` and `main`:
- CI must pass (lint, typecheck, tests, build)
- At least 1 approval
- No direct pushes
- Conversations resolved

### Caching

npm cache: handled by `actions/setup-node` with `cache: "npm"`.

Next.js build cache:
```yaml
- uses: actions/cache@v4
  with:
    path: .next/cache
    key: nextjs-${{ hashFiles('**/package-lock.json') }}-${{ hashFiles('src/**') }}
    restore-keys: nextjs-${{ hashFiles('**/package-lock.json') }}-
```

---

## Deployment

### Environment Structure

| Environment | Branch | URL | Purpose |
|-------------|--------|-----|---------|
| Development | `develop` | `dev.app.com` | Internal testing |
| Staging | `develop` (promoted) | `staging.app.com` | QA / client review |
| Production | `main` | `app.com` | Live |

### Vercel (Recommended for Next.js)

```bash
npm i -g vercel && vercel link
```

Auto-deploys: push to branch → preview. Merge to `main` → production.

Optional `vercel.json`:
```json
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" }
      ]
    }
  ]
}
```

### Docker (VPS / self-hosted)

```dockerfile
# Dockerfile (Next.js standalone)
FROM node:22-alpine AS base

FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
```

Requires `output: "standalone"` in `next.config.ts`.

### Security Headers

Apply via middleware, `next.config.ts`, or reverse proxy:

```typescript
// next.config.ts
const headers = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-XSS-Protection", value: "1; mode=block" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

// Strict-Transport-Security: added by hosting platform (Vercel, Cloudflare) — don't duplicate
// Content-Security-Policy: project-specific — configure per project in kickoff
```

### Rollback

**Vercel:** Dashboard → Deployments → select previous → "Promote to Production". Instant.

**Docker/VPS:** Keep last 3 images tagged. `docker compose up -d --pull always` with previous tag, or `docker rollback` script.

**Rule:** If a deploy causes a production issue, rollback first, investigate second.

### Pre-Deployment Checklist

- [ ] All CI checks pass (lint, typecheck, tests, build)
- [ ] Environment variables set for target environment
- [ ] Bundle size within budget
- [ ] No `console.log` in production code (ESLint rule or build-time strip)
- [ ] Error tracking configured (Sentry or equivalent)
- [ ] Security headers applied
- [ ] `robots.txt` and `sitemap.xml` present (if public-facing)
- [ ] HTTPS enforced
