# Docker Scripts Instructions

This document explains the utility scripts for managing your Django Docker deployment.

---

## Table of Contents

1. [Overview](#overview)
2. [Script Files](#script-files)
3. [Database Backup](#database-backup)
4. [Database Restore](#database-restore)
5. [Wait-for-it](#wait-for-it)
6. [Automation](#automation)
7. [Best Practices](#best-practices)

---

## Overview

### Script Inventory

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `backup-db.sh` | Create database backup | Before deployments, daily backups |
| `restore-db.sh` | Restore from backup | Disaster recovery, rollback |
| `wait-for-it.sh` | Wait for service availability | Docker entrypoints |

### Prerequisites

```bash
# Make scripts executable
chmod +x docker/scripts/*.sh
```

---

## Database Backup

### Basic Usage

```bash
# Create backup with timestamp (e.g., backup_20240115_143022.sql.gz)
./docker/scripts/backup-db.sh

# Create backup with custom name
./docker/scripts/backup-db.sh pre_migration

# Show help
./docker/scripts/backup-db.sh --help
```

### What It Creates

```
backups/
├── backup_20240115_143022.sql.gz   # Compressed SQL dump
└── backup_20240115_143022.meta     # Backup metadata
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_DB` | `backend_core_db` | Database name |
| `POSTGRES_USER` | `django_user` | Database user |
| `POSTGRES_PASSWORD` | (required) | Database password |
| `POSTGRES_HOST` | `db` | Database host |
| `BACKUP_DIR` | `./backups` | Where to store backups |
| `BACKUP_RETENTION_DAYS` | `0` (disabled) | Auto-delete old backups |

### Example Output

```
[INFO] Starting database backup...
[INFO] Database: backend_core_db
[INFO] Host: db:5432
[INFO] Output: ./backups/backup_20240115_143022.sql.gz
[INFO] Running from host, using docker exec
[INFO] Backup completed successfully!
[INFO] File: ./backups/backup_20240115_143022.sql.gz
[INFO] Size: 2.5M
[INFO] Done!
```

---

## Database Restore

### Basic Usage

```bash
# Restore from a backup file
./docker/scripts/restore-db.sh ./backups/backup_20240115_143022.sql.gz

# List available backups
./docker/scripts/restore-db.sh --list

# Show help
./docker/scripts/restore-db.sh --help
```

### Safety Features

1. **Confirmation prompt** - Requires typing "yes" to proceed
2. **Connection termination** - Safely disconnects active users
3. **Single transaction** - Atomic restore (all or nothing)

### Example Output

```
╔══════════════════════════════════════════════════════════════╗
║                        WARNING                               ║
╠══════════════════════════════════════════════════════════════╣
║  This will OVERWRITE all data in database: backend_core_db   ║
║  Backup file: ./backups/backup_20240115_143022.sql.gz        ║
╚══════════════════════════════════════════════════════════════╝

Are you sure you want to continue? (yes/no): yes
[INFO] Starting database restore...
[INFO] Database: backend_core_db
[INFO] Host: db:5432
[INFO] Backup: ./backups/backup_20240115_143022.sql.gz
[INFO] Running from host, using docker exec
[INFO] Restore completed successfully!

[INFO] Post-restore recommendations:
  1. Run migrations: docker compose exec app python manage.py migrate
  2. Check data: docker compose exec app python manage.py shell
  3. Restart app: docker compose restart app

[INFO] Done!
```

---

## Wait-for-it

### Purpose

Waits for a TCP service to become available before executing a command. Essential for Docker containers that depend on other services.

### Basic Usage

```bash
# Wait for PostgreSQL
./docker/scripts/wait-for-it.sh db:5432

# Wait for Redis with 60 second timeout
./docker/scripts/wait-for-it.sh redis:6379 -t 60

# Wait for database, then run migrations
./docker/scripts/wait-for-it.sh db:5432 -- python manage.py migrate

# Wait for multiple services (chain them)
./docker/scripts/wait-for-it.sh db:5432 && \
./docker/scripts/wait-for-it.sh redis:6379 && \
python manage.py runserver
```

### Using in Docker Entrypoint

**entrypoint.sh:**
```bash
#!/bin/sh
set -e

# Wait for dependencies
/app/scripts/wait-for-it.sh db:5432 -t 60
/app/scripts/wait-for-it.sh redis:6379 -t 30

# Run migrations
python manage.py migrate --noinput

# Start server
exec "$@"
```

### Options

| Option | Description |
|--------|-------------|
| `host:port` | Service to wait for |
| `-t TIMEOUT` | Timeout in seconds (default: 30) |
| `-q, --quiet` | Suppress output |
| `-- COMMAND` | Command to run after service is available |

---

## Automation

### Automated Daily Backups

Add to your server's crontab:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /path/to/project && ./docker/scripts/backup-db.sh daily_$(date +\%Y\%m\%d) >> /var/log/db-backup.log 2>&1
```

### Pre-Deployment Backup

Add to your CI/CD pipeline:

```yaml
# GitHub Actions example
- name: Backup database before deployment
  run: |
    ./docker/scripts/backup-db.sh pre_deploy_${{ github.sha }}
```

### Backup Rotation

Enable automatic cleanup of old backups:

```bash
# Keep backups for 7 days
BACKUP_RETENTION_DAYS=7 ./docker/scripts/backup-db.sh
```

### S3 Upload (Optional)

Add to backup script or run separately:

```bash
# Upload to S3 after backup
aws s3 cp ./backups/backup_*.sql.gz s3://your-bucket/backups/

# Or use a dedicated upload script
./docker/scripts/backup-db.sh && \
aws s3 sync ./backups/ s3://your-bucket/backups/ --exclude "*" --include "*.sql.gz"
```

---

## Best Practices

### Backup Strategy

| Backup Type | Frequency | Retention | Use Case |
|-------------|-----------|-----------|----------|
| **Daily** | Every day | 7 days | Regular recovery |
| **Weekly** | Every Sunday | 4 weeks | Point-in-time recovery |
| **Monthly** | 1st of month | 12 months | Long-term archive |
| **Pre-deploy** | Before each deploy | 5 versions | Quick rollback |

### Recommended Workflow

```bash
# Before any major change
./docker/scripts/backup-db.sh pre_change

# Make changes
docker compose exec app python manage.py migrate

# If something goes wrong
./docker/scripts/restore-db.sh ./backups/pre_change.sql.gz
docker compose restart app
```

### Security Recommendations

1. **Encrypt backups** for sensitive data:
   ```bash
   # Encrypt with GPG
   gpg --symmetric --cipher-algo AES256 backup.sql.gz

   # Decrypt
   gpg --decrypt backup.sql.gz.gpg > backup.sql.gz
   ```

2. **Store backups offsite**:
   - Use S3, Google Cloud Storage, or similar
   - Keep at least one copy in a different region

3. **Test restores regularly**:
   - Create a test environment
   - Practice restore procedures monthly

4. **Secure backup directory**:
   ```bash
   chmod 700 ./backups
   chmod 600 ./backups/*.sql.gz
   ```

### Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "Permission denied" | Script not executable | `chmod +x script.sh` |
| "pg_dump not found" | Not in container | Run from host using docker exec |
| "Connection refused" | DB not running | Start DB first: `docker compose up -d db` |
| "Authentication failed" | Wrong password | Check POSTGRES_PASSWORD in .env |
| Backup too large | DB size | Use `--compress=9` for better compression |

---

## Quick Reference

### Common Commands

```bash
# Backup
./docker/scripts/backup-db.sh                     # Default backup
./docker/scripts/backup-db.sh my_backup           # Named backup
./docker/scripts/backup-db.sh --help              # Show help

# Restore
./docker/scripts/restore-db.sh --list             # List backups
./docker/scripts/restore-db.sh backup.sql.gz      # Restore
./docker/scripts/restore-db.sh --help             # Show help

# Wait-for-it
./docker/scripts/wait-for-it.sh db:5432           # Wait for DB
./docker/scripts/wait-for-it.sh db:5432 -t 60     # With timeout
./docker/scripts/wait-for-it.sh db:5432 -- cmd    # Then run command
```

### Environment Setup

```bash
# Create .env file with required variables
cat > .env << EOF
POSTGRES_DB=backend_core_db
POSTGRES_USER=django_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_HOST=db
BACKUP_DIR=./backups
EOF
```
