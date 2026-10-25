"""server.py — DSH Research Lab 本地工作台服务（stdlib-only + desktop 集成）。

桌面应用（desktop.app / PyInstaller 打包）与命令行
（python scripts/dashboard.py）共用的本地服务：
- 管线一键运行：教育 T1–T5 / 公卫 H1–H5 / 总验收（49 项），日志实时查看；
- 产物浏览：outputs 沙箱内防路径穿越；
- 内置 DSH 智能体：desktop.dsh_manager 生命周期（启动/停止/带 token URL）；
- 模型设置：provider / key（只写不读）/ baseURL / model，写入凭据引用 patch；
- 仅绑定 127.0.0.1；响应与日志绝不包含模型 key。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

if hasattr(sys.stdout, "reconfigure") and (sys.stdout.encoding or "").lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

from desktop import dsh_manager, paths, runner  # noqa: E402
from desktop.bootstrap import ensure_home  # noqa: E402
from desktop.config import AppConfig  # noqa: E402
from desktop.patch_writer import sync_patch  # noqa: E402

JOBS: dict[str, dict] = {
    "education": {
        "title": "教育科研管线（T1–T5）",
        "script": "examples/education-demo/run_t1_t5.py",
        "outputs": "examples/education-demo/outputs",
    },
    "health": {
        "title": "公卫科研管线（H1–H5）",
        "script": "examples/health-demo/run_h1_h5.py",
        "outputs": "examples/health-demo/outputs",
    },
    "verify": {
        "title": "总验收（49 项对账）",
        "script": "scripts/verify.py",
        "outputs": "",
    },
}

_state_lock = threading.Lock()
_state: dict[str, dict] = {k: {"status": "idle", "returncode": None,
                               "log_path": "", "started": 0, "ended": 0}
                           for k in JOBS}

_dsh: dsh_manager.DshManager | None = None
_app_config: AppConfig | None = None
_home: Path | None = None
_dsh_version_cache: str | None = None


def lab_root() -> Path:
    """工作台根目录（打包形态为可写主目录 lab/，开发形态为仓库根）。"""
    return _home / "lab" if _home is not None else paths.repo_root()


def logs_root() -> Path:
    base = (_home or paths.app_home()) / "outputs_dashboard"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _job_states() -> dict:
    with _state_lock:
        return {k: dict(v) for k, v in _state.items()}


def _run_job(job: str) -> None:
    spec = JOBS[job]
    log_path = logs_root() / f"{job}.log"
    with _state_lock:
        _state[job] = {"status": "running", "returncode": None, "log_path": str(log_path),
                       "started": time.time(), "ended": 0}
    with log_path.open("w", encoding="utf-8") as log:
        rc = runner.run_python_script(lab_root() / spec["script"], log, cwd=lab_root())
    with _state_lock:
        _state[job].update({"status": "done" if rc == 0 else "failed",
                            "returncode": rc, "ended": time.time()})


def _safe_join(base: Path, rel: str) -> Path | None:
    """产物浏览沙箱：解析后必须仍在 base 内，防路径穿越。"""
    target = (base / rel).resolve()
    try:
        target.relative_to(base.resolve())
    except ValueError:
        return None
    return target


# -- 环境指纹 ------------------------------------------------------------------
def _probe_dsh_version() -> str:
    """DSH 版本：打包形态读 manifest；开发形态探测系统 dsh（缓存）。"""
    global _dsh_version_cache
    if _dsh_version_cache is not None:
        return _dsh_version_cache
    manifest = paths.manifest()
    if manifest.get("dsh_version"):
        _dsh_version_cache = manifest["dsh_version"]
        return _dsh_version_cache
    dsh_dir = paths.bundled_dsh_dir()
    node_bin = paths.bundled_node_bin()
    if dsh_dir is None or node_bin is None:
        _dsh_version_cache = ""
        return ""
    try:
        proc = subprocess.run(
            [*paths.dsh_launcher(dsh_dir, node_bin), "--version"],
            capture_output=True, text=True, timeout=30)
        _dsh_version_cache = (proc.stdout or proc.stderr).strip().splitlines()[-1] \
            if (proc.stdout or proc.stderr).strip() else ""
    except (OSError, subprocess.TimeoutExpired):
        _dsh_version_cache = ""
    return _dsh_version_cache


def _dep_versions() -> dict:
    out = {}
    for mod in ("pandas", "numpy", "scipy", "statsmodels", "sklearn", "matplotlib", "yaml"):
        try:
            m = __import__(mod)
            out[mod] = getattr(m, "__version__", "?")
        except Exception:  # noqa: BLE001 —— 指纹仅展示
            out[mod] = "缺失"
    return out


def env_fingerprint() -> dict:
    lab = lab_root()
    node_bin = paths.bundled_node_bin()
    dsh_dir = paths.bundled_dsh_dir()
    return {
        "mode": "packaged" if paths.bundled_root() else "dev",
        "version": paths.manifest().get("version", "dev"),
        "python": sys.version.split()[0],
        "deps": _dep_versions(),
        "lab": str(lab),
        "lab_ready": (lab / "tools").is_dir() and (lab / "datasets").is_dir(),
        "node": str(node_bin) if node_bin else "",
        "node_ok": bool(node_bin and node_bin.is_file()),
        "dsh": _probe_dsh_version(),
        "dsh_ok": bool(dsh_dir),
        "key_configured": bool(_app_config.has_key()) if _app_config else False,
    }


# -- 页面 ----------------------------------------------------------------------
PAGE = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DSH Research Lab · 本地工作台</title>
<style>
:root { --navy:#0b1524; --line:rgba(148,163,184,.25); --text:#eaf3ff; --muted:#9fb2c7;
  --blue:#38bdf8; --cyan:#67e8f9; --lime:#a3e635; --gold:#fbbf24; --pink:#f472b6; }
* { box-sizing:border-box; } body { margin:0; color:var(--text); font-size:15px; line-height:1.6;
  background:radial-gradient(900px 480px at 80% -10%, rgba(56,189,248,.16), transparent),
  linear-gradient(145deg,var(--navy),#101e33); min-height:100vh;
  font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; }
header { padding:26px 28px 6px; display:flex; align-items:flex-end; justify-content:space-between; gap:14px; flex-wrap:wrap; }
h1 { margin:0 0 4px; font-size:22px; letter-spacing:-.02em; }
header p { margin:0; color:var(--muted); font-size:13px; }
main { max-width:1020px; margin:auto; padding:18px 28px 48px; }
.chips { display:flex; gap:8px; flex-wrap:wrap; margin:10px 0 4px; }
.chip { font-size:12px; color:var(--muted); border:1px solid var(--line); border-radius:999px; padding:3px 11px; }
.chip b { color:var(--text); font-weight:700; }
.chip.ok b { color:var(--lime); } .chip.bad b { color:var(--pink); }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:12px; }
.card { border:1px solid var(--line); border-radius:14px; padding:16px; background:rgba(255,255,255,.04); }
.card h3 { margin:0 0 8px; font-size:15px; } .card p { margin:0 0 12px; color:var(--muted); font-size:12.5px; }
button, a.btn { display:inline-block; border:0; border-radius:10px; padding:8px 14px; font-size:13px;
  font-weight:700; cursor:pointer; text-decoration:none; color:#06121f;
  background:linear-gradient(135deg,var(--blue),#6366f1); }
button.alt { background:linear-gradient(135deg,var(--lime),var(--cyan)); }
button.warn { background:linear-gradient(135deg,var(--pink),#f97316); color:#1f0a0a; }
button.ghost { background:rgba(148,163,184,.25); color:var(--text); }
button:disabled { opacity:.5; cursor:wait; }
.state { font-size:12px; padding:2px 9px; border-radius:999px; border:1px solid var(--line); }
.ok { color:var(--lime); } .bad { color:var(--pink); } .run { color:var(--gold); }
pre { background:#0a1220; border:1px solid var(--line); border-radius:12px; padding:14px;
  font-size:12px; overflow:auto; max-height:300px; white-space:pre-wrap; }
ul.out { margin:6px 0 0; padding-left:18px; font-size:13px; }
ul.out a { color:var(--blue); }
.note { color:var(--muted); font-size:12px; margin-top:14px; }
h3.sec { margin:24px 0 10px; font-size:16px; }
/* DSH 卡 */
.dsh-url { font-size:12px; color:var(--cyan); word-break:break-all; }
/* 设置弹窗 */
dialog { border:1px solid var(--line); border-radius:16px; background:#0d1a2c; color:var(--text);
  max-width:460px; width:92vw; padding:22px; }
dialog::backdrop { background:rgba(4,10,20,.7); }
dialog h3 { margin:0 0 14px; font-size:17px; }
label { display:block; font-size:12.5px; color:var(--muted); margin:12px 0 4px; font-weight:700; }
input, select { width:100%; border:1px solid var(--line); border-radius:10px; padding:9px 11px;
  background:rgba(255,255,255,.05); color:var(--text); font-size:14px; }
input:focus, select:focus { outline:1px solid var(--blue); }
.row { display:flex; gap:10px; justify-content:flex-end; margin-top:18px; }
.hint { font-size:12px; color:var(--muted); margin-top:6px; }
.err { color:var(--pink); font-size:12.5px; margin-top:10px; min-height:16px; }
</style></head><body>
<header><div><h1>🧪 DSH Research Lab 本地工作台</h1>
<p>真实公开数据 · 全部统计来自本机真实执行 · 仅监听 127.0.0.1</p></div>
<button class="ghost" onclick="document.getElementById('settings').showModal()">⚙ 模型设置</button></header>
<main>
  <div class="chips" id="env"></div>

  <h3 class="sec">科研管线（一键运行）</h3>
  <div class="grid" id="jobs"></div>

  <h3 class="sec">DSH 智能体（内置 DeepSeek Harness）</h3>
  <div class="grid"><div class="card">
    <h3>DSH Web 工作区</h3>
    <p id="dsh-desc">启动真实 DSH（内嵌 Node + Harness，工作区指向本工作台），在浏览器窗口中使用科研台 Preset 与技能。</p>
    <div id="dsh-body"><span class="state">加载中…</span></div>
    <pre id="dsh-log" style="display:none;margin-top:12px"></pre>
    <p class="note">模型 API key 首次使用请在「⚙ 模型设置」中配置（仅保存在本机，
    不随应用分发）；未配置时 DSH 界面可正常打开，发起对话会提示缺少凭据。</p>
  </div></div>

  <h3 class="sec">产物浏览</h3>
  <ul class="out" id="outputs"></ul>
</main>

<dialog id="settings">
  <h3>模型设置</h3>
  <label>提供方</label>
  <select id="s-provider">
    <option value="deepseek">DeepSeek 官方 API</option>
    <option value="openai-compat">OpenAI 兼容端点（智谱 / 火山 / 自托管）</option>
  </select>
  <label>API Key（写入本机，不回显、不打包、不进日志）</label>
  <input id="s-key" type="password" placeholder="sk-…（留空表示不修改）">
  <div id="s-base-wrap"><label>Base URL</label>
  <input id="s-base" placeholder="https://open.bigmodel.cn/api/paas/v4"></div>
  <label>默认模型</label>
  <input id="s-model" placeholder="deepseek-chat">
  <label>推理强度（reasoningEffort）</label>
  <select id="s-effort">
    <option>high</option><option>medium</option><option>low</option><option>off</option>
  </select>
  <label>科研台 Preset（DSH 会话的智能体守则，重启 DSH 生效）</label>
  <select id="s-preset">
    <option value="edu-research">教育科研台（edu-research）</option>
    <option value="health-research">公卫科研台（health-research）</option>
    <option value="research-lab">通用科研台（research-lab）</option>
    <option value="none">不启用（通用助手）</option>
  </select>
  <div class="err" id="s-err"></div>
  <div class="row">
    <button class="ghost" onclick="this.closest('dialog').close()">取消</button>
    <button id="s-save">保存</button>
  </div>
  <p class="hint">密钥仅存于本机应用目录（0600），DSH 通过环境变量引用；更换 key 后
  需重启 DSH 生效。</p>
</dialog>

<script>
const $ = s => document.querySelector(s);
const esc = s => s.replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const inApp = !!(window.pywebview && window.pywebview.api);

function chip(label, val, ok) {
  return `<span class="chip ${ok ? 'ok' : 'bad'}">${esc(label)} <b>${esc(val)}</b></span>`;
}

async function refresh() {
  try {
    const env = await (await fetch('/api/env')).json();
    let chips = chip('版本', env.version, true) + chip('Python', env.python, true);
    for (const [k, v] of Object.entries(env.deps)) chips += chip(k, v, v !== '缺失');
    chips += chip('DSH', env.dsh_ok ? (env.dsh || '已内置') : '不可用', env.dsh_ok);
    chips += chip('数据', env.lab_ready ? '就绪' : '缺失', env.lab_ready);
    chips += chip('Key', env.key_configured ? '已配置' : '未配置', env.key_configured);
    $('#env').innerHTML = chips;

    const jobs = await (await fetch('/api/jobs')).json();
    $('#jobs').innerHTML = Object.entries(jobs).map(([k, j]) => `
      <div class="card"><h3>${esc(j.title)}</h3><p>${esc(j.desc)}</p>
      <div><button data-job="${k}" ${j.status === 'running' ? 'disabled' : ''}>▶ 运行</button>
      <span class="state ${j.cls}">${esc(j.label)}</span>
      <a class="btn" style="margin-left:8px;background:rgba(148,163,184,.25);color:var(--text)" href="/log?job=${k}">日志</a></div>
      </div>`).join('');
    document.querySelectorAll('button[data-job]').forEach(b =>
      b.onclick = () => fetch('/run?job=' + b.dataset.job, {method: 'POST'}).then(refresh));

    const dsh = await (await fetch('/api/dsh')).json();
    let body = '';
    if (dsh.state === 'running') {
      body = `<span class="state ok">运行中 · 端口 ${dsh.port}</span>
        <button class="alt" style="margin-left:8px" id="dsh-open">打开 DSH 窗口</button>
        <button class="warn" style="margin-left:8px" id="dsh-stop">停止</button>
        <p class="dsh-url" style="margin-top:8px">${esc(dsh.url)}</p>`;
    } else if (dsh.state === 'starting') {
      body = `<span class="state run">启动中…</span>
        <button class="warn" style="margin-left:8px" id="dsh-stop">停止</button>`;
    } else if (dsh.state === 'error') {
      body = `<span class="state bad">错误</span>
        <button style="margin-left:8px" id="dsh-start">重试启动</button>
        <p class="dsh-url" style="margin-top:8px;color:var(--pink)">${esc(dsh.error || '')}</p>`;
    } else {
      body = `<span class="state">未启动</span>
        <button style="margin-left:8px" id="dsh-start">▶ 启动 DSH</button>`;
    }
    body += ` <button class="ghost" style="margin-left:8px" id="dsh-log-btn">日志</button>`;
    $('#dsh-body').innerHTML = body;
    const open = $('#dsh-open'), start = $('#dsh-start'), stop = $('#dsh-stop');
    if (open) open.onclick = () => {
      if (inApp) window.pywebview.api.open_dsh(dsh.url);
      else window.open(dsh.url, '_blank');
    };
    if (start) start.onclick = () => fetch('/api/dsh/start', {method: 'POST'}).then(refresh);
    if (stop) stop.onclick = () => fetch('/api/dsh/stop', {method: 'POST'}).then(refresh);
    $('#dsh-log-btn').onclick = () => {
      const pre = $('#dsh-log');
      if (pre.style.display === 'none') {
        pre.style.display = 'block';
        pre.textContent = (dsh.log_tail || []).join('\\n') || '（暂无日志）';
      } else { pre.style.display = 'none'; }
    };

    const outs = await (await fetch('/api/outputs')).json();
    $('#outputs').innerHTML = outs.html ||
      '<li>尚无产物，先运行管线</li>';
  } catch (e) { /* 下轮重试 */ }
}

async function loadSettings() {
  const s = await (await fetch('/api/settings')).json();
  $('#s-provider').value = s.provider;
  $('#s-model').value = s.model || '';
  $('#s-effort').value = s.reasoning_effort || 'high';
  $('#s-preset').value = s.preset || 'edu-research';
  $('#s-base').value = s.base_url || '';
  $('#s-key').value = '';
  $('#s-key').placeholder = s.has_key ? '已配置（留空表示不修改）' : 'sk-…';
  $('#s-err').textContent = '';
  syncProvider();
}
function syncProvider() {
  $('#s-base-wrap').style.display =
    $('#s-provider').value === 'openai-compat' ? 'block' : 'none';
}
$('#s-provider').onchange = syncProvider;
$('#s-save').onclick = async () => {
  const payload = {
    provider: $('#s-provider').value,
    base_url: $('#s-base').value,
    model: $('#s-model').value,
    reasoning_effort: $('#s-effort').value,
    preset: $('#s-preset').value,
  };
  if ($('#s-key').value.trim()) payload.api_key = $('#s-key').value.trim();
  const resp = await (await fetch('/api/settings', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)})).json();
  if (resp.ok) {
    $('#settings').close();
    if (resp.restart_required) alert('已保存。DSH 正在运行——请停止并重新启动 DSH 使新 key 生效。');
    refresh();
  } else {
    $('#s-err').textContent = resp.error || '保存失败';
  }
};
document.getElementById('settings').addEventListener('open', loadSettings);
refresh();
setInterval(refresh, 3000);
</script></body></html>"""

CARD_DESC = {
    "education": "审计→关联/组间检验→回归诊断→泄漏对照→报告（649 名中学生真实数据）",
    "health": "审计→基线筛查/OR→防泄漏建模→ROC/阈值/校准→报告（303 例真实病例）",
    "verify": "SHA256 → 确定性复跑 → 双实现交叉验证 → 协议断言（49 项）",
}


def _job_view() -> dict:
    st = _job_states()
    out = {}
    for job, spec in JOBS.items():
        s = st[job]
        running = s["status"] == "running"
        cls, label = (("run", "运行中") if running else
                      ("ok", "完成 rc=0") if s["status"] == "done" else
                      ("bad", f"失败 rc={s['returncode']}") if s["status"] == "failed"
                      else ("", "未运行"))
        out[job] = {"title": spec["title"], "desc": CARD_DESC[job],
                    "status": s["status"], "cls": cls, "label": label}
    return out


def _outputs_html() -> str:
    rows = []
    lab = lab_root()
    for job in ("education", "health"):
        base = lab / JOBS[job]["outputs"]
        if not base.exists():
            continue
        files = sorted(p for p in base.rglob("*") if p.is_file())
        report = base / "report.md"
        rows.append(f"<li><b>{JOBS[job]['title']}</b>（{len(files)} 个文件）→ "
                    f"<a href='/outputs?job={job}'>浏览全部</a>")
        if report.exists():
            rows.append(f" ｜ <a href='/file?job={job}&name=report.md'>打开报告 report.md</a></li>")
        else:
            rows.append("</li>")
    return "".join(rows)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # 静默访问日志
        pass

    def _send(self, body: bytes, ctype="text/html; charset=utf-8", code=200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj: dict, code=200):
        self._send(json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json", code)

    def do_GET(self):
        from urllib.parse import parse_qs, urlparse
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/":
            self._send(PAGE.encode("utf-8"))
        elif u.path == "/api/health":
            self._json({"ok": True})
        elif u.path == "/api/env":
            self._json(env_fingerprint())
        elif u.path == "/api/jobs":
            self._json(_job_view())
        elif u.path == "/api/outputs":
            self._json({"html": _outputs_html()})
        elif u.path == "/api/dsh":
            self._json(_dsh.status())
        elif u.path == "/api/settings":
            self._json(_app_config.summary())
        elif u.path == "/log":
            job = q.get("job", ["verify"])[0]
            log = logs_root() / f"{job}.log"
            text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else "（暂无日志）"
            self._send(f"<meta http-equiv='refresh' content='3'><pre style='background:#0a1220;"
                       f"color:#cfe3ff;padding:18px;white-space:pre-wrap'>{text[-12000:]}"
                       f"</pre><p><a href='/' style='color:#38bdf8'>← 返回</a></p>".encode())
        elif u.path == "/file":
            job, name = q.get("job", [""])[0], q.get("name", [""])[0]
            base = lab_root() / JOBS.get(job, {}).get("outputs", "")
            f = _safe_join(base, name) if name else None
            if f and f.is_file() and f.suffix in {".md", ".json", ".csv", ".png", ".txt", ".yml", ".yaml"}:
                if f.suffix == ".png":
                    self._send(f.read_bytes(), "image/png")
                else:
                    self._send(f.read_text(encoding="utf-8", errors="replace").encode())
            else:
                self._send(b"not found or not allowed", code=404)
        elif u.path == "/outputs":
            job = q.get("job", ["education"])[0]
            base = lab_root() / JOBS.get(job, {}).get("outputs", "")
            rows = []
            if base.exists():
                for f in sorted(p for p in base.rglob("*") if p.is_file()):
                    rel = f.relative_to(base)
                    rows.append(f"<li><a href='/file?job={job}&name={rel}'>{rel}</a></li>")
            self._send(("<ul style='color:#eaf3ff;line-height:1.9'>" + "".join(rows)
                        + "</ul><p><a href='/' style='color:#38bdf8'>← 返回</a></p>").encode())
        else:
            self._send(b"not found", code=404)

    def do_POST(self):
        from urllib.parse import parse_qs, urlparse
        u = urlparse(self.path)
        if u.path == "/run":
            job = parse_qs(u.query).get("job", [""])[0]
            if job not in JOBS:
                self._json({"ok": False, "error": "bad job"}, 400)
                return
            if _job_states()[job]["status"] == "running":
                self._json({"ok": False, "error": "already running"}, 409)
                return
            threading.Thread(target=_run_job, args=(job,), daemon=True).start()
            self._json({"ok": True})
        elif u.path == "/api/dsh/start":
            self._json(_dsh.start())
        elif u.path == "/api/dsh/stop":
            self._json(_dsh.stop())
        elif u.path == "/api/settings":
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length) or b"{}")
                updates = {k: v for k, v in payload.items() if k != "api_key" or str(v).strip()}
                _app_config.save(updates)
                sync_patch(_home or paths.app_home(), _app_config)
                running = _dsh.status()["state"] in ("running", "starting")
                self._json({"ok": True, "restart_required": running})
            except (ValueError, json.JSONDecodeError, OSError) as exc:
                self._json({"ok": False, "error": str(exc)}, 400)
        else:
            self._send(b"not found", code=404)


def make_server(home: Path | None = None, port: int = 0) -> ThreadingHTTPServer:
    """构建（并绑定）工作台 HTTP 服务；desktop.app 与 CLI 共用。"""
    global _home, _app_config, _dsh
    _home = Path(home) if home else paths.app_home()
    _app_config = AppConfig(_home)
    _dsh = dsh_manager.DshManager(home=_home, app_config=_app_config)
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
