# Auto-SBM Project Cleanup Plan

## 1. Project Structure (as designed)

From documentation, the intended structure is:
```
sbm/
├── cli.py                  # Command-line interface
├── config.py               # Configuration management
├── core/
│   ├── full_workflow.py    # Complete migration orchestration
│   ├── git_operations.py   # Git workflow automation
│   ├── migration.py        # SCSS migration engine
│   ├── validation.py       # Validation framework
│   ├── diagnostics.py      # System diagnostics
│   └── workflow.py         # Individual workflow components
├── scss/
│   ├── processor.py        # Main SCSS processor
│   ├── mixin_parser.py     # Mixin conversion logic
│   ├── validation.py       # SCSS validation rules
│   ├── validator.py        # (May be duplicate of validation.py)
│   └── transformer.py      # SCSS to CSS transformation
├── oem/
│   └── ...                 # OEM-specific logic
└── utils/
    └── ...                 # Utility functions/logging
```

And you have:
- `/docs/`, `/ai-knowledgebase/` (documentation)
- Possibly `/tests/`, `/examples/`
- Old/deprecated files in `/docs/archive/old-docs-2025/`

---

## 2. Suspected Unnecessary or Out-of-Place Files

### A. Files Likely Unneeded or Redundant

- **sbm/scss/parser.py**  
  - Only contains stub/mock logic. If not used in actual processing, can be deleted.
- **sbm/scss/validator.py**  
  - If all logic is in `validation.py`, and this is a stub, it should be removed.
- **sbm/scss/transformer.py**  
  - If not called anywhere (processing/conversion is in `processor.py`), delete or merge relevant logic.
- **docs/archive/old-docs-2025/**  
  - All files here are legacy and should be moved to a proper `archive/` or deleted if not needed for compliance/history.
- **ai-knowledgebase/**  
  - If not referenced in code/tests, move to `docs/` or remove.
- **tests/old/** or similar  
  - Remove or archive old test scripts that do not cover the current codebase.

### B. Files Out of Place (Should Be Moved)

- **Any utility modules (e.g., logger.py) not in `/utils/`**
- **OEM handlers not in `/oem/`**
- **SCSS migration/validation logic not in `/scss/`**
- **Docs or AI knowledgebase files in the root**  
  - Move to `/docs/` or `/archive/` as appropriate.

### C. Files You Should Consolidate

- **Multiple validators:**  
  - Have a single source of truth for SCSS validation, in `sbm/scss/validation.py`.
- **Multiple processors/transformers:**  
  - Consolidate into `sbm/scss/processor.py` if possible.

---

## 3. Specific Cleanup Steps

### 3.1. Remove or Archive
- `sbm/scss/parser.py` (if mock only)
- `sbm/scss/validator.py` (if logic is duplicated in validation.py)
- `sbm/scss/transformer.py` (if never used)
- `docs/archive/old-docs-2025/` (move to `/archive/` or delete)
- `ai-knowledgebase/` (move to `/docs/` or remove)
- Old, unused test scripts

### 3.2. Move
- Utilities → `/utils/`
- OEM-specific code → `/oem/`
- Documentation/AI notes → `/docs/` or `/archive/`

### 3.3. Consolidate
- Validators and processing logic into single, clearly named files/modules

### 3.4. Document
- Update `README.md` and `docs/` to reflect new structure and clarify which files are authoritative.

---

## 4. Recommendations for Future Organization

- Enforce single-responsibility per file/module.
- Keep all legacy/obsolete files in a single `/archive/` or `/legacy/` directory.
- Use clear naming conventions so it is always obvious which file is canonical for a given responsibility.
- Maintain a clear separation between code, documentation, AI/knowledge base, and test data.

---

## 5. Next Steps

1. Review all files listed above and confirm which are truly unused (via search and import graph).
2. Move/archive/delete as indicated.
3. Refactor any code that references now-removed or moved files.
4. Update documentation to match the new structure.

---

**Note:** Due to API/search limits, this review is based on project documentation and typical best practices.  
For a 100% accurate sweep, manually review the project root, `/sbm/`, `/docs/`, and any top-level folders.

---