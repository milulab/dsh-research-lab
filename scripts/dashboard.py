"""dashboard.py — DSH Research Lab 本地工作台（命令行入口）。

桌面应用与命令行共用的服务在 scripts/server.py；本文件提供纯命令行
用法（浏览器打开，不依赖 pywebview）：

  python scripts/dashboard.py [--port 8765]
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser
from http.server import ThreadingHTTPServer

REPO = __import__("pathlib").Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from desktop import paths  # noqa: E402
from desktop.bootstrap import ensure_home  # noqa: E402
from scripts.server import make_server  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--home", type=__import__("pathlib").Path, default=None)
    args = parser.parse_args()

    home = args.home if args.home is not None else paths.app_home()
    ensure_home(home=home)
    server: ThreadingHTTPServer = make_server(home=home, port=args.port)
    url = f"http://127.0.0.1:{server.server_address[1]}"
    print(json.dumps({"ok": True, "serving": url, "home": str(home)}), flush=True)
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
