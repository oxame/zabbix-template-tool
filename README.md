# Zabbix Template Tool

`ztt` is a command-line toolkit for inspecting and refactoring Zabbix YAML templates.

The project is designed around layered templates:

```text
BASE (collection) -> SYSTEM (system LLD and triggers) -> BUSINESS (dashboards and business objects)
```

## Current capabilities

- Load and validate a Zabbix YAML export.
- Display template metadata and object counts.
- List and analyze LLD rules.
- Automatically create linked BASE, SYSTEM and BUSINESS templates.
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

## Create BASE, SYSTEM and BUSINESS automatically

Starting from an existing Zabbix YAML export:

```bash
ztt create-layers template-existing.yaml
```

The source file is not modified. By default, ZTT creates the three generated templates in the same directory as the source file.

```text
/templates/
├── template-existing.yaml
├── TEMPLATE_NAME_BASE.yaml
├── TEMPLATE_NAME_SYSTEM.yaml
└── TEMPLATE_NAME_BUSINESS.yaml
```

The generated layers contain:

```text
BASE
├── collection items
├── macros
├── value maps
├── standalone triggers
└── standalone graphs

SYSTEM -> BASE
├── LLD rules
├── item prototypes
├── trigger prototypes
├── graph prototypes
├── overrides
└── value maps required by prototypes

BUSINESS -> SYSTEM
└── dashboards
```

Dashboard widget references are rewritten to point to the layer that owns the referenced object:

- item and graph widgets point to BASE;
- graph prototype widgets point to SYSTEM.

Choose another output directory with `--output-dir` or `-o`:

```bash
ztt create-layers template-existing.yaml --output-dir generated
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
generated/TEMPLATE_LINUX_BUSINESS.yaml
```

ZTT refuses to overwrite existing files by default. To replace previously generated files:

```bash
ztt create-layers template-existing.yaml \
  --prefix TEMPLATE_LINUX \
  --overwrite
```

Before importing, inspect the generated templates:

```bash
ztt info TEMPLATE_LINUX_BASE.yaml
ztt info TEMPLATE_LINUX_SYSTEM.yaml
ztt analyze TEMPLATE_LINUX_SYSTEM.yaml
ztt info TEMPLATE_LINUX_BUSINESS.yaml
```

Import the templates in this order:

```text
1. BASE
2. SYSTEM
3. BUSINESS
```

SYSTEM already contains the link to BASE. BUSINESS already contains the link to SYSTEM.

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

```bash
ztt info template-existing.yaml
ztt list-lld template-existing.yaml
ztt analyze template-existing.yaml
ztt create-layers template-existing.yaml --prefix TEMPLATE_LINUX
ztt info TEMPLATE_LINUX_BASE.yaml
ztt analyze TEMPLATE_LINUX_SYSTEM.yaml
ztt info TEMPLATE_LINUX_BUSINESS.yaml
```

Keep the original export in Git and test the generated files in a qualification environment before importing them into production.

## Current limitations

External dependencies used by LLD rules are detected by `ztt analyze`. Value maps used by prototypes are copied automatically to SYSTEM, while broader automatic dependency transfer remains under development.

The BUSINESS layer currently contains exported template dashboards. Classification of business triggers, services and SLA objects will be added progressively.

## Tests

```bash
pytest
ruff check .
```

## Roadmap

The detailed project roadmap covers dependency management, full BASE/SYSTEM/BUSINESS generation, project mode, Git integration, Zabbix API exports, intelligent diff, documentation, CI/CD and the future graphical interface.

See [ROADMAP.md](ROADMAP.md).

The Zabbix API export feature is also tracked in [issue #6](https://github.com/oxame/zabbix-template-tool/issues/6).

## License

MIT
