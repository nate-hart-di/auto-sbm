#!/bin/bash

# SBM - Site Builder Migration Tool
# Interactive wrapper script for site_builder_migration.py

PLATFORM_DIR="/Users/nathanhart/di-websites-platform"
AUTO_SBM_DIR="/Users/nathanhart/auto-sbm"
LOG_DIR="$AUTO_SBM_DIR/logs"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Generate timestamp for log files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/sbm_${TIMESTAMP}.log"

# Function to log messages
log() {
  echo "$(date +"%Y-%m-%d %H:%M:%S") - $1" | tee -a "$LOG_FILE"
}

# Ensure helper scripts exist and are executable
START_DEALER_SCRIPT="$AUTO_SBM_DIR/start-dealer.sh"
POST_MIGRATION_SCRIPT="$AUTO_SBM_DIR/post-migration.sh"
CREATE_PR_SCRIPT="$AUTO_SBM_DIR/create-pr.sh"

if [ -f "$START_DEALER_SCRIPT" ]; then
  chmod +x "$START_DEALER_SCRIPT"
  log "Start dealer script available at $START_DEALER_SCRIPT"
else
  log "Warning: Start dealer script not found at $START_DEALER_SCRIPT"
fi

if [ -f "$POST_MIGRATION_SCRIPT" ]; then
  chmod +x "$POST_MIGRATION_SCRIPT"
  log "Post-migration script available at $POST_MIGRATION_SCRIPT"
else
  log "Warning: Post-migration script not found at $POST_MIGRATION_SCRIPT"
fi

if [ -f "$CREATE_PR_SCRIPT" ]; then
  chmod +x "$CREATE_PR_SCRIPT"
  log "PR creation script available at $CREATE_PR_SCRIPT"
else
  log "Warning: PR creation script not found at $CREATE_PR_SCRIPT"
fi

# Function to open files
open_files() {
  # Check if any files were provided
  if [ $# -eq 0 ]; then
    log "No files to open"
    return
  fi
  
  log "Opening modified files:"
  for file in "$@"; do
    if [ -f "$file" ]; then
      log "Opening: $file"
      open "$file"
    else
      log "File not found: $file"
    fi
  done
}

# Get the list of dealer themes
get_dealer_themes() {
  find "$PLATFORM_DIR/dealer-themes" -maxdepth 1 -type d | grep -v "^$PLATFORM_DIR/dealer-themes$" | xargs -n1 basename
}

# Function to run post-migration workflow
run_post_migration() {
  local slug="$1"
  if [ -f "$POST_MIGRATION_SCRIPT" ]; then
    log "Running post-migration workflow for $slug"
    bash "$POST_MIGRATION_SCRIPT" "$slug" 2>&1 | tee -a "$LOG_FILE"
  else
    log "Post-migration script not found. Please run these commands manually:"
    log "  cd $PLATFORM_DIR"
    log "  git add ."
    log "  git commit -m \"$slug SBM FE Audit\""
    log "  git push origin ${slug}-sbm$(date +"%m%y")"
  fi
}

# Main function
main() {
  # Log header
  log "=== SBM - Site Builder Migration Tool ==="
  log "Platform directory: $PLATFORM_DIR"

  # Check if dealer slug was provided
  if [ $# -gt 0 ]; then
    DEALER="$1"
    log "Dealer slug provided: $DEALER"
  else
    # Get dealer themes
    DEALERS=($(get_dealer_themes))
    DEALER_COUNT=${#DEALERS[@]}
    
    if [ $DEALER_COUNT -eq 0 ]; then
      log "No dealer themes found in $PLATFORM_DIR/dealer-themes"
      echo "No dealer themes found. Please check the platform directory."
      exit 1
    elif [ $DEALER_COUNT -eq 1 ]; then
      DEALER="${DEALERS[0]}"
      echo "Found one dealer theme: $DEALER"
      read -p "Proceed with migration for $DEALER? (y/n): " CONFIRM
      if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
        log "Migration cancelled by user"
        echo "Migration cancelled. Exiting."
        exit 0
      fi
    else
      echo "Found multiple dealer themes:"
      for i in "${!DEALERS[@]}"; do
        echo "$((i+1)). ${DEALERS[$i]}"
      done
      
      while true; do
        read -p "Enter the number of the dealer theme to migrate (1-$DEALER_COUNT): " SELECTION
        if [[ $SELECTION =~ ^[0-9]+$ ]] && [ $SELECTION -ge 1 ] && [ $SELECTION -le $DEALER_COUNT ]; then
          DEALER="${DEALERS[$((SELECTION-1))]}"
          break
        else
          echo "Invalid selection. Please enter a number between 1 and $DEALER_COUNT."
        fi
      done
    fi
  fi
  
  log "Selected dealer theme: $DEALER"
  
  # Check if dealer is already started
  echo ""
  echo "=== IMPORTANT: New Workflow ==="
  echo "It's recommended to start the dealer site separately before running the migration."
  echo "This ensures the environment is properly set up and avoids issues during migration."
  echo ""
  echo "To start the dealer site: $START_DEALER_SCRIPT $DEALER prod"
  echo ""
  read -p "Have you already started the dealer site? (y/n): " SITE_STARTED
  
  if [[ ! $SITE_STARTED =~ ^[Yy]$ ]]; then
    echo ""
    echo "Starting dealer site first..."
    if [ -f "$START_DEALER_SCRIPT" ]; then
      # Set environment variable to indicate script is called from sbm.sh
      export CALLED_FROM_SBM="true"
      bash "$START_DEALER_SCRIPT" "$DEALER" "prod" 2>&1 | tee -a "$LOG_FILE"
      if [ ${PIPESTATUS[0]} -ne 0 ]; then
        echo "Failed to start dealer site. Please fix the issues before running the migration."
        exit 1
      fi
    else
      echo "Start dealer script not found. Please run these commands manually:"
      echo "  cd $PLATFORM_DIR"
      echo "  just start $DEALER prod"
      read -p "Press Enter to continue after starting the dealer site manually..." DUMMY
    fi
  fi
  
  echo "Starting migration for $DEALER..."
  
  # Run the migration script
  cd "$AUTO_SBM_DIR"
  log "Running: python3 -u site_builder_migration.py --platform-dir=$PLATFORM_DIR --skip-just $DEALER"
  echo "Starting migration process... This may take a few minutes..."
  echo "Migration is running in the background. You will see output as it progresses."
  python3 -u site_builder_migration.py --platform-dir="$PLATFORM_DIR" --skip-just "$DEALER" 2>&1 | tee -a "$LOG_FILE"
  MIGRATION_EXIT_CODE=${PIPESTATUS[0]}
  
  if [ $MIGRATION_EXIT_CODE -eq 0 ]; then
    log "Migration completed successfully"
    
    # Find and open modified files
    THEME_DIR="$PLATFORM_DIR/dealer-themes/$DEALER"
    MODIFIED_FILES=(
      "$THEME_DIR/sb-inside.scss"
      "$THEME_DIR/sb-vdp.scss"
      "$THEME_DIR/sb-vrp.scss"
    )
    
    # Filter out files that don't exist
    EXISTING_FILES=()
    for file in "${MODIFIED_FILES[@]}"; do
      if [ -f "$file" ]; then
        EXISTING_FILES+=("$file")
      fi
    done
    
    # Generate a detailed report of changes
    echo ""
    log "=== Migration Report ==="
    
    # List all created/modified files
    log "Modified Files:"
    for file in "${EXISTING_FILES[@]}"; do
      if [ -f "$file" ]; then
        log "- $(basename "$file"): $(wc -l < "$file") lines"
        # Extract section headers to summarize content
        grep -n "\/\/ " "$file" | while read -r line; do
          log "  * $line"
        done
      fi
    done
    
    # Check for map components migration
    MAP_PARTIALS_DIR="$THEME_DIR/partials/dealer-groups"
    if [ -d "$MAP_PARTIALS_DIR" ]; then
      log "Map Components Migration:"
      find "$MAP_PARTIALS_DIR" -type f -name "*.php" | while read -r map_file; do
        log "- Migrated map partial: $(basename "$map_file")"
      done
    fi
    
    # Source files that were reviewed
    CSS_DIR="$THEME_DIR/css"
    log "Reviewed Source Files:"
    for source in "$CSS_DIR/style.scss" "$CSS_DIR/inside.scss" "$CSS_DIR/lvdp.scss" "$CSS_DIR/lvrp.scss"; do
      if [ -f "$source" ]; then
        log "- $(basename "$source"): $(wc -l < "$source") lines"
      fi
    done
    
    # Open the files
    echo ""
    echo "Opening modified files..."
    open_files "${EXISTING_FILES[@]}"
    
    echo ""
    echo "Migration completed successfully."
    echo "Log file: $LOG_FILE"
    
    # Ask if user wants to run post-migration now
    echo ""
    read -p "Would you like to commit and push these changes now? (y/n): " RUN_POST
    if [[ $RUN_POST =~ ^[Yy]$ ]]; then
      run_post_migration "$DEALER"
    else
      echo "You can run the post-migration workflow later with:"
      echo "  $POST_MIGRATION_SCRIPT $DEALER"
    fi
  else
    log "Migration failed with exit code $MIGRATION_EXIT_CODE"
    echo "Migration failed. Check the log file for details."
    echo "Log file: $LOG_FILE"
  fi
}

# Call the main function with all provided arguments
main "$@" 
