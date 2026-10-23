"""dashboard.py — DSH Research Lab 本地工作台（stdlib-only Web UI）

桌面应用（Electron 壳）与命令行（python scripts/dashboard.py）共用的本地服务：
- 首页：环境状态 + 一键运行（教育管线 / 公卫管线 / 总验收）+ 报告与产物浏览
- 运行日志实时查看；产物文件在 outputs 沙箱内浏览（防路径穿越）
- 端口默认 8765，仅绑定 127.0.0.1；无外部依赖（纯标准库）

用法：
  python scripts/dashboard.py [--port 8765]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

if hasattr(sys.stdout, "reconfigure") and (sys.stdout.encoding or "").lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

JOBS = {
    "education": {
        "title": "教育科研管线（T1–T5）",
        "cmd": [sys.executable, "examples/education-demo/run_t1_t5.py"],
        "outputs": "examples/education-demo/outputs",
    },
    "health": {
        "title": "公卫科研管线（H1–H5）",
        "cmd": [sys.executable, "examples/health-demo/run_h1_h5.py"],
        "outputs": "examples/health-demo/outputs",
    },
    "verify": {
        "title": "总验收（49 项对账）",
        "cmd": [sys.executable, "scripts/verify.py"],
        "outputs": "",
    },
}

_state_lock = threading.Lock()
_state: dict[str, dict] = {k: {"status": "idle", "returncode": None,
                               "log_path": "", "started": 0, "ended": 0}
                           for k in JOBS}
LOGS = REPO / "outputs_dashboard"
LOGS.mkdir(exist_ok=True)


def _run_job(job: str) -> None:
    spec = JOBS[job]
    log_path = LOGS / f"{job}.log"
    with _state_lock:
        _state[job] = {"status": "running", "returncode": None, "log_path": str(log_path),
                       "started": time.time(), "ended": 0}
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.run(spec["cmd"], cwd=REPO, stdout=log,
                              stderr=subprocess.STDOUT, text=True)
    with _state_lock:
        _state[job].update({"status": "done" if proc.returncode == 0 else "failed",
                            "returncode": proc.returncode, "ended": time.time()})


def _safe_join(base: Path, rel: str) -> Path | None:
    """产物浏览沙箱：解析后必须仍在 base 内，防路径穿越。"""
    target = (base / rel).resolve()
    try:
        target.relative_to(base.resolve())
    except ValueError:
        return None
    return target


def _job_states() -> dict:
    with _state_lock:
        return {k: dict(v) for k, v in _state.items()}


PAGE = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DSH Research Lab · 本地工作台</title><meta http-equiv="refresh" content="4">
<style>
:root { --navy:#0b1524; --line:rgba(148,163,184,.25); --text:#eaf3ff; --muted:#9fb2c7;
  --blue:#38bdf8; --lime:#a3e635; --gold:#fbbf24; --pink:#f472b6; }
* { box-sizing:border-box; } body { margin:0; color:var(--text); font-size:15px; line-height:1.6;
  background:radial-gradient(900px 480px at 80% -10%, rgba(56,189,248,.16), transparent),
  linear-gradient(145deg,var(--navy),#101e33); min-height:100vh;
  font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; }
header { padding:26px 28px 8px; } h1 { margin:0 0 4px; font-size:22px; letter-spacing:-.02em; }
header p { margin:0; color:var(--muted); font-size:13px; }
main { max-width:980px; margin:auto; padding:18px 28px 40px; }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:12px; }
.card { border:1px solid var(--line); border-radius:14px; padding:16px; background:rgba(255,255,255,.04); }
.card h3 { margin:0 0 8px; font-size:15px; } .card p { margin:0 0 12px; color:var(--muted); font-size:12.5px; }
button, a.btn { display:inline-block; border:0; border-radius:10px; padding:8px 14px; font-size:13px;
  font-weight:700; cursor:pointer; text-decoration:none; color:#06121f;
  background:linear-gradient(135deg,var(--blue),#6366f1); }
button.alt { background:linear-gradient(135deg,var(--lime),var(--cyan)); }
button:disabled { opacity:.5; cursor:wait; }
.state { font-size:12px; padding:2px 9px; border-radius:999px; border:1px solid var(--line); }
.ok { color:var(--lime); } .bad { color:var(--pink); } .run { color:var(--gold); }
pre { background:#0a1220; border:1px solid var(--line); border-radius:12px; padding:14px;
  font-size:12px; overflow:auto; max-height:320px; }
ul.out { margin:6px 0 0; padding-left:18px; font-size:13px; }
ul.out a { color:var(--blue); }
.note { color:var(--muted); font-size:12px; margin-top:14px; }
</style></head><body>
<header><h1>🧪 DSH Research Lab 本地工作台</h1>
<p>真实公开数据 · 全部统计来自本机真实执行 · 仅监听 127.0.0.1</p></header>
<main>
  <div class="grid">
    %%CARDS%%
  </div>
  <h3 style="margin:22px 0 8px">产物浏览</h3>
  <ul class="out">%%OUTPUTS%%</ul>
  <p class="note">接入 DSH 智能体：终端运行 <code>dsh web</code> 并把工作区指向本目录；
  框架文档见仓库 README 与 docs/。本页每 4 秒自动刷新。</p>
</main></body></html>"""

CARD = """<div class="card"><h3>{title}</h3>
<p>{desc}</p>
<div><button data-job="{job}" {disabled}>▶ 运行</button>
<span class="state {cls}">{label}</span>
<a class="btn" style="margin-left:8px;background:rgba(148,163,184,.25);color:var(--text)" href="/log?job={job}">日志</a></div>
</div>"""


def render() -> bytes:
    st = _job_states()
    cards = []
    desc = {"education": "审计→关联/组间检验→回归诊断→泄漏对照→报告（649 名中学生真实数据）",
            "health": "审计→基线筛查/OR→防泄漏建模→ROC/阈值/校准→报告（303 例真实病例）",
            "verify": "SHA256 → 确定性复跑 → 双实现交叉验证 → 协议断言（49 项）"}
    for job, spec in JOBS.items():
        s = st[job]
        running = s["status"] == "running"
        cls, label = (("run", "运行中") if running else
                      ("ok", f"完成 rc=0") if s["status"] == "done" else
                      ("bad", f"失败 rc={s['returncode']}") if s["status"] == "failed"
                      else ("", "未运行"))
        cards.append(CARD.format(job=job, title=spec["title"], desc=desc[job],
                                 disabled="disabled" if running else "",
                                 cls=cls, label=label))
    outs = []
    for job in ("education", "health"):
        base = REPO / JOBS[job]["outputs"]
        if base.exists():
            outs.append(f"<li><b>{JOBS[job]['title']}</b> → "
                        f"<a href='/outputs?job={job}'>{JOBS[job]['outputs']}</a></li>")
    for job in ("education", "health"):
        report = REPO / JOBS[job]["outputs"] / "report.md"
        if report.exists():
            outs.append(f"<li><a href='/file?job={job}&name=report.md'>打开 "
                        f"{job} 报告 report.md</a></li>")
    html = PAGE.replace("%%CARDS%%", "".join(cards)).replace(
        "%%OUTPUTS%%", "".join(outs) or "<li>尚无产物，先运行管线</li>")
    return html.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # 静默访问日志
        pass

    def _send(self, body: bytes, ctype="text/html; charset=utf-8", code=200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        from urllib.parse import parse_qs, urlparse
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/":
            self._send(render())
        elif u.path == "/api/health":
            self._send(b'{"ok":true}', "application/json")
        elif u.path == "/log":
            job = q.get("job", ["verify"])[0]
            log = LOGS / f"{job}.log"
            text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else "（暂无日志）"
            self._send(f"<meta http-equiv='refresh' content='3'><pre style='background:#0a1220;color:#cfe3ff;padding:18px;white-space:pre-wrap'>{text[-8000:]}</pre><p><a href='/' style='color:#38bdf8'>← 返回</a></p>".encode())
        elif u.path == "/file":
            job, name = q.get("job", [""])[0], q.get("name", [""])[0]
            base = REPO / JOBS.get(job, {}).get("outputs", "")
            f = _safe_join(base, name) if base else None
            if f and f.is_file() and f.suffix in {".md", ".json", ".csv", ".png", ".txt"}:
                if f.suffix == ".png":
                    self._send(f.read_bytes(), "image/png")
                else:
                    self._send(f.read_text(encoding="utf-8", errors="replace").encode())
            else:
                self._send(b"not found or not allowed", code=404)
        elif u.path == "/outputs":
            job = q.get("job", ["education"])[0]
            base = REPO / JOBS.get(job, {}).get("outputs", "")
            rows = []
            if base.exists():
                for f in sorted(base.rglob("*")):
                    if f.is_file():
                        rel = f.relative_to(base)
                        rows.append(f"<li><a href='/file?job={job}&name={rel}'>{rel}</a></li>")
            self._send(("<ul>" + "".join(rows) + "</ul><p><a href='/' style='color:#38bdf8'>← 返回</a></p>").encode())
        else:
            self._send(b"not found", code=404)

    def do_POST(self):
        from urllib.parse import parse_qs, urlparse
        u = urlparse(self.path)
        if u.path == "/run":
            job = parse_qs(u.query).get("job", [""])[0]
            if job not in JOBS:
                self._send(b"bad job", code=400)
                return
            if _job_states()[job]["status"] == "running":
                self._send(b'{"ok":false,"error":"already running"}', "application/json", 409)
                return
            threading.Thread(target=_run_job, args=(job,), daemon=True).start()
            self._send(b'{"ok":true}', "application/json")
        else:
            self._send(b"not found", code=404)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}"
    print(json.dumps({"ok": True, "serving": url}), flush=True)
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
