#!/bin/bash
# =============================================================================
# PostgreSQL Database Backup Script
# =============================================================================
# Creates a compressed backup of the PostgreSQL database.
#
# Usage:
#   ./backup-db.sh                    # Backup with timestamp
#   ./backup-db.sh my_backup          # Backup with custom name
#   ./backup-db.sh --help             # Show help
#
# Environment variables (loaded from .env if present):
#   POSTGRES_DB       - Database name
#   POSTGRES_USER     - Database user
#   POSTGRES_PASSWORD - Database password
#   POSTGRES_HOST     - Database host (default: db)
#   BACKUP_DIR        - Backup directory (default: ./backups)
#
# The script creates:
#   - Compressed SQL dump (.sql.gz)
#   - Backup metadata file (.meta)
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# Load environment variables from .env if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Database settings
DB_NAME="${POSTGRES_DB:-backend_core_db}"
DB_USER="${POSTGRES_USER:-django_user}"
DB_PASSWORD="${POSTGRES_PASSWORD:-}"
DB_HOST="${POSTGRES_HOST:-db}"
DB_PORT="${POSTGRES_PORT:-5432}"

# Backup settings
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="${1:-backup_${TIMESTAMP}}"

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

show_help() {
    echo "PostgreSQL Database Backup Script"
    echo ""
    echo "Usage: $0 [backup_name]"
    echo ""
    echo "Options:"
    echo "  backup_name    Custom name for the backup (default: backup_YYYYMMDD_HHMMSS)"
    echo "  --help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Creates backup_20240115_143022.sql.gz"
    echo "  $0 pre_migration      # Creates pre_migration.sql.gz"
    echo "  $0 daily_backup       # Creates daily_backup.sql.gz"
    echo ""
    echo "Environment variables:"
    echo "  POSTGRES_DB       Database name (default: backend_core_db)"
    echo "  POSTGRES_USER     Database user (default: django_user)"
    echo "  POSTGRES_PASSWORD Database password"
    echo "  POSTGRES_HOST     Database host (default: db)"
    echo "  BACKUP_DIR        Backup directory (default: ./backups)"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

# Show help if requested
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    show_help
    exit 0
fi

# Check required variables
if [ -z "$DB_PASSWORD" ]; then
    log_error "POSTGRES_PASSWORD is not set"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Backup file paths
BACKUP_FILE="${BACKUP_DIR}/${BACKUP_NAME}.sql.gz"
META_FILE="${BACKUP_DIR}/${BACKUP_NAME}.meta"

log_info "Starting database backup..."
log_info "Database: $DB_NAME"
log_info "Host: $DB_HOST:$DB_PORT"
log_info "Output: $BACKUP_FILE"

# Check if running inside Docker or on host
if [ -f /.dockerenv ]; then
    # Inside Docker container
    log_info "Running inside Docker container"

    PGPASSWORD="$DB_PASSWORD" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --no-owner \
        --no-acl \
        --clean \
        --if-exists \
        | gzip > "$BACKUP_FILE"
else
    # On host machine - use docker exec
    log_info "Running from host, using docker exec"

    docker compose exec -T db pg_dump \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --no-owner \
        --no-acl \
        --clean \
        --if-exists \
        | gzip > "$BACKUP_FILE"
fi

# Get backup size
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)

# Create metadata file
cat > "$META_FILE" << EOF
Backup Metadata
===============
Timestamp: $(date -Iseconds)
Database: $DB_NAME
Host: $DB_HOST:$DB_PORT
User: $DB_USER
Backup File: $BACKUP_FILE
Backup Size: $BACKUP_SIZE
EOF

log_info "Backup completed successfully!"
log_info "File: $BACKUP_FILE"
log_info "Size: $BACKUP_SIZE"

# Cleanup old backups (keep last 7 days)
if [ "${BACKUP_RETENTION_DAYS:-0}" -gt 0 ]; then
    log_info "Cleaning up backups older than ${BACKUP_RETENTION_DAYS} days..."
    find "$BACKUP_DIR" -name "*.sql.gz" -mtime +"$BACKUP_RETENTION_DAYS" -delete
    find "$BACKUP_DIR" -name "*.meta" -mtime +"$BACKUP_RETENTION_DAYS" -delete
fi

echo ""
log_info "Done!"
