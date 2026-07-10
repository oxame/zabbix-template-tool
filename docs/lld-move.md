# Moving LLD rules between template layers

`ztt move-lld` moves the complete YAML mapping of each selected low-level discovery rule.
This includes filters, preprocessing steps, item prototypes, trigger prototypes, graph prototypes,
LLD macro paths and overrides stored inside the rule.

## Safe workflow

1. List the rules in the BASE layer:

   ```bash
   ztt list-lld BASE.yaml
   ```

2. Simulate the move:

   ```bash
   ztt move-lld BASE.yaml SYSTEM.yaml --select vfs.fs.discovery
   ```

3. Review the selected rules and resulting counts.

4. Apply the move:

   ```bash
   ztt move-lld BASE.yaml SYSTEM.yaml --select vfs.fs.discovery --apply
   ```

Backups are enabled by default. The command refuses to overwrite a destination rule that has the
same UUID or key.

## Current boundary

The first implementation moves dependencies embedded inside the LLD block. External dependencies,
such as template-level value maps, macros or master items referenced by an item prototype, are not
yet copied automatically. Dependency analysis for those objects is planned for the next milestone.
