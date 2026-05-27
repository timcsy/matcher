"""名單資料模型：Participant / Target / Roster。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from matcher.errors import DuplicateIdentity, EmptyRoster


@dataclass(frozen=True)
class Participant:
    id: str
    attributes: dict
    preferences: tuple = ()


@dataclass(frozen=True)
class Target:
    id: str
    capacity: int
    attributes: dict


@dataclass(frozen=True)
class Roster:
    participants: tuple
    targets: tuple


def parse_roster(data: dict) -> Roster:
    raw_participants = data.get("participants") or []
    raw_targets = data.get("targets") or []

    if not raw_participants:
        raise EmptyRoster("名單為空：無待媒合參與者")
    if not raw_targets:
        raise EmptyRoster("名單為空：無待分配對象")

    # 重複身分檢查
    participant_ids: list[str] = []
    for r in raw_participants:
        rid = r["id"]
        if rid in participant_ids:
            raise DuplicateIdentity(f"名單有重複身分：參與者 id `{rid}` 出現多次")
        participant_ids.append(rid)

    target_ids: list[str] = []
    for t in raw_targets:
        tid = t["id"]
        if tid in target_ids:
            raise DuplicateIdentity(f"名單有重複身分：對象 id `{tid}` 出現多次")
        target_ids.append(tid)

    participants_list = []
    for r in raw_participants:
        prefs = r.get("preferences", [])
        if not isinstance(prefs, list):
            raise ValueError(f"參與者 `{r['id']}` 的 preferences 必須為 list[str]，得到 {type(prefs).__name__}")
        participants_list.append(Participant(
            id=r["id"],
            attributes=dict(r.get("attributes", {})),
            preferences=tuple(str(p) for p in prefs),
        ))
    participants = tuple(participants_list)

    targets = []
    for t in raw_targets:
        cap = int(t.get("capacity", 1))
        if cap < 1:
            raise ValueError(f"對象 `{t['id']}` 的容量 {cap} 無效；容量必須 ≥ 1")
        targets.append(Target(id=t["id"], capacity=cap, attributes=dict(t.get("attributes", {}))))

    return Roster(participants=participants, targets=tuple(targets))
