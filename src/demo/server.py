"""Minimal localhost-only HTTP server for APP-003-C1 demo (ADR-0022).

Binds only to 127.0.0.1. Uses Python standard library only (http.server).
No authentication, no deployment facilities, no external dependencies.

Routes:
  GET  /             → HTML demo UI
  POST /api/generate → JSON: run pipeline with manual bore_d
  GET  /download/<run_id> → STEP file download (validated)
"""

from __future__ import annotations

import json
import re
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from demo.handler import DemoHandler, CATALOG_TABLE_JS
from demo.product_flow import ProductFlowHandler

# Product live handler (optional — only instantiated if the caller supplies one)
try:
    from integration.product_live_runner import (
        ProductLiveRunState,
        ProductLiveService,
        confirm_product_live_run,
        PRODUCT_LIVE_STATUS_NEEDS_CONFIRMATION,
        PRODUCT_LIVE_STATUS_SUCCEEDED,
        _to_repo_relative_path,
    )
    _PRODUCT_LIVE_AVAILABLE = True
except ImportError:
    _PRODUCT_LIVE_AVAILABLE = False

# ---------------------------------------------------------------------------
# HTML UI (single self-contained page, no external resources)
# ---------------------------------------------------------------------------

def _build_html() -> str:
    catalog_json = json.dumps(CATALOG_TABLE_JS, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>参数化 CAD 本地演示 — 手动参数 / 离线 CAD 生成</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'PingFang SC',system-ui,sans-serif;background:#f5f5f5;color:#222;padding:1.5rem}}
.container{{max-width:900px;margin:0 auto}}
h1{{font-size:1.3rem;font-weight:600;margin-bottom:.3rem}}
.badge-warning{{display:inline-block;background:#fffbe6;border:1px solid #d4b106;
  color:#876800;padding:.2rem .7rem;border-radius:4px;font-size:.8rem;margin-bottom:1rem}}
.card{{background:#fff;border:1px solid #d9d9d9;border-radius:6px;padding:1.2rem;margin-bottom:1rem}}
label{{display:block;font-weight:500;margin-bottom:.4rem;font-size:.9rem}}
select,textarea,input{{width:100%;padding:.5rem .7rem;border:1px solid #ccc;border-radius:4px;
  font-size:.9rem;background:#fafafa}}
textarea{{resize:vertical;height:70px;font-family:inherit}}
.derived-table{{margin-top:.7rem;font-size:.85rem;border-collapse:collapse;width:100%}}
.derived-table th,.derived-table td{{border:1px solid #e0e0e0;padding:.3rem .6rem;text-align:left}}
.derived-table th{{background:#f0f0f0;font-weight:500}}
.source-tag{{display:inline-block;padding:.1rem .4rem;border-radius:3px;font-size:.75rem;margin-left:.3rem}}
.src-user{{background:#e6f4ff;color:#0958d9}}
.src-catalog{{background:#f6ffed;color:#389e0d}}
.src-rule{{background:#fff7e6;color:#d46b08}}
button{{padding:.55rem 1.4rem;background:#1677ff;color:#fff;border:none;border-radius:4px;
  cursor:pointer;font-size:.9rem;margin-top:.8rem}}
button:disabled{{background:#a0c4ff;cursor:not-allowed}}
#status-area{{margin-top:.5rem}}
.status-badge{{display:inline-block;padding:.2rem .8rem;border-radius:4px;font-weight:600;font-size:.85rem}}
.s-success{{background:#f6ffed;border:1px solid #b7eb8f;color:#389e0d}}
.s-blocked,.s-invalid_input{{background:#fff7e6;border:1px solid #ffd591;color:#d46b08}}
.s-failed,.s-error{{background:#fff2f0;border:1px solid #ffccc7;color:#cf1322}}
.s-ask{{background:#e6f4ff;border:1px solid #91caff;color:#0958d9}}
.error-list{{margin-top:.5rem;font-size:.85rem;color:#cf1322}}
.params-table{{border-collapse:collapse;width:100%;font-size:.85rem;margin-top:.5rem}}
.params-table th,.params-table td{{border:1px solid #e0e0e0;padding:.3rem .6rem}}
.params-table th{{background:#f0f0f0;font-weight:500}}
details{{margin-top:.6rem}}
summary{{cursor:pointer;font-size:.85rem;color:#1677ff;user-select:none}}
pre{{background:#f8f8f8;padding:.6rem;border-radius:4px;font-size:.75rem;
  overflow:auto;max-height:300px;white-space:pre-wrap;word-break:break-all}}
.download-btn{{background:#389e0d;margin-top:.5rem}}
.download-btn:hover{{background:#237804}}
.section-title{{font-weight:600;font-size:.9rem;margin-top:.8rem;margin-bottom:.3rem;
  color:#444;border-bottom:1px solid #eee;padding-bottom:.2rem}}
.validation-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));
  gap:.4rem;margin-top:.4rem}}
.val-item{{background:#fafafa;border:1px solid #e0e0e0;border-radius:4px;
  padding:.4rem .6rem;font-size:.8rem}}
.val-label{{color:#666;font-size:.75rem}}
.val-value{{font-weight:600;color:#222}}
.disclaimer{{font-size:.75rem;color:#888;margin-top:1rem;padding:.6rem;
  background:#fafafa;border:1px solid #e8e8e8;border-radius:4px}}
</style>
</head>
<body>
<div class="container">
  <h1>参数化 CAD 本地演示</h1>
  <div class="badge-warning">⚠ 手动参数 / 离线 CAD 生成 | 单族 set_screw_shaft_collar (GN 705) | 仅限本机 | STEP 通过 ≠ 制造认证</div>

  <div class="card">
    <label for="req-text">需求文本（仅作记录，不用于参数抽取）</label>
    <textarea id="req-text" placeholder="例：请按 GN 705 做一个轴环，轴孔孔径 24 mm"></textarea>

    <label for="bore-d" style="margin-top:.8rem">轴孔孔径 bore_d（必填，GN 705 目录值）</label>
    <select id="bore-d">
      <option value="">— 请选择 —</option>
    </select>

    <div id="derived-info" style="display:none">
      <div class="section-title" style="margin-top:.8rem">目录派生参数（只读）</div>
      <table class="derived-table">
        <thead><tr><th>参数</th><th>值 (mm)</th><th>来源</th></tr></thead>
        <tbody id="derived-tbody"></tbody>
      </table>
    </div>

    <button id="gen-btn" onclick="generate()">生成 STEP</button>
  </div>

  <div id="status-area"></div>
</div>

<script>
const CATALOG = {catalog_json};
const catalogByBore = {{}};
CATALOG.forEach(r => {{ catalogByBore[r.bore_d] = r; }});

// Populate bore_d dropdown
const sel = document.getElementById('bore-d');
CATALOG.forEach(r => {{
  const opt = document.createElement('option');
  opt.value = r.bore_d;
  opt.textContent = r.bore_d + ' mm';
  sel.appendChild(opt);
}});

sel.addEventListener('change', function() {{
  const v = parseInt(this.value);
  const info = document.getElementById('derived-info');
  const tbody = document.getElementById('derived-tbody');
  if (!v || !catalogByBore[v]) {{ info.style.display='none'; return; }}
  const row = catalogByBore[v];
  tbody.innerHTML = '';
  const fields = [
    ['outer_d', row.outer_d, '目录派生 (catalog_derived)'],
    ['screw_d', row.screw_d, '目录派生 (catalog_derived)'],
    ['screw_len', row.screw_len, '目录派生 (catalog_derived)'],
    ['width', row.width, '目录派生 (catalog_derived)'],
    ['second_screw', row.second_screw, '规则派生 (rule_derived)'],
  ];
  fields.forEach(([name, val, src]) => {{
    tbody.innerHTML += `<tr><td>${{name}}</td><td>${{val}}</td><td>${{src}}</td></tr>`;
  }});
  info.style.display='block';
}});

function srcClass(src) {{
  if (src==='user_explicit') return 'src-user';
  if (src==='catalog_derived') return 'src-catalog';
  return 'src-rule';
}}
function srcLabel(src) {{
  if (src==='user_explicit') return '用户输入';
  if (src==='catalog_derived') return '目录派生';
  return '规则派生';
}}

// HTML-escape dynamic values before inserting into innerHTML.
// Prevents XSS from pipeline/request data being interpreted as HTML.
function esc(s) {{
  if (s == null) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}}

async function generate() {{
  const reqText = document.getElementById('req-text').value.trim();
  const boreD = document.getElementById('bore-d').value;
  if (!reqText) {{ alert('请填写需求文本'); return; }}
  if (!boreD) {{ alert('请选择 bore_d'); return; }}

  const btn = document.getElementById('gen-btn');
  btn.disabled = true;
  btn.textContent = '生成中…';
  document.getElementById('status-area').innerHTML = '';

  try {{
    const resp = await fetch('/api/generate', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{request_text: reqText, bore_d: parseInt(boreD)}})
    }});
    const data = await resp.json();
    renderResult(data);
  }} catch(e) {{
    const errDiv = document.createElement('div');
    errDiv.className = 'card';
    const errP = document.createElement('p');
    errP.style.color = 'red';
    errP.textContent = '请求失败: ' + (e.message || '');
    errDiv.appendChild(errP);
    document.getElementById('status-area').replaceChildren(errDiv);
  }} finally {{
    btn.disabled = false;
    btn.textContent = '生成 STEP';
  }}
}}

function renderResult(d) {{
  const statusClass = `s-${{esc(d.status)}}`;
  const statusText = {{
    success:'成功', blocked:'阻断', failed:'失败', error:'错误',
    ask:'需要澄清', refuse:'拒绝', invalid_input:'输入无效'
  }}[d.status] || d.status;

  let html = `<div class="card">`;
  html += `<div class="section-title">生成结果</div>`;
  html += `<div>运行 ID：<code>${{esc(d.run_id)}}</code></div>`;
  html += `<div style="margin-top:.4rem">状态：<span class="status-badge ${{statusClass}}">${{esc(statusText)}}</span>`;
  html += ` <span style="font-size:.8rem;color:#666">阶段：${{esc(d.stage)}}</span></div>`;

  if (d.errors && d.errors.length > 0) {{
    html += `<div class="error-list"><b>错误：</b><ul>`;
    d.errors.forEach(e => {{
      html += `<li>[${{esc(e.code || '?')}}] ${{esc(e.message || JSON.stringify(e))}}</li>`;
    }});
    html += `</ul></div>`;
  }}

  if (d.parameters && d.provenance) {{
    html += `<div class="section-title">参数及来源</div>`;
    html += `<table class="params-table"><thead><tr><th>参数</th><th>值</th><th>来源</th></tr></thead><tbody>`;
    for (const [k, v] of Object.entries(d.parameters)) {{
      const src = d.provenance[k] || 'unknown';
      html += `<tr><td>${{esc(k)}}</td><td>${{esc(v)}}</td><td><span class="source-tag ${{esc(srcClass(src))}}">${{esc(srcLabel(src))}}</span></td></tr>`;
    }}
    html += `</tbody></table>`;
  }}

  if (d.validation_summary) {{
    const vs = d.validation_summary;
    html += `<div class="section-title">几何验证摘要</div>`;
    html += `<div class="validation-grid">`;
    const items = [
      ['实体数', vs.solid_count],
      ['有效', vs.is_valid != null ? (vs.is_valid ? '是' : '否') : null],
      ['体积 (mm³)', vs.volume_mm3 != null ? vs.volume_mm3.toFixed(2) : null],
      ['面数', vs.face_count],
      ['边数', vs.edge_count],
      ['顶点数', vs.vertex_count],
      ['STEP 字节', vs.step_bytes],
      ['回读通过', vs.readback_pass != null ? (vs.readback_pass ? '是' : '否') : null],
    ];
    items.forEach(([lbl, val]) => {{
      if (val == null) return;
      html += `<div class="val-item"><div class="val-label">${{esc(lbl)}}</div><div class="val-value">${{esc(val)}}</div></div>`;
    }});
    html += `</div>`;
  }}

  if (d.ir_document) {{
    html += `<details><summary>IR 文档（点击展开）</summary><pre>${{esc(JSON.stringify(d.ir_document, null, 2))}}</pre></details>`;
  }}

  if (d.status === 'success') {{
    html += `<div style="margin-top:.8rem">`;
    html += `<a href="/download/${{esc(d.run_id)}}" download="collar-${{esc(d.bore_d_input)}}mm.step">`;
    html += `<button class="download-btn">⬇ 下载 STEP（${{esc(d.step_bytes)}} 字节）</button></a>`;
    html += `</div>`;
  }}

  html += `<div class="disclaimer">`;
  html += `<b>限制说明：</b> 单族 set_screw_shaft_collar (GN 705) | 固定环境 Python 3.11.18 / CadQuery 2.3.0 | `;
  html += `螺纹采用回转环近似（非精确螺旋） | STEP 验证通过 ≠ 制造认证 | `;
  html += `本演示不调用任何 LLM/模型，参数均由用户手动确认。`;
  html += `</div></div>`;

  document.getElementById('status-area').innerHTML = html;
}}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

_RUN_ID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')

HTML_CONTENT = _build_html()
HTML_BYTES = HTML_CONTENT.encode("utf-8")


# ---------------------------------------------------------------------------
# C3 Product UI HTML (single self-contained page)
# ---------------------------------------------------------------------------

def _build_product_html() -> str:
    return """\
<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>C2 离线自然语言产品流程</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'PingFang SC',system-ui,sans-serif;background:#f5f5f5;color:#222;padding:1rem}
.container{max-width:900px;margin:0 auto}
.banner{background:#fffbe6;border:2px solid #d4b106;color:#614700;padding:.7rem 1rem;
  border-radius:6px;margin-bottom:1rem;font-size:.85rem;font-weight:600}
.card{background:#fff;border:1px solid #d9d9d9;border-radius:6px;padding:1.2rem;margin-bottom:1rem}
h2{font-size:1rem;font-weight:600;margin-bottom:.8rem;color:#333;
  border-bottom:1px solid #eee;padding-bottom:.4rem}
label{display:block;font-weight:500;margin-bottom:.3rem;font-size:.85rem}
select,textarea,input[type=text],input[type=number]{width:100%;padding:.45rem .6rem;
  border:1px solid #ccc;border-radius:4px;font-size:.85rem;background:#fafafa}
textarea{resize:vertical;height:65px;font-family:inherit}
button{padding:.5rem 1.2rem;background:#1677ff;color:#fff;border:none;border-radius:4px;
  cursor:pointer;font-size:.85rem;margin-top:.6rem}
button:disabled{background:#a0c4ff;cursor:not-allowed}
.btn-green{background:#389e0d}
.btn-green:hover{background:#237804}
.btn-reset{background:#8c8c8c}
.badge{display:inline-block;padding:.15rem .6rem;border-radius:4px;font-size:.78rem;font-weight:600}
.s-needs_confirmation{background:#e6f4ff;border:1px solid #91caff;color:#0958d9}
.s-succeeded{background:#f6ffed;border:1px solid #b7eb8f;color:#389e0d}
.s-blocked{background:#fff7e6;border:1px solid #ffd591;color:#d46b08}
.s-failed{background:#fff2f0;border:1px solid #ffccc7;color:#cf1322}
.s-request_received,.s-extraction_pending,.s-constructing{background:#f0f0ff;border:1px solid #aab;color:#333}
table.info-table{border-collapse:collapse;width:100%;font-size:.82rem;margin-top:.4rem}
table.info-table th,table.info-table td{border:1px solid #e0e0e0;padding:.3rem .6rem;text-align:left}
table.info-table th{background:#f5f5f5;font-weight:500}
.src-user{background:#e6f4ff;color:#0958d9;padding:.1rem .4rem;border-radius:3px;font-size:.75rem}
.src-catalog{background:#f6ffed;color:#389e0d;padding:.1rem .4rem;border-radius:3px;font-size:.75rem}
.src-rule{background:#fff7e6;color:#d46b08;padding:.1rem .4rem;border-radius:3px;font-size:.75rem}
.error-list{color:#cf1322;font-size:.82rem;margin-top:.4rem}
.error-list li{margin-left:1rem}
details{margin-top:.5rem}
summary{cursor:pointer;font-size:.82rem;color:#1677ff;user-select:none}
pre{background:#f8f8f8;padding:.5rem;border-radius:4px;font-size:.72rem;
  overflow:auto;max-height:280px;white-space:pre-wrap;word-break:break-all}
.val-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));
  gap:.3rem;margin-top:.4rem}
.val-item{background:#fafafa;border:1px solid #e0e0e0;border-radius:4px;padding:.3rem .5rem;font-size:.78rem}
.val-label{color:#666;font-size:.72rem}
.val-value{font-weight:600}
.disclaimer{font-size:.73rem;color:#888;margin-top:1rem;padding:.5rem;
  background:#fafafa;border:1px solid #e0e0e0;border-radius:4px}
#step2,#step3{display:none}
.fixture-note{font-size:.8rem;color:#666;margin-top:.4rem;background:#fffbe6;
  padding:.4rem .6rem;border-radius:4px;border:1px solid #ffe58f}
</style>
</head>
<body>
<div class="container">
  <div class="banner">
    ⚠ 离线 synthetic fixture 模式 — 非真实模型抽取 | 单族 set_screw_shaft_collar (GN 705) |
    STEP 通过 ≠ 制造认证 | 不调用任何 LLM/模型
  </div>

  <div id="step1" class="card">
    <h2>步骤 1：输入需求并选择 Fixture</h2>
    <label for="req-text">需求文本（仅作记录，不用于参数抽取）</label>
    <textarea id="req-text" placeholder="例：请按 GN 705 做一个轴环，轴孔孔径 24 mm"></textarea>
    <label for="fixture-sel" style="margin-top:.6rem">选择离线 Envelope Fixture</label>
    <select id="fixture-sel">
      <option value="">— 加载中… —</option>
    </select>
    <div class="fixture-note">
      需求文本只作为产品记录，参数抽取结果来自所选 fixture，非模型解析。
    </div>
    <button id="create-btn" onclick="createRun()">创建产品运行</button>
  </div>

  <div id="step2" class="card">
    <h2>步骤 2：确认或补充参数</h2>
    <div id="run-info"></div>
    <div id="confirm-form"></div>
  </div>

  <div id="step3" class="card">
    <h2>步骤 3：构造结果</h2>
    <div id="result-area"></div>
  </div>

  <div class="disclaimer">
    本演示仅用于验证 C2 离线产品流程正确性。fixture 来自 synthetic v5 envelope，不构成真实自然语言理解证据。
    固定环境 Python 3.11.18 / CadQuery 2.3.0。保留单族、螺纹近似及 "STEP 通过 ≠ 制造认证" 限制。
  </div>
</div>

<script>
let currentRunId = null;
let currentRevision = 0;
let currentStatus = null;

function esc(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;')
    .replace(/'/g,'&#39;');
}

function srcClass(src) {
  if (src==='user_explicit' || src==='user_input') return 'src-user';
  if (src==='catalog_derived') return 'src-catalog';
  return 'src-rule';
}
function srcLabel(src) {
  if (src==='user_explicit' || src==='user_input') return '用户输入';
  if (src==='catalog_derived') return '目录派生';
  return '规则派生';
}
function statusBadge(st) {
  return `<span class="badge s-${esc(st)}">${esc(st)}</span>`;
}

async function loadFixtures() {
  try {
    const r = await fetch('/api/product/fixtures');
    const d = await r.json();
    const sel = document.getElementById('fixture-sel');
    sel.innerHTML = '<option value="">— 请选择 —</option>';
    (d.fixtures||[]).forEach(f => {
      const o = document.createElement('option');
      o.value = f.fixture_id;
      o.textContent = f.label || f.fixture_id;
      sel.appendChild(o);
    });
  } catch(e) {
    document.getElementById('fixture-sel').innerHTML =
      '<option value="">— 加载失败 —</option>';
  }
}

async function createRun() {
  const reqText = document.getElementById('req-text').value.trim();
  const fixtureId = document.getElementById('fixture-sel').value;
  if (!reqText) { alert('请填写需求文本'); return; }
  if (!fixtureId) { alert('请选择 fixture'); return; }
  const btn = document.getElementById('create-btn');
  btn.disabled = true; btn.textContent = '创建中…';
  try {
    const r = await fetch('/api/product/create', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({request_text: reqText, fixture_id: fixtureId})
    });
    const d = await r.json();
    currentRunId = d.run_id;
    currentRevision = (d.confirmation && d.confirmation.revision != null) ? d.confirmation.revision : 0;
    currentStatus = d.product_status;
    renderConfirmSection(d);
    document.getElementById('step2').style.display = 'block';
    document.getElementById('step3').style.display = 'none';
  } catch(e) {
    alert('请求失败: ' + esc(e.message));
  } finally {
    btn.disabled = false; btn.textContent = '创建产品运行';
  }
}

function renderConfirmSection(d) {
  const info = document.getElementById('run-info');
  let html = `<div>运行 ID: <code>${esc(d.run_id)}</code></div>`;
  html += `<div style="margin:.4rem 0">产品状态: ${statusBadge(d.product_status)} 决策: <b>${esc(d.decision)}</b></div>`;
  if (d.extraction_source) html += `<div style="font-size:.8rem;color:#666">来源: ${esc(d.extraction_source)} / fixture: ${esc(d.envelope_fixture_label)}</div>`;
  if (d.request_text) html += `<div style="margin-top:.4rem;padding:.4rem .6rem;background:#f5f5f5;border-left:3px solid #aaa;font-size:.85rem"><b>原始需求文本（仅作记录）:</b><br>${esc(d.request_text)}</div>`;

  if (d.extracted_parameters && Object.keys(d.extracted_parameters).length) {
    html += '<div style="margin-top:.5rem"><b>抽取参数（来自 fixture）:</b></div>';
    html += '<table class="info-table"><thead><tr><th>参数</th><th>值</th></tr></thead><tbody>';
    for (const [k,v] of Object.entries(d.extracted_parameters)) {
      html += `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`;
    }
    html += '</tbody></table>';
  }
  if (d.catalog_derived_parameters && Object.keys(d.catalog_derived_parameters).length) {
    html += '<div style="margin-top:.4rem"><b>目录派生参数（只读）:</b></div>';
    html += '<table class="info-table"><thead><tr><th>参数</th><th>值</th><th>来源</th></tr></thead><tbody>';
    for (const [k,v] of Object.entries(d.catalog_derived_parameters)) {
      html += `<tr><td>${esc(k)}</td><td>${esc(v)}</td><td><span class="src-catalog">目录派生</span></td></tr>`;
    }
    html += '</tbody></table>';
  }
  if (d.rule_derived_parameters && Object.keys(d.rule_derived_parameters).length) {
    html += '<div style="margin-top:.4rem"><b>规则派生参数（只读）:</b></div>';
    html += '<table class="info-table"><thead><tr><th>参数</th><th>值</th><th>来源</th></tr></thead><tbody>';
    for (const [k,v] of Object.entries(d.rule_derived_parameters)) {
      html += `<tr><td>${esc(k)}</td><td>${esc(v)}</td><td><span class="src-rule">规则派生</span></td></tr>`;
    }
    html += '</tbody></table>';
  }
  if (d.missing_fields && d.missing_fields.length) {
    html += `<div class="error-list" style="margin-top:.4rem"><b>缺少参数:</b> ${d.missing_fields.map(f=>esc(f)).join(', ')}</div>`;
  }
  if (d.questions && d.questions.length) {
    html += '<div style="margin-top:.4rem"><b>问题:</b><ul class="error-list">';
    d.questions.forEach(q => { html += `<li>${esc(q)}</li>`; });
    html += '</ul></div>';
  }
  if (d.conflicts && d.conflicts.length) {
    html += '<div style="margin-top:.4rem"><b style="color:#cf1322">冲突:</b><ul class="error-list">';
    d.conflicts.forEach(c => { html += `<li>[${esc(c.code||'?')}] ${esc(c.message)}</li>`; });
    html += '</ul></div>';
  }
  if (d.unsupported_requests && d.unsupported_requests.length) {
    html += `<div class="error-list" style="margin-top:.4rem"><b>不支持的请求:</b> ${d.unsupported_requests.map(esc).join(', ')}</div>`;
  }
  if (d.errors && d.errors.length) {
    html += '<div style="margin-top:.4rem"><b style="color:#cf1322">错误:</b><ul class="error-list">';
    d.errors.forEach(e => { html += `<li>[${esc(e.code||'?')}] ${esc(e.message)}</li>`; });
    html += '</ul></div>';
  }
  info.innerHTML = html;

  const form = document.getElementById('confirm-form');
  if (d.product_status === 'needs_confirmation') {
    // Check if there are unanswered questions that cannot be resolved by a parameter patch.
    // If decision=ask and questions exist but no missing_fields correspond to them,
    // we show the questions but do NOT show a confirm button.
    const hasUnanswerableQuestions = d.decision === 'ask' && (d.questions||[]).length > 0
      && (d.missing_fields||[]).length === 0;
    const needsBore = (d.missing_fields||[]).includes('bore_d');

    if (hasUnanswerableQuestions) {
      let fhtml = '<div style="margin-top:.5rem;color:#d46b08;font-weight:600">⚠ 此运行有未回答的追问，当前界面无对应输入字段，无法确认或构造 STEP。</div>';
      fhtml += '<div style="margin-top:.3rem"><b>待回答问题:</b><ul class="error-list">';
      (d.questions||[]).forEach(q => { fhtml += `<li>${esc(q)}</li>`; });
      fhtml += '</ul></div>';
      fhtml += '<div style="font-size:.8rem;color:#666">如需继续，请重新创建运行并选择适当的 fixture。</div>';
      form.innerHTML = fhtml;
    } else {
      let fhtml = '<div style="margin-top:.7rem"><b>用户参数补充:</b></div>';
      fhtml += `<label for="patch-bore-d" style="margin-top:.5rem">bore_d 轴孔孔径 (mm)${needsBore?' <span style=color:red>*必填</span>':''}</label>`;
      fhtml += `<input type="number" id="patch-bore-d" placeholder="留空则使用 fixture 中的值" style="max-width:200px">`;
      fhtml += `<div style="margin-top:.7rem">`;
      fhtml += `<button class="btn-green" onclick="confirmRun()">确认并生成 STEP</button>`;
      fhtml += `</div>`;
      form.innerHTML = fhtml;
    }
  } else if (d.product_status === 'blocked') {
    form.innerHTML = '<div style="margin-top:.5rem;color:#d46b08;font-weight:600">⚠ 此运行已阻断，无法继续构造 STEP。请重新创建运行。</div>';
  } else {
    form.innerHTML = '';
  }
}

async function confirmRun() {
  const patch = {};
  const boreVal = document.getElementById('patch-bore-d').value.trim();
  if (boreVal !== '') {
    const parsed = parseInt(boreVal, 10);
    if (!isNaN(parsed)) patch.bore_d = parsed;
  }
  const btn = event.target;
  btn.disabled = true; btn.textContent = '生成中…';
  try {
    const r = await fetch(`/api/product/confirm/${esc(currentRunId)}`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({confirmation_revision: currentRevision, confirmed: true, patch})
    });
    const d = await r.json();
    currentStatus = d.product_status;
    renderResultSection(d);
    document.getElementById('step3').style.display = 'block';
  } catch(e) {
    alert('确认失败: ' + esc(e.message));
  } finally {
    btn.disabled = false; btn.textContent = '确认并生成 STEP';
  }
}

function renderResultSection(d) {
  const area = document.getElementById('result-area');
  let html = `<div>Child 运行 ID: <code>${esc(d.run_id)}</code> (parent: <code>${esc(d.parent_run_id)}</code>)</div>`;
  html += `<div style="margin:.4rem 0">产品状态: ${statusBadge(d.product_status)}`;
  if (d.pipeline_status) html += ` pipeline: <b>${esc(d.pipeline_status)}</b>`;
  if (d.pipeline_stage) html += ` / <b>${esc(d.pipeline_stage)}</b>`;
  html += `</div>`;

  if (d.validation_summary) {
    const vs = d.validation_summary;
    html += '<div style="margin-top:.5rem"><b>几何验证摘要:</b></div><div class="val-grid">';
    const items = [
      ['实体数', vs.solid_count], ['有效', vs.is_valid!=null?(vs.is_valid?'是':'否'):null],
      ['体积(mm³)', vs.volume_mm3!=null?vs.volume_mm3.toFixed(2):null],
      ['面数', vs.face_count], ['边数', vs.edge_count], ['顶点数', vs.vertex_count],
      ['STEP字节', vs.step_bytes],
      ['回读通过', vs.readback_pass!=null?(vs.readback_pass?'是':'否'):null]
    ];
    items.forEach(([lbl,val]) => {
      if (val==null) return;
      html += `<div class="val-item"><div class="val-label">${esc(lbl)}</div><div class="val-value">${esc(val)}</div></div>`;
    });
    html += '</div>';
  }
  if (d.errors && d.errors.length) {
    html += '<div style="margin-top:.5rem"><b style="color:#cf1322">错误:</b><ul class="error-list">';
    d.errors.forEach(e => { html += `<li>[${esc(e.code||e.stage||'?')}] ${esc(e.message||JSON.stringify(e))}</li>`; });
    html += '</ul></div>';
  }
  if (d.ir_document) {
    html += `<details><summary>IR 文档（点击展开）</summary><pre>${esc(JSON.stringify(d.ir_document,null,2))}</pre></details>`;
  }
  if (d.schema_result) {
    html += `<details><summary>Schema 结果</summary><pre>${esc(JSON.stringify(d.schema_result,null,2))}</pre></details>`;
  }
  if (d.product_status === 'succeeded') {
    html += `<div style="margin-top:.8rem">`;
    if (d.step_sha256) {
      html += `<div style="margin-bottom:.5rem"><b>STEP SHA-256:</b><br><code style="font-size:.75rem;word-break:break-all">${esc(d.step_sha256)}</code></div>`;
    }
    html += `<a href="/product-download/${esc(d.run_id)}" download="product-${esc(d.run_id).substring(0,8)}.step">`;
    html += `<button class="btn-green">⬇ 下载 STEP (${esc(d.step_bytes)} 字节)</button></a>`;
    html += `</div>`;
  }
  html += `<div style="margin-top:.7rem"><button class="btn-reset" onclick="resetAll()">新建另一个需求</button></div>`;
  area.innerHTML = html;
}

function resetAll() {
  currentRunId = null; currentRevision = 0; currentStatus = null;
  document.getElementById('step2').style.display = 'none';
  document.getElementById('step3').style.display = 'none';
  document.getElementById('run-info').innerHTML = '';
  document.getElementById('confirm-form').innerHTML = '';
  document.getElementById('result-area').innerHTML = '';
  document.getElementById('req-text').value = '';
  document.getElementById('fixture-sel').value = '';
}

loadFixtures();
</script>
</body>
</html>"""


PRODUCT_HTML_CONTENT = _build_product_html()
PRODUCT_HTML_BYTES = PRODUCT_HTML_CONTENT.encode("utf-8")


# ---------------------------------------------------------------------------
# Product Live UI HTML (APP-003-LIVE-UI)
# ---------------------------------------------------------------------------

def _build_product_live_html() -> str:
    return """\
<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Product Live 受控抽取确认</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'PingFang SC',system-ui,sans-serif;background:#f5f5f5;color:#222;padding:1rem}
.container{max-width:920px;margin:0 auto}
.banner{background:#fffbe6;border:2px solid #d4b106;color:#614700;padding:.7rem 1rem;
  border-radius:6px;margin-bottom:1rem;font-size:.85rem;font-weight:600}
.card{background:#fff;border:1px solid #d9d9d9;border-radius:6px;padding:1.2rem;margin-bottom:1rem}
h2{font-size:1rem;font-weight:600;margin-bottom:.8rem;color:#333;
  border-bottom:1px solid #eee;padding-bottom:.4rem}
label{display:block;font-weight:500;margin-bottom:.3rem;font-size:.85rem}
select,textarea,input[type=text],input[type=number]{width:100%;padding:.45rem .6rem;
  border:1px solid #ccc;border-radius:4px;font-size:.85rem;background:#fafafa}
textarea{resize:vertical;height:65px;font-family:inherit}
button{padding:.5rem 1.2rem;background:#1677ff;color:#fff;border:none;border-radius:4px;
  cursor:pointer;font-size:.85rem;margin-top:.6rem}
button:disabled{background:#a0c4ff;cursor:not-allowed}
.btn-green{background:#389e0d}
.btn-green:hover{background:#237804}
.btn-reset{background:#8c8c8c}
.badge{display:inline-block;padding:.15rem .6rem;border-radius:4px;font-size:.78rem;font-weight:600}
.s-needs_confirmation{background:#e6f4ff;border:1px solid #91caff;color:#0958d9}
.s-succeeded{background:#f6ffed;border:1px solid #b7eb8f;color:#389e0d}
.s-blocked{background:#fff7e6;border:1px solid #ffd591;color:#d46b08}
.s-failed{background:#fff2f0;border:1px solid #ffccc7;color:#cf1322}
.s-disabled{background:#f0f0f0;border:1px solid #d9d9d9;color:#888}
table.info-table{border-collapse:collapse;width:100%;font-size:.82rem;margin-top:.4rem}
table.info-table th,table.info-table td{border:1px solid #e0e0e0;padding:.3rem .6rem;text-align:left}
table.info-table th{background:#f5f5f5;font-weight:500}
.error-list{color:#cf1322;font-size:.82rem;margin-top:.4rem}
.error-list li{margin-left:1rem}
details{margin-top:.5rem}
summary{cursor:pointer;font-size:.82rem;color:#1677ff;user-select:none}
pre{background:#f8f8f8;padding:.5rem;border-radius:4px;font-size:.72rem;
  overflow:auto;max-height:280px;white-space:pre-wrap;word-break:break-all}
.val-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));
  gap:.3rem;margin-top:.4rem}
.val-item{background:#fafafa;border:1px solid #e0e0e0;border-radius:4px;padding:.3rem .5rem;font-size:.78rem}
.val-label{color:#666;font-size:.72rem}
.val-value{font-weight:600}
.disclaimer{font-size:.73rem;color:#888;margin-top:1rem;padding:.5rem;
  background:#fafafa;border:1px solid #e0e0e0;border-radius:4px}
#step2,#step3{display:none}
.note{font-size:.8rem;color:#666;margin-top:.4rem;background:#fffbe6;
  padding:.4rem .6rem;border-radius:4px;border:1px solid #ffe58f}
.status-row{margin:.4rem 0}
.param-patch{margin-top:.5rem}
.param-patch label{font-size:.82rem}
.changed{color:#0958d9;font-weight:600;font-size:.78rem}
</style>
</head>
<body>
<div class="container">
  <div class="banner">
    ⚠ 受控 Product Live UI — offline/mock transport 或 synthetic envelope | 非真实模型效果 |
    单族 set_screw_shaft_collar (GN 705) | STEP 通过 ≠ 制造认证 | 不接触 API key 或 raw response
  </div>

  <div id="step1" class="card">
    <h2>步骤 1：输入需求并选择受控输入</h2>
    <label for="live-req-text">需求文本（提交到服务端受控抽取 API）</label>
    <textarea id="live-req-text" placeholder="例：请按 GN 705 做一个轴环，轴孔直径 24 mm。"></textarea>
    <label for="input-sel" style="margin-top:.6rem">选择受控输入 ID</label>
    <select id="input-sel">
      <option value="">— 请选择 —</option>
    </select>
    <div class="note">
      服务端持有所有 transport 和 authorization；浏览器只提交 request_text 和 input_id，
      不提交模型响应、evaluator labels 或 CAD 结果。
    </div>
    <button id="live-create-btn" onclick="liveCreate()">发起受控抽取</button>
  </div>

  <div id="step2" class="card">
    <h2>步骤 2：确认或补充参数</h2>
    <div id="live-run-info"></div>
    <div id="live-confirm-form"></div>
  </div>

  <div id="step3" class="card">
    <h2>步骤 3：构造结果</h2>
    <div id="live-result-area"></div>
  </div>

  <div class="disclaimer">
    本页面为受控 product live 抽取确认界面。测试使用 offline/mock transport 或 synthetic envelope，
    不构成真实模型理解证据。固定环境 Python 3.11.18 / CadQuery 2.3.0。
    保留单族、螺纹近似及 "STEP 通过 ≠ 制造认证" 限制。
  </div>
</div>

<script>
let liveRunId = null;
let liveInputId = null;

function esc(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;')
    .replace(/'/g,'&#39;');
}

function statusBadge(st) {
  return `<span class="badge s-${esc(st)}">${esc(st)}</span>`;
}

async function loadInputs() {
  try {
    const r = await fetch('/api/product-live/inputs');
    if (!r.ok) {
      document.getElementById('input-sel').innerHTML = '<option value="">— 加载失败 —</option>';
      return;
    }
    const d = await r.json();
    const sel = document.getElementById('input-sel');
    sel.innerHTML = '<option value="">— 请选择 —</option>';
    (d.inputs||[]).forEach(item => {
      const o = document.createElement('option');
      o.value = item.input_id;
      o.textContent = item.input_id + (item.label ? ' — ' + item.label : '');
      sel.appendChild(o);
    });
  } catch(e) {
    document.getElementById('input-sel').innerHTML = '<option value="">— 加载失败 —</option>';
  }
}

async function liveCreate() {
  const reqText = document.getElementById('live-req-text').value.trim();
  const inputId = document.getElementById('input-sel').value;
  if (!reqText) { alert('请填写需求文本'); return; }
  if (!inputId) { alert('请选择输入 ID'); return; }
  const btn = document.getElementById('live-create-btn');
  btn.disabled = true; btn.textContent = '抽取中…';
  liveInputId = inputId;
  try {
    const r = await fetch('/api/product-live/create', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({request_text: reqText, input_id: inputId})
    });
    const d = await r.json();
    if (d.error) {
      // PRODUCT_LIVE_DISABLED or other error
      document.getElementById('step2').style.display = 'block';
      document.getElementById('live-run-info').innerHTML =
        `<div class="status-row">状态: ${statusBadge('disabled')}</div>` +
        `<div class="error-list">${esc(d.error.message||'Service not configured')}</div>`;
      document.getElementById('live-confirm-form').innerHTML = '';
      document.getElementById('step3').style.display = 'none';
      return;
    }
    liveRunId = d.logical_run_id;
    renderLiveConfirmSection(d);
    document.getElementById('step2').style.display = 'block';
    document.getElementById('step3').style.display = 'none';
  } catch(e) {
    alert('请求失败: ' + esc(e.message));
  } finally {
    btn.disabled = false; btn.textContent = '发起受控抽取';
  }
}

function renderLiveConfirmSection(d) {
  const info = document.getElementById('live-run-info');
  let html = `<div>逻辑运行 ID: <code>${esc(d.logical_run_id)}</code></div>`;
  html += `<div class="status-row">产品状态: ${statusBadge(d.product_status)}`;
  html += ` 决策: <b>${esc(d.decision)}</b></div>`;
  if (d.request_text) html += `<div style="margin-top:.4rem;padding:.4rem .6rem;background:#f5f5f5;border-left:3px solid #aaa;font-size:.85rem"><b>原始需求文本:</b><br>${esc(d.request_text)}</div>`;
  if (d.prompt_version) html += `<div style="font-size:.78rem;color:#666;margin-top:.3rem">Prompt: ${esc(d.prompt_version)} | Contract: ${esc(d.contract_version)}</div>`;

  if (d.extracted_parameters && Object.keys(d.extracted_parameters).length) {
    html += '<div style="margin-top:.5rem"><b>抽取参数:</b></div>';
    html += '<table class="info-table"><thead><tr><th>参数</th><th>值</th></tr></thead><tbody>';
    for (const [k,v] of Object.entries(d.extracted_parameters)) {
      html += `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`;
    }
    html += '</tbody></table>';
  }
  if (d.missing_fields && d.missing_fields.length) {
    html += `<div class="error-list" style="margin-top:.4rem"><b>缺少参数:</b> ${d.missing_fields.map(f=>esc(f)).join(', ')}</div>`;
  }
  if (d.questions && d.questions.length) {
    html += '<div style="margin-top:.4rem"><b>问题:</b><ul class="error-list">';
    d.questions.forEach(q => { html += `<li>${esc(q)}</li>`; });
    html += '</ul></div>';
  }
  if (d.conflicts && d.conflicts.length) {
    html += '<div style="margin-top:.4rem"><b style="color:#cf1322">冲突:</b><ul class="error-list">';
    d.conflicts.forEach(c => { html += `<li>[${esc(c.code||'?')}] ${esc(c.message)}</li>`; });
    html += '</ul></div>';
  }
  if (d.unsupported_requests && d.unsupported_requests.length) {
    html += `<div class="error-list" style="margin-top:.4rem"><b>不支持的请求:</b> ${d.unsupported_requests.map(esc).join(', ')}</div>`;
  }
  if (d.errors && d.errors.length) {
    html += '<div style="margin-top:.4rem"><b style="color:#cf1322">错误:</b><ul class="error-list">';
    d.errors.forEach(e => { html += `<li>[${esc(e.code||'?')}] ${esc(e.message||JSON.stringify(e))}</li>`; });
    html += '</ul></div>';
  }
  info.innerHTML = html;

  const form = document.getElementById('live-confirm-form');
  if (d.product_status === 'needs_confirmation') {
    const needsBore = (d.missing_fields||[]).includes('bore_d');
    let fhtml = '<div class="param-patch"><b>用户参数补充:</b></div>';
    fhtml += `<label for="live-patch-bore-d" style="margin-top:.5rem">bore_d 轴孔孔径 (mm)${needsBore?' <span style=color:red>*必填</span>':''}</label>`;
    fhtml += `<input type="number" id="live-patch-bore-d" placeholder="留空则使用抽取值" style="max-width:200px">`;
    fhtml += `<div style="margin-top:.7rem">`;
    fhtml += `<button class="btn-green" onclick="liveConfirm()">确认并生成 STEP</button>`;
    fhtml += `</div>`;
    form.innerHTML = fhtml;
  } else if (d.product_status === 'blocked') {
    form.innerHTML = '<div style="margin-top:.5rem;color:#d46b08;font-weight:600">⚠ 此运行已阻断，无法继续构造。请重新创建运行。</div>';
  } else if (d.product_status === 'failed') {
    form.innerHTML = '<div style="margin-top:.5rem;color:#cf1322;font-weight:600">⚠ 此运行已失败，无法继续构造。请重新创建运行。</div>';
  } else {
    form.innerHTML = '';
  }
}

async function liveConfirm() {
  if (!liveRunId) { alert('无有效 run ID'); return; }
  const patch = {};
  const boreVal = document.getElementById('live-patch-bore-d').value.trim();
  if (boreVal !== '') {
    const parsed = parseInt(boreVal, 10);
    if (!isNaN(parsed)) patch.bore_d = parsed;
  }
  const btn = event.target;
  btn.disabled = true; btn.textContent = '生成中…';
  try {
    const r = await fetch(`/api/product-live/confirm/${esc(liveRunId)}`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({confirmed: true, patch})
    });
    const d = await r.json();
    renderLiveResultSection(d);
    document.getElementById('step3').style.display = 'block';
  } catch(e) {
    alert('确认失败: ' + esc(e.message));
  } finally {
    btn.disabled = false; btn.textContent = '确认并生成 STEP';
  }
}

function renderLiveResultSection(d) {
  const area = document.getElementById('live-result-area');
  let html = `<div>运行 ID: <code>${esc(d.logical_run_id)}</code></div>`;
  html += `<div class="status-row">产品状态: ${statusBadge(d.product_status)}`;
  if (d.pipeline_status) html += ` pipeline: <b>${esc(d.pipeline_status)}</b>`;
  if (d.pipeline_stage) html += ` / <b>${esc(d.pipeline_stage)}</b>`;
  html += `</div>`;

  if (d.ir_index && d.ir_index.step_sha256) {
    html += `<div style="margin-top:.5rem"><b>STEP SHA-256:</b><br><code style="font-size:.75rem;word-break:break-all">${esc(d.ir_index.step_sha256)}</code></div>`;
  }
  if (d.ir_index && d.ir_index.step_bytes) {
    html += `<div style="font-size:.8rem;color:#666;margin-top:.3rem">STEP 字节: ${esc(d.ir_index.step_bytes)}</div>`;
  }

  if (d.errors && d.errors.length) {
    html += '<div style="margin-top:.5rem"><b style="color:#cf1322">错误:</b><ul class="error-list">';
    d.errors.forEach(e => { html += `<li>[${esc(e.code||e.stage||'?')}] ${esc(e.message||JSON.stringify(e))}</li>`; });
    html += '</ul></div>';
  }

  if (d.product_status === 'succeeded') {
    html += `<div style="margin-top:.8rem">`;
    html += `<a href="/product-live-download/${esc(d.logical_run_id)}" download="product-live-${esc(d.logical_run_id).substring(0,16)}.step">`;
    html += `<button class="btn-green">⬇ 下载 STEP</button></a>`;
    html += `</div>`;
  } else if (d.product_status === 'failed' || d.product_status === 'blocked') {
    html += `<div style="margin-top:.5rem;color:#cf1322;font-size:.85rem">此运行不产生可下载的 STEP 文件。</div>`;
  }

  html += `<div style="margin-top:.7rem"><button class="btn-reset" onclick="liveReset()">新建另一个需求</button></div>`;
  area.innerHTML = html;
}

function liveReset() {
  liveRunId = null; liveInputId = null;
  document.getElementById('step2').style.display = 'none';
  document.getElementById('step3').style.display = 'none';
  document.getElementById('live-run-info').innerHTML = '';
  document.getElementById('live-confirm-form').innerHTML = '';
  document.getElementById('live-result-area').innerHTML = '';
  document.getElementById('live-req-text').value = '';
  document.getElementById('input-sel').value = '';
}

loadInputs();
</script>
</body>
</html>"""


PRODUCT_LIVE_HTML_CONTENT = _build_product_live_html()
PRODUCT_LIVE_HTML_BYTES = PRODUCT_LIVE_HTML_CONTENT.encode("utf-8")


def _get_product_live_step_bytes_secure(state: "Any") -> bytes | None:
    """6-layer security check for product live STEP download.

    Mirrors the security logic in ProductFlowHandler.get_product_step_bytes_secure.
    Only returns bytes when all checks pass:
      1. product_status == succeeded
      2. step_path is set (internal field)
      3. pipeline_run_dir is set
      4. step_sha256 is set
      5. STEP path is inside the run's cad_output/ directory (containment)
      6. File is not a symlink, exists, is non-empty, and hash matches
    """
    import hashlib
    if state.product_status != PRODUCT_LIVE_STATUS_SUCCEEDED:
        return None
    step_path_str = state.step_path
    run_dir_str = state.pipeline_run_dir
    expected_sha256 = getattr(state, "ir_index", None)
    if isinstance(expected_sha256, dict):
        expected_sha256 = expected_sha256.get("step_sha256")
    if not step_path_str or not run_dir_str or not expected_sha256:
        return None
    step_path = Path(step_path_str)
    expected_prefix = Path(run_dir_str) / "cad_output"
    try:
        canonical_step = step_path.resolve()
        canonical_prefix = expected_prefix.resolve()
        canonical_step.relative_to(canonical_prefix)
    except (ValueError, OSError):
        return None
    if canonical_step.is_symlink():
        return None
    if not canonical_step.is_file() or canonical_step.stat().st_size == 0:
        return None
    content = canonical_step.read_bytes()
    if hashlib.sha256(content).hexdigest() != expected_sha256:
        return None
    return content


def _sanitize_state_for_http(state: "Any") -> dict:
    """Convert a ProductLiveRunState to a safe HTTP response dict.

    - Removes internal absolute step_path.
    - Normalises all file-system paths to repo-relative strings.
    - Strips raw body content, secrets, and evaluator labels from
      raw_retention_meta (keeps only retained, path, body_sha256).
    - pipeline_run_dir is normalised to repo-relative (or None if outside repo).
    """
    if not _PRODUCT_LIVE_AVAILABLE:
        return {}
    resp = state.as_dict()
    # Remove absolute internal step path — downloads happen via /product-live-download/
    resp.pop("step_path", None)
    # Normalise pipeline_run_dir
    if resp.get("pipeline_run_dir") and not _PRODUCT_LIVE_AVAILABLE:
        resp["pipeline_run_dir"] = None
    elif resp.get("pipeline_run_dir") and _PRODUCT_LIVE_AVAILABLE:
        resp["pipeline_run_dir"] = _to_repo_relative_path(resp["pipeline_run_dir"])
    # Normalize the top-level raw retention path as well.  It is evidence
    # metadata only; never expose an absolute or traversal path to the client.
    if "raw_retention_path" in resp:
        resp["raw_retention_path"] = _to_repo_relative_path(
            resp.get("raw_retention_path")
        )
    # Sanitise ir_index step_path
    if isinstance(resp.get("ir_index"), dict):
        idx = dict(resp["ir_index"])
        if "step_path" in idx:
            idx["step_path"] = _to_repo_relative_path(idx["step_path"])
        resp["ir_index"] = idx
    # Strip raw body — only keep retained, repo-relative path, and body_sha256
    if isinstance(resp.get("raw_retention_meta"), dict):
        meta = resp["raw_retention_meta"]
        resp["raw_retention_meta"] = {
            "retained": meta.get("retained"),
            "path": _to_repo_relative_path(meta.get("path")),
            "body_sha256": meta.get("body_sha256"),
        }
    return resp


def make_handler_class(
    demo_handler: DemoHandler,
    product_handler: ProductFlowHandler | None = None,
    product_live_handler: dict | None = None,
    product_live_service: "Any | None" = None,
):
    """Return a request handler class bound to the given handler instances.

    ``product_live_service`` is an optional :class:`ProductLiveService` instance
    (from ``integration.product_live_runner``).  When supplied it is used by
    the product live HTTP routes to call ``extract()`` / ``confirm()`` / ``get()``.
    The older ``product_live_handler`` dict interface is kept for backward
    compatibility but is superseded by ``product_live_service``.

    Default (both None): product live routes return ``PRODUCT_LIVE_DISABLED``.
    """

    _product = product_handler
    _product_live = product_live_handler  # dict with 'runs' and 'output_root' (legacy)
    _pl_service = product_live_service    # ProductLiveService instance (preferred)

    class _Handler(BaseHTTPRequestHandler):
        _demo = demo_handler

        def log_message(self, fmt: str, *args: Any) -> None:  # type: ignore[override]
            # Print to stderr with timestamp
            print(f"[demo] {self.address_string()} {fmt % args}", file=sys.stderr)

        def _send_json(self, status: int, data: Any) -> None:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_error_json(self, status: int, code: str, message: str) -> None:
            self._send_json(status, {"error": {"code": code, "message": message}})

        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]

            if path == "/" or path == "/index.html":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(HTML_BYTES)))
                self.end_headers()
                self.wfile.write(HTML_BYTES)
                return

            # C3: offline product confirmation UI
            if path == "/product" or path == "/product/":
                self._handle_product_ui()
                return

            # Product live UI (APP-003-LIVE-UI)
            if path == "/product-live" or path == "/product-live/":
                self._handle_product_live_ui()
                return

            # C3: fixture allowlist
            if path == "/api/product/fixtures":
                self._handle_product_fixtures()
                return

            if path.startswith("/download/"):
                run_id = path[len("/download/"):]
                self._handle_download(run_id)
                return

            if path.startswith("/product-download/"):
                run_id = path[len("/product-download/"):]
                self._handle_product_download(run_id)
                return

            if path.startswith("/api/product/"):
                tail = path[len("/api/product/"):]
                if tail:
                    self._handle_product_get(tail)
                    return

            # Product live routes (GET)
            if path == "/api/product-live/inputs":
                self._handle_product_live_inputs()
                return

            if path.startswith("/api/product-live/"):
                tail = path[len("/api/product-live/"):]
                if tail:
                    self._handle_product_live_get(tail)
                    return

            if path.startswith("/product-live-download/"):
                run_id = path[len("/product-live-download/"):]
                self._handle_product_live_download(run_id)
                return

            self._send_error_json(404, "NOT_FOUND", f"Path not found: {path}")

        def do_POST(self) -> None:
            path = self.path.split("?", 1)[0]

            if path == "/api/generate":
                self._handle_generate()
                return

            if path == "/api/product/create":
                self._handle_product_create()
                return

            if path.startswith("/api/product/confirm/"):
                run_id = path[len("/api/product/confirm/"):]
                self._handle_product_confirm(run_id)
                return

            # Product live routes (POST)
            if path == "/api/product-live/create":
                self._handle_product_live_create()
                return

            if path.startswith("/api/product-live/confirm/"):
                run_id = path[len("/api/product-live/confirm/"):]
                self._handle_product_live_confirm(run_id)
                return

            self._send_error_json(404, "NOT_FOUND", f"Path not found: {path}")

        def _handle_generate(self) -> None:
            # Read request body
            length_hdr = self.headers.get("Content-Length", "0")
            try:
                length = int(length_hdr)
            except (TypeError, ValueError):
                self._send_error_json(400, "CONTENT_LENGTH_MISSING", "Content-Length required")
                return
            if length > 65536:
                self._send_error_json(400, "REQUEST_TOO_LARGE", "Request body exceeds 64 KB")
                return
            try:
                raw_body = self.rfile.read(length)
                body = json.loads(raw_body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                self._send_error_json(400, "INVALID_JSON", f"Invalid JSON: {exc}")
                return

            if not isinstance(body, dict):
                self._send_error_json(400, "INVALID_BODY", "Body must be a JSON object")
                return

            request_text = body.get("request_text", "")
            if not isinstance(request_text, str) or not request_text.strip():
                self._send_error_json(400, "MISSING_REQUEST_TEXT",
                                       "request_text is required and must be a non-empty string")
                return

            bore_d_raw = body.get("bore_d")
            if bore_d_raw is None:
                self._send_error_json(400, "MISSING_BORE_D", "bore_d is required")
                return

            # Run the pipeline
            demo_result = self._demo.run(request_text, bore_d_raw)
            self._send_json(200, demo_result.as_dict())

        def _handle_download(self, run_id: str) -> None:
            # Validate run_id format (UUID v4)
            if not _RUN_ID_RE.match(run_id):
                self._send_error_json(400, "INVALID_RUN_ID",
                                       "run_id must be a UUID v4")
                return

            # Reject if unknown or not in registry
            demo_result = self._demo.get_run(run_id)
            if demo_result is None:
                self._send_error_json(404, "RUN_NOT_FOUND",
                                       "run_id not found in this session")
                return

            # Reject if not successful
            if demo_result.status != "success":
                self._send_error_json(403, "RUN_NOT_SUCCESSFUL",
                                       f"Run {run_id} has status={demo_result.status!r}; "
                                       "only successful runs can be downloaded")
                return

            # Get STEP bytes with full security validation
            step_bytes = self._demo.get_step_bytes_secure(run_id)
            if step_bytes is None:
                self._send_error_json(403, "STEP_UNAVAILABLE",
                                       "STEP file unavailable or failed integrity check")
                return

            # Serve the file
            filename = f"collar-{demo_result.bore_d_input}mm-{run_id[:8]}.step"
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(step_bytes)))
            self.end_headers()
            self.wfile.write(step_bytes)

        def _read_json_body(self) -> dict[str, Any] | None:
            """Read and parse a JSON request body. Returns None on error."""
            length_hdr = self.headers.get("Content-Length", "0")
            try:
                length = int(length_hdr)
            except (TypeError, ValueError):
                self._send_error_json(400, "CONTENT_LENGTH_MISSING", "Content-Length required")
                return None
            if length > 65536:
                self._send_error_json(400, "REQUEST_TOO_LARGE", "Request body exceeds 64 KB")
                return None
            try:
                raw_body = self.rfile.read(length)
                body = json.loads(raw_body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                self._send_error_json(400, "INVALID_JSON", f"Invalid JSON: {exc}")
                return None
            if not isinstance(body, dict):
                self._send_error_json(400, "INVALID_BODY", "Body must be a JSON object")
                return None
            return body

        def _handle_product_create(self) -> None:
            """POST /api/product/create — C2 product run creation."""
            if _product is None:
                self._send_error_json(503, "PRODUCT_FLOW_DISABLED", "Product flow handler not configured")
                return
            body = self._read_json_body()
            if body is None:
                return
            request_text = body.get("request_text", "")
            if not isinstance(request_text, str) or not request_text.strip():
                self._send_error_json(400, "MISSING_REQUEST_TEXT",
                                       "request_text is required and must be a non-empty string")
                return
            fixture_id = body.get("fixture_id", "")
            if not isinstance(fixture_id, str) or not fixture_id.strip():
                self._send_error_json(400, "MISSING_FIXTURE_ID", "fixture_id is required")
                return
            rec = _product.create_product_run(request_text, fixture_id)
            self._send_json(200, rec.as_dict())

        def _handle_product_confirm(self, run_id: str) -> None:
            """POST /api/product/confirm/<run_id> — confirm or modify a product run."""
            if _product is None:
                self._send_error_json(503, "PRODUCT_FLOW_DISABLED", "Product flow handler not configured")
                return
            if not _RUN_ID_RE.match(run_id):
                self._send_error_json(400, "INVALID_RUN_ID", "run_id must be a UUID v4")
                return
            body = self._read_json_body()
            if body is None:
                return

            # Strict type validation — must not coerce types silently.
            # confirmation_revision must be a JSON integer (not bool, not string).
            revision_raw = body.get("confirmation_revision")
            if revision_raw is None:
                self._send_error_json(400, "MISSING_CONFIRMATION_REVISION",
                                       "confirmation_revision is required")
                return
            if isinstance(revision_raw, bool) or not isinstance(revision_raw, int):
                self._send_error_json(400, "INVALID_CONFIRMATION_REVISION_TYPE",
                                       "confirmation_revision must be a JSON integer, "
                                       f"got {type(revision_raw).__name__!r}: {revision_raw!r}")
                return

            # confirmed must be a JSON boolean (not int 0/1, not string).
            confirmed_raw = body.get("confirmed")
            if confirmed_raw is None:
                self._send_error_json(400, "MISSING_CONFIRMED", "confirmed is required")
                return
            if not isinstance(confirmed_raw, bool):
                self._send_error_json(400, "INVALID_CONFIRMED_TYPE",
                                       "confirmed must be a JSON boolean (true or false), "
                                       f"got {type(confirmed_raw).__name__!r}: {confirmed_raw!r}")
                return

            patch = body.get("patch", {})
            if not isinstance(patch, dict):
                self._send_error_json(400, "INVALID_PATCH", "patch must be a JSON object")
                return

            rec = _product.confirm_product_run(run_id, revision_raw, confirmed_raw, patch)
            self._send_json(200, rec.as_dict())

        def _handle_product_get(self, run_id: str) -> None:
            """GET /api/product/<run_id> — get product run status."""
            if _product is None:
                self._send_error_json(503, "PRODUCT_FLOW_DISABLED", "Product flow handler not configured")
                return
            if not _RUN_ID_RE.match(run_id):
                self._send_error_json(400, "INVALID_RUN_ID", "run_id must be a UUID v4")
                return
            rec = _product.get_product_run(run_id)
            if rec is None:
                self._send_error_json(404, "RUN_NOT_FOUND", f"run_id {run_id!r} not found")
                return
            self._send_json(200, rec.as_dict())

        def _handle_product_download(self, run_id: str) -> None:
            """GET /product-download/<run_id> — STEP download for product flow."""
            if _product is None:
                self._send_error_json(503, "PRODUCT_FLOW_DISABLED", "Product flow handler not configured")
                return
            if not _RUN_ID_RE.match(run_id):
                self._send_error_json(400, "INVALID_RUN_ID", "run_id must be a UUID v4")
                return
            rec = _product.get_product_run(run_id)
            if rec is None:
                self._send_error_json(404, "RUN_NOT_FOUND", f"run_id {run_id!r} not found")
                return
            if rec.product_status != "succeeded":
                self._send_error_json(403, "RUN_NOT_SUCCESSFUL",
                                       f"Run {run_id} has product_status={rec.product_status!r}; "
                                       "only succeeded runs can be downloaded")
                return
            step_bytes = _product.get_product_step_bytes_secure(run_id)
            if step_bytes is None:
                self._send_error_json(403, "STEP_UNAVAILABLE",
                                       "STEP file unavailable or failed integrity check")
                return
            filename = f"product-{run_id[:8]}.step"
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(step_bytes)))
            self.end_headers()
            self.wfile.write(step_bytes)

        # ------------------------------------------------------------------
        # C3 handlers
        # ------------------------------------------------------------------

        def _handle_product_ui(self) -> None:
            """GET /product — C3 offline product confirmation UI."""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(PRODUCT_HTML_BYTES)))
            self.end_headers()
            self.wfile.write(PRODUCT_HTML_BYTES)

        def _handle_product_fixtures(self) -> None:
            """GET /api/product/fixtures — available fixture allowlist (keys only)."""
            if _product is None:
                self._send_error_json(503, "PRODUCT_FLOW_DISABLED",
                                       "Product flow handler not configured")
                return
            # Never expose file paths; return only the keys from the registry
            fixtures = [
                {"fixture_id": fid, "label": fid}
                for fid in _product._fixture_registry.keys()
            ]
            self._send_json(200, {"fixtures": fixtures})

        # ------------------------------------------------------------------
        # Product live UI handlers (APP-003-LIVE-UI)
        # ------------------------------------------------------------------

        def _handle_product_live_ui(self) -> None:
            """GET /product-live — Product live extraction confirmation UI.

            Always serves the page HTML regardless of whether a ProductLiveService
            is configured.  If no service is configured, the page will show
            'disabled' when the user attempts to create a run.
            """
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(PRODUCT_LIVE_HTML_BYTES)))
            self.end_headers()
            self.wfile.write(PRODUCT_LIVE_HTML_BYTES)

        def _handle_product_live_inputs(self) -> None:
            """GET /api/product-live/inputs — available input IDs (allowlist only).

            Returns the authorized input IDs from the product live scope.
            Never returns API keys, model responses, evaluator labels, or paths.
            If no service is configured, returns PRODUCT_LIVE_DISABLED.
            """
            if not _PRODUCT_LIVE_AVAILABLE:
                self._send_error_json(503, "PRODUCT_LIVE_DISABLED",
                                      "Product live runner not available")
                return
            if _pl_service is None and _product_live is None:
                self._send_error_json(503, "PRODUCT_LIVE_DISABLED",
                                      "Product live service not configured")
                return
            # Return the frozen input IDs from the authorization scope.
            # These are labels only — never expose model responses or evaluator labels.
            try:
                from integration.product_live_runner import PRODUCT_INPUT_IDS
                inputs = [
                    {"input_id": iid, "label": iid}
                    for iid in PRODUCT_INPUT_IDS
                ]
                self._send_json(200, {"inputs": inputs})
            except Exception as exc:
                self._send_error_json(503, "PRODUCT_LIVE_INPUTS_ERROR",
                                      f"Could not load input IDs: {type(exc).__name__}")

        # ------------------------------------------------------------------
        # Product live handlers (APP-003-LIVE-PRODUCT)
        # ------------------------------------------------------------------

        def _handle_product_live_create(self) -> None:
            """POST /api/product-live/create — run extraction for one input.

            Calls ProductLiveService.extract() (injected offline service) with
            the browser-supplied request_text and input_id.  Never exposes API
            keys, raw body, or evaluator labels to the browser.

            Request body: {request_text: str, input_id: str}
            """
            # Prefer the ProductLiveService interface; fall back to legacy dict.
            if not _PRODUCT_LIVE_AVAILABLE or (_pl_service is None and _product_live is None):
                self._send_error_json(503, "PRODUCT_LIVE_DISABLED",
                                      "Product live service not configured")
                return
            body = self._read_json_body()
            if body is None:
                return
            request_text = body.get("request_text", "")
            if not isinstance(request_text, str) or not request_text.strip():
                self._send_error_json(400, "MISSING_REQUEST_TEXT",
                                      "request_text is required and must be non-empty")
                return

            if _pl_service is not None:
                # New path: browser provides input_id, service calls the runner
                input_id = body.get("input_id", "")
                if not isinstance(input_id, str) or not input_id.strip():
                    self._send_error_json(400, "MISSING_INPUT_ID",
                                          "input_id is required (e.g. P1-24mm)")
                    return
                state = _pl_service.extract(input_id, request_text.strip())
                resp = _sanitize_state_for_http(state)
                self._send_json(200, resp)
            else:
                # Legacy path: logical_run_id lookup in pre-populated dict
                logical_run_id = body.get("logical_run_id", "")
                if not isinstance(logical_run_id, str) or not logical_run_id.strip():
                    self._send_error_json(400, "MISSING_LOGICAL_RUN_ID",
                                          "logical_run_id is required")
                    return
                runs: dict = _product_live.get("runs", {})
                state = runs.get(logical_run_id)
                if state is None:
                    self._send_error_json(404, "LOGICAL_RUN_NOT_FOUND",
                                          f"logical_run_id {logical_run_id!r} not found")
                    return
                resp = _sanitize_state_for_http(state)
                self._send_json(200, resp)

        def _handle_product_live_confirm(self, run_id: str) -> None:
            """POST /api/product-live/confirm/<run_id> — confirm and trigger CAD pipeline.

            Only product_status=needs_confirmation runs can be confirmed.
            Calls ProductLiveService.confirm() or confirm_product_live_run(),
            which is the ONLY code path that calls run_pipeline() for product live runs.

            Request body: {confirmed: bool, patch: dict}
            """
            if not _PRODUCT_LIVE_AVAILABLE or (_pl_service is None and _product_live is None):
                self._send_error_json(503, "PRODUCT_LIVE_DISABLED",
                                      "Product live service not configured")
                return
            if not run_id or not isinstance(run_id, str):
                self._send_error_json(400, "INVALID_RUN_ID", "run_id must be non-empty")
                return
            body = self._read_json_body()
            if body is None:
                return
            confirmed_raw = body.get("confirmed")
            if confirmed_raw is None:
                self._send_error_json(400, "MISSING_CONFIRMED", "confirmed is required")
                return
            if not isinstance(confirmed_raw, bool):
                self._send_error_json(400, "INVALID_CONFIRMED_TYPE",
                                      "confirmed must be a JSON boolean (true or false), "
                                      f"got {type(confirmed_raw).__name__!r}: {confirmed_raw!r}")
                return
            patch = body.get("patch", {})
            if not isinstance(patch, dict):
                self._send_error_json(400, "INVALID_PATCH", "patch must be a JSON object")
                return

            if _pl_service is not None:
                new_state = _pl_service.confirm(run_id, confirmed_raw, patch or None)
                if new_state is None:
                    self._send_error_json(404, "LOGICAL_RUN_NOT_FOUND",
                                          f"run_id {run_id!r} not found in product live registry")
                    return
                resp = _sanitize_state_for_http(new_state)
                self._send_json(200, resp)
            else:
                runs: dict = _product_live.get("runs", {})
                state = runs.get(run_id)
                if state is None:
                    self._send_error_json(404, "LOGICAL_RUN_NOT_FOUND",
                                          f"run_id {run_id!r} not found in product live registry")
                    return
                output_root = _product_live.get("output_root")
                new_state = confirm_product_live_run(
                    state, confirmed=confirmed_raw, patch=patch or None,
                    output_root=output_root,
                )
                runs[run_id + "__confirmed"] = new_state
                resp = _sanitize_state_for_http(new_state)
                self._send_json(200, resp)

        def _handle_product_live_get(self, run_id: str) -> None:
            """GET /api/product-live/<run_id> — get product live run status."""
            if not _PRODUCT_LIVE_AVAILABLE or (_pl_service is None and _product_live is None):
                self._send_error_json(503, "PRODUCT_LIVE_DISABLED",
                                      "Product live service not configured")
                return
            if _pl_service is not None:
                state = _pl_service.get(run_id)
            else:
                runs: dict = _product_live.get("runs", {})
                state = runs.get(run_id) or runs.get(run_id + "__confirmed")
            if state is None:
                self._send_error_json(404, "LOGICAL_RUN_NOT_FOUND",
                                      f"run_id {run_id!r} not found")
                return
            resp = _sanitize_state_for_http(state)
            self._send_json(200, resp)

        def _handle_product_live_download(self, run_id: str) -> None:
            """GET /product-live-download/<run_id> — STEP download for product live.

            Only succeeded runs with a valid STEP file can be downloaded.
            Applies path containment and SHA-256 verification.
            """
            if not _PRODUCT_LIVE_AVAILABLE or (_pl_service is None and _product_live is None):
                self._send_error_json(503, "PRODUCT_LIVE_DISABLED",
                                      "Product live service not configured")
                return
            if _pl_service is not None:
                state = _pl_service.get(run_id)
                step_bytes = _pl_service.get_step_bytes_secure(run_id) if state else None
            else:
                runs: dict = _product_live.get("runs", {})
                state = runs.get(run_id + "__confirmed") or runs.get(run_id)
                step_bytes = _get_product_live_step_bytes_secure(state) if state else None
            if state is None:
                self._send_error_json(404, "LOGICAL_RUN_NOT_FOUND",
                                      f"run_id {run_id!r} not found")
                return
            if state.product_status != PRODUCT_LIVE_STATUS_SUCCEEDED:
                self._send_error_json(403, "RUN_NOT_SUCCESSFUL",
                                      f"Run {run_id} has product_status={state.product_status!r}; "
                                      "only succeeded runs can be downloaded")
                return
            if step_bytes is None:
                self._send_error_json(403, "STEP_UNAVAILABLE",
                                      "STEP file unavailable or failed integrity check")
                return
            filename = f"product-live-{run_id[:16]}.step"
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(step_bytes)))
            self.end_headers()
            self.wfile.write(step_bytes)

    return _Handler


# ---------------------------------------------------------------------------
# Server entry point
# ---------------------------------------------------------------------------

def run_server(port: int = 8080, output_root: Path | None = None) -> None:
    """Start the demo HTTP server on 127.0.0.1:<port>.

    Parameters
    ----------
    port:
        TCP port to listen on (default 8080).
    output_root:
        Override for the demo runs output directory.
    """
    demo_handler = DemoHandler(output_root=output_root)
    product_handler = ProductFlowHandler(output_root=output_root)
    handler_class = make_handler_class(demo_handler, product_handler)
    server = HTTPServer(("127.0.0.1", port), handler_class)
    print(f"[demo] Server started at http://127.0.0.1:{port}/", file=sys.stderr)
    print(f"[demo] Output root: {demo_handler._output_root}", file=sys.stderr)
    print(f"[demo] Press Ctrl+C to stop.", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[demo] Stopped.", file=sys.stderr)
