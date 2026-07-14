# Trigger placement in layered templates

During `ztt create-layers`, BASE keeps collection objects only. Triggers exported either at `zabbix_export.triggers` or inside `items[].triggers` are moved to SYSTEM. Expressions and trigger dependencies are rewritten to reference the SYSTEM template, which inherits the corresponding items from BASE.
