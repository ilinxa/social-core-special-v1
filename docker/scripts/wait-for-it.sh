#!/bin/bash
# =============================================================================
# Wait-for-it Script
# =============================================================================
# Waits for a TCP host:port to be available before executing a command.
#
# Usage:
#   ./wait-for-it.sh host:port [-t timeout] [-- command args]
#   ./wait-for-it.sh -h host -p port [-t timeout] [-- command args]
#
# Examples:
#   ./wait-for-it.sh db:5432                          # Wait for PostgreSQL
#   ./wait-for-it.sh redis:6379 -t 30                 # Wait with 30s timeout
#   ./wait-for-it.sh db:5432 -- python manage.py runserver
#
# This is commonly used in Docker entrypoints to wait for dependent services.
# =============================================================================

set -e

# Default values
TIMEOUT=30
QUIET=0
HOST=""
PORT=""
CMD=""

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

show_help() {
    echo "Wait-for-it: Wait for a service to be available"
    echo ""
    echo "Usage:"
    echo "  $0 host:port [-t timeout] [-- command args]"
    echo "  $0 -h host -p port [-t timeout] [-- command args]"
    echo ""
    echo "Options:"
    echo "  host:port              Host and port to wait for"
    echo "  -h HOST, --host=HOST   Host to wait for"
    echo "  -p PORT, --port=PORT   Port to wait for"
    echo "  -t TIMEOUT             Timeout in seconds (default: 30)"
    echo "  -q, --quiet            Don't output status messages"
    echo "  --help                 Show this help message"
    echo "  -- COMMAND ARGS        Execute command after service is available"
    echo ""
    echo "Examples:"
    echo "  $0 db:5432"
    echo "  $0 db:5432 -t 60"
    echo "  $0 db:5432 -- python manage.py migrate"
    echo "  $0 -h redis -p 6379 -t 15 -- python app.py"
}

log() {
    if [ "$QUIET" -eq 0 ]; then
        echo "$@"
    fi
}

wait_for_service() {
    local host="$1"
    local port="$2"
    local timeout="$3"

    log "Waiting for $host:$port (timeout: ${timeout}s)..."

    local start_time=$(date +%s)

    while true; do
        # Try to connect
        if nc -z "$host" "$port" 2>/dev/null; then
            log "$host:$port is available!"
            return 0
        fi

        # Check timeout
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        if [ "$elapsed" -ge "$timeout" ]; then
            log "Timeout after ${timeout}s waiting for $host:$port"
            return 1
        fi

        # Wait before retry
        sleep 1
    done
}

# -----------------------------------------------------------------------------
# Parse Arguments
# -----------------------------------------------------------------------------

while [ $# -gt 0 ]; do
    case "$1" in
        *:*)
            # host:port format
            HOST="${1%%:*}"
            PORT="${1##*:}"
            shift
            ;;
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        --host=*)
            HOST="${1#*=}"
            shift
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        --port=*)
            PORT="${1#*=}"
            shift
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --timeout=*)
            TIMEOUT="${1#*=}"
            shift
            ;;
        -q|--quiet)
            QUIET=1
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        --)
            shift
            CMD="$@"
            break
            ;;
        *)
            echo "Unknown argument: $1"
            show_help
            exit 1
            ;;
    esac
done

# -----------------------------------------------------------------------------
# Validate Arguments
# -----------------------------------------------------------------------------

if [ -z "$HOST" ] || [ -z "$PORT" ]; then
    echo "Error: Host and port are required"
    echo ""
    show_help
    exit 1
fi

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

# Wait for the service
if wait_for_service "$HOST" "$PORT" "$TIMEOUT"; then
    # Execute command if provided
    if [ -n "$CMD" ]; then
        log "Executing: $CMD"
        exec $CMD
    fi
    exit 0
else
    exit 1
fi
