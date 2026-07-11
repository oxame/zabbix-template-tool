"""Validate Zabbix template dependencies before import."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ztt.template import ZabbixTemplate


@dataclass(slots=True, frozen=True)
class ValidationIssue:
    """One actionable validation problem."""

    code: str
    message: str
    location: str


@dataclass(slots=True, frozen=True)
class ValidationReport:
    """Validation result for one template."""

    issues: tuple[ValidationIssue, ...]

    @property
    def valid(self) -> bool:
        return not self.issues


def _walk(value: Any, location: str = "template"):
    yield value, location
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{location}[{index}]")


def validate_template(template: ZabbixTemplate) -> ValidationReport:
    """Validate UUIDs, prototype keys and referenced value maps."""

    issues: list[ValidationIssue] = []
    root = template.template

    # UUID uniqueness across the complete template export.
    seen_uuids: dict[str, str] = {}
    for value, location in _walk(template.document, "zabbix_export"):
        if not isinstance(value, dict):
            continue
        uuid = value.get("uuid")
        if not isinstance(uuid, str) or not uuid:
            continue
        if uuid in seen_uuids:
            issues.append(
                ValidationIssue(
                    "duplicate_uuid",
                    f"UUID {uuid} is already used at {seen_uuids[uuid]}.",
                    location,
                )
            )
        else:
            seen_uuids[uuid] = location

    valuemap_names = {
        entry.get("name")
        for entry in root.get("valuemaps", [])
        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
    }

    prototype_keys: dict[str, str] = {}
    rules = root.get("discovery_rules", [])
    if isinstance(rules, list):
        for rule_index, rule in enumerate(rules):
            if not isinstance(rule, dict):
                continue
            rule_name = str(rule.get("name", f"rule {rule_index}"))
            prototypes = rule.get("item_prototypes", [])
            if not isinstance(prototypes, list):
                continue
            for prototype_index, prototype in enumerate(prototypes):
                if not isinstance(prototype, dict):
                    continue
                location = f"discovery_rules[{rule_index}].item_prototypes[{prototype_index}]"
                key = prototype.get("key")
                if isinstance(key, str) and key:
                    if key in prototype_keys:
                        issues.append(
                            ValidationIssue(
                                "duplicate_prototype_key",
                                f"Item prototype key {key!r} is already used at {prototype_keys[key]}.",
                                location,
                            )
                        )
                    else:
                        prototype_keys[key] = location

                valuemap = prototype.get("valuemap")
                if isinstance(valuemap, dict):
                    name = valuemap.get("name")
                    if isinstance(name, str) and name and name not in valuemap_names:
                        issues.append(
                            ValidationIssue(
                                "missing_valuemap",
                                f"Prototype {prototype.get('name', key)!r} in {rule_name!r} references missing value map {name!r}.",
                                location,
                            )
                        )

    return ValidationReport(tuple(issues))


def ensure_valid_template(template: ZabbixTemplate) -> None:
    """Raise ValueError when a generated template is not self-consistent."""

    report = validate_template(template)
    if report.valid:
        return
    details = "; ".join(f"{issue.code}: {issue.message}" for issue in report.issues)
    raise ValueError(f"Template validation failed: {details}")
