"""dsh_manager.py — 内置 DSH web 服务生命周期。

以 [内嵌 node, 内嵌 dsh/lib/bin.js, web] 启动真实 DSH（非模拟）：
- DSH_HOME / DSH_AGENTS_HOME 指向应用主目录（与系统全局 DSH 完全隔离）；
- 工作区 cwd 指向可写 lab 工作台目录；
- 模型凭据经 apiKeyEnv 指定的环境变量注入，不落盘；
- stdout 解析 `dsh web: http://127.0.0.1:PORT/?token=...` 拿到带 token 的
  访问地址（无 token 会被 DSH 的 browser-trust fence 以 401 拒绝）；
- 退出时终止子进程（含其子进程进程组）。
"""
from __future__ import annotations

import collections
import re
import shutil
import signal
import socket
import subprocess
import threading
import time
from pathlib import Path

from . import paths, patch_writer
from .config import AppConfig

URL_RE = re.compile(r"https?://127\.0\.0\.1:(\d+)/\?token=([A-Za-z0-9_\-]+)")
READY_TIMEOUT = 60.0
LOG_LINES = 800


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class DshManager:
    """单实例 DSH web 进程管理。线程安全（内部锁）。"""

    def __init__(self, home: Path | None = None, app_config: AppConfig | None = None):
        self.home = Path(home) if home else paths.app_home()
        self.app_config = app_config or AppConfig(self.home)
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._state = "stopped"          # stopped | starting | running | error
        self._error = ""
        self._url = ""
        self._port = 0
        self._log: collections.deque[str] = collections.deque(maxlen=LOG_LINES)

    # -- 状态 ----------------------------------------------------------------
    def status(self) -> dict:
        with self._lock:
            alive = self._proc is not None and self._proc.poll() is None
            if self._state == "running" and not alive:
                rc = self._proc.returncode if self._proc else None
                self._state, self._error = "error", f"DSH 进程已退出（rc={rc}）"
            return {"state": self._state, "url": self._url if self._state == "running" else "",
                    "port": self._port, "error": self._error,
                    "log_tail": list(self._log)[-40:]}

    # -- 子进程环境 -------------------------------------------------------------
    def child_env(self) -> dict:
        """DSH 子进程与其 shell 工具共用的环境（随包依赖，无系统 Python 依赖）。

        PATH 顺序：随包 bin（python/python3 shim → 主可执行执行桥）→
        内嵌 node → 系统基础目录。确保 DSH 里 `python …` 命中的是随包
        桥（带 pandas/statsmodels 等），不会回退到系统 Python。
        """
        node_bin = paths.bundled_node_bin()
        shim_dir = paths.python_shim_dir()
        dirs: list[str] = []
        if shim_dir:
            dirs.append(str(shim_dir))
        if node_bin:
            dirs.append(str(node_bin.parent))
        dirs.append(default_path())
        return {
            "PATH": os_path_sep().join(dirs),
            "PYTHONUSERBASE": str(paths.pylibs_dir()),
            "PYTHONIOENCODING": "utf-8",
            "LANG": "en_US.UTF-8",
            "HOME": os_home(),
            **self.app_config.credential_env(),
        }

    # -- 启动 / 停止 ----------------------------------------------------------
    def start(self) -> dict:
        with self._lock:
            if self._state in ("starting", "running") and self._proc and self._proc.poll() is None:
                return {"ok": True, "state": self._state, "url": self._url}
            self._stop_locked()
            dsh_dir = paths.bundled_dsh_dir()
            node_bin = paths.bundled_node_bin()
            if dsh_dir is None or node_bin is None:
                self._state = "error"
                self._error = "未找到内嵌 DSH 或 Node 运行时（打包不完整？）"
                return {"ok": False, "error": self._error}

            port = free_port()
            self.home.mkdir(parents=True, exist_ok=True)
            patch_writer.sync_patch(self.home, self.app_config)
            dsh_home = self.home / "dsh-home"
            agents_home = dsh_home / "agents"
            agents_home.mkdir(parents=True, exist_ok=True)
            (dsh_home / "skills").mkdir(parents=True, exist_ok=True)

            env = {
                "DSH_HOME": str(dsh_home),
                "DSH_AGENTS_HOME": str(agents_home),
                **self.child_env(),
            }
            cmd = [*paths.dsh_launcher(dsh_dir, node_bin), "web",
                   "--no-open", "--host", "127.0.0.1", "--port", str(port)]
            log_path = self.home / "logs" / "dsh-web.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                self._proc = subprocess.Popen(
                    cmd, cwd=str(paths.lab_dir(self.home)), env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    start_new_session=True)
            except OSError as exc:
                self._state, self._error = "error", f"DSH 启动失败：{exc}"
                return {"ok": False, "error": self._error}

            self._state, self._error = "starting", ""
            self._port = port
            self._log.clear()
            self._log.append(f"$ {' '.join(cmd)}")
            threading.Thread(target=self._pump, args=(log_path,), daemon=True).start()

        # 就绪等待放到锁外（读取状态用短锁）
        deadline = time.time() + READY_TIMEOUT
        while time.time() < deadline:
            st = self.status()
            if st["state"] == "running":
                return {"ok": True, "state": "running", "url": st["url"]}
            if st["state"] == "error":
                return {"ok": False, "error": st["error"] or "DSH 启动超时"}
            time.sleep(0.3)
        self.stop()
        with self._lock:
            self._state, self._error = "error", "DSH 启动超时（60s 内未就绪）"
        return {"ok": False, "error": self._error}

    def stop(self) -> dict:
        with self._lock:
            self._stop_locked()
            self._state = "stopped"
        return {"ok": True, "state": "stopped"}

    def _stop_locked(self) -> None:
        proc, self._proc = self._proc, None
        self._url = ""
        if proc is None:
            return
        if proc.poll() is None:
            try:
                os_killpg(proc.pid)
            except (ProcessLookupError, PermissionError, OSError):
                try:
                    proc.terminate()
                except OSError:
                    pass
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                try:
                    os_killpg(proc.pid, signal.SIGKILL)
                except OSError:
                    pass
                proc.wait(timeout=5)

    # -- 内部 -----------------------------------------------------------------
    def _pump(self, log_path: Path) -> None:
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        try:
            with log_path.open("a", encoding="utf-8") as lf:
                for line in proc.stdout:
                    line = line.rstrip("\n")
                    with self._lock:
                        self._log.append(line)
                        m = URL_RE.search(line)
                        if m and self._state == "starting":
                            self._url = m.group(0)
                            self._port = int(m.group(1))
                            self._state = "running"
                    lf.write(line + "\n")
        except (OSError, ValueError):
            pass


# -- 平台小工具 ---------------------------------------------------------------
def os_path_sep() -> str:
    return ";" if _is_windows() else ":"


def default_path() -> str:
    return "/usr/bin:/bin:/usr/sbin:/sbin"


def os_home() -> str:
    return Path.home().as_posix()


def os_killpg(pid: int, sig: int = signal.SIGTERM) -> None:
    if _is_windows():
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                       capture_output=True)
    else:
        import os as _os
        _os.killpg(pid, sig)


def _is_windows() -> bool:
    return shutil.os.name == "nt"
