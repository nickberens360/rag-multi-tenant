#!/usr/bin/env python3
"""
Script to change admin user password for the admin dashboard.
"""

import getpass
import sys
from pathlib import Path

# Add project root (parent of the 'admin' directory) to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.core.admin_auth import admin_auth_manager as auth_manager
from backend.core.admin_database import admin_db_manager as db_manager


def change_password(username: str):
    """Change password for an admin user."""
    # Check if user exists
    user = db_manager.get_admin_user(username)
    if not user:
        print(f"Error: User '{username}' not found.")
        return False

    # Get new password
    password = getpass.getpass("Enter new password: ")
    confirm = getpass.getpass("Confirm new password: ")

    if password != confirm:
        print("Error: Passwords do not match.")
        return False

    if len(password) < 8:
        print("Error: Password must be at least 8 characters long.")
        return False

    # Hash the new password
    password_hash = auth_manager.hash_password(password)

    # Update the password in the database
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE admin_users SET password_hash = ? WHERE id = ?", (password_hash, user["id"]))
        conn.commit()

    print(f"✓ Password updated successfully for user '{username}'")

    # Expire all existing sessions for this user (force re-login)
    auth_manager.expire_user_sessions(user["id"])
    print("✓ All existing sessions expired. User will need to login with new password.")

    return True


def main():
    print("Admin Password Change Utility")
    print("-" * 30)

    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        username = input("Enter username (default: admin): ").strip() or "admin"

    change_password(username)


if __name__ == "__main__":
    main()
