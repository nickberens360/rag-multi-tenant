#!/bin/sh
set -e

# This script runs as root to fix volume permissions, then drops privileges

# Security audit logging function
log_security_event() {
    local event_type="$1"
    local details="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S UTC')
    echo "SECURITY_AUDIT: [$timestamp] $event_type - $details" >&2

    # Log to file if possible
    if [ -w "/data/logs" ] 2>/dev/null; then
        echo "[$timestamp] SECURITY_AUDIT: $event_type - $details" >> /data/logs/security_audit.log
    fi
}

# Fix volume permissions if needed
if [ -d "/data" ]; then
    # Validate that /data is actually a mount point for security
    if mountpoint -q /data; then
        echo "/data is a valid mount point, checking permissions..."
        log_security_event "MOUNT_VALIDATION" "/data verified as valid mount point"

        current_owner=$(stat -c %U /data)
        current_perms=$(stat -c %a /data)

        if [ "$current_owner" != "app" ]; then
            echo "Fixing /data directory permissions (current owner: $current_owner)..."
            log_security_event "PERMISSION_CHANGE" "Changing /data ownership from $current_owner to app:app (perms: $current_perms)"

            chown -R app:app /data

            new_owner=$(stat -c %U /data)
            echo "Permissions fixed successfully"
            log_security_event "PERMISSION_FIXED" "Successfully changed /data ownership to $new_owner"
        else
            echo "/data permissions already correct (owner: app)"
            log_security_event "PERMISSION_VERIFIED" "/data ownership verified as app:app (perms: $current_perms)"
        fi
    else
        echo "Warning: /data exists but is not a mount point, skipping permission fix"
        log_security_event "SECURITY_WARNING" "/data exists but is not a mount point - permission fix skipped"
    fi
else
    echo "/data directory not found, skipping permission fix"
    log_security_event "MOUNT_STATUS" "/data directory not found - no permission changes needed"
fi

# Drop privileges and execute the main command as the app user
echo "Starting application as app user..."

current_user=$(whoami)
log_security_event "PRIVILEGE_DROP" "Dropping privileges from $current_user to app user"

# If no arguments provided, start the default uvicorn server
if [ $# -eq 0 ]; then
    set -- uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
    log_security_event "DEFAULT_COMMAND" "Starting default uvicorn server on port ${PORT:-8000}"
else
    log_security_event "CUSTOM_COMMAND" "Starting custom command: $*"
fi

log_security_event "EXEC_TRANSITION" "Executing command as app user via gosu"
exec gosu app "$@"
