# Auth App

## Domain Rules
- JWT tokens: 15min access, 7day refresh. Refresh token gets blacklisted on logout.
- OAuth backends live in `services/oauth/` — google.py and apple.py. Configured via env vars only.
- Device sessions track active logins. New login on a new device does NOT invalidate others.
- Token endpoints: login (POST → access+refresh), refresh, logout (blacklists refresh token).