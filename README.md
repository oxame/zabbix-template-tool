# Zabbix Template Tool (ZTT)

> Export, analyze, compare and manage Zabbix templates with confidence.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Zabbix](https://img.shields.io/badge/Zabbix-7.x-red.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## Table of Contents

- [Overview](#overview)
- [Why ZTT?](#why-ztt)
- [Key Features](#key-features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Zabbix API](#zabbix-api)
- [YAML Engine](#yaml-engine)
- [Architecture](#architecture)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

# Overview

Zabbix Template Tool (**ZTT**) is an open-source command-line application that simplifies the management of Zabbix templates throughout their lifecycle.

It provides a complete toolkit to:

- Export templates directly from the Zabbix API
- Compare templates between environments
- Analyze configuration differences
- Generate layered YAML templates
- Refactor existing templates
- Prepare controlled promotion workflows between environments

ZTT is designed for administrators, consultants and DevOps engineers who maintain medium to large Zabbix infrastructures.

Unlike traditional manual exports, ZTT focuses on automation, reproducibility and version control.

---

# Why ZTT?

Managing Zabbix templates manually quickly becomes difficult.

A typical deployment workflow looks like this:

```text
Development
      │
      ▼
Qualification
      │
      ▼
Production
```

After several weeks of modifications it becomes difficult to answer simple questions:

- Which template is the most recent?
- What changed?
- Which macros were modified?
- Which discovery rules differ?
- Is Production identical to Qualification?
- Can this deployment be reproduced later?

ZTT answers these questions by introducing engineering practices inspired by Infrastructure as Code.

The project aims to make Zabbix template management predictable, repeatable and auditable.

---

# Key Features

## Zabbix API

Current capabilities:

| Feature | Status |
|----------|:------:|
| Profile management | ✅ |
| Connection testing | ✅ |
| Template export | ✅ |
| Host export | ✅ |
| Host Group export | ✅ |
| Template Group export | ✅ |
| Template comparison | ✅ |
| Rich console output | ✅ |
| JSON output | ✅ |
| Dry-run synchronization | 🚧 |
| Template promotion | 🚧 |

---

## YAML Engine

The YAML engine provides advanced manipulation of exported Zabbix templates.

Current capabilities:

| Feature | Status |
|----------|:------:|
| Template inspection | ✅ |
| Dependency analysis | ✅ |
| Layer generation | ✅ |
| BUSINESS template generation | ✅ |
| LLD migration | ✅ |
| Metadata inspection | ✅ |

---

# Design Principles

ZTT is built around five core principles.

## Safety

Potentially destructive operations should always be predictable.

Whenever possible, ZTT provides:

- previews
- dry-run execution
- explicit confirmation
- backup generation

---

## Repeatability

Running the same command twice against the same input should always produce the same output.

This guarantees deterministic deployments.

---

## Traceability

Generated templates are intended to be version-controlled using Git.

Future synchronization features will also generate deployment reports and automatic backups.

---

## Automation

Every command has been designed to integrate easily into automation pipelines.

Typical integrations include:

- GitHub Actions
- GitLab CI
- Azure DevOps
- Jenkins
- Scheduled tasks

---

## Simplicity

Despite advanced functionality, ZTT remains a lightweight command-line application with very few external dependencies.

---

# Installation

## Requirements

- Python 3.11 or newer
- Zabbix 7.x
- Git

Clone the repository:

```bash
git clone https://github.com/oxame/zabbix-template-tool.git
cd zabbix-template-tool
```

Create a virtual environment.

Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the project:

```bash
pip install -e .
```

or

```bash
pip install .
```

Verify the installation:

```bash
ztt --version
```

```bash
ztt --help
```

---

# Configuration

ZTT supports multiple connection profiles.

Example:

```yaml
profiles:

  lab:
    url: https://lab.example.com
    token: ${LAB_TOKEN}

  qualification:
    url: https://qual.example.com
    token: ${QUAL_TOKEN}

  production:
    url: https://prod.example.com
    token: ${PROD_TOKEN}
```

Using environment variables for API tokens is strongly recommended.

---

# Quick Start

Display configured profiles:

```bash
ztt profiles
```

Validate a connection:

```bash
ztt test --profile qualification
```

Export a template:

```bash
ztt api export-template \
    --profile qualification \
    --template "Linux by Zabbix agent"
```

Compare Qualification and Production:

```bash
ztt api compare-template \
    --source qualification \
    --target production \
    --template "Linux by Zabbix agent"
```

---

# Zabbix API

The API engine allows direct interaction with one or more Zabbix servers without requiring manual exports.

Current commands:

|         Command       | Description              |
|-----------------------|--------------------------|
| profiles              | List configured profiles |
| test                  | Test API connectivity    |
| export-template       | Export templates         |
| export-host           | Export hosts             |
| export-host-group     | Export host groups       |
| export-template-group | Export template groups   |
| compare-template      | Compare templates        |


## Listing Profiles

Profiles define connections to one or more Zabbix environments.

A profile contains the information required to authenticate against the Zabbix API.

Typical environments include:

- Development
- Laboratory
- Qualification
- Production

Display the configured profiles:

```bash
ztt profiles
```

Example:

```text
Available profiles

✔ development
✔ qualification
✔ production
```

Profiles can then be referenced by every API command.

---

## Testing a Connection

Before performing exports or comparisons, it is recommended to validate the API connection.

```bash
ztt test --profile qualification
```

Successful example:

```text
Profile      : qualification
Server       : https://qual.example.com
API Version  : 7.4.9

✔ Authentication successful
✔ API reachable
✔ Profile validated
```

If the connection fails, ZTT reports the exact API error without modifying any remote object.

Examples:

```text
Authentication failed
```

```text
Unable to reach server
```

```text
Invalid API token
```

---

# Exporting Templates

Template export retrieves one or more templates directly from the Zabbix API and stores them as standard YAML files compatible with the official Zabbix import format.

Export a single template:

```bash
ztt api export-template \
    --profile qualification \
    --template "Linux by Zabbix agent"
```

Export multiple templates:

```bash
ztt api export-template \
    --profile qualification \
    --template "Linux by Zabbix agent" \
    --template "Apache HTTP Server" \
    --template "PostgreSQL by ODBC"
```

---

## Output Directory

By default, exported templates are written into the current directory.

Another destination may be specified.

```bash
ztt api export-template \
    --profile qualification \
    --template "Linux by Zabbix agent" \
    --output ./exports
```

Result:

```text
exports/

├── Linux by Zabbix agent.yaml
├── Apache HTTP Server.yaml
└── PostgreSQL by ODBC.yaml
```

---

## Overwrite Existing Files

To avoid accidental data loss, ZTT never overwrites an existing file unless explicitly requested.

```bash
ztt api export-template \
    --profile qualification \
    --template "Linux by Zabbix agent" \
    --overwrite
```

---

## JSON Output

Machine-readable output is available for automation.

```bash
ztt api export-template \
    --profile qualification \
    --template "Linux by Zabbix agent" \
    --json
```

Typical use cases:

- GitHub Actions
- GitLab CI
- Azure DevOps
- Jenkins
- Scheduled scripts

---

# Exporting Hosts

Export one or more hosts.

```bash
ztt api export-host \
    --profile qualification \
    --host WEB01
```

Export several hosts:

```bash
ztt api export-host \
    --profile qualification \
    --host WEB01 \
    --host WEB02 \
    --host DB01
```

The generated YAML files are directly compatible with Zabbix imports.

---

# Exporting Host Groups

Export one or more Host Groups.

```bash
ztt api export-host-group \
    --profile qualification \
    --group Linux
```

Several groups can be exported simultaneously.

```bash
ztt api export-host-group \
    --profile qualification \
    --group Linux \
    --group Databases \
    --group Network
```

---

# Exporting Template Groups

Export Template Groups.

```bash
ztt api export-template-group \
    --profile qualification \
    --group OperatingSystems
```

Example:

```bash
ztt api export-template-group \
    --profile qualification \
    --group Databases \
    --group Applications
```

---

# Compare Engine

The Compare Engine is one of the core components of ZTT.

It compares templates between two completely independent Zabbix environments.

Typical workflow:

```text
 Qualification
        │
        │
        ▼
  Compare Engine
        ▲
        │
        │
   Production
```

The comparison is performed object by object instead of relying on textual differences.

This approach provides much more accurate results than comparing exported YAML files.

Current comparison scope includes:

- Template properties
- Template groups
- Linked templates
- Macros
- Value Maps
- Items
- Discovery Rules
- Item Prototypes
- Trigger Prototypes
- Graph Prototypes
- Dashboards
- Tags
- Preprocessing
- HTTP Tests (future)
- Value Mapping references
- Template UUIDs

---

## Basic Comparison

```bash
ztt api compare-template \
    --source qualification \
    --target production \
    --template "Linux by Zabbix agent"
```

Typical output:

```text
Comparing template

Linux by Zabbix agent

Source : qualification
Target : production

Result

✔ Identical
```

or

```text
Differences detected

Items                3
Macros               1
Triggers             2
Discovery Rules      1
```

---

## Detailed Report

For a complete analysis:

```bash
ztt api compare-template \
    --source qualification \
    --target production \
    --template "Linux by Zabbix agent" \
    --details
```

The report identifies every modified object.

Typical output:

```text
Items

+ system.cpu.load
- vfs.fs.discovery
~ system.swap.size

Macros

{$CPU.MAX}

modified

Discovery Rules

Filesystem Discovery

prototype added

```

This level of detail makes configuration drift immediately visible.

---

## JSON Report

Automation-friendly output.

```bash
ztt api compare-template \
    --source qualification \
    --target production \
    --template "Linux by Zabbix agent" \
    --json
```

This output is intended for:

- CI/CD validation
- GitOps workflows
- Automated compliance checks
- Deployment pipelines

---

## Rich Console Output

By default, ZTT uses a rich terminal interface.

Differences are grouped by category and highlighted using colours.

This allows administrators to identify important changes in just a few seconds.

---

## Exit Codes

The Compare Engine returns meaningful exit codes suitable for automation.

| Exit Code | Meaning                   |
|-----------|---------------------------|
| 0         | Templates are identical   |
| 1         | Differences detected      |
| 2         | Invalid arguments         |
| 3         | Connection error          |
| 4         | API error                 |
| 5         | Unexpected internal error |

This behaviour allows the Compare Engine to integrate naturally with CI/CD platforms.



---

# YAML Engine

The YAML Engine provides advanced manipulation of Zabbix template exports.

Unlike the API commands, which interact directly with a Zabbix server, the YAML Engine operates entirely on local files.

This makes it possible to prepare, refactor and validate templates before importing them into another environment.

The engine has been designed around the official Zabbix YAML format and preserves compatibility with native imports.

---

## Features

Current capabilities include:

| Feature | Status |
|----------|:------:|
| Template inspection | ✅ |
| Dependency analysis | ✅ |
| Layer generation | ✅ |
| BUSINESS template generation | ✅ |
| Discovery migration | ✅ |
| Trigger migration | ✅ |
| Graph migration | ✅ |
| UUID preservation | ✅ |

---

# Layered Templates

Large templates often mix several responsibilities:

- Data collection
- Low-Level Discovery
- Trigger definitions
- Business monitoring
- Service-specific monitoring

Maintaining all these components inside a single template rapidly becomes difficult.

The Layer Generator separates these responsibilities into independent templates.

Typical architecture:

```text
                    BUSINESS
                 Oracle Database
                      │
                      │
               Linux Services
                      │
                      │
                  SYSTEM Layer
            Discovery / Triggers
                      │
                      │
                  BASE Layer
              Items / Collection
```

Each layer has a single responsibility.


## BASE Layer

The BASE layer contains only the objects required to collect data.

Typical objects include:

- Items
- HTTP Agent Items
- SNMP Items
- Calculated Items
- Dependent Items
- Master Items
- Value Maps
- Required Macros

No monitoring logic should exist in this layer.

Its purpose is only to expose raw metrics.

---

## SYSTEM Layer

The SYSTEM layer contains operating-system monitoring logic.

Typical objects include:

- Triggers
- Discovery Rules
- Item Prototypes
- Trigger Prototypes
- Graph Prototypes

This layer transforms collected metrics into infrastructure monitoring.

It remains generic and reusable.

Examples:

- Windows
- Linux
- VMware
- Network devices

---

## BUSINESS Layer

The BUSINESS layer contains application-specific monitoring.

Examples include:

- Oracle
- SQL Server
- PostgreSQL
- Apache
- NGINX
- Active Directory
- Exchange
- Custom applications

This layer should never duplicate infrastructure monitoring already provided by the SYSTEM layer.

Instead, it extends it with business-specific checks.

---

# Layer Generation

Generate BASE and SYSTEM layers from an existing template.

```bash
ztt yaml create-layers \
    --input Linux.yaml \
    --output ./layers
```

Generated structure:

```text
layers/

├── BASE/
│   └── Linux_BASE.yaml
│
└── SYSTEM/
    └── Linux_SYSTEM.yaml
```

The generated templates preserve UUIDs whenever possible in order to minimise differences during future imports.

---

# BUSINESS Generation

A BUSINESS template can be created independently from an existing SYSTEM layer.

Example:

```bash
ztt yaml create-business \
    --system Linux_SYSTEM.yaml \
    --name Oracle
```

Generated result:

```text
Oracle_BUSINESS.yaml
```

The BUSINESS template automatically links to the SYSTEM template instead of duplicating infrastructure objects.

This significantly reduces maintenance effort.

---

# Discovery Migration

The Layer Generator automatically relocates discovery-related objects into the appropriate layer.

Migrated objects include:

- Discovery Rules
- Item Prototypes
- Trigger Prototypes
- Graph Prototypes
- Discovery Overrides

Dependencies are preserved during migration.

---

# Dependency Analysis

Before generating layers, ZTT analyses object dependencies.

The analysis detects relationships between:

- Items
- Dependent Items
- Triggers
- Graphs
- Discovery Rules
- Macros
- Value Maps

This prevents broken references after layer generation.

---

# UUID Management

Whenever possible, existing UUIDs are preserved.

Maintaining UUID stability offers several advantages:

- Cleaner Git history
- Smaller YAML differences
- Safer upgrades
- Easier synchronization
- Better compatibility with future promotion workflows

---

# Validation

Every generated template is validated before being written.

Validation includes:

- Missing dependencies
- Invalid references
- Duplicate UUIDs
- Duplicate names
- Circular dependencies
- Invalid discovery references

Generation stops immediately if validation fails.

---

# Output Structure

A typical project generated by ZTT looks like this:

```text
project/

├── exports/
│
├── templates/
│   ├── BASE/
│   ├── SYSTEM/
│   └── BUSINESS/
│
├── compare/
│
├── reports/
│
└── backups/
```

This organization keeps exported data, generated templates and reports separated and easy to version using Git.

---

# Architecture

The project is divided into several independent engines.

```text
                 +----------------+
                 |  Zabbix API    |
                 +--------+-------+
                          |
                          |
          +---------------+---------------+
          |                               |
          ▼                               ▼
   Export Engine                 Compare Engine
          |                               |
          +---------------+---------------+
                          |
                          ▼
                    YAML Engine
                          |
                          ▼
                  Layer Generator
                          |
                          ▼
                  Generated Templates
```

Each engine has a single responsibility and can evolve independently.

This modular architecture simplifies testing, maintenance and future feature development.

---

# Roadmap

The project continues to evolve around the complete lifecycle of Zabbix templates.

## Completed

- API profile management
- Connection testing
- Template export
- Host export
- Host Group export
- Template Group export
- Compare Engine
- Rich console rendering
- JSON reporting
- Layer generation
- BUSINESS generation

## In Progress

- Synchronization Engine
- Dry-run mode
- Deployment reports

## Planned

- Template promotion
- Automatic backups
- Rollback support
- Git integration
- Change history
- Interactive diff viewer
- Configuration validation
- Bulk synchronization
- Pipeline integration
- Plugin architecture

---


# Best Practices

The following recommendations help maintain a clean, maintainable and reproducible Zabbix environment.

## Use Version Control

Every exported template should be committed to a Git repository.

Recommended workflow:

```text
Export
   │
   ▼
Commit
   │
   ▼
Review
   │
   ▼
Compare
   │
   ▼
Deploy
```

Keeping templates under version control provides:

- Complete change history
- Easy rollback
- Peer review
- Safer deployments
- Team collaboration

---

## Separate Infrastructure and Business Logic

Avoid placing every object inside a single template.

Instead, split responsibilities.

```text
Infrastructure

BASE
 └── Collection

SYSTEM
 └── Infrastructure monitoring

Business

BUSINESS
 └── Application monitoring
```

This organization dramatically reduces maintenance costs.

---

## Keep Templates Generic

Infrastructure templates should remain reusable.

Avoid embedding:

- Environment names
- IP addresses
- Hostnames
- Customer names
- Credentials

Prefer macros whenever possible.

Example:

```text
{$HTTP.PORT}
{$SERVICE.NAME}
{$DB.INSTANCE}
{$TIMEOUT}
```

---

## Validate Before Deployment

Always compare templates before importing them into another environment.

Recommended workflow:

```text
Export
    │
    ▼
Compare
    │
    ▼
Review
    │
    ▼
Deploy
```

Never deploy a template you have not reviewed.

---

# Typical Workflow

A complete template lifecycle usually follows these steps.

```text
                Development

                     │
                     ▼

              Export Template

                     │
                     ▼

             Commit into Git

                     │
                     ▼

             Compare Versions

                     │
                     ▼

              Technical Review

                     │
                     ▼

          Qualification Environment

                     │
                     ▼

             Compare Again

                     │
                     ▼

          Production Deployment
```

ZTT has been designed to support each stage of this workflow.

---

# Logging

Every command provides clear and explicit feedback.

Example:

```text
Loading profile...

Connecting...

Exporting template...

Writing YAML...

Done.
```

Verbose logging is also available.

```bash
ztt --verbose
```

Future versions will also support:

- Debug logs
- Execution reports
- HTML reports
- JSON reports
- Deployment history

---

# Error Handling

Whenever possible, ZTT reports actionable error messages.

Example:

```text
Template "Linux by Zabbix agent" not found.
```

Instead of

```text
HTTP Error 500
```

The objective is to simplify troubleshooting.

---

# Security

ZTT never stores credentials inside exported templates.

Recommendations:

- Use API Tokens
- Store secrets in environment variables
- Avoid committing configuration files containing credentials
- Restrict API permissions to the minimum required
- Rotate API tokens regularly

Example:

```bash
export ZTT_TOKEN=xxxxxxxxxxxxxxxx
```

Configuration:

```yaml
token: ${ZTT_TOKEN}
```

---

# Performance

The API engine minimizes the number of requests whenever possible.

Current optimizations include:

- Object caching
- Batched API requests
- Parallel analysis
- Lazy loading
- Incremental comparison

Future releases will further improve performance for very large environments.

---

# Contributing

Contributions are welcome.

You can help by:

- Reporting bugs
- Suggesting improvements
- Improving documentation
- Adding unit tests
- Creating new features
- Reviewing pull requests

Before submitting code:

- Format your code
- Run the test suite
- Update the documentation
- Keep commits focused

---

# Development

Clone the repository.

```bash
git clone https://github.com/oxame/zabbix-template-tool.git
```

Install dependencies.

```bash
pip install -e .
```

Run the test suite.

```bash
pytest
```

Check formatting.

```bash
ruff check
```

Format code.

```bash
ruff format
```

---

# License

This project is distributed under the MIT License.

See the LICENSE file for details.

---

# Acknowledgements

ZTT is built for the Zabbix community.

Special thanks to:

- Zabbix developers
- Contributors
- Users providing feedback
- Open-source maintainers

Their work and feedback continue to improve this project.

---

# Project Vision

ZTT is evolving beyond a simple export utility.

The long-term objective is to become a complete **Template Lifecycle Management (TLM)** platform for Zabbix.

```text
                Create

                   │
                   ▼

               Export

                   │
                   ▼

              Compare

                   │
                   ▼

               Review

                   │
                   ▼

              Approve

                   │
                   ▼

             Promote

                   │
                   ▼

            Synchronize

                   │
                   ▼

              Deploy

                   │
                   ▼

              Maintain

                   │
                   ▼

               Repeat
```

The objective is to provide administrators with a complete toolkit to manage Zabbix templates from creation to production deployment while ensuring consistency, traceability and reproducibility.

As the project evolves, additional capabilities such as synchronization, promotion workflows, deployment reports and Git integration will extend this lifecycle even further.

---

---

# Examples

This section presents common use cases for ZTT.

## Export a Template

```bash
ztt api export-template \
    --profile production \
    --template "Linux by Zabbix agent"
```

Result:

```text
✔ Connected to production
✔ Template found
✔ Export completed

Saved to:
exports/Linux by Zabbix agent.yaml
```

---

## Compare Two Environments

```bash
ztt api compare-template \
    --source qualification \
    --target production \
    --template "Linux by Zabbix agent"
```

Example output:

```text
Comparing template...

Source : qualification
Target : production

Differences

Items.....................2
Triggers..................1
Macros....................1

Status

DIFFERENCES FOUND
```

---

## Export Every Template Group

```bash
ztt api export-template-group \
    --profile production
```

Result:

```text
Operating Systems
Databases
Applications
Network
Storage
Cloud

6 template groups exported.
```

---

## Export a Complete Host

```bash
ztt api export-host \
    --profile qualification \
    --host WEB01
```

Result

```text
Host exported successfully

WEB01.yaml
```

---

## JSON Integration

Example for automation.

```bash
ztt api compare-template \
    --source qualification \
    --target production \
    --template "Linux by Zabbix agent" \
    --json > report.json
```

Example JSON

```json
{
  "identical": false,
  "differences": {
    "items": 3,
    "macros": 1,
    "triggers": 2
  }
}
```

---

# Screenshots

The following screenshots illustrate the different capabilities of ZTT.

## Compare Engine

> _Screenshot coming soon_

---

## Rich Console Rendering

> _Screenshot coming soon_

---

## Export Engine

> _Screenshot coming soon_

---

## YAML Layer Generator

> _Screenshot coming soon_

---

# FAQ

## Does ZTT modify my Zabbix server?

No.

Every export and comparison command is read-only.

Synchronization features will always support a dry-run mode before applying any modification.

---

## Is ZTT compatible with older Zabbix versions?

The project currently targets Zabbix 7.x.

Older versions may work but are not officially supported.

---

## Can I use ZTT inside a CI/CD pipeline?

Yes.

Every command returns meaningful exit codes and supports machine-readable JSON output.

Typical platforms include:

- GitHub Actions
- GitLab CI
- Jenkins
- Azure DevOps

---

## Does ZTT require a database connection?

No.

All API operations are performed through the official Zabbix API.

The YAML engine operates entirely on local files.

---

## Why use layered templates?

Separating collection, infrastructure monitoring and business monitoring makes templates:

- easier to maintain
- easier to reuse
- easier to compare
- easier to evolve

---

## Why compare through the API instead of comparing YAML files?

Two exported YAML files may differ because of formatting, ordering or generated metadata.

The Compare Engine analyses the logical structure of templates instead of their textual representation, producing far more accurate results.

---

# Support

If you encounter an issue:

1. Check the documentation.
2. Verify your configuration profile.
3. Validate your API token.
4. Enable verbose mode.
5. Open an issue on GitHub.

When reporting a bug, include:

- ZTT version
- Python version
- Operating system
- Zabbix version
- Command executed
- Error message

This information greatly simplifies troubleshooting.

---

# Changelog

The project follows semantic versioning.

Example:

| Version | Highlights |
|----------|------------|
| 0.7.x | Export Engine, Compare Engine |
| 0.8.x | Synchronization Engine |
| 0.9.x | Promotion Workflow |
| 1.0.0 | Stable release |

---

# Philosophy

ZTT follows a few simple principles.

## Predictability

Every operation should produce deterministic results.

---

## Transparency

Nothing should happen without being visible to the user.

---

## Safety

Destructive actions should always support previews or dry-run execution.

---

## Reproducibility

The same inputs should always produce the same outputs.

---

## Automation First

Every feature should be usable interactively or from automation pipelines.

---

## Community Driven

The project evolves based on real-world operational needs and feedback from Zabbix administrators.

---

# Final Words

Managing Zabbix templates manually becomes increasingly difficult as infrastructures grow.

ZTT was created to simplify this process by introducing modern engineering practices:

- Version control
- Automated comparison
- Layered templates
- Deployment workflows
- Configuration validation

Whether you manage ten templates or several hundred, ZTT aims to make your workflow simpler, safer and more predictable.

If you find the project useful, consider:

- ⭐ Starring the repository
- 🐞 Reporting bugs
- 💡 Suggesting new features
- 🤝 Contributing to the project

Together, we can build a comprehensive toolkit for managing the complete lifecycle of Zabbix templates.
