"""bridge.py — 随包 Python 执行桥。

打包形态下 PyInstaller 的主可执行文件不是完整解释器，但 DSH 的 shell
工具（bash）需要能调用 `python` 运行科研脚本。为此主可执行支持
`--python-bridge` 模式，并随包提供 python/python3 shim 把调用转到本桥。

复刻 CPython 的关键语义（DSH 工具与管线脚本依赖这些）：
- `python script.py args…`：sys.path[0]=脚本所在目录；sys.argv=[脚本路径, args…]
- `python -c code args…`：sys.path[0]=cwd；sys.argv=['-c', args…]
- `python -m module args…`：sys.path[0]=cwd；以 __main__ 运行模块
- `python --version`、退出码透传（SystemExit）、异常打印 traceback 并返回 1

调用前（见 desktop_main）已把工作台根与用户扩展包目录（pylibs）插入
sys.path，使 `python tools/data_audit.py`、`python -m pip --user` 等可用。
"""
from __future__ import annotations

import runpy
import sys
import traceback
from pathlib import Path


def exec_script_file(script: Path) -> None:
    """以 __main__ 执行脚本文件（compile+exec，兼容 PyInstaller 冻结环境；
    runpy.run_path 在 frozen 下会因模块查找机制失效）。保留 __file__ 语义，
    管线脚本依赖它推导仓库根。"""
    code = compile(script.read_bytes(), str(script), "exec")
    globs = {"__name__": "__main__", "__file__": str(script),
             "__builtins__": __builtins__}
    exec(code, globs)  # noqa: S102 —— 执行用户指定脚本，与 CPython 语义一致

USAGE = """usage: python [option] … [-c cmd | -m mod | script.py] [args] …
       python --version
(DSH Research Lab bundled Python bridge; scientific deps preinstalled)"""


def run_argv(argv: list[str]) -> int:
    """执行桥主逻辑；argv 不含 '--python-bridge' 本身。返回进程退出码。"""
    if not argv:
        print(USAGE, file=sys.stderr)
        return 2
    head = argv[0]

    if head in ("-h", "--help"):
        print(USAGE)
        return 0
    if head in ("-V", "--version"):
        print(f"Python {sys.version.split()[0]} (DSH Research Lab bundled)")
        return 0

    cwd = Path.cwd()
    old_argv = sys.argv
    try:
        if head == "-c":
            code = argv[1] if len(argv) > 1 else ""
            sys.path.insert(0, str(cwd))
            sys.argv = ["-c", *argv[2:]]
            exec(compile(code, "<string>", "exec"),
                 {"__name__": "__main__", "__builtins__": __builtins__})
            return 0
        if head == "-m":
            if len(argv) < 2:
                print("python: module name required after -m", file=sys.stderr)
                return 2
            sys.path.insert(0, str(cwd))
            sys.argv = [cwd.as_posix(), *argv[2:]]
            runpy.run_module(argv[1], run_name="__main__", alter_sys=True)
            return 0

        script = Path(head)
        if not script.is_absolute():
            script = cwd / script
        if not script.is_file():
            print(f"python: can't open file '{head}': No such file or directory",
                  file=sys.stderr)
            return 2
        sys.path.insert(0, str(script.parent))
        sys.argv = [str(script), *argv[1:]]
        exec_script_file(script)
        return 0
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
    except BaseException:  # noqa: BLE001 —— 与 CPython 一致：打印 traceback，退出码 1
        traceback.print_exc()
        return 1
    finally:
        sys.argv = old_argv


if __name__ == "__main__":
    raise SystemExit(run_argv(sys.argv[1:]))
