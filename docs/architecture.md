# Layered template architecture

Zabbix Template Tool is designed for repositories that separate monitoring responsibilities into layers.

```text
BASE -> SYSTEM -> BUSINESS
```

## BASE

The BASE layer contains collection primitives such as standalone items, raw metrics and shared macros.
It should avoid operational triggers when the same metrics are consumed by several higher layers.

## SYSTEM

The SYSTEM layer contains operating-system discovery rules, item prototypes, trigger prototypes,
graph prototypes and system-level triggers. It links to BASE when it needs metrics collected there.

## BUSINESS

The BUSINESS layer contains application and service-specific monitoring, including business file
systems, services, processes and triggers. It links to SYSTEM and BASE as required.

## Refactoring principle

A move operation must preserve one coherent Zabbix object and its embedded children. For LLD rules,
this means moving the full rule mapping rather than reconstructing selected subfields. External
references are analyzed separately because they can belong to another layer by design.
