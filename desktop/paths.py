"""paths.py — 桌面应用的资源定位与应用主目录。

两种运行形态：
- 打包形态（PyInstaller onedir，.app 内）：捆绑资源在 Contents/Resources/
  （manifest.json / lab/ / node/ / dsh/），工作区与用户数据在应用主目录；
- 开发形态（源码仓库内直接运行）：捆绑资源回退到仓库本身与系统 PATH。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "DSHResearchLab"


def repo_root() -> Path:
    """开发形态的仓库根目录；打包形态返回工作区 lab 目录（由 bootstrap 装配）。"""
    if bundled_root() is not None:
        home = app_home()
        return home / "lab"
    return Path(__file__).resolve().parents[1]


def lab_dir(home: Path | None = None) -> Path:
    """DSH 工作区与管线 cwd：打包形态为可写主目录 lab/，开发形态为仓库根。"""
    if bundled_root() is not None:
        return (Path(home) if home else app_home()) / "lab"
    return repo_root()


def bundled_root() -> Path | None:
    """打包形态下 Contents/Resources 目录；开发形态返回 None。"""
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        res = exe.parent.parent / "Resources"
        if (res / "manifest.json").is_file():
            return res
    return None


def app_home() -> Path:
    """用户数据主目录（config / lab 工作区 / dsh-home / logs）。"""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / APP_DIR_NAME


def manifest() -> dict:
    """出厂清单（构建时生成）：版本、DSH/Node 版本、架构、构建信息。"""
    import json

    bundled = bundled_root()
    if bundled is None:
        return {"mode": "dev", "version": "0.0.0.dev"}
    return json.loads((bundled / "manifest.json").read_text(encoding="utf-8"))


def bundled_lab_template() -> Path | None:
    bundled = bundled_root()
    return (bundled / "lab") if bundled else None


def bundled_node_bin() -> Path | None:
    """打包形态返回内嵌 node 可执行文件；开发形态从 PATH 查找。"""
    bundled = bundled_root()
    if bundled is not None:
        node = bundled / "node" / "bin" / "node"
        return node if node.is_file() else None
    return _which("node")


def bundled_dsh_dir() -> Path | None:
    """打包形态返回内嵌 @deepseek-ai/dsh 包目录；开发形态从 PATH 推断。"""
    bundled = bundled_root()
    if bundled is not None:
        dsh = bundled / "dsh"
        if (dsh / "package.json").is_file():
            return dsh
    return _system_dsh_dir()


def python_shim_dir() -> Path | None:
    """随包 python shim 所在目录（注入 DSH 子进程 PATH，供 shell 工具调用）。

    打包形态：Resources/bin（python → 主可执行 --python-bridge）。
    开发形态：回退到当前解释器所在目录（.venv/bin；注意不 resolve，
    venv symlink 解析后会落到无依赖的基础解释器目录）。
    """
    bundled = bundled_root()
    if bundled is not None:
        d = bundled / "bin"
        return d if (d / "python").is_file() else None
    d = Path(sys.executable).parent
    return d if (d / "python" if sys.platform != "win32" else d / "python.exe").exists() else None


def pylibs_dir() -> Path:
    """用户扩展包目录（PYTHONUSERBASE）：pip --user 的落点，桥可 import。"""
    d = app_home() / "pylibs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def dsh_launcher(dsh_dir: Path, node_bin: Path) -> list[str]:
    """以 [node, lib/bin.js] 方式启动 DSH，避免依赖 shebang 与执行位。"""
    return [str(node_bin), str(dsh_dir / "lib" / "bin.js")]


def _which(name: str) -> Path | None:
    found = None
    for d in os.environ.get("PATH", "").split(os.pathsep):
        cand = Path(d) / name
        if cand.is_file():
            found = cand
            break
    return found


def _system_dsh_dir() -> Path | None:
    """开发形态：从 PATH 中的 dsh 推断 npm 全局包目录。"""
    bin_path = _which("dsh")
    if bin_path is None:
        return None
    try:
        real = bin_path.resolve()
        # <npm-global>/bin/dsh → <npm-global>/lib/node_modules/@deepseek-ai/dsh
        for parent in real.parents:
            cand = parent / "lib" / "node_modules" / "@deepseek-ai" / "dsh"
            if (cand / "package.json").is_file():
                return cand
        # Windows 布局：<npm-global>/node_modules/@deepseek-ai/dsh
        for parent in real.parents:
            cand = parent / "node_modules" / "@deepseek-ai" / "dsh"
            if (cand / "package.json").is_file():
                return cand
    except OSError:
        return None
    return None
