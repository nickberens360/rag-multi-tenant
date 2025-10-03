#!/usr/bin/env python3
"""
DEPRECATED: Script to sync query logs from JSON files to SQLite database.

This script is now DEPRECATED as the system only uses SQLite logging (SQLiteQueryLogger).
It's kept for historical data migration purposes only.

WARNING: The main system no longer generates JSON log files. This script is only
useful for migrating existing historical JSON log files to the SQLite database.
"""
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def parse_timestamp(timestamp_str):
    """Parse timestamp from various formats."""
    try:
        # Handle ISO format with microseconds
        if "." in timestamp_str and timestamp_str.endswith("Z"):
            return datetime.fromisoformat(timestamp_str[:-1])
        elif "." in timestamp_str:
            return datetime.fromisoformat(timestamp_str)
        else:
            return datetime.fromisoformat(timestamp_str)
    except ValueError:
        # Fallback to current time if parsing fails
        return datetime.now()


def generate_session_id(client_ip, timestamp):
    """Generate a consistent session ID based on IP and time."""
    # Use a time window of 1 hour for session grouping
    hour_window = timestamp.replace(minute=0, second=0, microsecond=0)
    session_key = f"{client_ip}_{hour_window.isoformat()}"
    return hashlib.md5(session_key.encode()).hexdigest()[:16]


def sync_json_to_sqlite():
    """Sync JSON query logs to SQLite database."""
    # Paths
    json_log_file = Path(os.environ.get("QUERY_LOG_JSON_PATH", "backend/logs/query_logs.json"))
    sqlite_db_file = Path(os.environ.get("RAG_MONITOR_DB_PATH", "admin/rag_monitoring.db"))

    if not json_log_file.exists():
        print(f"JSON log file not found: {json_log_file}")
        return False

    print(f"Syncing logs from {json_log_file} to {sqlite_db_file}")

    # Connect to SQLite database
    conn = sqlite3.connect(sqlite_db_file)
    cursor = conn.cursor()

    # Add location columns if they don't exist
    try:
        cursor.execute("ALTER TABLE query_logs ADD COLUMN client_ip TEXT")
        print("Added client_ip column")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        cursor.execute("ALTER TABLE query_logs ADD COLUMN location_city TEXT")
        print("Added location_city column")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        cursor.execute("ALTER TABLE query_logs ADD COLUMN location_region TEXT")
        print("Added location_region column")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        cursor.execute("ALTER TABLE query_logs ADD COLUMN location_country TEXT")
        print("Added location_country column")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        cursor.execute("ALTER TABLE query_logs ADD COLUMN location_country_code TEXT")
        print("Added location_country_code column")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Add query_hash column for better deduplication
    try:
        cursor.execute("ALTER TABLE query_logs ADD COLUMN query_hash TEXT UNIQUE")
        print("Added query_hash column")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Create index on query_hash
    try:
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_query_logs_hash ON query_logs(query_hash)")
    except sqlite3.OperationalError:
        pass

    # Get existing hashes to avoid duplicates
    cursor.execute("SELECT query_hash FROM query_logs WHERE query_hash IS NOT NULL")
    existing_hashes = {row[0] for row in cursor.fetchall()}
    print(f"Found {len(existing_hashes)} existing entries with hashes")

    # Process JSON log entries
    processed_count = 0
    skipped_count = 0

    with open(json_log_file, "r") as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue

            try:
                entry = json.loads(line.strip())
                timestamp = parse_timestamp(entry.get("timestamp", ""))

                # Generate query hash for deduplication
                hash_content = f"{entry['timestamp']}:{entry.get('user_query', '')}:{entry.get('llm_model', '')}"
                query_hash = hashlib.sha256(hash_content.encode()).hexdigest()[:32]

                # Skip if already processed (based on hash)
                if query_hash in existing_hashes:
                    skipped_count += 1
                    continue

                # Generate session ID
                session_id = generate_session_id(entry.get("client_ip", "unknown"), timestamp)

                # Extract data with defaults
                user_query = entry.get("question", "")
                system_response = entry.get("response", "")
                response_time_ms = (entry.get("response_time") or 0) * 1000  # Convert to ms
                llm_provider = (
                    "anthropic" if entry.get("model_used") == "claude" else entry.get("model_used", "unknown")
                )
                llm_model = entry.get("model_used", "unknown")

                # Handle location data
                client_ip = entry.get("client_ip", "")
                location = entry.get("location", {})
                location_city = location.get("city", "")
                location_region = location.get("region", "")
                location_country = location.get("country_name", "")
                location_country_code = location.get("country_code", "")

                # Handle metadata
                metadata = entry.get("metadata", {})
                vector_search_score = metadata.get("retrieval_score", 0.0)
                sources_used = json.dumps(metadata.get("sources", []))
                follow_up_questions = json.dumps(metadata.get("followup_questions", []))
                cache_hit = metadata.get("cache_hit", False)

                # Error handling
                error_occurred = entry.get("error") is not None
                error_message = str(entry.get("error", "")) if error_occurred else None

                # Insert into SQLite with hash-based deduplication
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO query_logs (
                        session_id, user_query, system_response, response_time_ms,
                        llm_provider, llm_model, vector_search_score, sources_used,
                        follow_up_questions, cache_hit, error_occurred, error_message,
                        client_ip, location_city, location_region, location_country, location_country_code,
                        timestamp, query_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        session_id,
                        user_query,
                        system_response,
                        response_time_ms,
                        llm_provider,
                        llm_model,
                        vector_search_score,
                        sources_used,
                        follow_up_questions,
                        cache_hit,
                        error_occurred,
                        error_message,
                        client_ip,
                        location_city,
                        location_region,
                        location_country,
                        location_country_code,
                        timestamp.isoformat(),
                        query_hash,
                    ),
                )

                # Track the new hash
                existing_hashes.add(query_hash)

                processed_count += 1

                if processed_count % 100 == 0:
                    print(f"Processed {processed_count} entries...")

            except json.JSONDecodeError as e:
                print(f"JSON decode error on line {line_num}: {e}")
                continue
            except Exception as e:
                print(f"Error processing line {line_num}: {e}")
                continue

    # Commit changes
    conn.commit()
    conn.close()

    print("Sync completed:")
    print(f"  - Processed: {processed_count} new entries")
    print(f"  - Skipped: {skipped_count} existing entries")

    return processed_count > 0


if __name__ == "__main__":
    success = sync_json_to_sqlite()
    sys.exit(0 if success else 1)
