# Changelog

## 0.7.0

### Added

- Automatic generation of linked BASE, SYSTEM and BUSINESS templates.
- Interactive BUSINESS naming, tags and filesystem/service filter macros.
- Creation of additional BUSINESS templates from an existing SYSTEM template.
- BUSINESS filesystem and Windows service LLD cloning.
- Automatic UUID regeneration and BUSINESS key namespacing.
- Automatic copy of required value maps.
- Validation of missing value maps, duplicate UUIDs and duplicate prototype keys.
- Rewriting of graph prototype and trigger references to the generated template.
- Phase 1 template merge command with dry-run support.
- Merge conflict modes: `error`, `keep-first` and `keep-last`.
- Merge support for items, LLD rules, triggers, graphs, macros, value maps, tags and linked templates.

### Fixed

- Duplicate UUID errors during layered template import.
- Dashboard references to unavailable object IDs.
- Missing value maps such as `Windows service state`.
- Inherited prototype key collisions and read-only `value_type` import errors.
- Graph prototype `host` references in additional BUSINESS templates.
- Graph prototype and trigger references in merged templates.

## Earlier development

- `ztt list-lld` to display low-level discovery rules and nested object counts.
- `ztt move-lld` with selectors by exact name, key or UUID.
- Dry-run mode enabled by default.
- Optional `.bak` backups before writing.
- Duplicate detection on destination UUIDs and keys.
- Round-trip YAML writer preserving ordering and quotes.
