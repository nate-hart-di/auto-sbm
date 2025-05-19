#!/bin/bash
# Helper script to start a dealer site before running site builder migration

# Check if arguments are provided
if [ -z "$1" ]; then
  echo "Usage: $0 <dealer-slug> [environment]"
  echo "Example: $0 fiatofportland prod"
  exit 1
fi

# Get dealer slug from first argument
DEALER=$1

# Get environment from second argument, default to prod
ENVIRONMENT=${2:-"prod"}

# Set platform directory, or use default if not set
PLATFORM_DIR=${DI_WEBSITES_PLATFORM_DIR:-"/Users/nathanhart/di-websites-platform"}

# Check if platform directory exists
if [ ! -d "$PLATFORM_DIR" ]; then
  echo "Error: Platform directory not found at $PLATFORM_DIR"
  echo "Please make sure DI_WEBSITES_PLATFORM_DIR is set correctly or the default path exists."
  exit 1
fi

# Change to platform directory
echo "Changing to platform directory: $PLATFORM_DIR"
cd "$PLATFORM_DIR"

# Execute just start command
echo "Starting dealer theme: $DEALER ($ENVIRONMENT)"
echo "Running: just start $DEALER $ENVIRONMENT"
echo "This may take a few minutes..."

# Execute just start command
# Using the execute_command function for real-time output
execute_command() {
  # Run the command and capture the output and error streams
  output=$(just start $DEALER $ENVIRONMENT 2>&1)
  # Get the exit status of the command
  status=$?
  
  # Print the output
  echo "$output"
  
  # Check if the command was successful
  if [ $status -eq 0 ]; then
    if echo "$output" | grep -q "Starting the web server"; then
      echo "===== Dealer theme started successfully ====="
      
      # Check if this was called from the main sbm.sh script
      if [ "$CALLED_FROM_SBM" = "true" ]; then
        echo "Continuing with migration..."
        # Exit with success status - the main script will continue
        exit 0
      else
        # If running standalone, provide message but don't wait for input
        echo "You can now proceed with the migration by running:"
        echo "  cd $(dirname "$0")"
        echo "  ./sbm.sh $DEALER"
        exit 0
      fi
    else
      echo "Warning: The dealer theme may have started, but with warnings or errors."
      echo "Please check the output above for any issues before proceeding."
      
      # Check if this was called from the main sbm.sh script
      if [ "$CALLED_FROM_SBM" = "true" ]; then
        # If called from main script, we'll continue automatically
        echo "Continuing with migration despite warnings..."
        exit 0
      else
        # Only ask for input if running standalone
        read -p "Would you like to continue anyway? (y/n): " CONTINUE
        if [[ ! $CONTINUE =~ ^[Yy]$ ]]; then
          echo "Exiting. Please fix the issues before running the migration."
          exit 1
        fi
      fi
    fi
  else
    echo "===== Error starting dealer theme ====="
    echo "The 'just start' command failed with exit code $status."
    echo "Please check the output above for errors and fix them before proceeding."
    exit 1
  fi
}

# Execute the command
execute_command

# Exit with success
exit 0 
