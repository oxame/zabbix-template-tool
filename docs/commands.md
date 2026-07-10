# Command reference

## `ztt info`

Display template metadata and top-level object counts.

## `ztt list-lld`

List LLD rules and embedded object counts.

## `ztt move-lld`

Simulate or apply an atomic move of complete LLD blocks between two YAML exports.

Use `--select` repeatedly to select exact names, keys or UUIDs, or use `--all`. Add `--apply` to
write changes. Backups are enabled unless `--no-backup` is supplied.
