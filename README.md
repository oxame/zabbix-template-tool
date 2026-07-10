# Zabbix Template Tool

`ztt` is a command-line toolkit for inspecting and refactoring Zabbix YAML templates.

The project is designed around layered templates:

```text
BASE (collection) -> SYSTEM (system LLD and triggers) -> BUSINESS (business services and triggers)
```

## Current capabilities

- Load a Zabbix YAML export.
- Validate its basic structure.
- Display template metadata and object counts.
- List LLD rules with nested item, trigger and graph prototype counts.
- Move selected LLD rules between templates.
- Preserve the complete LLD block, including preprocessing, filters, prototypes and overrides.
- Simulate changes before writing.
- Create `.bak` backups before modifying source files.
- Preserve YAML ordering and quotes through `ruamel.yaml`.

## Installation for development

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Usage

### Inspect a template

```bash
ztt info path/to/template.yaml
```

### List its LLD rules

```bash
ztt list-lld BASE.yaml
```

The table displays each rule name and key together with the number of embedded item prototypes, trigger prototypes, graph prototypes and overrides.

### Simulate an LLD move

A selector can be the exact LLD name, key or UUID:

```bash
ztt move-lld BASE.yaml SYSTEM.yaml --select "Filesystem discovery"
ztt move-lld BASE.yaml SYSTEM.yaml --select vfs.fs.discovery
```

Several selectors can be supplied:

```bash
ztt move-lld BASE.yaml SYSTEM.yaml \
  --select vfs.fs.discovery \
  --select net.if.discovery
```

Move every discovery rule:

```bash
ztt move-lld BASE.yaml SYSTEM.yaml --all
```

These commands only simulate the operation. Add `--apply` to write both files:

```bash
ztt move-lld BASE.yaml SYSTEM.yaml --select vfs.fs.discovery --apply
```

By default, `BASE.yaml.bak` and `SYSTEM.yaml.bak` are created before writing. Use `--no-backup` only when backups are managed elsewhere:

```bash
ztt move-lld BASE.yaml SYSTEM.yaml --all --apply --no-backup
```

The destination is rejected if it already contains a rule with the same UUID or key.

## Tests and linting

```bash
pytest
ruff check .
```

## Roadmap

- `v0.1`: inspection, structural validation and atomic LLD moves.
- `v0.2`: dependency analysis for external macros, value maps and master items.
- `v0.3`: move standalone items, triggers, graphs and macros.
- `v0.4`: split and merge layered templates.
- `v1.0`: graphical interface.

## License

MIT
