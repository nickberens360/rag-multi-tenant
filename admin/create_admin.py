#!/usr/bin/env python3
"""
Command-line utility to create admin users.
"""

import argparse
import getpass
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.core.admin_auth import admin_auth_manager as auth_manager
from backend.core.admin_database import admin_db_manager as db_manager


def create_admin_user(args=None):
    """Interactive admin user creation."""
    if args is None:
        parser = argparse.ArgumentParser(description="Create an admin user for the RAG dashboard")
        parser.add_argument("--username", "-u", help="Username for the admin user")
        parser.add_argument("--email", "-e", help="Email for the admin user")
        parser.add_argument(
            "--role",
            "-r",
            choices=["viewer", "admin", "owner"],
            default="admin",
            help="Role for the admin user (default: admin)",
        )
        parser.add_argument("--password", "-p", help="Password (not recommended, will prompt if not provided)")
        args = parser.parse_args()

    # Get username
    username = args.username
    if not username:
        username = input("Enter username: ").strip()
        if not username:
            print("Username cannot be empty")
            return False

    # Check if user already exists
    existing_user = db_manager.get_admin_user(username)
    if existing_user:
        print(f"Error: User '{username}' already exists")
        return False

    # Get email
    email = args.email
    if not email:
        email = input("Enter email (optional): ").strip() or None

    # Get password
    password = args.password
    if not password:
        while True:
            password = getpass.getpass("Enter password: ")
            confirm_password = getpass.getpass("Confirm password: ")

            if not password:
                print("Password cannot be empty")
                continue

            if password != confirm_password:
                print("Passwords do not match")
                continue

            if len(password) < 8:
                print("Password must be at least 8 characters long")
                continue

            break

    # Get role
    role = args.role

    try:
        # Create the user
        user_id = auth_manager.create_admin_user(username=username, password=password, email=email, role=role)

        print("✅ Successfully created admin user:")
        print(f"   Username: {username}")
        print(f"   Email: {email or 'Not provided'}")
        print(f"   Role: {role}")
        print(f"   User ID: {user_id}")
        print()
        print("The user can now log in to the admin dashboard.")

        return True

    except Exception as e:
        print(f"❌ Error creating admin user: {str(e)}")
        return False


def list_admin_users():
    """List all admin users."""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, username, email, role, is_active, created_at, last_login_at
                FROM admin_users
                ORDER BY created_at DESC
            """
            )

            users = cursor.fetchall()

            if not users:
                print("No admin users found.")
                return

            print(
                f"{'ID':<5} {'Username':<20} {'Email':<30} {'Role':<10} {'Active':<8} "
                f"{'Created':<20} {'Last Login':<20}"
            )
            print("-" * 120)

            for user in users:
                user_dict = dict(user)
                print(
                    f"{user_dict['id']:<5} {user_dict['username']:<20} {user_dict['email'] or 'N/A':<30} "
                    f"{user_dict['role']:<10} {'Yes' if user_dict['is_active'] else 'No':<8} "
                    f"{user_dict['created_at'] or 'N/A':<20} {user_dict['last_login_at'] or 'Never':<20}"
                )

    except Exception as e:
        print(f"❌ Error listing users: {str(e)}")


def main():
    """Main function with proper argparse subcommands."""
    parser = argparse.ArgumentParser(description="Admin User Management Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new admin user")
    create_parser.add_argument("--username", "-u", help="Username for the admin user")
    create_parser.add_argument("--email", "-e", help="Email for the admin user")
    create_parser.add_argument(
        "--role",
        "-r",
        choices=["viewer", "admin", "owner"],
        default="admin",
        help="Role for the admin user (default: admin)",
    )
    create_parser.add_argument("--password", "-p", help="Password (not recommended, will prompt if not provided)")

    # List command
    list_parser = subparsers.add_parser("list", help="List all admin users")

    # Parse arguments
    args = parser.parse_args()

    # Handle no command provided (backward compatibility)
    if args.command is None:
        print("🔧 Admin User Creation Tool")
        print("=" * 30)
        print("No command specified. Creating admin user...")
        print()
        success = create_admin_user()
        if success:
            print("\n🚀 You can now start the admin server with:")
            print("   cd admin && python3 start-admin.py")
        sys.exit(0 if success else 1)

    # Handle commands
    if args.command == "list":
        list_admin_users()
    elif args.command == "create":
        print("🔧 Admin User Creation Tool")
        print("=" * 30)
        success = create_admin_user(args)
        if success:
            print("\n🚀 You can now start the admin server with:")
            print("   cd admin && python3 start-admin.py")
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
