"""Transparent Product Passport recurrence summaries from retained records."""
import json
import re

from .outcomes import history as outcome_history, serialise as serialise_outcome
from .snapshots import original


def normalise(value):
    return re.sub(r"\s+", " ", (value or "").strip().casefold())


def analyse(db, jobs):
    groups = {}
    snapshot_count = 0
    latest_outcome_count = 0
    omitted_without_diagnosis = 0
    for job in jobs:
        snapshot = original(db, job.id)
        if snapshot:
            snapshot_count += 1
            captured = json.loads(snapshot.payload_json)
            diagnosis = captured.get("diagnosis", "")
            basis = "Immutable original diagnosis"
        else:
            diagnosis = job.diagnosis
            basis = "Current legacy diagnosis; no original snapshot"
        key = normalise(diagnosis)
        if not key:
            omitted_without_diagnosis += 1
            continue
        outcomes = outcome_history(db, job)
        latest = serialise_outcome(outcomes[-1]) if outcomes else None
        if latest:
            latest_outcome_count += 1
        group = groups.setdefault(
            key,
            {
                "diagnosis": diagnosis,
                "cases": 0,
                "resolved": 0,
                "not_resolved": 0,
                "outcome_not_recorded": 0,
                "repeat_visit_required": 0,
                "original_snapshot_cases": 0,
                "occurrences": [],
            },
        )
        group["cases"] += 1
        group["original_snapshot_cases"] += int(snapshot is not None)
        if latest:
            payload = latest["payload"]
            group["resolved"] += int(bool(payload.get("resolved")))
            group["not_resolved"] += int(not bool(payload.get("resolved")))
            group["repeat_visit_required"] += int(bool(payload.get("repeat_visit_required")))
        else:
            group["outcome_not_recorded"] += 1
        group["occurrences"].append(
            {
                "job_id": job.id,
                "reference": job.reference,
                "created_at": job.created_at,
                "diagnosis_basis": basis,
                "latest_outcome_version": latest["version"] if latest else None,
            }
        )
    patterns = []
    for group in groups.values():
        group["signal"] = "Repeated diagnosis" if group["cases"] >= 2 else "Single observation"
        group["requires_review"] = group["cases"] >= 2 and (
            group["not_resolved"] > 0 or group["repeat_visit_required"] > 0
        )
        patterns.append(group)
    patterns.sort(key=lambda item: (-item["cases"], normalise(item["diagnosis"])))
    return {
        "visible_linked_inspections": len(jobs),
        "original_snapshot_cases": snapshot_count,
        "latest_outcomes": latest_outcome_count,
        "omitted_without_diagnosis": omitted_without_diagnosis,
        "patterns": patterns,
        "method": "Groups visible linked inspections by normalised original diagnosis. Counts are descriptive signals for engineer review, not causal findings or automatic rule updates.",
    }
