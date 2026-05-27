"""媒合路由：新建媒合（含向導）、執行、結果頁、下載 audit。"""

from __future__ import annotations

import base64
import dataclasses
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from matcher.data_import import load_roster_csv, load_roster_xlsx
from matcher.errors import MatcherError, QualifiedSetEmpty, SeedMissing, TemplateNotFound
from matcher.pipeline import MatcherInput, run_match
from matcher.template_loader import TemplateRegistry
from matcher.web.auth import current_email, require_login
from matcher.web.errors import MatchRecordNotFound, UploadInvalidMime, UploadTooLarge
from matcher.web.humanize import mechanism_label, preference_rank_display, target_summary
from matcher.web.individual import build_individual_audit_subset
from matcher.web.pdf import PdfRenderUnavailable, render_match_report_pdf
from matcher.web.ratelimit import rate_limit
from matcher.web.security import sign_role_token, validate_csrf, verify_role_token
from matcher.web.store import MatchRecord, MatchStore, SCHEMA_VERSION


def _check_csrf(request: Request, form) -> None:
    """驗證 CSRF token；不符拋 403。"""
    if not validate_csrf(request.session.get("csrf_token"), form.get("csrf_token")):
        raise HTTPException(status_code=403, detail="CSRF 驗證失敗，請重新整理頁面再試。")


def _owner_or_403(request: Request, record) -> None:
    """確認登入者是該紀錄擁有者；否則 403。"""
    email = current_email(request)
    if record.owner is not None and record.owner != email:
        raise HTTPException(status_code=403, detail="這筆配對不屬於你，無法查看。")


def _targets_to_yaml_bytes(targets) -> bytes:
    """Target tuple → targets YAML bytes（供志願頁 handoff 重建旁檔用）。"""
    import yaml as _yaml
    data = {"targets": [
        {"id": t.id, "capacity": t.capacity, "attributes": dict(t.attributes)}
        for t in targets
    ]}
    return _yaml.safe_dump(data, allow_unicode=True, sort_keys=False).encode("utf-8")


def _empty_set_message(e: QualifiedSetEmpty) -> str:
    """把空集合診斷組成一句白話、給填清單頁的紅字 banner（feature 015）。"""
    base = "沒有任何人符合資格——清單與對象的所有組合都沒通過條件。"
    if getattr(e, "culprit", None):
        desc = e.rule_descriptions.get(e.culprit, e.culprit)
        n = e.rule_stats.get(e.culprit, 0)
        return f"{base}最可能的原因：「{desc}」把 {n}／{e.total_pairs} 組都刷掉了——請檢查清單裡這項的值是否符合。"
    return base


def _error_dict(e: MatcherError) -> dict:
    """建失敗 record 的 error；資格集合為空時附診斷（feature 015）。"""
    d = {"type": type(e).__name__, "exit_code": e.exit_code, "message": str(e)}
    from matcher.errors import QualifiedSetEmpty
    if isinstance(e, QualifiedSetEmpty) and getattr(e, "rule_stats", None):
        d["diagnostic"] = {
            "total_pairs": e.total_pairs,
            "rule_stats": e.rule_stats,
            "culprit": e.culprit,
            "rules": e.rule_descriptions,
        }
    return d

router = APIRouter()

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB

MECHANISMS = [
    ("M0", "純抽籤"),
    ("M1", "輪流挑"),
    ("M2", "依志願先後填滿"),
]
VALID_MECHANISMS = {value for value, _ in MECHANISMS}
ALLOWED_MIMES = {
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",  # 某些瀏覽器對 .xlsx 仍回 ms-excel
}


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


@router.get("/match/new")
async def new_match(
    request: Request,
    template_id: Optional[str] = None,
    template_snapshot: Optional[str] = None,
    email: str = Depends(require_login),
):
    """新建配對表單。

    US4：?template_snapshot=<rid> 從某次配對紀錄還原其使用的範本快照。
    用於「以此版本再執行」——即使該範本後來被改成新版本，仍能用當時的版本跑。
    """
    from matcher.web.routes.pages import _reg as _shared_reg
    reg = _shared_reg()
    items = [reg.get(tid) for tid in reg.list_ids()]

    snapshot_template = None
    snapshot_note = None
    if template_snapshot:
        # 從 record 還原 template snapshot
        store = MatchStore()
        try:
            record = store.get(template_snapshot)
        except MatchRecordNotFound:
            raise HTTPException(404, "找不到該配對紀錄")
        if record.audit is None or "template_snapshot" not in record.audit:
            raise HTTPException(404, "該紀錄沒有範本快照")
        from matcher.template_loader import parse_template
        snapshot_template = parse_template(record.audit["template_snapshot"])
        snapshot_note = f"已預載「{snapshot_template.name}」當時的版本（來自配對紀錄 {template_snapshot}）"
        template_id = snapshot_template.id

    return _templates(request).TemplateResponse(
        request, "new_match.html",
        {
            "templates": items,
            "selected_id": template_id,
            "mechanisms": MECHANISMS,
            "default_mechanism": "M0",
            "snapshot_note": snapshot_note,
        },
    )


# ── Feature 012：UI 直接填清單 ───────────────────────────────────

def _render_fill_form(
    request: Request,
    tpl,
    *,
    prefill_roles=None,
    prefill_targets=None,
    form_error: Optional[str] = None,
    seed=None,
    mechanism: str = "M0",
    status_code: int = 200,
):
    """渲染填清單頁。錯誤時帶 prefill 與 form_error 回填，避免使用者重打清單。"""
    role_attrs = [
        {"key": a.key, "type": a.type, "required": a.required,
         "label": a.description or a.key}
        for a in tpl.attributes.roles
    ]
    target_attrs = [
        {"key": a.key, "type": a.type, "required": a.required,
         "label": a.description or a.key}
        for a in tpl.attributes.targets
    ]
    # 預設給三列空白；錯誤回填時用使用者送來的內容
    if prefill_roles is None:
        prefill_roles = [{}, {}, {}]
    if prefill_targets is None:
        prefill_targets = [{}, {}, {}]

    return _templates(request).TemplateResponse(
        request, "roster_form_fill.html",
        {
            "template": tpl,
            "role_attrs": role_attrs,
            "target_attrs": target_attrs,
            # Feature 013：對象段一律顯示
            "has_prefs_schema": tpl.preferences_schema is not None,
            "mechanisms": MECHANISMS,
            "default_mechanism": "M0",
            "prefill_roles": prefill_roles,
            "prefill_targets": prefill_targets,
            "form_error": form_error,
            "prefill_seed": seed,
            "prefill_mechanism": mechanism,
        },
        status_code=status_code,
    )


def _extract_form_rows(form: dict, prefix: str, keys: list[str]) -> list[dict]:
    """從 form dict 撈 `<prefix>_<i>_<key>` → list of row dicts（保留所有列，含空白）。"""
    rows: dict[int, dict] = {}
    for k, v in form.items():
        for key in keys:
            suffix = f"_{key}"
            if k.startswith(f"{prefix}_") and k.endswith(suffix):
                mid = k[len(prefix) + 1 : -len(suffix)]
                if mid.isdigit():
                    rows.setdefault(int(mid), {})[key] = v
    return [rows[i] for i in sorted(rows.keys())]


@router.get("/match/new/fill")
async def new_match_fill(request: Request, template_id: str, email: str = Depends(require_login)):
    """填寫頁：依範本宣告動態渲染欄位。"""
    from matcher.web.routes.pages import _reg as _shared_reg
    reg = _shared_reg()
    try:
        tpl = reg.get(template_id)
    except TemplateNotFound as e:
        return _error_page(request, "TemplateNotFound", str(e), status_code=404)
    return _render_fill_form(request, tpl)


@router.post("/match/run-from-form")
async def run_from_form(request: Request, email: str = Depends(require_login),
                        _rl=Depends(rate_limit("run", 120, 60))):
    """UI 填清單 → CSV bytes → 既有 pipeline。

    M1/M2 路徑沿用 feature 009：偵測志願缺 → 跳 preferences_form。
    """
    from matcher.web.roster_form import (
        assemble_roster_csv_bytes,
        assemble_targets_yaml_bytes,
    )
    from matcher.web.routes.pages import _reg as _shared_reg

    form_raw = await request.form()
    _check_csrf(request, form_raw)
    form: dict = {k: v for k, v in form_raw.items() if isinstance(v, str)}

    template_id = form.get("template_id", "").strip()
    if not template_id:
        return _error_page(request, "BadForm", "缺少範本選擇。")
    try:
        tpl = _shared_reg().get(template_id)
    except TemplateNotFound as e:
        return _error_page(request, "TemplateNotFound", str(e), status_code=404)

    # 蒐集使用者填的列，供驗證失敗時回填（不讓他重打）
    role_keys = ["id"] + [a.key for a in tpl.attributes.roles]
    if tpl.preferences_schema is not None:
        role_keys.append("preferences")
    target_keys = ["id", "capacity"] + [a.key for a in tpl.attributes.targets]
    filled_roles = _extract_form_rows(form, "role", role_keys)
    filled_targets = _extract_form_rows(form, "target", target_keys)
    mechanism = (form.get("mechanism") or "M0").strip().upper()
    seed_raw = form.get("seed", "123456")

    def _refill(msg: str):
        return _render_fill_form(
            request, tpl,
            prefill_roles=filled_roles or None,
            prefill_targets=filled_targets or None,
            form_error=msg,
            seed=seed_raw,
            mechanism=mechanism if mechanism in VALID_MECHANISMS else "M0",
            status_code=400,
        )

    try:
        seed = int(seed_raw)
    except ValueError:
        return _refill("亂數種子必須是整數（只能填數字）。")
    if mechanism not in VALID_MECHANISMS:
        return _refill("請選一個抽籤方式。")

    csv_bytes = assemble_roster_csv_bytes(form, tpl)
    # 檢查空白：CSV 只有 header 列 → 沒有任何角色
    if csv_bytes.decode("utf-8-sig").strip().count("\n") < 1:
        return _refill("請至少填一位（第 1 步的清單還是空的）。")

    targets_yaml = assemble_targets_yaml_bytes(form, tpl)
    if targets_yaml is None:
        return _refill("請至少填一個對象，並記得每個對象都要有「編號」和「容量」（第 2 步）。")

    # 寫到 tmp、走 CSV path
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(csv_bytes)
        csv_path = Path(tmp.name)
    sidecar_path = None
    if targets_yaml is not None:
        sidecar_path = csv_path.with_suffix(".targets.yaml")
        sidecar_path.write_bytes(targets_yaml)

    store = MatchStore()
    record_id = MatchRecord.new_id()
    now = datetime.now(timezone.utc).isoformat()
    roster_filename = "ui-form.csv"
    common = dict(
        schema_version=SCHEMA_VERSION,
        id=record_id, created_at=now,
        template_id=template_id, seed=seed,
        input_file=roster_filename, mechanism=mechanism,
        owner=email,
    )

    qse = None  # Feature 015：捕捉空集合，於 finally 後回填清單頁
    try:
        try:
            ro, import_meta = load_roster_csv(csv_path, tpl)
            import_meta["file_basename"] = roster_filename

            # M1/M2 + 範本有 schema + 全無 prefs → 跳 preferences_form
            if (
                tpl.preferences_schema is not None
                and mechanism in ("M1", "M2")
                and all(not role.preferences for role in ro.roles)
            ):
                return _render_preferences_form(
                    request, template_id=template_id, template_name=tpl.name,
                    mechanism=mechanism, seed=seed,
                    roster_bytes=csv_bytes, roster_filename=roster_filename,
                    roles=ro.roles, targets=ro.targets, targets_bytes=targets_yaml,
                    max_choices=tpl.preferences_schema.max_choices,
                )

            result = run_match(MatcherInput(
                ruleset=tpl.ruleset, roster=ro, seed=seed, preferences=None,
                mechanism=mechanism, template=tpl, import_metadata=import_meta,
            ))
            record = MatchRecord(**common, status="success", audit=result.audit, error=None)
        except QualifiedSetEmpty as e:
            # Feature 015：UI 填清單觸發空集合 → 回填清單頁 + 診斷，保留使用者輸入
            qse = e
            record = None
        except MatcherError as e:
            record = MatchRecord(
                **common, status="failed", audit=None,
                error=_error_dict(e),
            )
    finally:
        csv_path.unlink(missing_ok=True)
        if sidecar_path is not None:
            sidecar_path.unlink(missing_ok=True)

    if qse is not None:
        return _render_fill_form(
            request, tpl,
            prefill_roles=filled_roles or None,
            prefill_targets=filled_targets or None,
            form_error=_empty_set_message(qse),
            seed=seed_raw, mechanism=mechanism, status_code=400,
        )
    store.save(record)
    return RedirectResponse(url=f"/match/{record.id}", status_code=303)


@router.post("/match/run")
async def run(
    request: Request,
    template_id: str = Form(...),
    seed: int = Form(...),
    roster: UploadFile = File(...),
    targets_yaml: Optional[UploadFile] = File(None),
    mechanism: str = Form("M0"),
    csrf_token: str = Form(""),
    email: str = Depends(require_login),
    _rl=Depends(rate_limit("run", 120, 60)),
):
    if not validate_csrf(request.session.get("csrf_token"), csrf_token):
        raise HTTPException(status_code=403, detail="CSRF 驗證失敗，請重新整理頁面再試。")
    # 驗證機制
    mechanism = (mechanism or "M0").strip().upper()
    if mechanism not in VALID_MECHANISMS:
        return _templates(request).TemplateResponse(
            request, "error_page.html",
            {
                "error_type": "InvalidMechanism",
                "error_message": f"不支援的抽籤方式 `{mechanism}`；請選「純抽籤」、「輪流挑」或「依志願先後填滿」。",
            },
            status_code=400,
        )

    # 驗證大小
    data = await roster.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise UploadTooLarge(
            f"上傳檔過大（{len(data)} bytes，上限 {MAX_UPLOAD_BYTES} bytes / 5 MB）。\n"
            f"建議：縮減檔案後重新上傳，或拆分成多次媒合。"
        )

    # 驗證 MIME
    if roster.content_type not in ALLOWED_MIMES:
        raise UploadInvalidMime(
            f"上傳檔類型不支援：{roster.content_type}。\n"
            f"細節：僅接受 CSV（text/csv）與 Excel（.xlsx）。\n"
            f"建議：另存為 CSV 或 .xlsx 後重新上傳。"
        )

    # 載入模板
    from matcher.web.routes.pages import _reg as _shared_reg  # feature 011：共用 singleton
    try:
        reg = _shared_reg()
        tpl = reg.get(template_id)
    except TemplateNotFound as e:
        return _templates(request).TemplateResponse(
            request, "error_page.html",
            {"error_type": "TemplateNotFound", "error_message": str(e)},
            status_code=404,
        )

    # 寫到 tmp 並讀取
    suffix = Path(roster.filename or "upload").suffix.lower()
    is_xlsx = suffix == ".xlsx" or "spreadsheetml" in (roster.content_type or "")

    store = MatchStore()
    record_id = MatchRecord.new_id()
    now = datetime.now(timezone.utc).isoformat()
    common = dict(
        schema_version=SCHEMA_VERSION,
        id=record_id,
        created_at=now,
        template_id=template_id,
        seed=seed,
        input_file=roster.filename,
        mechanism=mechanism,
        owner=email,
    )

    with tempfile.NamedTemporaryFile(suffix=suffix or (".xlsx" if is_xlsx else ".csv"), delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)

    # Feature 016：對象清單可為 CSV/Excel（試算表）或 YAML（依副檔名分派）
    # - .csv/.xlsx → 解析成 targets tuple，以 targets= 注入 load_roster
    # - .yaml/.yml → 寫旁檔，由 data_import 自動取用（向後相容）
    sidecar_tmp = None
    targets_tmp = None
    sidecar_data: bytes = b""          # 志願頁 handoff 用的 targets YAML bytes
    injected_targets = None            # csv/xlsx 解析出的 targets tuple
    if targets_yaml is not None and targets_yaml.filename:
        tname = targets_yaml.filename.lower()
        traw = await targets_yaml.read()
        if traw:
            if tname.endswith(".csv") or tname.endswith(".xlsx"):
                from matcher.data_import import load_targets_csv, load_targets_xlsx
                tsuffix = ".xlsx" if tname.endswith(".xlsx") else ".csv"
                with tempfile.NamedTemporaryFile(suffix=tsuffix, delete=False) as ttmp:
                    ttmp.write(traw)
                    targets_tmp = Path(ttmp.name)
                # 解析延後到 try 內，讓錯誤變成失敗 record / 診斷
            else:
                sidecar_data = traw
                sidecar_tmp = tmp_path.with_suffix(".targets.yaml")
                sidecar_tmp.write_bytes(traw)

    try:
        try:
            if targets_tmp is not None:
                from matcher.data_import import load_targets_csv, load_targets_xlsx
                injected_targets = (
                    load_targets_xlsx(targets_tmp, tpl) if targets_tmp.suffix == ".xlsx"
                    else load_targets_csv(targets_tmp, tpl)
                )
                sidecar_data = _targets_to_yaml_bytes(injected_targets)
            if is_xlsx:
                ro, import_meta = load_roster_xlsx(tmp_path, tpl, targets=injected_targets)
            else:
                ro, import_meta = load_roster_csv(tmp_path, tpl, targets=injected_targets)

            # 修正 import_metadata 中的 basename 為原檔名（避免暴露 tmp 路徑）
            import_meta["file_basename"] = roster.filename or import_meta["file_basename"]

            # Feature 009：偵測「需要使用者填志願」→ 跳到中介頁，不執行 pipeline
            if (
                tpl.preferences_schema is not None
                and mechanism in ("M1", "M2")
                and all(not role.preferences for role in ro.roles)
            ):
                tmp_path.unlink(missing_ok=True)
                return _render_preferences_form(
                    request, template_id=template_id, template_name=tpl.name,
                    mechanism=mechanism, seed=seed,
                    roster_bytes=data, roster_filename=roster.filename or "roster.csv",
                    roles=ro.roles, targets=ro.targets, targets_bytes=sidecar_data,
                    max_choices=tpl.preferences_schema.max_choices,
                )

            result = run_match(MatcherInput(
                ruleset=tpl.ruleset,
                roster=ro,
                seed=seed,
                preferences=None,
                mechanism=mechanism,
                template=tpl,
                import_metadata=import_meta,
            ))
            record = MatchRecord(**common, status="success", audit=result.audit, error=None)
        except MatcherError as e:
            record = MatchRecord(
                **common, status="failed", audit=None,
                error=_error_dict(e),
            )
    finally:
        tmp_path.unlink(missing_ok=True)
        if sidecar_tmp is not None:
            sidecar_tmp.unlink(missing_ok=True)
        if targets_tmp is not None:
            targets_tmp.unlink(missing_ok=True)

    store.save(record)
    return RedirectResponse(url=f"/match/{record.id}", status_code=303)


# ── Feature 009：填志願表單中介頁面 ────────────────────────────

def _render_preferences_form(
    request: Request,
    *,
    template_id: str,
    template_name: str,
    mechanism: str,
    seed: int,
    roster_bytes: bytes,
    roster_filename: str,
    roles,
    targets,
    targets_bytes: bytes = b"",
    max_choices: int,
    form_errors: Optional[list] = None,
    previous_form_values: Optional[dict] = None,
    status_code: int = 200,
):
    """渲染填志願中介頁面。targets 為本次配對的對象（從 sidecar 或 UI form 載入）。"""
    targets_for_options = None
    if targets:
        targets_for_options = [
            {
                "id": t.id,
                "name": (t.attributes or {}).get("name", t.id),
                "capacity": t.capacity,
                "summary": target_summary({
                    "id": t.id,
                    "name": (t.attributes or {}).get("name", t.id),
                    "capacity": t.capacity,
                }),
            }
            for t in targets
        ]
    roles_for_form = [
        {"id": r.id, "display_name": (r.attributes or {}).get("name", r.id)}
        for r in roles
    ]
    return _templates(request).TemplateResponse(
        request, "preferences_form.html",
        {
            "template_id": template_id,
            "template_name": template_name,
            "mechanism": mechanism,
            "mechanism_label": mechanism_label(mechanism),
            "seed": seed,
            "roster_bytes_b64": base64.b64encode(roster_bytes).decode("ascii"),
            "roster_filename": roster_filename,
            "targets_bytes_b64": base64.b64encode(targets_bytes).decode("ascii"),
            "roles_for_form": roles_for_form,
            "targets_for_options": targets_for_options,
            "max_choices": max_choices,
            "form_errors": form_errors or [],
            "previous_form_values": previous_form_values or {},
        },
        status_code=status_code,
    )


def _error_page(request: Request, error_type: str, message: str, status_code: int = 400):
    return _templates(request).TemplateResponse(
        request, "error_page.html",
        {"error_type": error_type, "error_message": message},
        status_code=status_code,
    )


@router.post("/match/preferences")
async def submit_preferences(request: Request, email: str = Depends(require_login)):
    form = await request.form()
    _check_csrf(request, form)
    try:
        template_id = form["template_id"]
        mechanism = (form["mechanism"] or "M0").strip().upper()
        seed = int(form["seed"])
        roster_bytes_b64 = form["roster_bytes_b64"]
        roster_filename = form["roster_filename"]
        action = form.get("_action", "submit")
    except (KeyError, ValueError):
        return _error_page(request, "PreferencesFormCorrupt", "填志願表單資料異常，請回到上一步重新上傳。")

    try:
        roster_bytes = base64.b64decode(roster_bytes_b64)
        targets_bytes_b64 = form.get("targets_bytes_b64", "")
        targets_bytes = base64.b64decode(targets_bytes_b64) if targets_bytes_b64 else b""
    except Exception:
        return _error_page(request, "PreferencesFormCorrupt", "填志願表單資料異常，請回到上一步重新上傳。")

    try:
        from matcher.web.routes.pages import _reg as _shared_reg
        tpl = _shared_reg().get(template_id)
    except TemplateNotFound as e:
        return _error_page(request, "TemplateNotFound", str(e), status_code=404)

    suffix = Path(roster_filename).suffix.lower()
    is_xlsx = suffix == ".xlsx"

    with tempfile.NamedTemporaryFile(suffix=suffix or ".csv", delete=False) as tmp:
        tmp.write(roster_bytes)
        tmp_path = Path(tmp.name)
    # Feature 013：sidecar 從 hidden input 還原
    sidecar_tmp_pref = None
    if targets_bytes:
        sidecar_tmp_pref = tmp_path.with_suffix(".targets.yaml")
        sidecar_tmp_pref.write_bytes(targets_bytes)

    try:
        try:
            if is_xlsx:
                ro, import_meta = load_roster_xlsx(tmp_path, tpl)
            else:
                ro, import_meta = load_roster_csv(tmp_path, tpl)
            import_meta["file_basename"] = roster_filename
        except MatcherError as e:
            return _error_page(request, type(e).__name__, str(e))
    finally:
        tmp_path.unlink(missing_ok=True)
        if sidecar_tmp_pref is not None:
            sidecar_tmp_pref.unlink(missing_ok=True)

    max_choices = tpl.preferences_schema.max_choices if tpl.preferences_schema else 0
    valid_target_ids = {t.id for t in ro.targets}

    # _action == "submit"：驗證 + 組裝；"skip"：保留空 prefs 直接跑
    form_errors: list[str] = []
    previous_form_values: dict[str, str] = {}
    if action == "submit":
        new_roles = []
        any_pref = False
        for role in ro.roles:
            prefs: list[str] = []
            for rank in range(1, max_choices + 1):
                field = f"pref_{role.id}_{rank}"
                value = (form.get(field) or "").strip()
                previous_form_values[field] = value
                if value:
                    if value not in valid_target_ids:
                        form_errors.append(f"角色 {role.id} 的第 {rank} 志願選了無效的對象「{value}」。")
                        continue
                    prefs.append(value)
            if len(set(prefs)) != len(prefs):
                form_errors.append(f"角色 {role.id} 的志願中有重複——同列不可重複選同對象。")
            if prefs:
                any_pref = True
            new_roles.append(dataclasses.replace(role, preferences=tuple(prefs)))

        if form_errors:
            return _render_preferences_form(
                request,
                template_id=template_id, template_name=tpl.name,
                mechanism=mechanism, seed=seed,
                roster_bytes=roster_bytes, roster_filename=roster_filename,
                roles=ro.roles, targets=ro.targets, targets_bytes=targets_bytes,
                max_choices=max_choices,
                form_errors=form_errors,
                previous_form_values=previous_form_values,
            )

        if not any_pref:
            form_errors.append("請至少為一位角色填寫 1 個志願；若確實沒有志願，請點「跳過此步驟」。")
            return _render_preferences_form(
                request,
                template_id=template_id, template_name=tpl.name,
                mechanism=mechanism, seed=seed,
                roster_bytes=roster_bytes, roster_filename=roster_filename,
                roles=ro.roles, targets=ro.targets, targets_bytes=targets_bytes,
                max_choices=max_choices,
                form_errors=form_errors,
                previous_form_values=previous_form_values,
            )

        ro = dataclasses.replace(ro, roles=tuple(new_roles))
    # action == "skip" → ro 不動（preferences 全空），交由 pipeline reject

    # 跑 pipeline 並寫 record
    store = MatchStore()
    record_id = MatchRecord.new_id()
    now = datetime.now(timezone.utc).isoformat()
    common = dict(
        schema_version=SCHEMA_VERSION,
        id=record_id, created_at=now,
        template_id=template_id, seed=seed,
        input_file=roster_filename, mechanism=mechanism,
        owner=email,
    )
    try:
        result = run_match(MatcherInput(
            ruleset=tpl.ruleset, roster=ro, seed=seed, preferences=None,
            mechanism=mechanism, template=tpl, import_metadata=import_meta,
        ))
        record = MatchRecord(**common, status="success", audit=result.audit, error=None)
    except MatcherError as e:
        record = MatchRecord(
            **common, status="failed", audit=None,
            error={"type": type(e).__name__, "exit_code": e.exit_code, "message": str(e)},
        )
    store.save(record)
    return RedirectResponse(url=f"/match/{record.id}", status_code=303)


@router.get("/match/{record_id}")
async def match_detail(request: Request, record_id: str, email: str = Depends(require_login)):
    store = MatchStore()
    record = store.get(record_id)
    _owner_or_403(request, record)

    roles_for_links: list = []
    mechanism = "M0"
    processing_order_display = None
    rank_display_by_role: dict = {}
    if record.status == "success" and record.audit:
        roles_for_links = [
            {"id": r["id"], "name": r.get("attributes", {}).get("name", r["id"]),
             "token": sign_role_token(record.id, r["id"])}
            for r in record.audit.get("roster_snapshot", {}).get("roles", [])
        ]
        mechanism = record.audit.get("mechanism", "M0")
        # 處理順序段（M1/M2 才注入；M0 audit.processing_order 為 null）
        po = record.audit.get("processing_order")
        if po:
            name_by_id = {r["id"]: r.get("attributes", {}).get("name", r["id"])
                          for r in record.audit.get("roster_snapshot", {}).get("roles", [])}
            processing_order_display = [(rid, name_by_id.get(rid, rid)) for rid in po]
        # 志願排名欄（M1/M2）
        for entry in record.audit.get("allocation_trace", []):
            display = preference_rank_display(
                mechanism,
                entry.get("preference_rank"),
                entry.get("fallback_random_index"),
            )
            if display is not None:
                rank_display_by_role[entry["role_id"]] = display
    return _templates(request).TemplateResponse(
        request, "match_result.html",
        {
            "record": record,
            "roles_for_links": roles_for_links,
            "mechanism": mechanism,
            "mechanism_label": mechanism_label(mechanism),
            "processing_order_display": processing_order_display,
            "rank_display_by_role": rank_display_by_role,
        },
    )


def _individual_error(request: Request, message: str) -> Response:
    return _templates(request).TemplateResponse(
        request, "individual_error.html",
        {"message": message},
        status_code=404,
    )


def _render_individual(request: Request, record, role_id: str):
    """渲染個別查詢頁（被舊 admin 路徑與 /r/{token} 共用）。"""
    if record.status == "failed" or record.audit is None:
        return _individual_error(request, "該次配對執行失敗，無個別查詢資料")

    role = next(
        (r for r in record.audit.get("roster_snapshot", {}).get("roles", []) if r["id"] == role_id),
        None,
    )
    if role is None:
        return _individual_error(request, "您不在這次配對的清單中")

    # 載入模板（用於 humanize 規則描述）
    from matcher.web.routes.pages import _reg as _shared_reg  # feature 011：共用 singleton
    reg = _shared_reg()
    try:
        template = reg.get(record.template_id)
    except TemplateNotFound:
        template = None

    subset = build_individual_audit_subset(record.audit, role_id)

    # US2：志願滿足度
    mechanism = record.audit.get("mechanism", "M0")
    preference_rank = None
    fallback_random_index = None
    for entry in record.audit.get("allocation_trace", []):
        if entry.get("role_id") == role_id:
            preference_rank = entry.get("preference_rank")
            fallback_random_index = entry.get("fallback_random_index")
            break
    preferred_count = len(role.get("preferences", []) or [])

    rules_lookup = {
        r["id"]: r["description"]
        for r in record.audit.get("rules_snapshot", {}).get("rules", [])
    }
    target_lookup = {
        t["id"]: t.get("attributes", {})
        for t in record.audit.get("roster_snapshot", {}).get("targets", [])
    }

    return _templates(request).TemplateResponse(
        request, "individual_view.html",
        {
            "record": record,
            "role": role,
            "subset": subset,
            "template": template,
            "rules_lookup": rules_lookup,
            "target_lookup": target_lookup,
            "mechanism": mechanism,
            "preference_rank": preference_rank,
            "fallback_random_index": fallback_random_index,
            "preferred_count": preferred_count,
        },
    )


@router.get("/match/{record_id}/role/{role_id}")
async def individual_view(request: Request, record_id: str, role_id: str,
                          email: str = Depends(require_login)):
    """舊個別路徑：Feature 014 改為僅擁有者（登入）可看（行政預覽用）。
    匿名當事人請改用 /r/{token}。"""
    store = MatchStore()
    try:
        record = store.get(record_id)
    except MatchRecordNotFound:
        return _individual_error(request, "找不到該次配對的紀錄")
    _owner_or_403(request, record)
    return _render_individual(request, record, role_id)


@router.get("/r/{token}")
async def individual_view_by_token(request: Request, token: str):
    """Feature 014：當事人用不可猜 token 看自己結果，免登入。"""
    verified = verify_role_token(token)
    if verified is None:
        return _individual_error(request, "連結無效或已失效")
    record_id, role_id = verified
    store = MatchStore()
    try:
        record = store.get(record_id)
    except MatchRecordNotFound:
        return _individual_error(request, "找不到該次配對的紀錄")
    return _render_individual(request, record, role_id)


def _individual_audit_payload(record, role_id: str) -> str:
    subset = build_individual_audit_subset(record.audit, role_id)
    return json.dumps(subset, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


@router.get("/match/{record_id}/role/{role_id}/audit.json")
async def individual_audit_download(request: Request, record_id: str, role_id: str,
                                    email: str = Depends(require_login)):
    store = MatchStore()
    try:
        record = store.get(record_id)
    except MatchRecordNotFound:
        raise HTTPException(status_code=404, detail="找不到該次配對的紀錄")
    _owner_or_403(request, record)
    if record.status != "success" or record.audit is None:
        raise HTTPException(status_code=404, detail="該次配對執行失敗，無個別查詢資料")
    role_exists = any(
        r["id"] == role_id for r in record.audit.get("roster_snapshot", {}).get("roles", [])
    )
    if not role_exists:
        raise HTTPException(status_code=404, detail="您不在這次配對的清單中")
    return Response(
        content=_individual_audit_payload(record, role_id),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{record_id}-{role_id}.individual.json"'},
    )


@router.get("/r/{token}/audit.json")
async def individual_audit_by_token(request: Request, token: str):
    verified = verify_role_token(token)
    if verified is None:
        raise HTTPException(status_code=404, detail="連結無效")
    record_id, role_id = verified
    store = MatchStore()
    try:
        record = store.get(record_id)
    except MatchRecordNotFound:
        raise HTTPException(status_code=404, detail="找不到該次配對的紀錄")
    if record.status != "success" or record.audit is None:
        raise HTTPException(status_code=404, detail="無個別查詢資料")
    role_exists = any(
        r["id"] == role_id for r in record.audit.get("roster_snapshot", {}).get("roles", [])
    )
    if not role_exists:
        raise HTTPException(status_code=404, detail="找不到對應角色")
    return Response(
        content=_individual_audit_payload(record, role_id),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{record_id}-{role_id}.individual.json"'},
    )


@router.get("/match/{record_id}/audit")
async def download_audit(request: Request, record_id: str, email: str = Depends(require_login)):
    store = MatchStore()
    record = store.get(record_id)
    _owner_or_403(request, record)
    if record.status != "success" or record.audit is None:
        raise HTTPException(status_code=404, detail="該配對執行失敗，無稽核紀錄可下載")
    body = json.dumps(record.audit, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    return Response(
        content=body,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{record_id}.audit.json"'},
    )


# ── Feature 010：PDF 報告匯出 ───────────────────────────────────

def _record_meta_for_pdf(record) -> dict:
    return {
        "id": record.id,
        "created_at": record.created_at,
        "input_file": record.input_file,
        "status": record.status,
        "error": record.error,
    }


@router.get("/match/{record_id}/report.pdf")
async def download_report_pdf(request: Request, record_id: str, email: str = Depends(require_login)):
    store = MatchStore()
    try:
        record = store.get(record_id)
    except MatchRecordNotFound:
        raise HTTPException(status_code=404, detail="找不到該次配對的紀錄")
    _owner_or_403(request, record)

    # 失敗 record 也能出失敗版 PDF；audit 為 None 時樣板會走 failed 分支
    audit_for_pdf = record.audit if record.audit is not None else {
        "assignment": {}, "roster_snapshot": {"roles": [], "targets": []}, "mechanism": "M0",
    }
    try:
        pdf_bytes = render_match_report_pdf(audit_for_pdf, record_meta=_record_meta_for_pdf(record))
    except PdfRenderUnavailable as e:
        return Response(
            content=f"PDF 渲染功能不可用——{str(e)}（請見 README 安裝指引）",
            status_code=503, media_type="text/plain; charset=utf-8",
        )
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{record_id}.report.pdf"'},
    )


def _individual_pdf_response(record, role_id: str):
    if record.status != "success" or record.audit is None:
        raise HTTPException(status_code=404, detail="該次配對執行失敗，無個別查詢資料")
    role_exists = any(
        r["id"] == role_id for r in record.audit.get("roster_snapshot", {}).get("roles", [])
    )
    if not role_exists:
        raise HTTPException(status_code=404, detail="您不在這次配對的清單中")
    try:
        tpl = TemplateRegistry().get(record.template_id)
    except TemplateNotFound:
        tpl = None
    try:
        pdf_bytes = render_match_report_pdf(
            record.audit, record_meta=_record_meta_for_pdf(record),
            role_id=role_id, template=tpl,
        )
    except PdfRenderUnavailable as e:
        return Response(
            content=f"PDF 渲染功能不可用——{str(e)}（請見 README 安裝指引）",
            status_code=503, media_type="text/plain; charset=utf-8",
        )
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{record.id}-{role_id}.report.pdf"'},
    )


@router.get("/match/{record_id}/role/{role_id}/report.pdf")
async def download_individual_report_pdf(request: Request, record_id: str, role_id: str,
                                         email: str = Depends(require_login)):
    store = MatchStore()
    try:
        record = store.get(record_id)
    except MatchRecordNotFound:
        raise HTTPException(status_code=404, detail="找不到該次配對的紀錄")
    _owner_or_403(request, record)
    return _individual_pdf_response(record, role_id)


@router.get("/r/{token}/report.pdf")
async def individual_report_pdf_by_token(request: Request, token: str):
    verified = verify_role_token(token)
    if verified is None:
        raise HTTPException(status_code=404, detail="連結無效")
    record_id, role_id = verified
    store = MatchStore()
    try:
        record = store.get(record_id)
    except MatchRecordNotFound:
        raise HTTPException(status_code=404, detail="找不到該次配對的紀錄")
    return _individual_pdf_response(record, role_id)
