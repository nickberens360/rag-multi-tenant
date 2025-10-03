#!/usr/bin/env python3
"""
Security Test Runner for Admin Dashboard
Runs comprehensive security tests with proper configuration and reporting.
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_command(cmd, description=""):
    """Run command and return success status."""
    print(f"\n{'='*60}")
    print(f"🔒 {description}")
    print(f"{'='*60}")
    print(f"Running: {cmd}")
    print()

    result = subprocess.run(cmd, shell=True, capture_output=False)
    success = result.returncode == 0

    if success:
        print(f"✅ {description} - PASSED")
    else:
        print(f"❌ {description} - FAILED")

    return success


def main():
    """Main security test runner."""
    parser = argparse.ArgumentParser(description="Run admin dashboard security tests")
    parser.add_argument("--quick", action="store_true", help="Run quick security tests only")
    parser.add_argument(
        "--category",
        choices=["auth", "database", "api", "integration", "production"],
        help="Run specific security test category",
    )
    parser.add_argument("--coverage", action="store_true", help="Run with coverage reporting")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fail-fast", "-x", action="store_true", help="Stop on first failure")
    parser.add_argument("--parallel", "-n", type=int, help="Run tests in parallel (number of workers)")

    args = parser.parse_args()

    # Ensure we're in the project root
    project_root = Path(__file__).parent
    os.chdir(project_root)

    # Set environment variables for testing
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["PYTHONPATH"] = str(project_root)

    print("🛡️  ADMIN DASHBOARD SECURITY TEST SUITE")
    print("=" * 60)
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📂 Project: {project_root}")
    print(f"🐍 Python: {sys.version}")
    print()

    # Build base pytest command
    base_cmd = ["python3", "-m", "pytest", "tests/security/"]

    if args.verbose:
        base_cmd.append("-v")

    if args.fail_fast:
        base_cmd.append("-x")

    if args.parallel:
        base_cmd.extend(["-n", str(args.parallel)])

    # Coverage configuration
    coverage_args = []
    if args.coverage:
        coverage_args = [
            "--cov=backend.core.admin_auth",
            "--cov=backend.routes.admin",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov/security",
        ]

    success_count = 0
    total_tests = 0

    # Test categories to run
    if args.category:
        test_categories = [args.category]
    elif args.quick:
        test_categories = ["auth", "database", "api"]  # Quick critical tests including new API tests
    else:
        test_categories = ["auth", "database", "api", "integration", "production"]

    # Run security tests by category
    for category in test_categories:
        total_tests += 1
        cmd = base_cmd + ["-m", category] + coverage_args
        cmd_str = " ".join(cmd)

        description = f"Security Tests - {category.upper()}"
        success = run_command(cmd_str, description)

        if success:
            success_count += 1
        elif args.fail_fast:
            break

    # Run comprehensive security validation if not quick mode
    if not args.quick and not args.category:
        total_tests += 1
        comprehensive_cmd = base_cmd + ["--tb=short", "--durations=10"] + coverage_args

        cmd_str = " ".join(comprehensive_cmd)
        description = "Comprehensive Security Validation"
        success = run_command(cmd_str, description)

        if success:
            success_count += 1

    # Security linting and static analysis
    if not args.quick:
        print(f"\n{'='*60}")
        print("🔍 SECURITY STATIC ANALYSIS")
        print(f"{'='*60}")

        # Run bandit security linter on admin code
        bandit_cmd = "python3 -m bandit -r backend/core/admin_auth.py backend/routes/admin.py -f json -o security_analysis.json || true"
        subprocess.run(bandit_cmd, shell=True)

        # Check for common security issues
        security_check_cmd = (
            "python3 -c \"import backend.core.admin_auth; print('✅ Security modules import successfully')\""
        )
        subprocess.run(security_check_cmd, shell=True)

    # Final report
    print(f"\n{'='*60}")
    print("📊 SECURITY TEST RESULTS")
    print(f"{'='*60}")
    print(f"✅ Passed: {success_count}/{total_tests}")
    print(f"❌ Failed: {total_tests - success_count}/{total_tests}")

    if success_count == total_tests:
        print("\n🎉 ALL SECURITY TESTS PASSED! 🎉")
        print("The admin dashboard security controls are working correctly.")
        exit_code = 0
    else:
        print("\n⚠️  SECURITY TEST FAILURES DETECTED!")
        print("Please review and fix security issues before deployment.")
        exit_code = 1

    if args.coverage and success_count > 0:
        print("\n📈 Security test coverage report: htmlcov/security/index.html")

    print(f"\n📅 Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return exit_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
