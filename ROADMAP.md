# Zabbix Template Tool Roadmap

This roadmap describes the planned evolution of Zabbix Template Tool (ZTT).

The project goal is to provide a complete development toolkit for creating, refactoring, validating, documenting and publishing Zabbix templates.

## Project vision

ZTT is designed around layered templates:

```text
BASE (collection) -> SYSTEM (system LLD and triggers) -> BUSINESS (business services and triggers)
```

The YAML export remains the interchange format, while ZTT provides the tooling required to manipulate templates safely and consistently.

## Phase 1 — Core template manipulation

Status: in progress

Completed:

- load and validate Zabbix YAML exports;
- display template metadata and object counts;
- list LLD rules;
- analyze LLD dependencies;
- move complete LLD blocks between templates;
- create linked BASE and SYSTEM templates;
- regenerate UUIDs for generated templates and nested objects;
- preserve YAML ordering and quoting.

Planned:

- strengthen structural validation;
- detect duplicate UUIDs and keys;
- verify broken references;
- validate linked templates;
- provide a complete `ztt validate` command.

## Phase 2 — Dependency engine and intelligent refactoring

Objective: understand the relationships between Zabbix objects before moving or splitting them.

Planned capabilities:

- dependency graph for items, discovery rules, prototypes, triggers and graphs;
- automatic copy or move of required macros;
- automatic copy or move of value maps;
- automatic copy or move of master items;
- dependency validation before import;
- detection of missing, unused and orphaned objects;
- standalone object moves for items, triggers, graphs and macros.

## Phase 3 — Complete layered template generation

Objective: generate a complete layered architecture automatically.

Planned commands and capabilities:

```bash
ztt split template.yaml
```

- generate BASE, SYSTEM and BUSINESS templates;
- assign objects to the correct layer;
- create template links automatically;
- preserve dependencies between layers;
- support configurable naming conventions;
- support split profiles and layer rules;
- merge layered templates when needed.

## Phase 4 — ZTT project mode

Objective: transform a folder of templates into a managed ZTT project.

Planned structure:

```text
project/
├── ztt.yml
├── templates/
│   ├── BASE.yaml
│   ├── SYSTEM.yaml
│   └── BUSINESS.yaml
├── docs/
├── tests/
└── .git/
```

Planned commands:

```bash
ztt project init
ztt project status
ztt project validate
ztt project release
```

The `ztt.yml` file will define project metadata, layer rules, validation settings, documentation options and Git behavior.

## Phase 5 — Git integration

Objective: make version control a first-class but optional feature.

Planned capabilities:

- initialize a Git repository from ZTT;
- detect repository status;
- create optional commits after refactoring operations;
- generate meaningful commit messages;
- compare template versions between commits;
- support local Git workflows without requiring Git for basic YAML operations;
- later support GitHub and GitLab integrations.

## Phase 6 — Zabbix API integration

Objective: create Zabbix YAML templates from data retrieved through the Zabbix API.

Tracked in [issue #6](https://github.com/oxame/zabbix-template-tool/issues/6).

Planned capabilities:

- connect to a Zabbix instance with an API token;
- select templates by name or template ID;
- retrieve items, discovery rules, prototypes, triggers, graphs, macros, value maps, tags and template links;
- convert Zabbix API responses into importable YAML exports;
- regenerate required UUIDs;
- create BASE and SYSTEM layers directly from API data;
- support version-specific API conversion rules;
- protect secrets through environment variables or local configuration excluded from Git.

Possible commands:

```bash
ztt api export-template \
  --url https://zabbix.example/api_jsonrpc.php \
  --template "Linux by Zabbix agent"
```

```bash
ztt api create-layers \
  --template-id 10001 \
  --output-dir ./templates
```

## Phase 7 — Intelligent template diff

Objective: compare Zabbix objects instead of raw YAML formatting.

Example output:

```text
+ Item CPU usage
+ Trigger memory pressure
~ Update interval: 1m -> 5m
- Graph legacy CPU
+ Filesystem discovery rule
```

The diff engine should ignore irrelevant UUID and formatting changes whenever possible.

## Phase 8 — Documentation generation

Objective: generate documentation directly from template definitions.

Planned formats:

- Markdown;
- HTML;
- PDF.

Planned content:

- template metadata;
- items and triggers;
- LLD rules and prototypes;
- macros and value maps;
- dependency reports;
- layer relationships;
- validation results.

## Phase 9 — CI/CD and releases

Objective: validate and publish templates through automated pipelines.

Planned capabilities:

- GitHub Actions and GitLab CI examples;
- automatic validation on each push;
- dependency analysis in CI;
- generated documentation artifacts;
- release packages containing BASE, SYSTEM and BUSINESS templates;
- optional semantic versioning and release notes.

## Phase 10 — Graphical interface

Objective: provide a graphical template designer.

Planned features:

- drag-and-drop movement between BASE, SYSTEM and BUSINESS;
- dependency graph visualization;
- template object browser;
- validation dashboard;
- intelligent diff viewer;
- graphical project management.

## Version targets

- `v0.1`: inspection, structural validation and atomic LLD moves;
- `v0.2`: dependency analysis and automatic BASE/SYSTEM creation;
- `v0.3`: automatic dependency transfer and standalone object moves;
- `v0.4`: complete BASE/SYSTEM/BUSINESS split and merge;
- `v0.5`: ZTT project mode;
- `v0.6`: local Git integration;
- `v0.7`: Zabbix API export and conversion;
- `v0.8`: intelligent diff and documentation generation;
- `v0.9`: CI/CD and release workflows;
- `v1.0`: stable CLI, complete validation and graphical interface foundation.

## Development principles

- one feature per pull request when practical;
- tests for each new behavior;
- keep `main` stable;
- preserve backward compatibility whenever possible;
- never expose credentials in command-line history or committed configuration;
- validate generated templates in a qualification environment before production import.
