"""Versioned, declarative repair verification definitions."""
import hashlib
import json


DEFINITION = {
    "id": "feniq-core-repair-verification",
    "revision": 1,
    "title": "Core repair verification",
    "source_status": "FenIQ field workflow; not a manufacturer specification",
    "checks": [
        {
            "key": "repair_matches_record",
            "label": "Completed work matches the recorded repair",
            "required_for_resolved": True,
        },
        {
            "key": "full_operation_cycle",
            "label": "Product completed its full intended operation cycle",
            "required_for_resolved": True,
        },
        {
            "key": "original_fault_rechecked",
            "label": "Original reported fault was specifically rechecked",
            "required_for_resolved": True,
        },
        {
            "key": "safety_security_rechecked",
            "label": "Relevant safety and security functions were rechecked",
            "required_for_resolved": True,
        },
    ],
}


def current():
    definition = json.loads(json.dumps(DEFINITION))
    encoded = json.dumps(definition, sort_keys=True, separators=(",", ":"))
    definition["sha256"] = hashlib.sha256(encoded.encode()).hexdigest()
    return definition


def validate_submission(definition_id, definition_sha256, answers, resolved):
    definition = current()
    if definition_id != definition["id"] or definition_sha256 != definition["sha256"]:
        raise ValueError("Verification definition changed. Reopen the outcome form.")
    expected = {check["key"] for check in definition["checks"]}
    if set(answers) != expected:
        raise ValueError("Complete every structured verification check.")
    if resolved:
        failed = [
            check["label"]
            for check in definition["checks"]
            if check["required_for_resolved"] and answers[check["key"]] != "Pass"
        ]
        if failed:
            raise ValueError("Every required verification check must pass before marking resolved.")
    return definition
