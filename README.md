# Zabbix Template Tool

`ztt` is a command-line toolkit for inspecting and refactoring Zabbix YAML templates.

The project is designed around layered templates:

```text
BASE (collection) -> SYSTEM (system LLD and triggers) -> BUSINESS (business services and triggers)
```

## Current capabilities

- Load and validate a Zabbix YAML export.
- Display template metadata and object counts.
- List LLD rules with nested item, trigger and graph prototype counts.
- Analyze LLD dependencies on macros, value maps and master items.
- Move selected LLD rules between templates.
- Preserve the complete LLD block, including preprocessing, filters, prototypes and overrides.
- Simulate changes before writing.
- Create `.bak` backups before modifying source files.
- Preserve YAML ordering and quotes through `ruamel.yaml`.

## Requirements

- Python 3.11 or newer.
- Git, when installing directly from the repository.
- Zabbix templates exported in YAML format.

Check the installed Python version:

```bash
python --version
```

On some Linux systems, use `python3` instead of `python`.

## Installation

### Linux

Clone the repository and create an isolated Python environment:

```bash
git clone https://github.com/oxame/zabbix-template-tool.git
cd zabbix-template-tool
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install .
```

Verify the installation:

```bash
ztt --version
ztt --help
```

### Windows PowerShell

```powershell
git clone https://github.com/oxame/zabbix-template-tool.git
Set-Location zabbix-template-tool
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install .
```

Verify the installation:

```powershell
ztt --version
ztt --help
```

If PowerShell blocks activation of the virtual environment, allow locally created scripts for the current user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### Installation for development

Install the project in editable mode with the test and lint dependencies:

```bash
pip install -e ".[dev]"
```

After modifying the source code, the `ztt` command immediately uses the updated files.

### Updating an existing installation

```bash
cd zabbix-template-tool
git pull
source .venv/bin/activate
pip install --upgrade .
```

On Windows PowerShell:

```powershell
Set-Location zabbix-template-tool
git pull
.\.venv\Scripts\Activate.ps1
pip install --upgrade .
```

## Usage

Display the general help:

```bash
ztt --help
```

Display help for a command:

```bash
ztt move-lld --help
```

### Inspect a template

```bash
ztt info path/to/template.yaml
```

This command displays the Zabbix export version, the technical and visible template names, and the number of items, LLD rules, triggers, graphs, dashboards and macros.

### List the LLD rules

```bash
ztt list-lld BASE.yaml
```

The table displays each rule name and key together with the number of embedded item prototypes, trigger prototypes, graph prototypes and overrides.

### Analyze LLD dependencies

```bash
ztt analyze BASE.yaml
```

The analysis currently detects:

- user macros such as `{$FS.WARN}`;
- value maps used by item prototypes;
- master items referenced by dependent item prototypes.

Each dependency is reported as:

- `OK` when it exists in the template;
- `MISSING` when the referenced object cannot be found.

Run this command before moving LLD rules so that external dependencies can be identified.

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

Without `--apply`, `move-lld` only simulates the operation. No file is changed.

### Apply an LLD move

```bash
ztt move-lld BASE.yaml SYSTEM.yaml \
  --select vfs.fs.discovery \
  --apply
```

By default, the following backups are created before writing:

```text
BASE.yaml.bak
SYSTEM.yaml.bak
```

Disable backups only when another backup mechanism is already in place:

```bash
ztt move-lld BASE.yaml SYSTEM.yaml --all --apply --no-backup
```

The destination is rejected if it already contains an LLD rule with the same UUID or key.

## Recommended workflow

For the layered architecture, the recommended sequence is:

```bash
ztt info BASE.yaml
ztt list-lld BASE.yaml
ztt analyze BASE.yaml
ztt move-lld BASE.yaml SYSTEM.yaml --select vfs.fs.discovery
ztt move-lld BASE.yaml SYSTEM.yaml --select vfs.fs.discovery --apply
ztt info BASE.yaml
ztt info SYSTEM.yaml
```

Keep the original Zabbix exports in Git before applying changes. This makes it possible to review the YAML diff and revert a modification when necessary.

## Important limitations

The LLD block itself is moved completely, including nested prototypes and overrides. External dependencies are currently analyzed but are not yet copied automatically. In particular, verify macros, value maps and master items before importing the resulting templates into Zabbix.

Always test generated templates in a qualification environment before importing them into production.

## Tests and linting

Activate the development virtual environment, then run:

```bash
pytest
ruff check .
```

## Roadmap

- `v0.1`: inspection, structural validation and atomic LLD moves.
- `v0.2`: dependency analysis for external macros, value maps and master items.
- `v0.3`: automatic dependency transfer and standalone object moves.
- `v0.4`: split and merge layered templates.
- `v1.0`: graphical interface.

## License

MIT
