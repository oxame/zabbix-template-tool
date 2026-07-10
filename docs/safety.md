# Write safety model

Refactoring commands are simulations by default. Files are modified only when `--apply` is present.
Before writing, the current implementation checks that source and destination are different files,
that at least one selector matches and that the destination has no LLD with the same UUID or key.

When backups are enabled, each original file is copied to `<filename>.bak` before serialization.
