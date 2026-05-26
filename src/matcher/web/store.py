"""媒合紀錄儲存：純檔案系統 JSON。"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from matcher.web.errors import MatchRecordNotFound

SCHEMA_VERSION = "match-record/1.0"


@dataclass
class MatchRecord:
    schema_version: str
    id: str
    created_at: str
    template_id: str
    seed: int
    input_file: Optional[str]
    mechanism: str
    status: str  # "success" | "failed"
    audit: Optional[dict]
    error: Optional[dict]
    owner: Optional[str] = None  # Feature 014：建立者 email；舊資料 / 未登入為 None

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "created_at": self.created_at,
            "template_id": self.template_id,
            "seed": self.seed,
            "input_file": self.input_file,
            "mechanism": self.mechanism,
            "status": self.status,
            "audit": self.audit,
            "error": self.error,
            "owner": self.owner,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MatchRecord":
        return cls(
            schema_version=d["schema_version"],
            id=d["id"],
            created_at=d["created_at"],
            template_id=d["template_id"],
            seed=d["seed"],
            input_file=d.get("input_file"),
            mechanism=d["mechanism"],
            status=d["status"],
            audit=d.get("audit"),
            error=d.get("error"),
            owner=d.get("owner"),
        )

    @classmethod
    def new_id(cls) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
        return f"{ts}-{uuid.uuid4().hex[:8]}"


class MatchStore:
    def __init__(self, base_dir: str | Path = "data/matches") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, record_id: str) -> Path:
        return self.base_dir / f"{record_id}.json"

    def save(self, record: MatchRecord) -> str:
        p = self._path(record.id)
        tmp = p.with_suffix(".json.tmp")
        s = json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True, indent=2)
        tmp.write_text(s + "\n", encoding="utf-8")
        os.replace(tmp, p)
        return record.id

    def list(self, limit: int = 50, owner: Optional[str] = None) -> list[MatchRecord]:
        if not self.base_dir.exists():
            return []
        files = sorted(self.base_dir.glob("*.json"), reverse=True)
        records = [self.get(f.stem) for f in files]
        if owner is not None:
            records = [r for r in records if r.owner == owner]
        return records[:limit]

    def get(self, record_id: str) -> MatchRecord:
        p = self._path(record_id)
        if not p.exists():
            raise MatchRecordNotFound(f"找不到媒合紀錄：{record_id}")
        return MatchRecord.from_dict(json.loads(p.read_text(encoding="utf-8")))
