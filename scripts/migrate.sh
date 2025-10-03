#!/bin/bash

# Phase 3 Infrastructure Settings Migration Helper Script
# This script provides a guided workflow for migrating infrastructure settings

set -e  # Exit on any error

# Check bash version for compatibility
if [ -z "${BASH_VERSION:-}" ]; then
    echo "Error: This script requires bash to run properly"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "\n${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}\n"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi

    # Check Railway CLI for sync operations
    if command -v railway &> /dev/null; then
        log_success "Railway CLI is available"
        RAILWAY_AVAILABLE=true
    else
        log_warning "Railway CLI not found - Railway sync will be skipped"
        RAILWAY_AVAILABLE=false
    fi

    log_success "Prerequisites check passed"
}

# Show current state analysis
analyze_current_state() {
    print_header "ANALYZING CURRENT STATE"

    log_info "Running current state analysis..."
    python3 migrate_infra_settings.py --analyze-only

    echo
    read -p "Continue with migration? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Migration cancelled by user"
        exit 0
    fi
}

# Generate migration plan
generate_migration_plan() {
    print_header "GENERATING MIGRATION PLAN"

    local output_file=".env.migration"

    log_info "Generating migration plan (dry-run)..."
    python3 migrate_infra_settings.py --output "$output_file"

    if [[ -f "$output_file" ]]; then
        log_success "Migration plan generated: $output_file"
        log_info "Please review the generated file before proceeding"

        echo
        read -p "Open the file for review? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if command -v code &> /dev/null; then
                code "$output_file"
            elif command -v vim &> /dev/null; then
                vim "$output_file"
            else
                cat "$output_file"
            fi
        fi
    else
        log_error "Failed to generate migration plan"
        exit 1
    fi
}

# Execute migration
execute_migration() {
    print_header "EXECUTING MIGRATION"

    local env_file="${1:-.env.migration}"

    log_warning "This will execute the migration and create environment files"
    echo
    read -p "Proceed with migration execution? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Migration execution cancelled"
        return 1
    fi

    log_info "Executing infrastructure migration..."
    python3 migrate_infra_settings.py --execute --output "$env_file"

    log_success "Migration executed successfully"
    log_info "Environment file created: $env_file"
}

# Railway sync workflow
railway_sync_workflow() {
    if [[ "$RAILWAY_AVAILABLE" != true ]]; then
        log_warning "Railway CLI not available - skipping Railway sync"
        return 0
    fi

    print_header "RAILWAY ENVIRONMENT SYNC"

    local env_file="${1:-.env.migration}"

    if [[ ! -f "$env_file" ]]; then
        log_error "Environment file not found: $env_file"
        return 1
    fi

    log_info "Comparing local environment with Railway..."
    python3 railway_env_sync.py compare --env-file "$env_file"

    echo
    read -p "Push variables to Railway? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Pushing variables to Railway (dry-run)..."
        python3 railway_env_sync.py push --env-file "$env_file"

        echo
        read -p "Execute the push? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python3 railway_env_sync.py push --env-file "$env_file" --execute
            log_success "Variables pushed to Railway"
        fi
    fi
}

# Deployment validation
validate_deployment() {
    print_header "DEPLOYMENT VALIDATION"

    local environment="${1:-production}"

    log_info "Running deployment validation for $environment..."

    # Run validation and capture exit code
    if python3 deployment_validation.py --environment "$environment"; then
        log_success "Deployment validation passed!"
    else
        log_error "Deployment validation failed!"

        echo
        read -p "Run specific validation checks? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Available checks: env, api, db, precedence, railway, smoke"
            read -p "Enter checks to run (space-separated): " checks

            for check in $checks; do
                log_info "Running $check validation..."
                python3 deployment_validation.py --environment "$environment" --check "$check"
            done
        fi
    fi
}

# Main workflow
run_full_workflow() {
    local environment="${1:-production}"
    local env_file=".env.$environment"

    print_header "PHASE 3 INFRASTRUCTURE MIGRATION"
    log_info "Starting full migration workflow for $environment environment"

    check_prerequisites
    analyze_current_state
    generate_migration_plan
    execute_migration "$env_file"
    railway_sync_workflow "$env_file"
    validate_deployment "$environment"

    print_header "MIGRATION COMPLETE"
    log_success "Phase 3 infrastructure migration completed successfully!"
    log_info "Environment file: $env_file"
    log_info "Next steps:"
    echo "  1. Review and customize $env_file for your environment"
    echo "  2. Set security-critical variables manually"
    echo "  3. Deploy and monitor the application"
    echo "  4. Run post-deployment validation"
}

# Show usage
show_usage() {
    echo "Phase 3 Infrastructure Settings Migration Helper"
    echo
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo
    echo "Commands:"
    echo "  full [ENV]        Run complete migration workflow (default: production)"
    echo "  analyze           Analyze current state only"
    echo "  plan              Generate migration plan only"
    echo "  execute [FILE]    Execute migration with specified output file"
    echo "  sync [FILE]       Run Railway sync workflow"
    echo "  validate [ENV]    Run deployment validation"
    echo "  help              Show this help message"
    echo
    echo "Examples:"
    echo "  $0 full development     # Full workflow for development"
    echo "  $0 analyze              # Just analyze current state"
    echo "  $0 validate production  # Validate production deployment"
    echo
}

# Main command dispatcher
main() {
    case "${1:-full}" in
        "full")
            run_full_workflow "${2:-production}"
            ;;
        "analyze")
            check_prerequisites
            analyze_current_state
            ;;
        "plan")
            check_prerequisites
            generate_migration_plan
            ;;
        "execute")
            check_prerequisites
            execute_migration "$2"
            ;;
        "sync")
            check_prerequisites
            railway_sync_workflow "$2"
            ;;
        "validate")
            check_prerequisites
            validate_deployment "${2:-production}"
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            log_error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"