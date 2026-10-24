"""desktop_main.py — 桌面端打包入口（PyInstaller 指定此文件）。

分发两种模式：
- `DSHResearchLab [app 参数…]`：桌面工作台窗口；
- `DSHResearchLab --python-bridge [python 参数…]`：随包 Python 执行桥，
  由 Resources/bin/{python,python3} shim 调用，供 DSH 的 shell 工具运行
  科研脚本（无系统 Python 依赖）。
"""
from __future__ import annotations

import sys


def main() -> int:
    argv = sys.argv[1:]
    if argv and argv[0] == "--python-bridge":
        from desktop import bridge, paths

        # 执行桥的 import 语义扩展：工作台根（tools/ 等）与用户扩展包目录。
        # 标准语义（脚本目录 / -c 与 -m 的 cwd）由 bridge 自行 insert(0, …)。
        pylibs = paths.app_home() / "pylibs"
        pylibs.mkdir(parents=True, exist_ok=True)
        for p in (str(paths.lab_dir()), str(pylibs)):
            if p not in sys.path:
                sys.path.insert(0, p)
        return bridge.run_argv(argv[1:])

    from desktop.app import main as app_main
    return app_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
