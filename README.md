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
- Preserve YAML ordering and formatting through `ruamel.yaml`.

The first refactoring feature planned is moving selected LLD rules from a BASE template to a SYSTEM template with their prototypes and dependencies.

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

```bash
ztt --version
ztt info path/to/template.yaml
```

Example output:

```text
File            template.yaml
Export version  7.4
Template        TEMPLATE_TEST_BASE
Visible name    Test Base

Objects
Items                   1
Discovery rules (LLD)   1
Triggers                0
Graphs                  0
Dashboards              0
Macros                   1
```

## Tests and linting

```bash
pytest
ruff check .
```

## Roadmap

- `v0.1`: inspection and structural validation.
- `v0.2`: move LLD rules and embedded prototypes between templates.
- `v0.3`: dependency analysis, macros and referenced objects.
- `v0.4`: split and merge layered templates.
- `v1.0`: graphical interface.

## License

MIT
