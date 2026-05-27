// Feature 011 template_form.js — Alpine.js data + 提交 helpers。

// ── Alpine 元件：表單狀態 ─────────────────────────────────

let _keyCounter = 0;
const _newKey = () => `k_${++_keyCounter}`;

function _parsePrefillRows(prefill, prefix, fields) {
  // 從 prefill dict 中蒐集 `<prefix>_<i>_<field>` → list of dicts
  const rowsByIdx = {};
  Object.keys(prefill || {}).forEach(k => {
    fields.forEach(fld => {
      const suffix = `_${fld}`;
      if (k.startsWith(`${prefix}_`) && k.endsWith(suffix)) {
        const middle = k.slice(prefix.length + 1, k.length - suffix.length);
        if (/^\d+$/.test(middle)) {
          const idx = parseInt(middle, 10);
          if (!rowsByIdx[idx]) rowsByIdx[idx] = {};
          rowsByIdx[idx][fld] = prefill[k];
        }
      }
    });
  });
  return Object.keys(rowsByIdx).sort((a, b) => a - b).map(idx => {
    const row = rowsByIdx[idx];
    // checkbox 欄位轉為 boolean
    if ('required' in row) row.required = !!(row.required && row.required !== 'false');
    row._k = _newKey();
    return row;
  });
}

window.templateAuthor = function () {
  const pf = window._initialPrefill || {};
  const attrFields = ['key', 'type', 'required', 'description', 'aliases'];
  const ruleFields = ['id', 'type', 'field', 'value', 'set', 'participant_field', 'target_field', 'mode', 'custom_description'];
  const targetFields = ['id', 'capacity', 'name', 'topic', 'min_grade'];

  const _attrRowsOrDefault = (prefix) => {
    const rows = _parsePrefillRows(pf, prefix, attrFields);
    return rows.length > 0 ? rows : [
      { key: '', type: 'str', required: true, description: '', aliases: '', _k: _newKey() }
    ];
  };
  const _ruleRowsOrDefault = () => {
    const rows = _parsePrefillRows(pf, 'rule', ruleFields);
    return rows.length > 0 ? rows : [
      { id: 'R001', type: '', field: '', value: '', set: '', participant_field: '', target_field: '', mode: 'auto', custom_description: '', _k: _newKey() }
    ];
  };
  const _targetRowsOrDefault = () => {
    const rows = _parsePrefillRows(pf, 'target', targetFields);
    return rows.length > 0 ? rows : [
      { id: '', capacity: '', name: '', topic: '', min_grade: '', _k: _newKey() }
    ];
  };

  return {
    tab: 'simple',
    participantAttrs: _attrRowsOrDefault('participant_attr'),
    targetAttrs: _attrRowsOrDefault('target_attr'),
    rules: _ruleRowsOrDefault(),
    targets: _targetRowsOrDefault(),

    addParticipantAttr() {
      this.participantAttrs.push({ key: '', type: 'str', required: true, description: '', aliases: '', _k: _newKey() });
    },
    addTargetAttr() {
      this.targetAttrs.push({ key: '', type: 'str', required: true, description: '', aliases: '', _k: _newKey() });
    },
    addRule() {
      const n = this.rules.length + 1;
      this.rules.push({
        id: `R${String(n).padStart(3, '0')}`, type: '',
        field: '', value: '', set: '', participant_field: '', target_field: '', mode: 'auto', custom_description: '',
        _k: _newKey(),
      });
    },
    addTarget() {
      this.targets.push({ id: '', capacity: '', name: '', topic: '', min_grade: '', _k: _newKey() });
    },
  };
};

// ── 結果顯示 ──────────────────────────────────────────────

function showResult(elemId, ok, summary, errors) {
  const el = document.getElementById(elemId);
  if (ok) {
    el.innerHTML = `<div style="padding:0.8em;background:#e8f5e9;border:1px solid #4caf50;color:#1b5e20;border-radius:6px">
      ✅ 檢查通過：範本 <code>${summary.id}</code>（${summary.name}）<br>
      參與者欄位 ${summary.attribute_count.participants} 個、對象欄位 ${summary.attribute_count.targets} 個、
      條件 ${summary.rule_count} 條、${summary.has_preferences_schema ? "有" : "未啟用"}志願功能。
    </div>`;
  } else {
    el.innerHTML = `<div style="padding:0.8em;background:#ffebee;border:1px solid #f44336;color:#b71c1c;border-radius:6px">
      ❌ 檢查失敗：<ul style="margin:0.5em 0 0 1.5em">${(errors || []).map(e => `<li>${e}</li>`).join("")}</ul>
    </div>`;
  }
}

// ── 提交 ──────────────────────────────────────────────────

async function _submit(formId, url, resultElemId) {
  const form = document.getElementById(formId);
  const res = await fetch(url, { method: "POST", body: new FormData(form) });
  return await res.json();
}

async function validateForm() {
  const json = await _submit("simple-form", "/templates/validate", "result-area");
  showResult("result-area", json.ok, json.summary, json.errors);
}

async function saveForm() {
  const json = await _submit("simple-form", "/templates/save", "result-area");
  if (json.ok) {
    document.getElementById("result-area").innerHTML =
      `<div style="padding:0.8em;background:#e8f5e9;border:1px solid #4caf50;border-radius:6px">
        ✅ 已儲存為 <code>${json.id}</code> v${json.version}；3 秒後跳轉...
      </div>`;
    setTimeout(() => { window.location.href = json.redirect_to; }, 3000);
  } else {
    showResult("result-area", false, null, json.errors);
  }
}

async function validateAdvanced() {
  const json = await _submit("advanced-form", "/templates/validate", "adv-result-area");
  showResult("adv-result-area", json.ok, json.summary, json.errors);
}

async function saveAdvanced() {
  const json = await _submit("advanced-form", "/templates/save", "adv-result-area");
  if (json.ok) {
    document.getElementById("adv-result-area").innerHTML =
      `<div style="padding:0.8em;background:#e8f5e9;border:1px solid #4caf50;border-radius:6px">
        ✅ 已儲存為 <code>${json.id}</code> v${json.version}；3 秒後跳轉...
      </div>`;
    setTimeout(() => { window.location.href = json.redirect_to; }, 3000);
  } else {
    showResult("adv-result-area", false, null, json.errors);
  }
}

// ── AI Prompt ────────────────────────────────────────────

async function copyAiPrompt() {
  const scenario = document.getElementById("ai-scenario").value || "______";
  const participant = document.getElementById("ai-participant").value || "______";
  const target = document.getElementById("ai-target").value || "______";
  const rules = document.getElementById("ai-rules").value || "______";
  const prefs = document.getElementById("ai-prefs").value || "______";

  let guideText = "";
  try {
    const res = await fetch("/templates/authoring-guide.txt");
    guideText = await res.text();
  } catch (e) {
    guideText = "（無法載入指南；請手動到 docs/template-authoring-guide.md 複製）";
  }

  const prompt = `${guideText}\n\n---\n\n請依上面指南幫我做範本：\n\n` +
    `情境：${scenario}\n參與者：${participant}\n對象：${target}\n條件：${rules}\n是否填志願：${prefs}\n\n` +
    `請產出完整 YAML 並依 §10 self-check 自我驗證。`;

  try {
    await navigator.clipboard.writeText(prompt);
    alert("✅ 已複製到剪貼簿");
  } catch (e) {
    alert("複製失敗：" + e);
  }
}

function loadScenario() {
  const sel = document.getElementById("scenario-select");
  if (!sel) return;
  window.location.href = `/templates/new?scenario=${encodeURIComponent(sel.value)}`;
}
