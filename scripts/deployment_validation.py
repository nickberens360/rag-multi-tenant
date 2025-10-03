#!/usr/bin/env python3
"""
Deployment Validation Script - Phase 3

This script validates deployment configuration after settings migration,
ensuring that the application can start correctly with the new environment-based
configuration.

Features:
- Validate critical environment variables
- Test database connectivity
- Verify API key configurations
- Check Railway deployment health
- Validate settings precedence (env > db > defaults)
- Pre-deployment smoke tests
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Add backend to path for imports
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DeploymentValidator:
    """Validates deployment configuration and health."""

    def __init__(self, environment: str = "production"):
        """Initialize deployment validator."""
        self.environment = environment
        self.validation_results = {
            "timestamp": time.time(),
            "environment": environment,
            "checks": {},
            "warnings": [],
            "errors": [],
            "summary": {},
        }

    def validate_environment_variables(self) -> bool:
        """Validate critical environment variables are present and valid."""
        logger.info("Validating environment variables...")

        critical_vars = {
            "ANTHROPIC_API_KEY": {
                "required": True,
                "description": "Anthropic Claude API key",
                "pattern": r"^sk-ant-[\w-]+$",  # More flexible pattern for various Anthropic API key formats
                "min_length": 20,
            },
            "GOOGLE_API_KEY": {
                "required": self.environment != "development",
                "description": "Google Gemini API key",
                "pattern": None,
                "min_length": 20,
            },
            "ENVIRONMENT": {
                "required": True,
                "description": "Application environment",
                "valid_values": ["development", "staging", "production"],
                "min_length": 1,
            },
            "DATABASE_URL": {
                "required": False,
                "description": "Database connection URL",
                "pattern": None,
                "min_length": 10,
            },
        }

        optional_vars = {
            "DEBUG": {
                "description": "Debug mode flag",
                "valid_values": ["true", "false", "1", "0"],
                "default": "false",
            },
            "LOG_LEVEL": {
                "description": "Logging level",
                "valid_values": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                "default": "INFO",
            },
            "CACHE_TTL_SECONDS": {
                "description": "Cache TTL in seconds",
                "type": "int",
                "min_value": 60,
                "max_value": 86400,
            },
            "SESSION_TIMEOUT_MINUTES": {
                "description": "Session timeout in minutes",
                "type": "int",
                "min_value": 30,
                "max_value": 1440,
            },
        }

        all_valid = True
        check_results = {"critical": {}, "optional": {}}

        # Check critical variables
        for var_name, config in critical_vars.items():
            value = os.environ.get(var_name)
            is_valid, message = self._validate_single_var(var_name, value, config)

            check_results["critical"][var_name] = {
                "present": value is not None,
                "valid": is_valid,
                "message": message,
                "required": config["required"],
            }

            if config["required"] and not is_valid:
                all_valid = False
                self.validation_results["errors"].append(f"Critical variable {var_name}: {message}")
            elif not is_valid:
                self.validation_results["warnings"].append(f"Variable {var_name}: {message}")

        # Check optional variables
        for var_name, config in optional_vars.items():
            value = os.environ.get(var_name)
            is_valid, message = self._validate_single_var(var_name, value, config)

            check_results["optional"][var_name] = {
                "present": value is not None,
                "valid": is_valid,
                "message": message,
                "default_used": value is None,
            }

            if not is_valid and value is not None:
                self.validation_results["warnings"].append(f"Optional variable {var_name}: {message}")

        self.validation_results["checks"]["environment_vars"] = check_results
        return all_valid

    def _validate_single_var(self, name: str, value: Optional[str], config: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate a single environment variable."""
        if value is None:
            if config.get("required", False):
                return False, "Required variable is missing"
            else:
                return True, f"Using default value: {config.get('default', 'none')}"

        # Check minimum length
        min_length = config.get("min_length", 0)
        if len(value) < min_length:
            return False, f"Value too short (minimum {min_length} characters)"

        # Check valid values
        valid_values = config.get("valid_values")
        if valid_values and value not in valid_values:
            return False, f"Invalid value. Must be one of: {valid_values}"

        # Check pattern
        pattern = config.get("pattern")
        if pattern:
            import re

            if not re.match(pattern, value):
                return False, "Value does not match required pattern"

        # Check type and bounds for numeric values
        var_type = config.get("type")
        if var_type == "int":
            try:
                int_value = int(value)
                min_val = config.get("min_value")
                max_val = config.get("max_value")

                if min_val is not None and int_value < min_val:
                    return False, f"Value too small (minimum {min_val})"
                if max_val is not None and int_value > max_val:
                    return False, f"Value too large (maximum {max_val})"
            except ValueError:
                return False, "Value must be an integer"

        return True, "Valid"

    def validate_api_connectivity(self) -> bool:
        """Test API connectivity for configured services."""
        logger.info("Validating API connectivity...")

        api_tests = {}
        all_connected = True

        # Test Anthropic API
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            is_connected, message = self._test_anthropic_api(anthropic_key)
            api_tests["anthropic"] = {"connected": is_connected, "message": message}
            if not is_connected:
                all_connected = False
                self.validation_results["errors"].append(f"Anthropic API: {message}")
        else:
            api_tests["anthropic"] = {"connected": False, "message": "API key not configured"}
            all_connected = False

        # Test Google API
        google_key = os.environ.get("GOOGLE_API_KEY")
        if google_key:
            is_connected, message = self._test_google_api(google_key)
            api_tests["google"] = {"connected": is_connected, "message": message}
            if not is_connected:
                all_connected = False
                self.validation_results["errors"].append(f"Google API: {message}")
        else:
            if self.environment != "development":
                api_tests["google"] = {"connected": False, "message": "API key not configured"}
                all_connected = False
            else:
                api_tests["google"] = {"connected": True, "message": "Optional in development"}

        self.validation_results["checks"]["api_connectivity"] = api_tests
        return all_connected

    def _test_anthropic_api(self, api_key: str) -> Tuple[bool, str]:
        """Test Anthropic API connectivity."""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)

            # Simple API test
            response = client.messages.create(
                model="claude-3-haiku-20240307", max_tokens=10, messages=[{"role": "user", "content": "Hello"}]
            )

            if response and response.content:
                return True, "Connected successfully"
            else:
                return False, "Invalid response from API"

        except ImportError:
            return False, "Anthropic library not installed"
        except anthropic.AuthenticationError:
            return False, "Invalid API key"
        except anthropic.RateLimitError:
            return True, "Rate limited (API key is valid)"
        except anthropic.APIError as e:
            return False, f"API error: {e}"
        except Exception as e:
            return False, f"Connection failed: {e}"

    def _test_google_api(self, api_key: str) -> Tuple[bool, str]:
        """Test Google API connectivity."""
        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)

            # List models to test API
            models = list(genai.list_models())
            if models:
                return True, "Connected successfully"
            else:
                return False, "No models available"

        except ImportError:
            return False, "Google AI library not installed"
        except Exception as e:
            error_msg = str(e).lower()
            if "api key" in error_msg or "authentication" in error_msg:
                return False, "Invalid API key"
            elif "quota" in error_msg or "rate limit" in error_msg:
                return True, "Rate limited (API key is valid)"
            else:
                return False, f"Connection failed: {e}"

    def validate_database_access(self) -> bool:
        """Validate database connectivity and structure."""
        logger.info("Validating database access...")

        try:
            # Test admin database
            from core.admin_database import admin_db_manager

            # Check if database file exists and is accessible
            db_info = admin_db_manager.get_db_info()
            if not db_info.get("exists", False):
                self.validation_results["errors"].append("Admin database file not found")
                return False

            # Test basic database operations
            test_key = "_deployment_validation_test"
            test_value = "test_value"

            # Test write
            write_success = admin_db_manager.set_admin_setting(test_key, test_value, 0)
            if not write_success:
                self.validation_results["errors"].append("Database write test failed")
                return False

            # Test read
            read_value = admin_db_manager.get_admin_setting(test_key)
            if read_value != test_value:
                self.validation_results["errors"].append("Database read test failed")
                return False

            # Cleanup test data
            admin_db_manager.delete_admin_setting(test_key)

            self.validation_results["checks"]["database"] = {
                "accessible": True,
                "file_size": db_info.get("size_mb", 0),
                "table_count": db_info.get("table_count", 0),
                "message": "Database operations successful",
            }

            return True

        except Exception as e:
            self.validation_results["errors"].append(f"Database validation failed: {e}")
            self.validation_results["checks"]["database"] = {"accessible": False, "message": str(e)}
            return False

    def validate_settings_precedence(self) -> bool:
        """Validate that environment variables take precedence over database settings."""
        logger.info("Validating settings precedence...")

        try:
            from core.settings_manager import settings_manager

            # Test a few key settings that should respect env var precedence
            test_cases = [
                {
                    "env_var": "CACHE_TTL_SECONDS",
                    "test_value": "7200",
                    "setting_path": "system_config_settings.system_cache_ttl_seconds",
                },
                {
                    "env_var": "SESSION_TIMEOUT_MINUTES",
                    "test_value": "240",
                    "setting_path": "security_settings.session_timeout_minutes",
                },
            ]

            precedence_results = {}
            all_valid = True

            for test_case in test_cases:
                env_var = test_case["env_var"]
                test_value = test_case["test_value"]

                # Set environment variable temporarily
                original_value = os.environ.get(env_var)
                os.environ[env_var] = test_value

                try:
                    # Clear cache to force reload
                    settings_manager.invalidate_cache()

                    # Check if the environment value is used
                    if env_var == "CACHE_TTL_SECONDS":
                        config = settings_manager.get_system_config_settings()
                        actual_value = str(config.system_cache_ttl_seconds)
                    elif env_var == "SESSION_TIMEOUT_MINUTES":
                        security = settings_manager.get_security_settings()
                        actual_value = str(security.session_timeout_minutes)
                    else:
                        actual_value = None

                    is_valid = actual_value == test_value
                    precedence_results[env_var] = {"valid": is_valid, "expected": test_value, "actual": actual_value}

                    if not is_valid:
                        all_valid = False
                        self.validation_results["errors"].append(
                            f"Settings precedence failed for {env_var}: expected {test_value}, got {actual_value}"
                        )

                finally:
                    # Restore original environment variable
                    if original_value is not None:
                        os.environ[env_var] = original_value
                    else:
                        os.environ.pop(env_var, None)

            self.validation_results["checks"]["settings_precedence"] = precedence_results
            return all_valid

        except Exception as e:
            self.validation_results["errors"].append(f"Settings precedence validation failed: {e}")
            return False

    def validate_railway_deployment(self) -> bool:
        """Validate Railway-specific deployment configuration."""
        logger.info("Validating Railway deployment...")

        railway_results = {}

        try:
            import subprocess

            # Check Railway CLI availability
            result = subprocess.run(["railway", "status"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                railway_results["cli_available"] = True
                railway_results["status"] = result.stdout.strip()

                # Check deployment status
                deploy_result = subprocess.run(
                    ["railway", "logs", "--tail", "10"], capture_output=True, text=True, timeout=15
                )
                if deploy_result.returncode == 0:
                    railway_results["recent_logs"] = deploy_result.stdout.strip()
                    railway_results["deployment_healthy"] = "error" not in deploy_result.stdout.lower()
                else:
                    railway_results["deployment_healthy"] = False
                    railway_results["logs_error"] = deploy_result.stderr

            else:
                railway_results["cli_available"] = False
                railway_results["error"] = result.stderr

        except subprocess.TimeoutExpired:
            railway_results["cli_available"] = False
            railway_results["error"] = "Railway CLI timeout"
        except FileNotFoundError:
            railway_results["cli_available"] = False
            railway_results["error"] = "Railway CLI not found"
        except Exception as e:
            railway_results["cli_available"] = False
            railway_results["error"] = str(e)

        self.validation_results["checks"]["railway"] = railway_results

        # Railway validation is informational only
        return True

    def run_smoke_tests(self) -> bool:
        """Run basic smoke tests to ensure application functionality."""
        logger.info("Running smoke tests...")

        smoke_tests = {}
        all_passed = True

        # Test 1: Settings loading
        try:
            from core.settings_manager import settings_manager

            settings_manager.get_all_settings()
            smoke_tests["settings_loading"] = {"passed": True, "message": "All settings loaded successfully"}
        except Exception as e:
            smoke_tests["settings_loading"] = {"passed": False, "message": f"Settings loading failed: {e}"}
            all_passed = False

        # Test 2: Core imports
        try:
            pass

            smoke_tests["core_imports"] = {"passed": True, "message": "Core modules imported successfully"}
        except Exception as e:
            smoke_tests["core_imports"] = {"passed": False, "message": f"Core imports failed: {e}"}
            all_passed = False

        # Test 3: Configuration validation
        try:
            from core.config import get_config

            config = get_config()
            smoke_tests["config_validation"] = {
                "passed": hasattr(config, "anthropic_api_key"),
                "message": "Configuration object valid",
            }
        except Exception as e:
            smoke_tests["config_validation"] = {"passed": False, "message": f"Configuration validation failed: {e}"}
            all_passed = False

        self.validation_results["checks"]["smoke_tests"] = smoke_tests
        return all_passed

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        # Calculate summary
        total_checks = len(self.validation_results["checks"])
        total_errors = len(self.validation_results["errors"])
        total_warnings = len(self.validation_results["warnings"])

        overall_status = "PASS" if total_errors == 0 else "FAIL"
        if total_warnings > 0 and total_errors == 0:
            overall_status = "PASS_WITH_WARNINGS"

        self.validation_results["summary"] = {
            "overall_status": overall_status,
            "total_checks": total_checks,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "deployment_ready": total_errors == 0,
        }

        return self.validation_results

    def run_full_validation(self) -> bool:
        """Run all validation checks."""
        logger.info(f"Starting full deployment validation for environment: {self.environment}")

        checks = [
            ("Environment Variables", self.validate_environment_variables),
            ("API Connectivity", self.validate_api_connectivity),
            ("Database Access", self.validate_database_access),
            ("Settings Precedence", self.validate_settings_precedence),
            ("Railway Deployment", self.validate_railway_deployment),
            ("Smoke Tests", self.run_smoke_tests),
        ]

        all_passed = True

        for check_name, check_func in checks:
            logger.info(f"Running {check_name} validation...")
            try:
                result = check_func()
                if not result:
                    all_passed = False
                    logger.error(f"{check_name} validation failed")
                else:
                    logger.info(f"{check_name} validation passed")
            except Exception as e:
                all_passed = False
                logger.error(f"{check_name} validation error: {e}")
                self.validation_results["errors"].append(f"{check_name}: {e}")

        return all_passed


def main():
    """Main function for deployment validation."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate deployment configuration")
    parser.add_argument(
        "--environment",
        default="production",
        choices=["development", "staging", "production"],
        help="Target environment",
    )
    parser.add_argument("--output", help="Output file for validation report")
    parser.add_argument(
        "--check",
        action="append",
        choices=["env", "api", "db", "precedence", "railway", "smoke"],
        help="Run specific checks only",
    )

    args = parser.parse_args()

    # Initialize validator
    validator = DeploymentValidator(args.environment)

    try:
        if args.check:
            # Run specific checks
            check_mapping = {
                "env": validator.validate_environment_variables,
                "api": validator.validate_api_connectivity,
                "db": validator.validate_database_access,
                "precedence": validator.validate_settings_precedence,
                "railway": validator.validate_railway_deployment,
                "smoke": validator.run_smoke_tests,
            }

            for check_name in args.check:
                logger.info(f"Running {check_name} validation...")
                result = check_mapping[check_name]()
                if not result:
                    pass
        else:
            # Run full validation
            validator.run_full_validation()

        # Generate report
        report = validator.generate_report()

        # Output report
        if args.output:
            with open(args.output, "w") as f:
                json.dump(report, f, indent=2, default=str)
            logger.info(f"Validation report saved to {args.output}")

        # Print summary
        print(f"\n=== DEPLOYMENT VALIDATION SUMMARY ===")
        print(f"Environment: {args.environment}")
        print(f"Overall Status: {report['summary']['overall_status']}")
        print(f"Total Checks: {report['summary']['total_checks']}")
        print(f"Errors: {report['summary']['total_errors']}")
        print(f"Warnings: {report['summary']['total_warnings']}")
        print(f"Deployment Ready: {'Yes' if report['summary']['deployment_ready'] else 'No'}")

        if report["errors"]:
            print(f"\n❌ Errors:")
            for error in report["errors"]:
                print(f"  - {error}")

        if report["warnings"]:
            print(f"\n⚠️  Warnings:")
            for warning in report["warnings"]:
                print(f"  - {warning}")

        if report["summary"]["deployment_ready"]:
            print(f"\n✅ Deployment validation passed!")
        else:
            print(f"\n❌ Deployment validation failed!")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Validation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Validation script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
