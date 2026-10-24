"""app.py — 桌面端入口。

用法：
  python -m desktop.app                 # 桌面窗口（打包形态为默认入口）
  python -m desktop.app --port 8765     # 指定工作台端口
  python -m desktop.app --smoke         # 无界面冒烟验证（CI / 交付自检）
  python -m desktop.app --smoke --with-dsh   # 冒烟 + 真实启动内置 DSH

--smoke 流程：首启装配 → 依赖指纹 → 教育管线真实运行 → 产物断言
→ （可选）DSH web 启动 + token 访问 200 → 停止。全部通过退出码 0。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from . import bootstrap, dsh_manager, paths  # noqa: E402
from .config import AppConfig  # noqa: E402


def _env_fingerprint() -> dict:
    from scripts.server import env_fingerprint  # 复用 dashboard 的指纹逻辑

    return env_fingerprint()


def start_server(home: Path, port: int):
    from scripts.server import make_server

    return make_server(home=home, port=port)


def _probe_workbench() -> dict:
    """真实起一个工作台 HTTP 服务并请求 /api/health。

    回归：make_server 只绑定不循环（serve_forever 由调用方负责）。窗口流程
    曾因无人调用 serve_forever 而整窗白屏，且不开窗口的冒烟此前测不到。
    """
    import threading

    from scripts.server import make_server

    server = make_server(home=paths.app_home(), port=0)
    thread = threading.Thread(target=server.serve_forever,
                              kwargs={"poll_interval": 0.2}, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/api/health"
        with urllib.request.urlopen(url, timeout=10) as resp:
            ok = resp.status == 200
    except (urllib.error.URLError, OSError):
        ok = False
    finally:
        server.shutdown()
        thread.join(timeout=5)
    return {"ok": ok}


def run_smoke(home: Path, with_dsh: bool) -> int:
    """无界面冒烟验证；打印 JSON 结果，返回退出码。"""
    report: dict = {"ok": True, "steps": {}}

    def fail(step: str, error: str) -> int:
        report["ok"] = False
        report["steps"][step] = {"ok": False, "error": error}
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return 1

    try:
        bs = bootstrap.ensure_home(home=home)
        report["steps"]["bootstrap"] = {"ok": True, "home": bs["home"],
                                        "skills": bs["skills"], "presets": bs["presets"]}
    except Exception as exc:  # noqa: BLE001
        return fail("bootstrap", repr(exc))

    try:
        report["steps"]["env"] = {"ok": True, **_env_fingerprint()}
    except Exception as exc:  # noqa: BLE001
        return fail("env", repr(exc))

    try:
        report["steps"]["workbench-http"] = _probe_workbench()
    except Exception as exc:  # noqa: BLE001
        return fail("workbench-http", repr(exc))
    if not report["steps"]["workbench-http"]["ok"]:
        return fail("workbench-http", "/api/health 未达 200")

    lab = paths.lab_dir(home)
    t0 = time.time()
    rc, err = _run_pipeline(home)
    if rc != 0:
        return fail("education-pipeline", err or f"rc={rc}")
    results = lab / "examples/education-demo/outputs/results.json"
    if not results.is_file():
        return fail("education-pipeline", "results.json 未产出")
    report["steps"]["education-pipeline"] = {
        "ok": True, "seconds": round(time.time() - t0, 1),
        "results_json": str(results)}

    # DSH shell 工具视角：用 DshManager 注入的同一 PATH/env（随包 python
    # shim → 执行桥）在子进程里跑两条管线，证明最终用户的 DSH 会话内
    # `python examples/…` 真实可用，而非仅工作台按钮。
    t0 = time.time()
    env_step = _run_pipeline_via_child_env(home)
    env_step["seconds"] = round(time.time() - t0, 1)
    report["steps"]["shell-env-pipelines"] = env_step
    if not env_step["ok"]:
        return fail("shell-env-pipelines", env_step.get("error", "unknown"))

    if with_dsh:
        mgr = dsh_manager.DshManager(home=home, app_config=AppConfig(home))
        t0 = time.time()
        started = mgr.start()
        if not started.get("ok"):
            return fail("dsh-start", started.get("error", "unknown"))
        url = started["url"]
        code_with, code_without = _probe_dsh(url)
        stopped = mgr.stop()
        # DSH 的 browser-trust fence：带 token → 200/303（set-cookie 跳转）；
        # 无 token → 401 拒绝。两者同时成立才证明是真实 DSH 且凭据隔离有效。
        dsh_ok = code_with in (200, 303) and code_without == 401 and stopped.get("ok")
        report["steps"]["dsh"] = {"ok": dsh_ok,
                                  "with_token": code_with, "without_token": code_without,
                                  "url": url.split("?token=")[0] + "?token=***",
                                  "seconds": round(time.time() - t0, 1)}
        if not dsh_ok:
            return fail("dsh-http", f"token 校验异常：with={code_with} without={code_without}")

    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if report["ok"] else 1


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def _probe_dsh(url: str) -> tuple[int, int]:
    """返回 (带 token 状态码, 不带 token 状态码)。"""
    opener = urllib.request.build_opener(_NoRedirect)

    def one(u: str) -> int:
        try:
            with opener.open(u, timeout=15) as resp:
                return resp.status
        except urllib.error.HTTPError as exc:
            return exc.code
        except (urllib.error.URLError, OSError):
            return 0

    return one(url), one(url.split("?")[0])


def _run_pipeline_via_child_env(home: Path) -> dict:
    """以 DSH 子进程环境（child_env 的 PATH/PYTHONUSERBASE）跑教育与公卫管线。"""
    import subprocess

    mgr = dsh_manager.DshManager(home=home, app_config=AppConfig(home))
    env = mgr.child_env()
    # 模拟受限 shell：不继承开发机 PATH，只保留注入序
    env = {k: v for k, v in env.items() if k in
           ("PATH", "PYTHONUSERBASE", "PYTHONIOENCODING", "LANG", "HOME")}
    lab = paths.lab_dir(home)
    log_dir = home / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    shim = paths.python_shim_dir()
    if not shim:
        return {"ok": False, "error": "python shim 不存在"}
    out: dict = {"ok": True, "python": str(Path(shim) / "python"), "path": env["PATH"]}
    for job, script in (("education", "examples/education-demo/run_t1_t5.py"),
                        ("health", "examples/health-demo/run_h1_h5.py")):
        log_path = log_dir / f"smoke-shell-{job}.log"
        proc = subprocess.run(
            [str(Path(shim) / "python"), str(lab / script)],
            env=env, cwd=str(lab), capture_output=True, text=True, timeout=600)
        log_path.write_text((proc.stdout or "") + (proc.stderr or ""), encoding="utf-8")
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "")[-400:]
            return {"ok": False, "error": f"{job} rc={proc.returncode}: {tail}", **out}
        results = lab / script.replace("run_t1_t5.py", "outputs/results.json") \
            .replace("run_h1_h5.py", "outputs/results.json")
        if not results.is_file():
            return {"ok": False, "error": f"{job} results.json 未产出", **out}
    return out


def _run_pipeline(home: Path) -> tuple[int, str]:
    from . import runner

    lab = paths.lab_dir(home)
    log_dir = home / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "smoke-education.log"
    with log_path.open("w", encoding="utf-8") as lf:
        rc = runner.run_python_script(
            lab / "examples/education-demo/run_t1_t5.py", lf, cwd=lab)
    if rc != 0:
        tail = log_path.read_text(encoding="utf-8", errors="replace")[-600:]
        return rc, tail
    return 0, ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dsh-research-lab-desktop")
    parser.add_argument("--port", type=int, default=0, help="工作台端口（默认自动）")
    parser.add_argument("--home", type=Path, default=None, help="覆盖应用主目录")
    parser.add_argument("--smoke", action="store_true", help="无界面冒烟验证后退出")
    parser.add_argument("--with-dsh", action="store_true", help="smoke 中真实启动内置 DSH")
    args = parser.parse_args(argv)

    home = args.home if args.home is not None else paths.app_home()

    if args.smoke:
        return run_smoke(home, with_dsh=args.with_dsh)

    result = bootstrap.ensure_home(home=home)
    server = start_server(home, args.port)
    # make_server 只绑定不循环（dashboard CLI 自行 serve_forever 阻塞主线程）；
    # 窗口流程主线程被 webview 事件循环占用，服务必须放后台线程。
    import threading
    serve_thread = threading.Thread(target=server.serve_forever,
                                    kwargs={"poll_interval": 0.2}, daemon=True)
    serve_thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    print(json.dumps({"ok": True, "serving": url, "home": str(home),
                      "bootstrap": result}, ensure_ascii=False), flush=True)
    from . import shell
    code = shell.run_window(url)
    server.shutdown()
    serve_thread.join(timeout=5)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
