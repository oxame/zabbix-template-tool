# Changelog

## Unreleased

### Added

- `ztt list-lld` to display low-level discovery rules and nested object counts.
- `ztt move-lld` with selectors by exact name, key or UUID.
- Dry-run mode enabled by default.
- Optional `.bak` backups before writing.
- Duplicate detection on destination UUIDs and keys.
- Round-trip YAML writer preserving ordering and quotes.
- Tests for listing, simulation, complete moves and duplicate rejection.
