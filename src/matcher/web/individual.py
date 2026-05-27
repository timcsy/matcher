"""個別查詢 audit 子集：純函式，從完整 audit 中萃取屬於某參與者的部分。"""

from __future__ import annotations

from typing import Optional

from matcher.web.errors import MatchRecordNotFound

INDIVIDUAL_AUDIT_SCHEMA_VERSION = "individual-audit/1.0"


def _find_participant(audit: dict, participant_id: str) -> Optional[dict]:
    for r in audit.get("roster_snapshot", {}).get("participants", []):
        if r["id"] == participant_id:
            return r
    return None


def _find_target(audit: dict, target_id: str) -> Optional[dict]:
    if target_id is None:
        return None
    for t in audit.get("roster_snapshot", {}).get("targets", []):
        if t["id"] == target_id:
            return t
    return None


def build_individual_audit_subset(audit: dict, participant_id: str) -> dict:
    """從完整 audit 中萃取屬於某 participant_id 的部分。

    participant_id 不存在 → 拋 MatchRecordNotFound。
    """
    participant = _find_participant(audit, participant_id)
    if participant is None:
        raise MatchRecordNotFound(f"參與者 `{participant_id}` 不在這次媒合的清單中")

    assigned_target_id = audit.get("assignment", {}).get(participant_id)
    assigned_target = _find_target(audit, assigned_target_id) if assigned_target_id else None

    filter_subset = [
        entry for entry in audit.get("filter_trace", [])
        if entry.get("participant_id") == participant_id
    ]

    allocation_step = next(
        (s for s in audit.get("allocation_trace", []) if s.get("participant_id") == participant_id),
        None,
    )

    return {
        "schema_version": INDIVIDUAL_AUDIT_SCHEMA_VERSION,
        "record_seed": audit.get("seed"),
        "participant_id": participant_id,
        "participant_attributes": dict(participant.get("attributes", {})),
        "participant_preferences": list(participant.get("preferences", [])),
        "assignment": {
            "target_id": assigned_target_id,
            "target_attributes": dict(assigned_target["attributes"]) if assigned_target else None,
        },
        "filter_trace_subset": filter_subset,
        "allocation_step": allocation_step,
    }
