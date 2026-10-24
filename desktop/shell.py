"""shell.py — pywebview 桌面窗口壳。

pywebview 在 macOS 使用系统 WKWebView（无额外浏览器运行时）。缺失该可选
依赖时优雅降级：打印工作台地址由系统浏览器打开。
"""
from __future__ import annotations

import json


class LabApi:
    """暴露给页面 JS 的桥：window.pywebview.api.*"""

    def __init__(self):
        import webview  # noqa: F401 —— shell 仅在 pywebview 可用时被调用

    def open_dsh(self, url: str):
        """在新窗口打开 DSH Web UI（带 token 的本机地址）。"""
        import webview
        webview.create_window("DSH 智能体", url, width=1280, height=860)
        return {"ok": True}

    def reveal_path(self, path: str):
        """在系统文件管理器中显示产物目录。"""
        import subprocess
        import sys
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        elif sys.platform == "win32":
            subprocess.Popen(["explorer", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return {"ok": True}


def run_window(url: str) -> int:
    try:
        import webview
    except ImportError:
        print(json.dumps({"ok": False, "fallback": "browser", "url": url,
                          "hint": "未安装 pywebview，请在浏览器打开以上地址"}), flush=True)
        return 2
    webview.create_window("DSH Research Lab", url, width=1280, height=860,
                          min_size=(980, 640), js_api=LabApi())
    webview.start()
    return 0
