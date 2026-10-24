"""runner.py — 科研管线执行器（开发 / 打包双形态）。

开发形态：sys.executable 子进程运行脚本。
打包形态（PyInstaller frozen）：主可执行文件不是完整解释器，无法
`app_exe script.py` 方式再启动，因此在进程内 runpy 执行（stdout/stderr
重定向到日志文件）。管线脚本通过 __file__ 推导仓库根，落到工作区后
自洽。
"""
from __future__ import annotations

import contextlib
import subprocess
import sys
import traceback
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def run_python_script(script: Path, log_file, cwd: Path | None = None) -> int:
    """运行一个科研管线/验收脚本，返回退出码；日志写入 log_file。"""
    script = Path(script)
    if not is_frozen():
        proc = subprocess.run(
            [sys.executable, str(script)],
            stdout=log_file, stderr=subprocess.STDOUT,
            cwd=str(cwd) if cwd else str(script.parents[2]),
            text=True)
        return proc.returncode

    code = 0
    old_out, old_err = sys.stdout, sys.stderr
    try:
        with contextlib.redirect_stdout(log_file), contextlib.redirect_stderr(log_file):
            from .bridge import exec_script_file

            exec_script_file(script)
    except SystemExit as exc:  # 脚本主动退出
        code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
    except BaseException:  # noqa: BLE001 —— 记录后按失败退出
        traceback.print_exc(file=log_file)
        code = 1
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    return code
