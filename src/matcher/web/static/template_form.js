// Feature 011 template_form.js — vanilla JS for clipboard + form submission (fetch).
// 動態增刪行未實作（樣板用 10 列固定 + 6 規則卡，足夠 MVP）。

function showResult(elemId, ok, summary, errors) {
  const el = document.getElementById(elemId);
  if (ok) {
    el.innerHTML = `<div style="padding:0.8em;background:#e8f5e9;border:1px solid #4caf50;color:#1b5e20">
      ✅ 驗證通過：模板 <code>${summary.id}</code>（${summary.name}）<br>
      角色屬性 ${summary.attribute_count.roles} 個、對象屬性 ${summary.attribute_count.targets} 個、
      規則 ${summary.rule_count} 條、預設對象 ${summary.default_target_count} 個、
      ${summary.has_preferences_schema ? "含" : "不含"}志願結構。
    </div>`;
  } else {
    el.innerHTML = `<div style="padding:0.8em;background:#ffebee;border:1px solid #f44336;color:#b71c1c">
      ❌ 驗證失敗：<ul>${(errors || []).map(e => `<li>${e}</li>`).join("")}</ul>
    </div>`;
  }
}

async function postForm(form) {
  const data = new FormData(form);
  return await fetch(form.action || "/templates/validate", { method: "POST", body: data });
}

async function validateForm() {
  const form = document.getElementById("simple-form");
  const data = new FormData(form);
  const res = await fetch("/templates/validate", { method: "POST", body: data });
  const json = await res.json();
  showResult("result-area", json.ok, json.summary, json.errors);
}

async function saveForm() {
  const form = document.getElementById("simple-form");
  const data = new FormData(form);
  const res = await fetch("/templates/save", { method: "POST", body: data });
  const json = await res.json();
  if (json.ok) {
    document.getElementById("result-area").innerHTML =
      `<div style="padding:0.8em;background:#e8f5e9;border:1px solid #4caf50">
        ✅ 已儲存為 <code>${json.id}</code> v${json.version}；3 秒後跳轉...
      </div>`;
    setTimeout(() => { window.location.href = json.redirect_to; }, 3000);
  } else {
    showResult("result-area", false, null, json.errors);
  }
}

async function validateAdvanced() {
  const form = document.getElementById("advanced-form");
  const data = new FormData(form);
  const res = await fetch("/templates/validate", { method: "POST", body: data });
  const json = await res.json();
  showResult("adv-result-area", json.ok, json.summary, json.errors);
}

async function saveAdvanced() {
  const form = document.getElementById("advanced-form");
  const data = new FormData(form);
  const res = await fetch("/templates/save", { method: "POST", body: data });
  const json = await res.json();
  if (json.ok) {
    document.getElementById("adv-result-area").innerHTML =
      `<div style="padding:0.8em;background:#e8f5e9;border:1px solid #4caf50">
        ✅ 已儲存為 <code>${json.id}</code> v${json.version}；3 秒後跳轉...
      </div>`;
    setTimeout(() => { window.location.href = json.redirect_to; }, 3000);
  } else {
    showResult("adv-result-area", false, null, json.errors);
  }
}

async function copyAiPrompt() {
  const scenario = document.getElementById("ai-scenario").value || "______";
  const role = document.getElementById("ai-role").value || "______";
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

  const prompt = `${guideText}\n\n---\n\n請依上面指南幫我做模板：\n\n` +
    `場景：${scenario}\n` +
    `角色：${role}\n` +
    `對象：${target}\n` +
    `規則：${rules}\n` +
    `是否填志願：${prefs}\n\n` +
    `請產出完整 YAML 並依 §10 self-check 自我驗證。`;

  try {
    await navigator.clipboard.writeText(prompt);
    alert("✅ 完整 Prompt 已複製到剪貼簿");
  } catch (e) {
    alert("複製失敗：" + e);
  }
}

function loadScenario() {
  const sel = document.getElementById("scenario-select");
  if (!sel) return;
  const scenario = sel.value;
  window.location.href = `/templates/new?scenario=${encodeURIComponent(scenario)}`;
}
