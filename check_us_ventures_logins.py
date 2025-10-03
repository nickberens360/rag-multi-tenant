#!/usr/bin/env python3
"""
Quick script to check us_ventures login activity in production.
Run with: railway run python check_us_ventures_logins.py
"""

import os
import sys

from sqlalchemy import create_engine, text


def main():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not found in environment")
        sys.exit(1)

    print(f"Connecting to database...")
    engine = create_engine(database_url)

    query = text(
        """
        SELECT
            event_type,
            identifier,
            ip_address,
            severity,
            created_at,
            details::text
        FROM security_events
        WHERE identifier = 'us_ventures'
            AND event_type LIKE 'audit_login%'
        ORDER BY created_at DESC
        LIMIT 20
    """
    )

    with engine.connect() as conn:
        result = conn.execute(query)
        rows = result.fetchall()

        if not rows:
            print("\n❌ No login events found for username 'us_ventures'\n")
            return

        print(f"\n✅ Found {len(rows)} login event(s) for 'us_ventures':\n")
        print("-" * 120)
        print(f"{'Event Type':<25} {'Username':<15} {'IP Address':<20} {'Severity':<10} {'Created At':<25}")
        print("-" * 120)

        for row in rows:
            event_type = row[0] or ""
            identifier = row[1] or ""
            ip_address = row[2] or ""
            severity = row[3] or ""
            created_at = row[4] or ""

            print(f"{event_type:<25} {identifier:<15} {ip_address:<20} {severity:<10} {str(created_at):<25}")

        print("-" * 120)
        print()


if __name__ == "__main__":
    main()
