"""模板載入：parse_template、load_template_file、TemplateRegistry。"""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Optional

import yaml

from matcher.errors import (
    TemplateConflict,
    TemplateMissingField,
    TemplateNotFound,
    UnknownSchemaVersion,
)
from matcher.roster import Target
from matcher.rules import parse_ruleset
from matcher.template import (
    AttributeDecl,
    AttributeSchema,
    PreferencesSchema,
    ReportFieldDecl,
    Template,
    UIFieldDecl,
)

SUPPORTED_SCHEMA_VERSIONS = ("1.0",)
_ALLOWED_ATTR_TYPES = {"str", "int", "list_str"}
_ALLOWED_UI_TYPES = {"text", "number", "select", "multiselect", "textarea"}


def _require(data: dict, key: str, ctx: str) -> object:
    if key not in data:
        raise TemplateMissingField(f"{ctx} 缺必要欄位 `{key}`")
    return data[key]


def _parse_attribute_decl(d: dict, side: str) -> AttributeDecl:
    key = _require(d, "key", f"attributes.{side}[].")
    type_ = _require(d, "type", f"attributes.{side}[].{key}.")
    if type_ not in _ALLOWED_ATTR_TYPES:
        raise TemplateMissingField(
            f"attributes.{side}[].{key} 的 type `{type_}` 不支援；"
            f"支援：{sorted(_ALLOWED_ATTR_TYPES)}"
        )
    aliases_raw = d.get("aliases") or []
    if not isinstance(aliases_raw, list):
        raise TemplateMissingField(
            f"attributes.{side}[].{key} 的 aliases 必須為 list[str]"
        )
    return AttributeDecl(
        key=key,
        type=type_,
        required=bool(d.get("required", True)),
        description=str(d.get("description", "")),
        aliases=tuple(str(a) for a in aliases_raw),
    )


def _parse_attributes(data: dict) -> AttributeSchema:
    roles = tuple(_parse_attribute_decl(r, "roles") for r in data.get("roles", []))
    targets = tuple(_parse_attribute_decl(t, "targets") for t in data.get("targets", []))
    if not roles:
        raise TemplateMissingField("attributes.roles 不可為空")
    if not targets:
        raise TemplateMissingField("attributes.targets 不可為空")
    return AttributeSchema(roles=roles, targets=targets)


def _parse_ui_field(d: dict) -> UIFieldDecl:
    key = _require(d, "key", "ui_fields[].")
    label = _require(d, "label", f"ui_fields[].{key}.")
    type_ = _require(d, "type", f"ui_fields[].{key}.")
    if type_ not in _ALLOWED_UI_TYPES:
        raise TemplateMissingField(
            f"ui_fields[].{key} 的 type `{type_}` 不支援；支援：{sorted(_ALLOWED_UI_TYPES)}"
        )
    options = d.get("options")
    if type_ in {"select", "multiselect"} and not options:
        raise TemplateMissingField(f"ui_fields[].{key} 的 type=`{type_}` 必須提供 `options`")
    return UIFieldDecl(
        key=key,
        label=str(label),
        type=type_,
        required=bool(d.get("required", True)),
        options=tuple(options) if options is not None else None,
        placeholder=d.get("placeholder"),
        help=d.get("help"),
    )


def _parse_report_field(d: dict) -> ReportFieldDecl:
    return ReportFieldDecl(
        key=_require(d, "key", "report_fields[]."),
        label=str(_require(d, "label", "report_fields[].")),
        source=str(_require(d, "source", "report_fields[].")),
    )


def _parse_preferences_schema(d: Optional[dict]) -> Optional[PreferencesSchema]:
    if d is None:
        return None
    return PreferencesSchema(
        max_choices=int(_require(d, "max_choices", "preferences_schema.")),
        required=bool(_require(d, "required", "preferences_schema.")),
        description=str(_require(d, "description", "preferences_schema.")),
    )


def parse_template(data: dict) -> Template:
    """從 dict（YAML 載入後）解析為 Template。

    驗證：schema_version 支援、必填欄位、子結構正確。
    """
    if not isinstance(data, dict):
        raise TemplateMissingField("模板檔頂層必須為 mapping")

    schema_version = _require(data, "schema_version", "模板頂層")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise UnknownSchemaVersion(
            f"未支援的 schema_version `{schema_version}`。"
            f"目前支援：{list(SUPPORTED_SCHEMA_VERSIONS)}"
        )

    default_targets_raw = data.get("default_targets") or []
    if not isinstance(default_targets_raw, list):
        raise TemplateMissingField("default_targets 必須為 list")
    default_targets = []
    for t in default_targets_raw:
        if "id" not in t:
            raise TemplateMissingField("default_targets[] 缺欄位 `id`")
        cap = int(t.get("capacity", 1))
        if cap < 1:
            raise TemplateMissingField(f"default_targets[{t['id']}] 容量必須 ≥ 1")
        default_targets.append(Target(
            id=str(t["id"]),
            capacity=cap,
            attributes=dict(t.get("attributes", {})),
        ))

    return Template(
        schema_version=str(schema_version),
        id=str(_require(data, "id", "模板頂層")),
        name=str(_require(data, "name", "模板頂層")),
        description=str(_require(data, "description", "模板頂層")),
        attributes=_parse_attributes(_require(data, "attributes", "模板頂層")),
        ruleset=parse_ruleset({"rules": _require(data, "rules", "模板頂層"), "version": str(schema_version)}),
        ui_fields=tuple(_parse_ui_field(f) for f in data.get("ui_fields", [])),
        report_fields=tuple(_parse_report_field(f) for f in data.get("report_fields", [])),
        preferences_schema=_parse_preferences_schema(data.get("preferences_schema")),
        default_targets=tuple(default_targets),
    )


def load_template_file(path: str | Path) -> Template:
    with Path(path).open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return parse_template(data)


# ── 內建模板登錄 ─────────────────────────────────────────────────


_CUSTOM_VERSION_PATTERN = __import__("re").compile(r"^v(\d+)\.yaml$")


class TemplateRegistry:
    """掃描內建模板目錄並提供查詢介面。Feature 011 擴充：自訂模板（檔案系統）+ 版本歷史。"""

    def __init__(self, custom_dir: Path | str = Path("data/templates")) -> None:
        self._cache: dict[str, Template] = {}
        self._builtin_ids: set[str] = set()
        self._custom_versions: dict[str, dict[int, Template]] = {}
        self._custom_dir = Path(custom_dir)
        self._scan()
        self._scan_custom_dir()

    def _scan(self) -> None:
        pkg = resources.files("matcher.templates.builtin")
        for entry in pkg.iterdir():
            if entry.name.endswith(".yaml") or entry.name.endswith(".yml"):
                with entry.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                tpl = parse_template(data)
                if tpl.id in self._cache:
                    raise TemplateConflict(
                        f"內建模板 id 衝突：`{tpl.id}` 同時出現在 "
                        f"{self._cache[tpl.id]} 與 {entry.name}"
                    )
                self._cache[tpl.id] = tpl
                self._builtin_ids.add(tpl.id)

    def _scan_custom_dir(self) -> None:
        """掃 data/templates/<id>/v<N>.yaml；最新版本進主 cache、所有版本進 _custom_versions。"""
        if not self._custom_dir.exists():
            return
        for tpl_dir in self._custom_dir.iterdir():
            if not tpl_dir.is_dir() or tpl_dir.name.startswith("."):
                continue
            tpl_id = tpl_dir.name
            versions: dict[int, Template] = {}
            for entry in tpl_dir.iterdir():
                m = _CUSTOM_VERSION_PATTERN.match(entry.name)
                if not m:
                    continue
                version_n = int(m.group(1))
                with entry.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                tpl = parse_template(data)
                if tpl.id != tpl_id:
                    raise TemplateConflict(
                        f"自訂模板檔內 id `{tpl.id}` 與目錄名 `{tpl_id}` 不一致"
                    )
                versions[version_n] = tpl
            if versions:
                self._custom_versions[tpl_id] = versions
                latest = max(versions.keys())
                # 自訂模板不可覆蓋內建（理論上 save_custom 已擋；萬一發生則 builtin 優先）
                if tpl_id not in self._builtin_ids:
                    self._cache[tpl_id] = versions[latest]

    def invalidate(self) -> None:
        """重新掃描所有來源（save_custom 後呼叫）。"""
        self._cache = {}
        self._builtin_ids = set()
        self._custom_versions = {}
        self._scan()
        self._scan_custom_dir()

    def list_ids(self) -> list[str]:
        return sorted(self._cache.keys())

    def get(self, template_id: str) -> Template:
        if template_id not in self._cache:
            available = ", ".join(self.list_ids()) or "（無）"
            raise TemplateNotFound(
                f"找不到模板 `{template_id}`。\n"
                f"細節：目前可用模板：{available}。\n"
                f"建議：執行 `matcher template list` 檢視所有可用模板。"
            )
        return self._cache[template_id]

    def has(self, template_id: str) -> bool:
        return template_id in self._cache

    def is_builtin(self, template_id: str) -> bool:
        return template_id in self._builtin_ids

    def list_versions(self, template_id: str) -> list[int]:
        """回此自訂模板的版本號（排序）。內建模板回 []。"""
        return sorted(self._custom_versions.get(template_id, {}).keys())

    def get_version(self, template_id: str, version: int) -> Template:
        """取自訂模板的指定版本。內建或版本不存在 → raise TemplateNotFound。"""
        if template_id not in self._custom_versions:
            raise TemplateNotFound(f"自訂模板 `{template_id}` 不存在")
        versions = self._custom_versions[template_id]
        if version not in versions:
            raise TemplateNotFound(
                f"自訂模板 `{template_id}` 沒有版本 v{version}（現有：{sorted(versions.keys())}）"
            )
        return versions[version]

    def save_custom(self, tpl_dict: dict) -> tuple[str, int]:
        """寫入新版本檔案；返回 (id, version)。

        驗證流程：
        1. parse_template 確認 tpl_dict 合法（fail → raise）
        2. 檢查 id 不在內建模板（fail → raise ValueError "id 已存在於內建模板"）
        3. 檢查 id 格式（限定 `[a-z0-9-]+`）
        4. 計算 next_version = max(現有) + 1（或 1）
        5. 寫檔 + invalidate
        """
        import re as _re
        tpl = parse_template(tpl_dict)  # 1
        if tpl.id in self._builtin_ids:
            raise ValueError(
                f"模板 id `{tpl.id}` 已存在於內建模板，不可覆蓋；請改名或選擇 Fork"
            )
        if not _re.fullmatch(r"[a-z0-9-]+", tpl.id):
            raise ValueError(
                f"模板 id `{tpl.id}` 格式不合法；僅允許小寫英數字與連字號"
            )
        tpl_dir = self._custom_dir / tpl.id
        tpl_dir.mkdir(parents=True, exist_ok=True)
        existing = [
            int(_CUSTOM_VERSION_PATTERN.match(p.name).group(1))
            for p in tpl_dir.iterdir()
            if _CUSTOM_VERSION_PATTERN.match(p.name)
        ]
        next_version = (max(existing) if existing else 0) + 1
        path = tpl_dir / f"v{next_version}.yaml"
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(tpl_dict, f, allow_unicode=True, sort_keys=False)
        self.invalidate()
        return tpl.id, next_version


def dump_template_yaml(tpl: Template, path: str | Path) -> None:
    """將 Template 序列化為 YAML，頂層欄位固定順序，保留繁中。"""
    out = {
        "schema_version": tpl.schema_version,
        "id": tpl.id,
        "name": tpl.name,
        "description": tpl.description,
        "attributes": {
            "roles": [_attr_decl_to_dict(a) for a in tpl.attributes.roles],
            "targets": [_attr_decl_to_dict(a) for a in tpl.attributes.targets],
        },
        "rules": _ruleset_to_yaml_list(tpl.ruleset),
    }
    if tpl.ui_fields:
        out["ui_fields"] = [_ui_field_to_dict(u) for u in tpl.ui_fields]
    if tpl.report_fields:
        out["report_fields"] = [
            {"key": r.key, "label": r.label, "source": r.source} for r in tpl.report_fields
        ]
    if tpl.preferences_schema is not None:
        ps = tpl.preferences_schema
        out["preferences_schema"] = {
            "max_choices": ps.max_choices,
            "required": ps.required,
            "description": ps.description,
        }
    if tpl.default_targets:
        out["default_targets"] = [
            {"id": t.id, "capacity": t.capacity, "attributes": dict(t.attributes)}
            for t in tpl.default_targets
        ]

    s = yaml.safe_dump(out, allow_unicode=True, sort_keys=False)
    Path(path).write_text(s, encoding="utf-8")


def _attr_decl_to_dict(a: AttributeDecl) -> dict:
    d = {"key": a.key, "type": a.type, "required": a.required}
    if a.description:
        d["description"] = a.description
    return d


def _ui_field_to_dict(u: UIFieldDecl) -> dict:
    d: dict = {"key": u.key, "label": u.label, "type": u.type, "required": u.required}
    if u.options is not None:
        d["options"] = list(u.options)
    if u.placeholder is not None:
        d["placeholder"] = u.placeholder
    if u.help is not None:
        d["help"] = u.help
    return d


def _ruleset_to_yaml_list(ruleset) -> list:
    from matcher.audit import _expr_to_dict
    return [
        {"id": r.id, "description": r.description, "expr": _expr_to_dict(r.expr)}
        for r in ruleset.rules
    ]
