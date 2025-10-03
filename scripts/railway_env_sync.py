#!/usr/bin/env python3
"""
Railway Environment Sync Script - Phase 3

This script synchronizes infrastructure settings with Railway environments,
ensuring consistency between local .env files and Railway environment variables.

Features:
- Compare local and Railway environment variables
- Push local env vars to Railway
- Pull Railway env vars to local
- Validate Railway deployment configuration
- Support for multiple Railway environments (dev, staging, production)
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class RailwayEnvSync:
    """Synchronizes environment variables with Railway."""

    def __init__(self, dry_run: bool = True, environment: Optional[str] = None):
        """Initialize Railway environment sync."""
        self.dry_run = dry_run
        self.environment = environment
        self.railway_available = False
        self.current_env: Optional[str] = None

    def check_railway_cli(self) -> bool:
        """Check if Railway CLI is available and user is logged in."""
        try:
            # Check if railway command exists
            result = subprocess.run(["railway", "whoami"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.railway_available = True
                logger.info(f"Railway CLI available, logged in as: {result.stdout.strip()}")
                return True
            else:
                logger.error("Railway CLI not logged in. Run 'railway login' first.")
                return False
        except FileNotFoundError:
            logger.error("Railway CLI not found. Install from https://railway.app/cli")
            return False
        except subprocess.TimeoutExpired:
            logger.error("Railway CLI command timed out")
            return False
        except Exception as e:
            logger.error(f"Failed to check Railway CLI: {e}")
            return False

    def get_current_railway_env(self) -> Optional[str]:
        """Get current Railway environment."""
        try:
            result = subprocess.run(["railway", "status"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Parse status output to find environment
                for line in result.stdout.split("\n"):
                    if "Environment:" in line:
                        env = line.split("Environment:")[1].strip()
                        self.current_env = env
                        return env
                logger.warning("Could not determine current Railway environment")
                return None
            else:
                logger.error(f"Failed to get Railway status: {result.stderr}")
                return None
        except Exception as e:
            logger.error(f"Failed to get Railway environment: {e}")
            return None

    def list_railway_variables(self, environment: Optional[str] = None) -> Dict[str, str]:
        """List all environment variables in Railway."""
        try:
            cmd = ["railway", "variables"]
            if environment:
                cmd.extend(["--environment", environment])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                # Parse railway variables output
                variables = {}
                lines = result.stdout.strip().split("\n")

                for line in lines:
                    if "=" in line and not line.startswith("#"):
                        # Handle Railway CLI output format
                        line = line.strip()
                        if line:
                            try:
                                key, value = line.split("=", 1)
                                variables[key.strip()] = value.strip()
                            except ValueError:
                                # Skip malformed lines
                                continue

                logger.info(f"Found {len(variables)} Railway environment variables")
                return variables
            else:
                logger.error(f"Failed to list Railway variables: {result.stderr}")
                return {}
        except Exception as e:
            logger.error(f"Failed to list Railway variables: {e}")
            return {}

    def set_railway_variable(self, key: str, value: str, environment: Optional[str] = None) -> bool:
        """Set a single environment variable in Railway."""
        try:
            cmd = ["railway", "variables", "set", f"{key}={value}"]
            if environment:
                cmd.extend(["--environment", environment])

            if self.dry_run:
                logger.info(f"DRY RUN: Would set Railway variable {key}={value}")
                return True

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                logger.info(f"Set Railway variable: {key}")
                return True
            else:
                logger.error(f"Failed to set Railway variable {key}: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Failed to set Railway variable {key}: {e}")
            return False

    def delete_railway_variable(self, key: str, environment: Optional[str] = None) -> bool:
        """Delete an environment variable from Railway."""
        try:
            cmd = ["railway", "variables", "delete", key]
            if environment:
                cmd.extend(["--environment", environment])

            if self.dry_run:
                logger.info(f"DRY RUN: Would delete Railway variable {key}")
                return True

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                logger.info(f"Deleted Railway variable: {key}")
                return True
            else:
                logger.error(f"Failed to delete Railway variable {key}: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Failed to delete Railway variable {key}: {e}")
            return False

    def load_local_env_file(self, env_file: str = ".env") -> Dict[str, str]:
        """Load environment variables from local .env file."""
        env_vars = {}
        env_path = Path(env_file)

        if not env_path.exists():
            logger.warning(f"Environment file not found: {env_file}")
            return {}

        try:
            with open(env_path, "r") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    # Parse key=value pairs
                    if "=" in line:
                        try:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip()

                            # Remove quotes if present
                            if value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                            elif value.startswith("'") and value.endswith("'"):
                                value = value[1:-1]

                            env_vars[key] = value
                        except ValueError:
                            logger.warning(f"Skipping malformed line {line_num} in {env_file}: {line}")
                    else:
                        logger.warning(f"Skipping invalid line {line_num} in {env_file}: {line}")

            logger.info(f"Loaded {len(env_vars)} variables from {env_file}")
            return env_vars

        except Exception as e:
            logger.error(f"Failed to load env file {env_file}: {e}")
            return {}

    def compare_environments(self, local_vars: Dict[str, str], railway_vars: Dict[str, str]) -> Dict[str, Any]:
        """Compare local and Railway environment variables."""
        comparison = {"local_only": {}, "railway_only": {}, "different_values": {}, "identical": {}, "summary": {}}

        all_keys = set(local_vars.keys()) | set(railway_vars.keys())

        for key in all_keys:
            local_val = local_vars.get(key)
            railway_val = railway_vars.get(key)

            if local_val is not None and railway_val is None:
                comparison["local_only"][key] = local_val
            elif local_val is None and railway_val is not None:
                comparison["railway_only"][key] = railway_val
            elif local_val != railway_val:
                comparison["different_values"][key] = {"local": local_val, "railway": railway_val}
            else:
                comparison["identical"][key] = local_val

        # Generate summary
        comparison["summary"] = {
            "total_keys": len(all_keys),
            "local_only_count": len(comparison["local_only"]),
            "railway_only_count": len(comparison["railway_only"]),
            "different_count": len(comparison["different_values"]),
            "identical_count": len(comparison["identical"]),
        }

        return comparison

    def push_to_railway(
        self, local_vars: Dict[str, str], exclude_keys: Optional[Set[str]] = None, environment: Optional[str] = None
    ) -> Tuple[int, int]:
        """Push local environment variables to Railway."""
        exclude_keys = exclude_keys or set()
        success_count = 0
        fail_count = 0

        # Security-sensitive keys that should be set manually
        sensitive_keys = {
            "ANTHROPIC_API_KEY",
            "GOOGLE_API_KEY",
            "OPENAI_API_KEY",
            "DATABASE_URL",
            "REDIS_URL",
            "SECRET_KEY",
            "JWT_SECRET",
        }

        logger.info(f"Pushing {len(local_vars)} variables to Railway...")

        for key, value in local_vars.items():
            if key in exclude_keys:
                logger.info(f"Skipping excluded key: {key}")
                continue

            if key in sensitive_keys:
                logger.warning(f"Skipping sensitive key {key} - set manually in Railway for security")
                continue

            if self.set_railway_variable(key, value, environment):
                success_count += 1
            else:
                fail_count += 1

        logger.info(f"Push completed: {success_count} success, {fail_count} failed")
        return success_count, fail_count

    def pull_from_railway(self, output_file: str = ".env.railway", environment: Optional[str] = None) -> bool:
        """Pull Railway environment variables to local file."""
        railway_vars = self.list_railway_variables(environment)

        if not railway_vars:
            logger.error("No Railway variables to pull")
            return False

        try:
            lines = [
                f"# Railway Environment Variables - {environment or 'current'}",
                f"# Generated on {__import__('datetime').datetime.now().isoformat()}",
                f"# Total variables: {len(railway_vars)}",
                "",
            ]

            # Sort variables for consistent output
            for key in sorted(railway_vars.keys()):
                value = railway_vars[key]

                # Escape value if it contains spaces or special characters
                if any(char in value for char in [" ", '"', "'", "\n", "\t"]):
                    value = f'"{value}"'

                lines.append(f"{key}={value}")

            content = "\n".join(lines)

            if self.dry_run:
                logger.info(f"DRY RUN: Would write Railway variables to {output_file}")
                logger.info(f"Content preview:\n{content[:500]}...")
            else:
                with open(output_file, "w") as f:
                    f.write(content)
                logger.info(f"Railway variables saved to {output_file}")

            return True

        except Exception as e:
            logger.error(f"Failed to pull Railway variables: {e}")
            return False

    def sync_environments(
        self, local_env_file: str = ".env", direction: str = "push", environment: Optional[str] = None
    ) -> bool:
        """Synchronize local and Railway environments."""
        if not self.check_railway_cli():
            return False

        # Get current environment if not specified
        if not environment:
            environment = self.get_current_railway_env()

        logger.info(f"Syncing with Railway environment: {environment or 'current'}")

        if direction == "push":
            # Load local variables and push to Railway
            local_vars = self.load_local_env_file(local_env_file)
            if not local_vars:
                logger.error(f"No local variables found in {local_env_file}")
                return False

            # Get current Railway state for comparison
            railway_vars = self.list_railway_variables(environment)
            comparison = self.compare_environments(local_vars, railway_vars)

            logger.info("Environment comparison:")
            logger.info(f"  Local only: {comparison['summary']['local_only_count']}")
            logger.info(f"  Railway only: {comparison['summary']['railway_only_count']}")
            logger.info(f"  Different values: {comparison['summary']['different_count']}")
            logger.info(f"  Identical: {comparison['summary']['identical_count']}")

            # Push local-only and different variables
            push_vars = {
                **comparison["local_only"],
                **{k: v["local"] for k, v in comparison["different_values"].items()},
            }

            if push_vars:
                success, fail = self.push_to_railway(push_vars, environment=environment)
                return fail == 0
            else:
                logger.info("No variables to push - environments are in sync")
                return True

        elif direction == "pull":
            # Pull Railway variables to local file
            return self.pull_from_railway(local_env_file, environment)

        else:
            logger.error(f"Invalid sync direction: {direction}. Use 'push' or 'pull'")
            return False

    def validate_railway_deployment(self, environment: Optional[str] = None) -> Tuple[bool, List[str]]:
        """Validate Railway deployment configuration."""
        errors = []

        try:
            # Check critical environment variables
            railway_vars = self.list_railway_variables(environment)

            critical_vars = {
                "ANTHROPIC_API_KEY": "API access for Claude models",
                "GOOGLE_API_KEY": "API access for Gemini models",
                "ENVIRONMENT": "Application environment (production/staging/development)",
            }

            for var, description in critical_vars.items():
                if var not in railway_vars:
                    errors.append(f"Missing critical variable {var}: {description}")
                elif not railway_vars[var].strip():
                    errors.append(f"Empty critical variable {var}: {description}")

            # Check Railway service health
            try:
                result = subprocess.run(["railway", "status"], capture_output=True, text=True, timeout=10)
                if result.returncode != 0:
                    errors.append("Railway service status check failed")
            except Exception as e:
                errors.append(f"Railway service status unavailable: {e}")

            is_valid = len(errors) == 0
            return is_valid, errors

        except Exception as e:
            errors.append(f"Validation failed: {e}")
            return False, errors


def main():
    """Main function for Railway environment sync."""
    import argparse

    parser = argparse.ArgumentParser(description="Sync environment variables with Railway")
    parser.add_argument("action", choices=["compare", "push", "pull", "validate"], help="Action to perform")
    parser.add_argument("--env-file", default=".env", help="Local environment file")
    parser.add_argument("--environment", help="Railway environment name")
    parser.add_argument("--execute", action="store_true", help="Execute changes (default: dry-run)")
    parser.add_argument("--output", help="Output file for pull action")

    args = parser.parse_args()

    # Initialize sync client
    sync = RailwayEnvSync(dry_run=not args.execute, environment=args.environment)

    try:
        if args.action == "compare":
            # Compare local and Railway environments
            if not sync.check_railway_cli():
                sys.exit(1)

            local_vars = sync.load_local_env_file(args.env_file)
            railway_vars = sync.list_railway_variables(args.environment)
            comparison = sync.compare_environments(local_vars, railway_vars)

            print("\n=== ENVIRONMENT COMPARISON ===")
            print(f"Total variables: {comparison['summary']['total_keys']}")
            print(f"Local only: {comparison['summary']['local_only_count']}")
            print(f"Railway only: {comparison['summary']['railway_only_count']}")
            print(f"Different values: {comparison['summary']['different_count']}")
            print(f"Identical: {comparison['summary']['identical_count']}")

            if comparison["local_only"]:
                print(f"\n📁 Local only variables:")
                for key, value in comparison["local_only"].items():
                    print(f"  {key}={value[:50]}{'...' if len(value) > 50 else ''}")

            if comparison["railway_only"]:
                print(f"\n🚄 Railway only variables:")
                for key, value in comparison["railway_only"].items():
                    print(f"  {key}={value[:50]}{'...' if len(value) > 50 else ''}")

            if comparison["different_values"]:
                print(f"\n⚠️  Different values:")
                for key, values in comparison["different_values"].items():
                    print(f"  {key}:")
                    print(f"    Local:   {values['local'][:50]}{'...' if len(values['local']) > 50 else ''}")
                    print(f"    Railway: {values['railway'][:50]}{'...' if len(values['railway']) > 50 else ''}")

        elif args.action == "push":
            # Push local variables to Railway
            success = sync.sync_environments(args.env_file, "push", args.environment)
            if not success:
                sys.exit(1)

        elif args.action == "pull":
            # Pull Railway variables to local
            output_file = args.output or f"{args.env_file}.railway"
            success = sync.pull_from_railway(output_file, args.environment)
            if not success:
                sys.exit(1)

        elif args.action == "validate":
            # Validate Railway deployment
            is_valid, errors = sync.validate_railway_deployment(args.environment)

            print("\n=== RAILWAY DEPLOYMENT VALIDATION ===")
            if is_valid:
                print("✅ Deployment configuration is valid")
            else:
                print("❌ Deployment configuration has issues:")
                for error in errors:
                    print(f"  - {error}")
                sys.exit(1)

        print(f"\n✅ Action '{args.action}' completed successfully!")

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
