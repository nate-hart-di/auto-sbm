# Story 2.1: Firebase Infrastructure Setup

Status: review

## Story

As a Developer,
I want to set up the Firebase infrastructure and dependencies,
So that the application can connect to the remote database securely.

## Acceptance Criteria

**Given** the project codebase
**When** I install dependencies
**Then** `firebase-admin` is added to `pyproject.toml`
**And** `.env.example` is updated with `FIREBASE_CREDENTIALS_PATH` and `FIREBASE_DB_URL`
**And** `config.py` loads these new variables
**And** a service account JSON can be loaded successfully by the application

## Tasks / Subtasks

- [x] Task 1: Add Firebase dependency to project (AC: #1)
  - [x] Add `firebase-admin>=6.5.0` to `pyproject.toml` dependencies list
  - [x] Run `pip install firebase-admin` to verify installation
  - [x] Document version selection reasoning

- [x] Task 2: Update environment configuration (AC: #2)
  - [x] Add `FIREBASE_CREDENTIALS_PATH` to `.env.example`
  - [x] Add `FIREBASE_DB_URL` to `.env.example`
  - [x] Add inline comments explaining each variable's purpose
  - [x] Create `.gitignore` entry for Firebase service account JSON files if not exists

- [x] Task 3: Extend Pydantic configuration model (AC: #3)
  - [x] Create new `FirebaseSettings` class in `sbm/config.py`
  - [x] Add `credentials_path` field (Optional[Path]) for service account JSON
  - [x] Add `database_url` field (Optional[str]) for Firebase Realtime Database URL
  - [x] Add field validators for path existence and URL format
  - [x] Integrate `FirebaseSettings` into `AutoSBMSettings` using `Field(default_factory=...)`
  - [x] Ensure graceful degradation when Firebase is not configured

- [x] Task 4: Create Firebase initialization module (AC: #4)
  - [x] Create `sbm/utils/firebase_sync.py` module
  - [x] Implement `initialize_firebase()` function with connection validation
  - [x] Add error handling for missing/invalid credentials
  - [x] Return None or raise specific exceptions when Firebase is unavailable
  - [x] Log initialization status (success/failure) using existing logger

- [x] Task 5: Write unit tests
  - [x] Test `FirebaseSettings` validation (valid/invalid paths, URLs)
  - [x] Test Firebase initialization with mock credentials
  - [x] Test graceful degradation when credentials missing
  - [x] Verify no crashes when Firebase is unavailable

- [x] Task 6: Write integration tests
  - [x] Test actual Firebase connection with test service account (if available)
  - [x] Verify database URL connectivity
  - [x] Test error messages for common misconfiguration scenarios

## Dev Notes

### Critical Implementation Patterns

**Existing Pydantic v2 Configuration Pattern**: The codebase uses Pydantic v2 `BaseSettings` with nested configuration models. Firebase settings MUST follow this exact pattern:

```python
class FirebaseSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    credentials_path: Path | None = Field(
        default=None,
        description="Path to Firebase service account JSON file"
    )
    database_url: str | None = Field(
        default=None,
        description="Firebase Realtime Database URL"
    )

    @field_validator("credentials_path")
    @classmethod
    def validate_credentials_path(cls, v: Path | None) -> Path | None:
        if v is None:
            return v
        if not v.exists():
            msg = f"Firebase credentials file not found: {v}"
            raise ValueError(msg)
        return v
```

**Integration into AutoSBMSettings**:
```python
class AutoSBMSettings(BaseSettings):
    # ... existing fields ...
    firebase: FirebaseSettings = Field(default_factory=lambda: FirebaseSettings())
```

**Environment Variable Naming**: Following existing pattern, Firebase env vars should use double underscore delimiter:
- `FIREBASE__CREDENTIALS_PATH` maps to `firebase.credentials_path`
- `FIREBASE__DATABASE_URL` maps to `firebase.database_url`

### Existing Infrastructure to Leverage

1. **Stats Tracking System**: There's an existing `sbm/utils/tracker.py` with:
   - Local JSON tracking at `~/.sbm_migrations.json`
   - Global stats directory at `repo/stats/`
   - Git-based sync using `sync_global_stats()`
   - This is the system Firebase will eventually replace (Story 2.2+)

2. **User Identification**: `_get_user_id()` function already exists in tracker.py:
   - Tries GitHub username via `gh api user`
   - Falls back to git email
   - Final fallback to hostname + username
   - Firebase should reuse this same logic for consistent user IDs

3. **Background Task Support**: Existing `sbm/utils/processes.py` has `run_background_task()` for async operations - Firebase sync will use this

4. **Logger**: Use existing `sbm/utils/logger.py` - already configured with Rich formatting

### Architecture Compliance

**From `_bmad-output/architecture.md`:**

- **Tech Stack**: Python 3.9+, must maintain compatibility
- **CLI Framework**: Click (already configured)
- **UI**: Rich (for beautiful terminal output)
- **Error Handling**: Must not crash CLI, fail gracefully
- **State Management**: Tool maintains state across long-running processes

**Firebase-Specific Requirements**:
- Firebase Admin SDK will be imported but not initialize until credentials are configured
- Initialization MUST be lazy (only when needed) to avoid blocking startup
- All Firebase operations must have timeout handlers
- Connection errors should log but not crash the application

### Project Structure Notes

**Files to Create:**
- `sbm/utils/firebase_sync.py` - New module for Firebase initialization

**Files to Modify:**
- `pyproject.toml` - Add `firebase-admin` dependency
- `.env.example` - Add Firebase environment variables
- `sbm/config.py` - Add `FirebaseSettings` class
- `tests/test_config.py` - Add Firebase configuration tests (if exists)
- `.gitignore` - Ensure `*-firebase-*.json` and service account files are ignored

**Naming Convention**:
- Classes: PascalCase (e.g., `FirebaseSettings`)
- Functions: snake_case (e.g., `initialize_firebase`)
- Module names: snake_case (e.g., `firebase_sync.py`)

### Testing Requirements

**Unit Tests** (required):
- Test `FirebaseSettings` with valid/invalid paths
- Test `FirebaseSettings` with valid/invalid database URLs
- Mock Firebase initialization to test error handling
- Verify configuration loads correctly from environment

**Integration Tests** (optional, if Firebase test account available):
- Test actual connection to Firebase Realtime Database
- Verify authentication with service account
- Test read/write operations (Story 2.2 will expand this)

**Test Coverage**: Aim for 80%+ on new code per existing standards

### Security Considerations

⚠️ **CRITICAL**: Service account JSON files contain sensitive credentials:
- MUST be in `.gitignore`
- MUST NOT be committed to repository
- MUST validate file permissions (readable only by user)
- `.env` file already in `.gitignore` per existing setup

**Environment Variable Best Practices**:
- Use absolute paths for `FIREBASE_CREDENTIALS_PATH`
- Validate URL format for `FIREBASE_DB_URL`
- Default to None, making Firebase optional (offline-first design)

### References

- Firebase Admin SDK Python Docs: https://firebase.google.com/docs/admin/setup#python
- Firebase Realtime Database Docs: https://firebase.google.com/docs/database/admin/start
- Pydantic v2 Settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- [Source: sbm/config.py] - Existing Pydantic configuration pattern
- [Source: _bmad-output/architecture.md#Tech Stack] - Python version requirements
- [Source: sbm/utils/tracker.py#_get_user_id] - Existing user identification logic
- [Source: pyproject.toml] - Existing dependency management pattern

### Recent Work Context

Latest commits show:
- `5d3da70` - stats tracking refactor (code review feedback addressed)
- `129c19b` - Fixed lines_migrated tracking bug
- Recent focus on stats/tracking improvements sets the stage for Firebase migration

### Known Gotchas

1. **Pydantic v2 Migration**: Project already uses Pydantic v2 - use `Field()` not `Field(...)` for defaults with factory
2. **Optional Firebase**: System MUST work without Firebase configured (local-first design, Epic 2 NFR1)
3. **Type Hints**: Project uses Python 3.9+ union syntax (`str | None` not `Optional[str]`)
4. **Validation**: Use `@field_validator` decorator, not the old `@validator`

## Dev Agent Record

### Agent Model Used

PLACEHOLDER_M8

### Debug Log References

- Mocking `sys.modules` for proper `ImportError` simulation in `test_firebase_sync.py`.
- Ensuring `FirebaseInitializationError` is re-raised and not swallowed by broad exception handler.

### Completion Notes List

- Implemented `FirebaseSettings` in `sbm/config.py` following Pydantic v2 patterns.
- Created `sbm/utils/firebase_sync.py` for safe, lazy Firebase initialization.
- Added `firebase-admin>=6.5.0` to `pyproject.toml`.
- Updated `.env.example` and `.gitignore`.
- Added comprehensive unit tests in `tests/test_config.py` and `tests/test_firebase_sync.py`.
- Added integration tests in `tests/test_firebase_integration.py` (skipped if credentials missing).
- Verified implementation with passing tests.

### File List

- sbm/config.py
- sbm/utils/firebase_sync.py
- pyproject.toml
- .env.example
- .gitignore
- tests/test_config.py
- tests/test_firebase_sync.py
- tests/test_firebase_integration.py
