---
title: 'GitHub Secrets Integration for Firebase API Key'
slug: 'gh-secrets-firebase-api-key'
created: '2026-01-22'
status: 'in-progress'
stepsCompleted: [1, 2, 3, 4, 5]
implementedDate: '2026-01-22'
tech_stack: ['bash', 'python3.8+', 'gh-cli', 'pydantic-v2', 'click', 'rich', 'pytest']
files_to_modify: ['setup.sh', 'sbm/cli.py', 'sbm/config.py', 'sbm/utils/secure_store.py', '.github/workflows/fetch-firebase-api-key.yml', '.env.example', 'README.md', '.gitignore', 'CHANGELOG.md', 'tests/test_config.py']
code_patterns: ['bash-functions', 'pydantic-settings', 'click-commands', 'rich-ui', 'pytest-fixtures']
test_patterns: ['pytest-fixtures', 'unittest-mock', 'env-variable-mocking', 'integration-tests-marked']
---

# Tech-Spec: GitHub Secrets Integration for Firebase API Key

**Created:** 2026-01-22

## Overview

### Problem Statement

Firebase API key is required for ALL auto-sbm operations (stats tracking). Currently requires manual `.env` setup, which is error-prone and a barrier to onboarding new users. The 1Password CLI approach was over-engineered and created unnecessary complexity.

### Solution

Use GitHub Secrets + GitHub Actions to fetch `FIREBASE_API_KEY` during setup. If fetch fails (no repo access, auth issues, workflow failure), prompt the user to manually enter the key. This becomes a mandatory prerequisite for all migrations.

### Scope

**In Scope:**
- Store `FIREBASE_API_KEY` as GitHub repository secret (repo-level, not org-level)
- Add a GitHub Actions workflow that exposes the secret via artifact on demand
- Modify `setup.sh` to trigger the workflow, download artifact, and write to `.env`
- Add fallback prompt if fetch fails
- Validate API key exists in `.env` and isn't placeholder before allowing any migrations
- Add validation to `sbm setup` and `sbm update` commands (Python CLI)
- Add validation before any migration command runs (mandatory prereq check)
- Remove all 1Password CLI references and logic

**Out of Scope:**
- 1Password CLI integration (removing entirely)
- Marker files for tracking key fetch (checking `.env` directly is sufficient)
- GitHub repository secrets
- Optional/skippable Firebase config (it's now REQUIRED for all operations)

## Context for Development

### Codebase Patterns

**Bash (setup.sh):**
- Functions: `log()`, `warn()`, `error()` for consistent output
- Retry pattern: `retry_command()` for network operations with 3 attempts
- Step-based execution: Step 0-9 with clear progress indicators
- Cleanup on failure: `cleanup_failed_installation()` with ERR trap
- `.env` creation: Step 6 (lines 643-653) from `.env.example` template
- GitHub auth: Step 7 (lines 738-748) via `gh auth login`
- Firebase validation: Step 8 (lines 754-774) via `validate_firebase_api_key()`

**Python (sbm/cli.py):**
- Click commands with Rich UI integration (`rich_click`)
- Health checks: `is_env_healthy()` validates tools/packages
- Constants: `REQUIRED_CLI_TOOLS`, `REPO_ROOT`, marker files
- Setup integration: `setup()` command calls `setup.sh` then `_ensure_secure_firebase_secrets()`
- Config singleton: `get_settings()` returns `AutoSBMSettings` instance

**Config (sbm/config.py):**
- Pydantic v2 BaseSettings with nested models
- Environment variables: `FIREBASE__API_KEY`, `FIREBASE__DATABASE_URL` with double underscore delimiter
- Field validation: `@field_validator` for URL/path checks
- Default values: Hardcoded Firebase URL and API key (lines 110-116)
- Settings customization: Reads from keyring via `settings_customise_sources()` (lines 226-246)

**Tests:**
- Pytest with fixtures: `@pytest.fixture`, `clean_firebase_state`, `mock_settings`
- Mocking: `unittest.mock.patch`, `MagicMock` for dependencies
- Integration tests: `@pytest.mark.integration` with skip decorators
- Environment mocking: Override env vars in test fixtures

### Files to Reference

| File | Purpose | Changes Needed |
| ---- | ------- | -------------- |
| `setup.sh` | Main bash setup script | ADD: GitHub Actions fetch after gh auth; MODIFY: validate_firebase_api_key with fallback prompt; REMOVE: `op` from install_required_tools (line 170) |
| `.env.example` | Environment template | REMOVE: OP reference comments (lines 29-32) |
| `sbm/cli.py` | Python CLI entry point | REMOVE: OP functions (lines 2629-2712), keyring calls (line 2744-2773), `"op"` from REQUIRED_CLI_TOOLS (line 120), OP constants (lines 117-118); ADD: Firebase validation before migrate/auto commands |
| `sbm/config.py` | Pydantic settings | REMOVE: keyring from settings_customise_sources (lines 226-246); REMOVE: hardcoded default API key (line 114) |
| `sbm/utils/secure_store.py` | Keyring integration | DELETE: Entire file no longer needed |
| `.gitignore` | Git ignore rules | REMOVE: .sbm_op_refs entries (lines 75-76) |
| `README.md` | Documentation | REMOVE: OP references (lines 90-94, 218); ADD: GitHub Actions fetch instructions |
| `CHANGELOG.md` | Change history | ADD: Entry for this change |
| `tests/test_config.py` | Config unit tests | UPDATE: Remove keyring-related tests if any |
| `tests/test_firebase_integration.py` | Firebase integration tests | VERIFY: Tests still pass with new auth flow |
| `tests/test_firebase_sync.py` | Firebase sync tests | VERIFY: Tests still pass with new auth flow |

### Technical Decisions

**Architecture:**
- **Use GitHub Secrets at repo level**: Secret is stored in GitHub, workflow emits artifact for setup
- **Remove ALL existing auth systems**: Three systems exist (1Password CLI, macOS Keyring, manual .env) - consolidating to GitHub Secrets → .env only
- **Fallback to manual prompt**: Better UX than hard failure - allows custom key override when fetch fails
- **No marker files**: Directly check `.env` for API key presence and validity (not placeholder values)
- **Mandatory for all operations**: Firebase stats are core functionality, not optional

**Removal Decisions:**
- **1Password CLI (op)**: Over-engineered, complex onboarding, not needed for public Firebase Web API key
  - Remove from `REQUIRED_CLI_TOOLS`
  - Remove installation from `setup.sh`
  - Remove 9 functions from `sbm/cli.py` (OP refs, reading, writing, loading)
  - Remove OP marker files from `.gitignore`
  - Remove OP documentation from `README.md` and `.env.example`
- **macOS Keyring/secure_store**: Adds complexity, can fail, requires SBM_ENABLE_KEYRING flag
  - Delete `sbm/utils/secure_store.py` entirely
  - Remove keyring imports from `sbm/cli.py` and `sbm/config.py`
  - Remove `settings_customise_sources()` keyring integration
  - Remove `_ensure_secure_firebase_secrets()` function
  - Remove `_remove_env_secrets()` function

**Implementation Strategy:**
- Fetch during setup: After `gh auth login` (Step 7), before Firebase validation (Step 8)
- Store in `.env`: Simple `echo "FIREBASE__API_KEY=$api_key" >> .env` after sync
- Validate everywhere: `setup`, `update`, `migrate`, `auto` commands check key before proceeding
- Clear error messages: Tell users exactly what to do if key is missing

## Implementation Plan

### Tasks

#### Phase 1: Store Secret in GitHub (Pre-Implementation)

- [ ] Task 1: Store Firebase API key in GitHub repository secret
  - Command: `gh secret set FIREBASE_API_KEY --repo nate-hart-di/auto-sbm`
  - Value: `AIzaSyC278H_TiIrtGE_YYip1r28eDENYs-1RiI`
  - Notes: This must be done BEFORE implementation starts; verify with `gh secret list --repo nate-hart-di/auto-sbm`

#### Phase 2: Remove 1Password CLI Integration

- [ ] Task 2: Remove 1Password CLI from setup.sh
  - File: `setup.sh`
  - Action: Remove `"op"` from `tools` array in `install_required_tools()` function (line 170)
  - Action: Remove the `if [ "$tool" == "op" ]` special case block (lines 174-176)
  - Notes: Keep other tools (git, gh, python3, node) unchanged

- [ ] Task 3: Remove 1Password constants and functions from sbm/cli.py
  - File: `sbm/cli.py`
  - Action: Remove constants `OP_REFS_FILE` and `OP_REFS_MARKER` (lines 117-118)
  - Action: Remove `"op"` from `REQUIRED_CLI_TOOLS` list (line 120)
  - Action: Delete function `_read_op_refs_file()` (lines 2629-2646)
  - Action: Delete function `_write_op_refs_file()` (lines 2648-2659)
  - Action: Delete function `_ensure_op_refs()` (lines 2661-2676)
  - Action: Delete function `_read_1password_reference()` (lines 2678-2698)
  - Action: Delete function `_load_firebase_from_1password()` (lines 2701-2712)
  - Notes: Total of 7 constants/functions to remove (lines 117-118, 120, 2629-2712)

- [ ] Task 4: Remove 1Password references from documentation
  - File: `.env.example`
  - Action: Remove lines 29-32 (OP reference comments)
  - File: `README.md`
  - Action: Remove lines 90-94 (OP setup instructions)
  - Action: Remove line 218 (OP recommendation)
  - File: `.gitignore`
  - Action: Remove lines 75-76 (`.sbm_op_refs` and `.sbm_op_refs_complete`)

#### Phase 3: Remove Keyring/Secure Store Integration

- [ ] Task 5: Delete secure_store module
  - File: `sbm/utils/secure_store.py`
  - Action: Delete entire file (64 lines)
  - Notes: Module provides keyring integration, no longer needed

- [ ] Task 6: Remove keyring integration from sbm/cli.py
  - File: `sbm/cli.py`
  - Action: Remove import `from sbm.utils.secure_store import is_secure_store_available, set_secret` (line 105)
  - Action: Delete function `_remove_env_secrets()` (lines 2715-2742)
  - Action: Delete function `_ensure_secure_firebase_secrets()` (lines 2744-2773)
  - Action: Remove call to `_ensure_secure_firebase_secrets()` in `setup()` command (line 3321)
  - Notes: 3 functions + 1 import + 1 function call to remove

- [ ] Task 7: Remove keyring integration from sbm/config.py
  - File: `sbm/config.py`
  - Action: Delete entire `settings_customise_sources()` method (lines 226-246)
  - Action: Remove `from sbm.utils.secure_store import get_secret, is_secure_store_available` import if present
  - Action: Remove hardcoded default API key value on line 114, change to `default=None`
  - Notes: Config will now only read from .env, no keyring fallback

#### Phase 4: Add GitHub Actions Fetch to setup.sh

- [ ] Task 8: Add GitHub Actions workflow to emit secret as artifact
  - File: `.github/workflows/fetch-firebase-api-key.yml`
  - Action: Create workflow with `workflow_dispatch` trigger
  - Action: Write secret to `firebase_api_key.txt` and upload artifact `firebase-api-key`

- [ ] Task 9: Add GitHub Actions fetch function after gh auth
  - File: `setup.sh`
  - Action: Add new function `fetch_firebase_api_key_from_github_actions()` after `setup_github_auth()` function (around line 748)
  - Function logic:
    ```bash
    function fetch_firebase_api_key_from_github_actions() {
      local workflow_file="fetch-firebase-api-key.yml"
      local artifact_name="firebase-api-key"
      local download_dir="/tmp/auto-sbm-firebase-key"
      local key_file="$download_dir/firebase_api_key.txt"

      log "Fetching Firebase API key via GitHub Actions..."

      if ! gh workflow run "$workflow_file" &> /dev/null; then
        warn "❌ Failed to trigger GitHub Actions workflow: $workflow_file"
        return 1
      fi

      # Wait for latest run to complete
      local run_id=""
      for _ in {1..30}; do
        run_id=$(gh run list --workflow "$workflow_file" --limit 1 --json databaseId,status,conclusion -q '.[0].databaseId')
        run_status=$(gh run list --workflow "$workflow_file" --limit 1 --json status -q '.[0].status')
        run_conclusion=$(gh run list --workflow "$workflow_file" --limit 1 --json conclusion -q '.[0].conclusion')
        if [ -n "$run_id" ] && [ "$run_status" = "completed" ]; then
          if [ "$run_conclusion" != "success" ]; then
            warn "❌ GitHub Actions run failed (conclusion: $run_conclusion)"
            return 1
          fi
          break
        fi
        sleep 2
      done

      if [ -z "$run_id" ]; then
        warn "❌ Could not find a completed GitHub Actions run"
        return 1
      fi

      rm -rf "$download_dir"
      mkdir -p "$download_dir"

      if ! gh run download "$run_id" -n "$artifact_name" -D "$download_dir" &> /dev/null; then
        warn "❌ Failed to download artifact: $artifact_name"
        return 1
      fi

      if [ ! -f "$key_file" ]; then
        warn "❌ Firebase API key file missing in artifact"
        return 1
      fi

      local firebase_key
      firebase_key="$(cat "$key_file" | tr -d '\r\n')"

      if [ -z "$firebase_key" ]; then
        warn "❌ Firebase API key file is empty"
        return 1
      fi

      log "✅ Firebase API key fetched from GitHub Actions"
      if grep -q "^FIREBASE__API_KEY=" .env 2>/dev/null; then
        sed -i.bak "s|^FIREBASE__API_KEY=.*|FIREBASE__API_KEY=$firebase_key|" .env
        rm -f .env.bak
      else
        echo "FIREBASE__API_KEY=$firebase_key" >> .env
      fi
      export FIREBASE__API_KEY="$firebase_key"
      return 0
    }
    ```
  - Notes: Place after line 748 (after `setup_github_auth()`)

- [ ] Task 10: Add fallback manual prompt to validate_firebase_api_key
  - File: `setup.sh`
  - Action: Modify `validate_firebase_api_key()` function (lines 754-774) to add manual prompt fallback
  - Logic changes:
    ```bash
    # After existing validation logic that checks for placeholder/missing key
    # If key is still missing, prompt user
    if [ -z "${FIREBASE__API_KEY:-}" ] || [ "${FIREBASE__API_KEY}" = "your-firebase-web-api-key" ]; then
      echo ""
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo "⚠️  Firebase API Key Required"
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo ""
      echo "Auto-SBM requires a Firebase API key for stats tracking."
      echo "The key could not be fetched automatically."
      echo ""
      echo "If you have a custom key, enter it now."
      echo ""
      read -p "Enter Firebase API key (or press Enter to exit setup): " USER_KEY

      if [ -z "$USER_KEY" ]; then
        error "Setup cannot continue without Firebase API key"
        return 1
      fi

      # Write user-provided key to .env
      if grep -q "^FIREBASE__API_KEY=" .env 2>/dev/null; then
        sed -i.bak "s|^FIREBASE__API_KEY=.*|FIREBASE__API_KEY=$USER_KEY|" .env
        rm -f .env.bak
      else
        echo "FIREBASE__API_KEY=$USER_KEY" >> .env
      fi

      export FIREBASE__API_KEY="$USER_KEY"
      log "✅ Firebase API key stored in .env"
    fi
    ```

- [ ] Task 11: Call fetch function in setup.sh execution flow
  - File: `setup.sh`
  - Action: Add `fetch_firebase_api_key_from_github_actions` call after GitHub auth (Step 8, around line 750)
  - Insert after `setup_github_auth` and before Step 8 label:
    ```bash
    echo ""
    echo "Step 8/10: Fetching Firebase API key from GitHub Actions..."
    fetch_firebase_api_key_from_github_actions
    ```
  - Notes: Increment step numbers for Step 9 and 10 accordingly

#### Phase 5: Add Validation to Python CLI Commands

- [ ] Task 12: Create Firebase validation helper in sbm/cli.py
  - File: `sbm/cli.py`
  - Action: Add new function `_validate_firebase_key_required()` before command definitions (around line 1000)
  - Function logic:
    ```python
    def _validate_firebase_key_required() -> None:
        """Validate Firebase API key is present before running commands."""
        config = get_settings()

        # Check if API key is present and not a placeholder
        if not config.firebase.api_key or config.firebase.api_key == "your-firebase-web-api-key":
            logger.error("❌ Firebase API key is required for this operation")
            logger.error("")
            logger.error("The Firebase API key is missing or not configured properly.")
            logger.error("")
            logger.error("To resolve this:")
            logger.error("  1. Run: sbm setup")
        logger.error("  2. Or add it to .env: FIREBASE__API_KEY=<your-key>")
            sys.exit(1)
    ```

- [ ] Task 13: Add validation to migrate command
  - File: `sbm/cli.py`
  - Action: Add `_validate_firebase_key_required()` call at the beginning of `migrate()` function (after line 1082, before theme loop)
  - Insert: `_validate_firebase_key_required()`

- [ ] Task 14: Add validation to auto command
  - File: `sbm/cli.py`
  - Action: Add `_validate_firebase_key_required()` call at the beginning of `auto()` function (line ~1158)
  - Insert: `_validate_firebase_key_required()`

- [ ] Task 15: Add validation to update command
  - File: `sbm/cli.py`
  - Action: Add `_validate_firebase_key_required()` call at the beginning of `update()` function (line ~2784)
  - Insert: `_validate_firebase_key_required()`

- [ ] Task 16: Update setup command to skip keyring calls
  - File: `sbm/cli.py`
  - Action: Remove `_ensure_secure_firebase_secrets()` call from `setup()` function (line 3321, already done in Task 6)
  - Action: Verify setup() just calls setup.sh without additional Firebase logic
  - Notes: Setup.sh now handles all Firebase key fetching

#### Phase 6: Update Documentation

- [ ] Task 17: Update README.md with GitHub Actions instructions
  - File: `README.md`
  - Action: Replace removed OP instructions (lines 90-94) with new GitHub Actions section:
    ```markdown
    Firebase API key is fetched via GitHub Actions during setup.
    If the fetch fails, you'll be prompted to enter the key manually.
    ```
  - Action: Update line 218 to reference GitHub Actions instead of 1Password

- [ ] Task 18: Add CHANGELOG.md entry
  - File: `CHANGELOG.md`
  - Action: Add new entry under latest version:
    ```markdown
    ### Changed
    - **Firebase Authentication**: Simplified to use GitHub Secrets → .env only
    - Removed 1Password CLI integration (op) - no longer required
    - Removed macOS Keyring/secure_store - simpler authentication flow
    - Added automatic Firebase API key fetch via GitHub Actions during setup
    - Added manual fallback prompt if GitHub fetch fails
    - Added mandatory Firebase API key validation before all migration commands
    ```

#### Phase 7: Testing & Verification

- [ ] Task 19: Run existing test suite
  - Command: `pytest tests/ -v`
  - Action: Verify all tests pass after removals
  - Action: Check for any tests that reference removed modules (secure_store, OP functions)
  - Notes: Fix or remove tests that depend on removed functionality

- [ ] Task 20: Manual testing - fresh setup
  - Action: Test full `setup.sh` execution on clean machine
- Verify: GitHub Actions fetch works when authenticated
  - Verify: Fallback prompt appears if fetch fails
  - Verify: `.env` contains correct FIREBASE__API_KEY after setup

- [ ] Task 21: Manual testing - migration validation
  - Action: Run `sbm migrate <theme>` without Firebase key in .env
  - Verify: Command exits with clear error message
  - Action: Add key to .env and retry
  - Verify: Migration proceeds normally

### Acceptance Criteria

**Setup & Configuration:**

- [ ] AC1: Given GitHub is authenticated and secret exists, when setup.sh runs, then Firebase API key is automatically fetched via GitHub Actions and written to .env
- [ ] AC2: Given GitHub fetch fails, when setup.sh runs, then user is prompted to manually enter Firebase API key
- [ ] AC3: Given user enters valid API key at prompt, when setup completes, then .env contains FIREBASE__API_KEY=<user-provided-key>
- [ ] AC4: Given user presses Enter at prompt without entering key, when setup runs, then setup fails with error message

**Validation:**

- [ ] AC5: Given Firebase API key is missing from .env, when user runs `sbm migrate`, then command exits with error message instructing how to resolve
- [ ] AC6: Given Firebase API key is placeholder value "your-firebase-web-api-key", when user runs `sbm auto`, then command exits with validation error
- [ ] AC7: Given Firebase API key is valid in .env, when user runs any migration command, then command proceeds without validation errors
- [ ] AC8: Given Firebase API key is missing, when user runs `sbm update`, then command exits with error message

**Removal/Cleanup:**

- [ ] AC9: Given 1Password CLI removal, when setup.sh runs, then `op` tool is not installed
- [ ] AC10: Given keyring removal, when Python imports are checked, then `sbm.utils.secure_store` module does not exist
- [ ] AC11: Given removed OP functions, when sbm/cli.py is inspected, then no references to `_read_op_refs_file`, `_write_op_refs_file`, `_ensure_op_refs`, `_read_1password_reference`, `_load_firebase_from_1password` exist
- [ ] AC12: Given removed keyring functions, when sbm/cli.py is inspected, then no references to `_ensure_secure_firebase_secrets`, `_remove_env_secrets` exist
- [ ] AC13: Given config changes, when sbm/config.py is inspected, then `settings_customise_sources()` method does not exist and hardcoded API key default is removed

**Documentation:**

- [ ] AC14: Given updated README, when documentation is reviewed, then no references to 1Password CLI exist
- [ ] AC15: Given updated .env.example, when file is reviewed, then no OP reference comments exist
- [ ] AC16: Given updated .gitignore, when file is reviewed, then no .sbm_op_refs entries exist
- [ ] AC17: Given CHANGELOG update, when file is reviewed, then entry describes Firebase authentication simplification

**Integration:**

- [ ] AC18: Given existing test suite, when `pytest tests/` runs, then all tests pass
- [ ] AC19: Given Firebase integration tests, when tests run, then connection succeeds with new authentication flow
- [ ] AC20: Given fresh auto-sbm installation, when user completes setup and runs first migration, then stats are successfully synced to Firebase

## Additional Context

### Dependencies

**Required (already present):**
- GitHub CLI (`gh`) - installed in `setup.sh` Step 1, authenticated in Step 7
- `.env` file - created from `.env.example` in Step 6
- Firebase Realtime Database - `https://auto-sbm-default-rtdb.firebaseio.com`
- Firebase anonymous auth - implemented in `sbm/utils/firebase_sync.py`
- Pydantic v2 - config validation in `sbm/config.py`

**To Remove:**
- 1Password CLI (`op`) - currently installed in setup.sh, no longer needed
- keyring package - optional dependency, removing usage
- secure_store module - will be deleted

**External Services:**
- GitHub repository: `nate-hart-di/auto-sbm` (where secret is stored)
- Firebase project: `auto-sbm` (anonymous auth endpoint)

### Testing Strategy

**Unit Tests:**
- Mock GitHub Actions artifact download
- Test fallback prompt when GitHub fetch fails
- Test validation logic in setup/update/migrate commands
- Verify placeholder detection (not accepting `your-firebase-web-api-key`)

**Integration Tests:**
- Test full setup.sh flow with GitHub Actions fetch
- Test Firebase connection with fetched API key
- Verify existing Firebase tests still pass

**Manual Testing:**
- Fresh install on clean machine
- Setup with GitHub auth already present
- Setup when GitHub fetch fails (simulate by denying repo access)
- Verify all migration commands check for API key

**Regression Testing:**
- Run existing test suite: `pytest tests/`
- Verify no tests depend on removed OP or keyring functionality
- Check that Firebase integration tests still pass

### Notes

**Context:**
- Prior chat context showed attempted 1Password CLI integration - this is being removed
- User (Nate) expressed frustration with complexity - this solution is much simpler
- API key: `AIzaSyC278H_TiIrtGE_YYip1r28eDENYs-1RiI` (for GitHub Secret storage and testing)

**Investigation Findings:**
- **Three auth systems found**: 1Password CLI (9 functions), macOS Keyring (secure_store module), manual .env (current)
- **1Password CLI locations**: `setup.sh` line 170, `sbm/cli.py` lines 117-118, 120, 2629-2712, `.gitignore` lines 75-76, `README.md` lines 90-94, 218
- **Keyring locations**: `sbm/utils/secure_store.py` (entire file), `sbm/cli.py` lines 105, 2744-2773, `sbm/config.py` lines 226-246
- **Current validation**: `setup.sh` line 754 checks for placeholder, but no validation before migrations run
- **Config defaults**: Firebase URL default remains; API key is required from .env
- **Test coverage**: 3 Firebase test files exist, use pytest fixtures and mocking patterns

**Architecture Decision (confirmed with user):**
- Remove keyring/secure_store entirely - adds complexity for minimal security benefit on public Firebase Web API key
- GitHub Secrets → .env is sufficient - simpler, fewer failure modes, easier to debug

---

## Dev Agent Record

### File List
- setup.sh
- sbm/config.py
- sbm/cli.py
- .github/workflows/fetch-firebase-api-key.yml
- .env.example
- README.md
- CHANGELOG.md
- tests/test_config.py
- _bmad-output/implementation-artifacts/tech-spec-gh-secrets-firebase-api-key.md

### Tests
- `pytest tests/test_config.py -q`
- `pytest tests/test_firebase_sync.py -q`
