#!/bin/bash
# SBM Master Script
# This is the main entry point for the Site Builder Migration process

# Set up environment
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PARENT_DIR="$( dirname "$SCRIPT_DIR" )"
export PYTHONPATH="$PARENT_DIR:$PYTHONPATH"

# Set default DI_WEBSITES_PLATFORM_DIR if not already set
if [ -z "$DI_WEBSITES_PLATFORM_DIR" ]; then
    export DI_WEBSITES_PLATFORM_DIR="/Users/nathanhart/di-websites-platform"
    echo -e "${YELLOW}DI_WEBSITES_PLATFORM_DIR was not set, using default: $DI_WEBSITES_PLATFORM_DIR${NC}"
fi

# Default configuration
SKIP_JUST=false
FORCE_RESET=false
SKIP_GIT=false
SKIP_MAPS=false
PLATFORM_DIR=""
VERBOSE=false

# Color codes
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No color

# Function to show usage
show_usage() {
    echo -e "${BLUE}Site Builder Migration (SBM) Tool${NC}"
    echo "A comprehensive toolset for automating dealer website migrations to the Site Builder platform."
    echo ""
    echo "Usage: $0 [options] <dealer-slug> [dealer-slug2 ...]"
    echo ""
    echo "Options:"
    echo "  --skip-just          Skip the 'just start' command (use if site is already started)"
    echo "  --force-reset        Force reset Site Builder files if they already exist"
    echo "  --skip-git           Skip Git operations (checkout, branch creation)"
    echo "  --skip-maps          Skip map components migration"
    echo "  --platform-dir=DIR   Set the DI Websites Platform directory"
    echo "  --verbose            Enable verbose output"
    echo "  --help               Show this help message"
    echo ""
    echo "Example: $0 fiatofportland --skip-just"
    echo ""
}

# Function to check if a dealer site is already started
check_dealer_started() {
    local slug=$1
    
    # If platform dir is not set, use the environment variable
    if [ -z "$PLATFORM_DIR" ]; then
        PLATFORM_DIR="${DI_WEBSITES_PLATFORM_DIR}"
    fi
    
    # Check if the dealer site is started by looking for site.json
    local site_json="${PLATFORM_DIR}/site.json"
    
    if [ ! -f "$site_json" ]; then
        echo -e "${YELLOW}Site not started. Need to run 'just start' command.${NC}"
        return 1
    fi
    
    # Check if the current site matches the slug
    local current_site=$(grep -o '"slug":"[^"]*' "$site_json" | cut -d':' -f2 | tr -d '"')
    
    if [ "$current_site" != "$slug" ]; then
        echo -e "${YELLOW}Different site currently started: $current_site${NC}"
        echo -e "Need to start $slug."
        return 1
    fi
    
    echo -e "${GREEN}Dealer site $slug is already started.${NC}"
    return 0
}

# Function to start a dealer site
start_dealer() {
    local slug=$1
    
    echo -e "${BLUE}Starting dealer site: $slug${NC}"
    
    # Look for start-dealer.sh in both script directory and parent directory
    START_DEALER_SCRIPT=""
    if [ -f "$SCRIPT_DIR/start-dealer.sh" ]; then
        START_DEALER_SCRIPT="$SCRIPT_DIR/start-dealer.sh"
    elif [ -f "$PARENT_DIR/start-dealer.sh" ]; then
        START_DEALER_SCRIPT="$PARENT_DIR/start-dealer.sh"
    fi
    
    if [ -n "$START_DEALER_SCRIPT" ]; then
        # Make sure it's executable
        chmod +x "$START_DEALER_SCRIPT"
        
        # Run the start-dealer.sh script
        "$START_DEALER_SCRIPT" "$slug" prod
        if [ $? -ne 0 ]; then
            echo -e "${RED}Failed to start dealer site: $slug${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}start-dealer.sh not found, using direct command${NC}"
        
        # If platform dir is not set, use the environment variable
        if [ -z "$PLATFORM_DIR" ]; then
            PLATFORM_DIR="${DI_WEBSITES_PLATFORM_DIR}"
        fi
        
        # Change to the platform directory
        cd "$PLATFORM_DIR"
        
        # Run the just start command
        just start "$slug" prod
        if [ $? -ne 0 ]; then
            echo -e "${RED}Failed to start dealer site: $slug${NC}"
            return 1
        fi
    fi
    
    echo -e "${GREEN}Successfully started dealer site: $slug${NC}"
    return 0
}

# Function to run the migration
run_migration() {
    local slug=$1
    
    echo -e "${BLUE}Running migration for: $slug${NC}"
    
    # Build the migration command
    COMMAND="python3 -m sbm.cli"
    
    # Add the options
    if [ "$SKIP_JUST" = true ]; then
        COMMAND="$COMMAND --skip-just"
    fi
    
    if [ "$FORCE_RESET" = true ]; then
        COMMAND="$COMMAND --force-reset"
    fi
    
    if [ "$SKIP_GIT" = true ]; then
        COMMAND="$COMMAND --skip-git"
    fi
    
    if [ "$SKIP_MAPS" = true ]; then
        COMMAND="$COMMAND --skip-maps"
    fi
    
    if [ -n "$PLATFORM_DIR" ]; then
        COMMAND="$COMMAND --platform-dir=\"$PLATFORM_DIR\""
    fi
    
    if [ "$VERBOSE" = true ]; then
        COMMAND="$COMMAND --verbose"
    fi
    
    # Add the slug
    COMMAND="$COMMAND $slug"
    
    # Run the command
    cd "$PARENT_DIR"
    echo "Executing: $COMMAND"
    eval "$COMMAND"
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Migration failed for: $slug${NC}"
        return 1
    fi
    
    echo -e "${GREEN}Migration completed successfully for: $slug${NC}"
    return 0
}

# Function to handle post-migration steps
post_migration() {
    local slug=$1
    
    echo -e "${BLUE}Running post-migration steps for: $slug${NC}"
    
    # Ask if the user wants to run post-migration steps
    read -p "Do you want to run post-migration steps (commit, push, PR creation)? [y/N] " answer
    
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        # Look for post-migration.sh in both script directory and parent directory
        POST_MIGRATION_SCRIPT=""
        if [ -f "$SCRIPT_DIR/post-migration.sh" ]; then
            POST_MIGRATION_SCRIPT="$SCRIPT_DIR/post-migration.sh"
        elif [ -f "$PARENT_DIR/post-migration.sh" ]; then
            POST_MIGRATION_SCRIPT="$PARENT_DIR/post-migration.sh"
        fi
        
        if [ -n "$POST_MIGRATION_SCRIPT" ]; then
            # Make sure it's executable
            chmod +x "$POST_MIGRATION_SCRIPT"
            
            # Run the post-migration.sh script
            "$POST_MIGRATION_SCRIPT" "$slug"
            if [ $? -ne 0 ]; then
                echo -e "${RED}Post-migration steps failed for: $slug${NC}"
                return 1
            fi
        else
            echo -e "${YELLOW}post-migration.sh not found in $SCRIPT_DIR or $PARENT_DIR, skipping post-migration steps${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}Skipping post-migration steps${NC}"
    fi
    
    return 0
}

# Parse command line arguments
SLUGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-just)
            SKIP_JUST=true
            shift
            ;;
        --force-reset)
            FORCE_RESET=true
            shift
            ;;
        --skip-git)
            SKIP_GIT=true
            shift
            ;;
        --skip-maps)
            SKIP_MAPS=true
            shift
            ;;
        --platform-dir=*)
            PLATFORM_DIR="${1#*=}"
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        -*)
            echo -e "${RED}Unknown option: $1${NC}"
            show_usage
            exit 1
            ;;
        *)
            SLUGS+=("$1")
            shift
            ;;
    esac
done

# Check if we have any slugs
if [ ${#SLUGS[@]} -eq 0 ]; then
    echo -e "${RED}Error: No dealer slugs provided${NC}"
    show_usage
    exit 1
fi

# Process each slug
for slug in "${SLUGS[@]}"; do
    echo -e "${BLUE}=== Processing dealer: $slug ===${NC}"
    
    # If not skipping just, check if the dealer site is already started
    if [ "$SKIP_JUST" = false ]; then
        if ! check_dealer_started "$slug"; then
            # Try to start the dealer site
            if ! start_dealer "$slug"; then
                echo -e "${RED}Skipping migration for $slug due to startup failure${NC}"
                continue
            fi
        fi
    fi
    
    # Run the migration
    if ! run_migration "$slug"; then
        echo -e "${RED}Migration failed for $slug${NC}"
        continue
    fi
    
    # Run post-migration steps
    post_migration "$slug"
    
    echo -e "${GREEN}=== Completed processing: $slug ===${NC}"
done

echo -e "${GREEN}All operations completed.${NC}"
exit 0 
