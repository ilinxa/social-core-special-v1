# Nginx Configuration Instructions

This document explains the Nginx setup for both development and production environments.

---

## Table of Contents

1. [Overview](#overview)
2. [Configuration Files](#configuration-files)
3. [Development Setup](#development-setup)
4. [Production Setup](#production-setup)
5. [SSL/TLS Configuration](#ssltls-configuration)
6. [Common Operations](#common-operations)
7. [Troubleshooting](#troubleshooting)

---

## Overview

### Why Nginx?

Nginx serves as a **reverse proxy** in front of your Django application:

```
┌─────────────────────────────────────────────────────────────┐
│                         INTERNET                             │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                     NGINX (Port 80/443)                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  - SSL Termination                                     │  │
│  │  - Static file serving                                 │  │
│  │  - Load balancing                                      │  │
│  │  - Request buffering                                   │  │
│  │  - Gzip compression                                    │  │
│  │  - Rate limiting                                       │  │
│  └───────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Django 1   │    │   Django 2   │    │   Django N   │
│  (Gunicorn)  │    │  (Gunicorn)  │    │  (Gunicorn)  │
└──────────────┘    └──────────────┘    └──────────────┘
```

### Benefits

| Feature | Benefit |
|---------|---------|
| **Static Files** | Serves CSS, JS, images efficiently (no Python overhead) |
| **SSL Termination** | Handles HTTPS, decrypts requests before Django |
| **Load Balancing** | Distributes traffic across multiple Django instances |
| **Buffering** | Buffers slow client connections, freeing up Django workers |
| **Compression** | Gzip compresses responses to reduce bandwidth |
| **Security** | Hides Django errors, adds security headers |

---

## Configuration Files

### File Structure

```
docker/nginx/
├── NGINX_INSTRUCTIONS.md    # This document
├── nginx.conf               # Production configuration
├── nginx.dev.conf           # Development configuration
└── ssl/                     # SSL certificates (gitignored)
    ├── .gitkeep
    ├── cert.pem             # SSL certificate
    └── key.pem              # SSL private key
```

### Which Config to Use

| Environment | File | Features |
|-------------|------|----------|
| Development | `nginx.dev.conf` | No SSL, debug-friendly, CORS headers |
| Production | `nginx.conf` | SSL, security headers, gzip, caching |

---

## Development Setup

### When to Use Nginx in Dev

You typically **don't need** Nginx for development because:
- Django's runserver handles static files
- No need for SSL locally
- Simpler debugging

**Use Nginx in dev when:**
- Testing production-like setup
- Testing WebSocket proxying
- Testing static file serving
- Reproducing production issues

### Running with Docker

```bash
# Start development stack with Nginx
docker compose -f docker-compose.dev.yml --profile nginx up -d
```

### Manual Testing

```bash
# Test Nginx configuration
docker compose exec nginx nginx -t

# Reload configuration
docker compose exec nginx nginx -s reload
```

---

## Production Setup

### Prerequisites

1. **Domain name** pointing to your server
2. **SSL certificate** (see SSL section below)
3. **Docker and Docker Compose** installed

### Deployment Steps

1. **Copy SSL certificates** to `docker/nginx/ssl/`:
   ```bash
   cp /path/to/fullchain.pem docker/nginx/ssl/cert.pem
   cp /path/to/privkey.pem docker/nginx/ssl/key.pem
   chmod 600 docker/nginx/ssl/*.pem
   ```

2. **Update environment variables**:
   ```bash
   # In .env file
   DOMAIN_NAME=yourdomain.com
   ```

3. **Start the stack**:
   ```bash
   docker compose up -d
   ```

4. **Verify**:
   ```bash
   curl -I https://yourdomain.com
   ```

### Enabling Nginx in docker-compose.yml

Uncomment the nginx service in `docker-compose.yml`:

```yaml
services:
  nginx:
    image: nginx:1.25-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./docker/nginx/ssl:/etc/nginx/ssl:ro
      - static_files:/app/staticfiles:ro
      - media_files:/app/media:ro
    depends_on:
      - app
    networks:
      - frontend_network
```

---

## SSL/TLS Configuration

### Option 1: Let's Encrypt (Recommended)

Free, automated SSL certificates.

```bash
# Install certbot
sudo apt install certbot

# Get certificate (standalone mode)
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Certificates are saved to:
# /etc/letsencrypt/live/yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/yourdomain.com/privkey.pem

# Copy to your project
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem docker/nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem docker/nginx/ssl/key.pem
```

**Auto-renewal** (add to crontab):
```bash
0 0 1 * * certbot renew --quiet && docker compose exec nginx nginx -s reload
```

### Option 2: Self-Signed (Development Only)

```bash
# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout docker/nginx/ssl/key.pem \
    -out docker/nginx/ssl/cert.pem \
    -subj "/CN=localhost"
```

### Option 3: Cloudflare (Origin Certificate)

If using Cloudflare as CDN:

1. Go to Cloudflare Dashboard → SSL/TLS → Origin Server
2. Create Certificate
3. Copy certificate and key to `docker/nginx/ssl/`

---

## Common Operations

### Useful Commands

```bash
# Test configuration syntax
docker compose exec nginx nginx -t

# Reload configuration (no downtime)
docker compose exec nginx nginx -s reload

# View access logs
docker compose logs -f nginx

# View error logs
docker compose exec nginx tail -f /var/log/nginx/error.log

# Check Nginx status
docker compose exec nginx nginx -V
```

### Maintenance Mode

To show a maintenance page:

```bash
# Create maintenance file
touch docker/nginx/maintenance.html

# Nginx will serve this when backend is down (configured in nginx.conf)
```

### Rate Limiting

The production config includes rate limiting:

```nginx
# Limit requests per IP
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

# In location block
location /api/ {
    limit_req zone=api burst=20 nodelay;
    # ...
}
```

Adjust `rate=10r/s` (10 requests/second) as needed.

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| 502 Bad Gateway | Django not running | Check `docker compose ps` |
| 504 Gateway Timeout | Django too slow | Increase `proxy_read_timeout` |
| SSL certificate error | Wrong cert path | Verify paths in `nginx.conf` |
| Static files 404 | Volume not mounted | Check volume mounts |
| WebSocket fails | Missing upgrade headers | Check proxy headers |

### Debug Steps

1. **Check Nginx is running**:
   ```bash
   docker compose ps nginx
   ```

2. **Check configuration**:
   ```bash
   docker compose exec nginx nginx -t
   ```

3. **Check logs**:
   ```bash
   docker compose logs nginx
   ```

4. **Test backend directly**:
   ```bash
   curl http://localhost:8000/admin/
   ```

5. **Check DNS resolution inside container**:
   ```bash
   docker compose exec nginx nslookup app
   ```

### Performance Tuning

For high-traffic sites:

```nginx
# Increase worker connections
events {
    worker_connections 4096;
}

# Enable sendfile for static files
sendfile on;
tcp_nopush on;
tcp_nodelay on;

# Increase buffer sizes
proxy_buffer_size 128k;
proxy_buffers 4 256k;
proxy_busy_buffers_size 256k;
```

---

## Quick Reference

### Nginx Signals

| Signal | Command | Effect |
|--------|---------|--------|
| reload | `nginx -s reload` | Reload config, no downtime |
| stop | `nginx -s stop` | Fast shutdown |
| quit | `nginx -s quit` | Graceful shutdown |
| reopen | `nginx -s reopen` | Reopen log files |

### Important Paths (Inside Container)

| Path | Purpose |
|------|---------|
| `/etc/nginx/nginx.conf` | Main configuration |
| `/var/log/nginx/access.log` | Access logs |
| `/var/log/nginx/error.log` | Error logs |
| `/app/staticfiles/` | Django static files |
| `/app/media/` | User uploaded files |
