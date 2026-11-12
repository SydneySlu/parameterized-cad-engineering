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


def make_handler_class(demo_handler: DemoHandler, product_handler: ProductFlowHandler | None = None):
    """Return a request handler class bound to the given handler instances."""

    _product = product_handler

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
