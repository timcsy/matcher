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


def safe_fs_id(raw: str) -> str:
    """檔名/路徑用 id 清洗：擋目錄遍歷（../、絕對路徑、夾帶分隔符）。

    任何含 '/'、'\\'、'..'、null、或空白的 id 一律拒絕——這些 id 會被直接接到
    檔案系統路徑，未清洗等於任意檔案讀寫漏洞。回傳原值（合法）或拋 ValueError。
    """
    if not raw or "/" in raw or "\\" in raw or ".." in raw or "\x00" in raw:
        raise ValueError(f"不合法的識別碼：{raw!r}")
    if raw in (".", "") or raw.strip() != raw:
        raise ValueError(f"不合法的識別碼：{raw!r}")
    return raw


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
    # Feature 021：失敗紀錄也存清單快照，讓「用這份清單再配對」可重用、不必重打
    roster_snapshot: Optional[dict] = None

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
            "roster_snapshot": self.roster_snapshot,
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
            roster_snapshot=d.get("roster_snapshot"),
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
        return self.base_dir / f"{safe_fs_id(record_id)}.json"

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
        try:
            p = self._path(record_id)
        except ValueError:
            raise MatchRecordNotFound(f"找不到媒合紀錄：{record_id}")
        if not p.exists():
            raise MatchRecordNotFound(f"找不到媒合紀錄：{record_id}")
        return MatchRecord.from_dict(json.loads(p.read_text(encoding="utf-8")))
