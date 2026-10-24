"""desktop 集成冒烟：本地服务 API 与 DSH 子进程环境下的真实管线执行。

不启动 DSH web（那属于打包验证，见 scripts/build_desktop.py --verify）；
这里验证桌面层在源码形态下的可运行性与凭据不泄露。
"""
import json
import sys
import threading
import time
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    from desktop.config import AppConfig
    from scripts.server import make_server

    home = tmp_path_factory.mktemp("dshrl-int")
    AppConfig(home).save({"model": "deepseek-chat", "api_key": "sk-int-test"})
    srv = make_server(home=home, port=0)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.2)
    yield f"http://127.0.0.1:{port}", home
    srv.shutdown()


def _get(base: str, path: str) -> dict:
    with urllib.request.urlopen(base + path, timeout=10) as r:
        return json.loads(r.read())


def test_server_health_and_env(server):
    base, _ = server
    assert _get(base, "/api/health") == {"ok": True}
    env = _get(base, "/api/env")
    assert env["deps"]["pandas"] != "缺失"
    # DSH 为可选运行时；存在性在 desktop-build CI（安装 dsh）中强制断言
    if env["dsh_ok"]:
        assert env["dsh"]


def test_server_settings_never_echo_key(server):
    base, _ = server
    s = _get(base, "/api/settings")
    assert s["has_key"] is True
    assert "sk-int-test" not in json.dumps(s)


def test_server_jobs_and_outputs(server):
    base, _ = server
    jobs = _get(base, "/api/jobs")
    assert set(jobs) == {"education", "health", "verify"}
    assert _get(base, "/api/outputs")["html"] is not None


def test_dsh_child_env_runs_pipeline(server):
    """DSH 子进程同款 PATH/env 下，教育管线真实执行并产出 results.json。"""
    import subprocess

    base, home = server
    from desktop import paths
    from desktop.dsh_manager import DshManager
    from desktop.config import AppConfig

    if paths.bundled_dsh_dir() is None:
        pytest.skip("DSH 运行时不可用（CI 纯测试环境）；完整验证见 build_desktop --verify")
    env = DshManager(home=home, app_config=AppConfig(home)).child_env()
    lab = paths.lab_dir(home)
    shim = paths.python_shim_dir()
    script = lab / "examples/education-demo/run_t1_t5.py"
    proc = subprocess.run(
        [str(shim / "python"), str(script)],
        env=env, cwd=str(lab), capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, (proc.stdout + proc.stderr)[-800:]
    assert (lab / "examples/education-demo/outputs/results.json").is_file()
