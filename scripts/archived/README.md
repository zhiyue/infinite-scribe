# Archived Scripts

This directory contains scripts that are no longer actively used but are kept for historical reference or potential future use.

## Directory Structure

### `one-time-migrations/`
Scripts that were used for one-time data or configuration migrations during development:

- **`consolidate-env-files.sh`** - Consolidated multiple .env files into a cleaner structure
- **`migrate-env-structure.sh`** - Migrated from single .env to layered environment structure

### `testing-utilities/`
Development and testing utility scripts that were used for specific testing scenarios:

- **`test-matrix-generation.sh`** - Testing script for CI matrix generation logic
- **`test-openapi-examples.sh`** - Testing script for OpenAPI example generation

### `database-utilities/`
Database maintenance and validation scripts:

- **`convert_comments_to_column_param.py`** - Converted inline comments to SQLAlchemy Column comment parameters
- **`verify_genesis_schema.py`** - Validates the Genesis Studio database schema
- **`check_migration.py`** - Checks database migration status
- **`show_table_info.py`** - Database table inspection utility

## Usage Notes

- Scripts in this directory are **not actively maintained** and may not work with current project structure
- They are kept for reference in case similar operations are needed in the future
- Before using any archived script, review and update it for current project structure
- These scripts are excluded from the main project documentation and pnpm scripts

## When to Archive Scripts

Scripts should be archived when they:
1. Are one-time use scripts that have completed their purpose
2. Are testing utilities used only during specific development phases
3. Are superseded by better implementations
4. Are no longer compatible with current project structure

## Restoration

If an archived script is needed again:
1. Copy it back to the appropriate active directory
2. Update it for current project structure
3. Add it back to the main scripts README.md
4. Add pnpm scripts if needed