#!/bin/bash
# =============================================================================
# PostgreSQL Database Restore Script
# =============================================================================
# Restores a PostgreSQL database from a compressed backup file.
#
# Usage:
#   ./restore-db.sh backup_file.sql.gz
#   ./restore-db.sh --list                 # List available backups
#   ./restore-db.sh --help                 # Show help
#
# WARNING: This will OVERWRITE all data in the target database!
#
# Environment variables (loaded from .env if present):
#   POSTGRES_DB       - Database name
#   POSTGRES_USER     - Database user
#   POSTGRES_PASSWORD - Database password
#   POSTGRES_HOST     - Database host (default: db)
#   BACKUP_DIR        - Backup directory (default: ./backups)
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

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

show_help() {
    echo "PostgreSQL Database Restore Script"
    echo ""
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Options:"
    echo "  backup_file.sql.gz    Path to the backup file to restore"
    echo "  --list                List available backups"
    echo "  --help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 ./backups/backup_20240115_143022.sql.gz"
    echo "  $0 --list"
    echo ""
    echo "WARNING: This will OVERWRITE all data in the target database!"
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

list_backups() {
    echo "Available backups in $BACKUP_DIR:"
    echo ""
    if [ -d "$BACKUP_DIR" ]; then
        ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null || echo "No backup files found."
    else
        echo "Backup directory does not exist."
    fi
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

# Show help if requested
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    show_help
    exit 0
fi

# List backups if requested
if [ "${1:-}" = "--list" ] || [ "${1:-}" = "-l" ]; then
    list_backups
    exit 0
fi

# Check for backup file argument
BACKUP_FILE="${1:-}"
if [ -z "$BACKUP_FILE" ]; then
    log_error "No backup file specified"
    echo ""
    show_help
    exit 1
fi

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    log_error "Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Check required variables
if [ -z "$DB_PASSWORD" ]; then
    log_error "POSTGRES_PASSWORD is not set"
    exit 1
fi

# Confirmation prompt
echo ""
echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║                        WARNING                               ║${NC}"
echo -e "${YELLOW}╠══════════════════════════════════════════════════════════════╣${NC}"
echo -e "${YELLOW}║  This will OVERWRITE all data in database: $DB_NAME${NC}"
echo -e "${YELLOW}║  Backup file: $BACKUP_FILE${NC}"
echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    log_info "Restore cancelled."
    exit 0
fi

log_info "Starting database restore..."
log_info "Database: $DB_NAME"
log_info "Host: $DB_HOST:$DB_PORT"
log_info "Backup: $BACKUP_FILE"

# Check if running inside Docker or on host
if [ -f /.dockerenv ]; then
    # Inside Docker container
    log_info "Running inside Docker container"

    # Drop existing connections
    PGPASSWORD="$DB_PASSWORD" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" \
        2>/dev/null || true

    # Restore database
    gunzip -c "$BACKUP_FILE" | PGPASSWORD="$DB_PASSWORD" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --single-transaction
else
    # On host machine - use docker exec
    log_info "Running from host, using docker exec"

    # Drop existing connections
    docker compose exec -T db psql \
        -U "$DB_USER" \
        -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" \
        2>/dev/null || true

    # Restore database
    gunzip -c "$BACKUP_FILE" | docker compose exec -T db psql \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --single-transaction
fi

log_info "Restore completed successfully!"
echo ""

# Post-restore steps
log_info "Post-restore recommendations:"
echo "  1. Run migrations: docker compose exec app python manage.py migrate"
echo "  2. Check data: docker compose exec app python manage.py shell"
echo "  3. Restart app: docker compose restart app"
echo ""
log_info "Done!"
