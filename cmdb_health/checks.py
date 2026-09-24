"""Pure-Python CMDB health checks.

Every check takes plain dictionaries shaped like ServiceNow Table API records
(cmdb_ci and cmdb_rel_ci) and returns a list of findings, so the checks can run
against a live instance or against an exported JSON file.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

REQUIRED_FIELDS = ("owned_by", "support_group", "environment")
APPLICATION_SERVICE_CLASSES = {
    "cmdb_ci_service_auto",
    "cmdb_ci_service_discovered",
    "cmdb_ci_service_calculated",
}
BUSINESS_APP_CLASS = "cmdb_ci_business_app"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"  # ServiceNow display format for glide_date_time


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, DATE_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _finding(check: str, ci: dict, detail: str) -> dict:
    return {
        "check": check,
        "sys_id": ci.get("sys_id"),
        "name": ci.get("name"),
        "class": ci.get("sys_class_name"),
        "detail": detail,
    }


def find_duplicates(cis: list[dict]) -> list[dict]:
    """CIs sharing a serial number, or the same name within the same class."""
    findings = []
    by_serial = defaultdict(list)
    by_name = defaultdict(list)
    for ci in cis:
        serial = (ci.get("serial_number") or "").strip().upper()
        if serial:
            by_serial[serial].append(ci)
        name = (ci.get("name") or "").strip().lower()
        if name:
            by_name[(ci.get("sys_class_name"), name)].append(ci)
    seen = set()
    for key, group in list(by_serial.items()) + list(by_name.items()):
        if len(group) < 2:
            continue
        ids = tuple(sorted(c["sys_id"] for c in group))
        if ids in seen:
            continue
        seen.add(ids)
        label = f"serial {key}" if isinstance(key, str) else f"name '{key[1]}'"
        for ci in group:
            findings.append(_finding("duplicate", ci, f"{len(group)} CIs share {label}"))
    return findings


def find_orphans(cis: list[dict], relationships: list[dict]) -> list[dict]:
    """CIs with no parent or child relationship."""
    related = set()
    for rel in relationships:
        related.add(rel.get("parent"))
        related.add(rel.get("child"))
    return [_finding("orphan", ci, "No relationships in cmdb_rel_ci")
            for ci in cis if ci.get("sys_id") not in related]


def find_stale(cis: list[dict], now: datetime, max_age_days: int = 30) -> list[dict]:
    """Operational CIs whose last_discovered date is missing or older than max_age_days."""
    cutoff = now - timedelta(days=max_age_days)
    findings = []
    for ci in cis:
        if ci.get("sys_class_name") in APPLICATION_SERVICE_CLASSES | {BUSINESS_APP_CLASS}:
            continue  # logical CIs are not discovered
        if str(ci.get("operational_status", "1")) != "1":
            continue  # only operational CIs are expected to be current
        seen = _parse(ci.get("last_discovered"))
        if seen is None:
            findings.append(_finding("stale", ci, "Never discovered"))
        elif seen < cutoff:
            findings.append(_finding("stale", ci, f"Last discovered {(now - seen).days} days ago"))
    return findings


def find_incomplete(cis: list[dict], required: tuple[str, ...] = REQUIRED_FIELDS) -> list[dict]:
    """CIs missing any required attribute."""
    findings = []
    for ci in cis:
        missing = [f for f in required if not ci.get(f)]
        if missing:
            findings.append(_finding("incomplete", ci, "Missing " + ", ".join(missing)))
    return findings


def find_csdm_gaps(cis: list[dict], relationships: list[dict]) -> list[dict]:
    """Business applications not linked to any application service (CSDM 'Design' to 'Build/Manage')."""
    by_id = {ci["sys_id"]: ci for ci in cis}
    linked = set()
    for rel in relationships:
        parent, child = by_id.get(rel.get("parent")), by_id.get(rel.get("child"))
        if not parent or not child:
            continue
        classes = {parent.get("sys_class_name"), child.get("sys_class_name")}
        if BUSINESS_APP_CLASS in classes and classes & APPLICATION_SERVICE_CLASSES:
            linked.add(parent["sys_id"])
            linked.add(child["sys_id"])
    return [_finding("csdm", ci, "Business application has no application service")
            for ci in cis
            if ci.get("sys_class_name") == BUSINESS_APP_CLASS and ci["sys_id"] not in linked]


def run_all(cis: list[dict], relationships: list[dict], now: datetime | None = None,
            max_age_days: int = 30) -> dict:
    """Run every check and compute scores in the style of the CMDB Health dashboard."""
    now = now or datetime.now(timezone.utc)
    results = {
        "duplicate": find_duplicates(cis),
        "orphan": find_orphans(cis, relationships),
        "stale": find_stale(cis, now, max_age_days),
        "incomplete": find_incomplete(cis),
        "csdm": find_csdm_gaps(cis, relationships),
    }
    total = len(cis) or 1

    def pct_clean(*checks: str) -> float:
        flagged = {f["sys_id"] for c in checks for f in results[c]}
        return round(100 * (total - len(flagged)) / total, 1)

    scores = {
        "completeness": pct_clean("incomplete"),
        "correctness": pct_clean("duplicate", "orphan"),
        "compliance": pct_clean("stale", "csdm"),
    }
    scores["overall"] = round(sum(scores.values()) / 3, 1)
    return {"total_cis": len(cis), "scores": scores, "findings": results}
