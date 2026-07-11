# Zabbix Template Tool

`ztt` is a command-line toolkit for inspecting and refactoring Zabbix YAML templates.

The project is designed around layered templates:

```text
BASE (collection) -> SYSTEM (system LLD and triggers) -> BUSINESS (business services and triggers)
```

## Current capabilities

- Load and validate a Zabbix YAML export.
- Display template metadata and object counts.
- List and analyze LLD rules.
- Automatically create linked BASE and SYSTEM templates from an existing export.
- Move selected LLD rules between existing templates.
- Preserve complete LLD blocks, including preprocessing, filters, prototypes and overrides.
- Preserve YAML ordering and quotes through `ruamel.yaml`.

## Requirements

- Python 3.11 or newer.
- Git when installing from the repository.
- A Zabbix template exported in YAML format.

## Installation

### Linux

```bash
git clone https://github.com/oxame/zabbix-template-tool.git
cd zabbix-template-tool
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install .
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

```bash
ztt --version
ztt --help
```

For development:

```bash
pip install -e ".[dev]"
```

## Create BASE and SYSTEM automatically

Starting from an existing Zabbix YAML export:

```bash
ztt create-layers template-existing.yaml
```

The source file is not modified. By default, ZTT creates the two generated templates in the same directory as the source file.

Example:

```text
/templates/
├── template-existing.yaml
├── TEMPLATE_NAME_BASE.yaml
└── TEMPLATE_NAME_SYSTEM.yaml
```

The generated BASE template keeps the collection items, macros and shared objects. Its LLD rules are removed.

The generated SYSTEM template receives the complete LLD blocks and is automatically linked to the BASE template.

Choose another output directory with `--output-dir` or `-o`:

```bash
ztt create-layers template-existing.yaml --output-dir generated
```

The output path can be relative or absolute:

```bash
ztt create-layers /data/templates/template-existing.yaml \
  --output-dir /data/templates/generated
```

Choose the technical-name prefix:

```bash
ztt create-layers template-existing.yaml \
  --output-dir generated \
  --prefix TEMPLATE_LINUX
```

This produces:

```text
generated/TEMPLATE_LINUX_BASE.yaml
generated/TEMPLATE_LINUX_SYSTEM.yaml
```

ZTT refuses to overwrite existing files by default. To replace previously generated files:

```bash
ztt create-layers template-existing.yaml \
  --output-dir generated \
  --prefix TEMPLATE_LINUX \
  --overwrite
```

Before importing, inspect the generated templates:

```bash
ztt info TEMPLATE_NAME_BASE.yaml
ztt info TEMPLATE_NAME_SYSTEM.yaml
ztt analyze TEMPLATE_NAME_SYSTEM.yaml
```

Import BASE first, then SYSTEM. SYSTEM already contains the link to BASE.

## Other commands

Inspect a template:

```bash
ztt info template.yaml
```

List LLD rules:

```bash
ztt list-lld template.yaml
```

Analyze macros, value maps and master-item references used by LLD rules:

```bash
ztt analyze template.yaml
```

Simulate moving a selected LLD between two existing templates:

```bash
ztt move-lld BASE.yaml SYSTEM.yaml --select vfs.fs.discovery
```

Apply the move:

```bash
ztt move-lld BASE.yaml SYSTEM.yaml \
  --select vfs.fs.discovery \
  --apply
```

Move all LLD rules:

```bash
ztt move-lld BASE.yaml SYSTEM.yaml --all --apply
```

By default, `move-lld` creates `.bak` copies before modifying files.

## Recommended workflow

Generate files beside the source template:

```bash
ztt info template-existing.yaml
ztt list-lld template-existing.yaml
ztt analyze template-existing.yaml
ztt create-layers template-existing.yaml --prefix TEMPLATE_LINUX
ztt info TEMPLATE_LINUX_BASE.yaml
ztt info TEMPLATE_LINUX_SYSTEM.yaml
ztt analyze TEMPLATE_LINUX_SYSTEM.yaml
```

Or generate them in a dedicated directory:

```bash
ztt create-layers template-existing.yaml \
  --output-dir generated \
  --prefix TEMPLATE_LINUX
```

Keep the original export in Git and test the generated files in a qualification environment before importing them into production.

## Current limitations

The first `create-layers` implementation creates BASE and SYSTEM only. The BUSINESS layer will be added later.

External dependencies used by LLD rules are detected by `ztt analyze`, but automatic dependency transfer is still under development. Verify macros, value maps and master items before importing the generated templates.

## Tests

```bash
pytest
ruff check .
```

## Roadmap

- `v0.1`: inspection, structural validation and atomic LLD moves.
- `v0.2`: dependency analysis and automatic BASE/SYSTEM creation.
- `v0.3`: automatic dependency transfer and standalone object moves.
- `v0.4`: complete BASE/SYSTEM/BUSINESS split and merge.
- `v1.0`: graphical interface.

## License

MIT
