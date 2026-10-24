"""desktop 层单元测试：执行桥语义、bootstrap 保留规则、config/patch、URL 解析。"""
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from desktop import bridge, paths  # noqa: E402
from desktop.bootstrap import _sync_tree  # noqa: E402
from desktop.config import API_KEY_ENV, AppConfig  # noqa: E402
from desktop.dsh_manager import URL_RE  # noqa: E402
from desktop.patch_writer import build_patch  # noqa: E402


# -- python 执行桥 -------------------------------------------------------------
def test_bridge_version():
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert bridge.run_argv(["--version"]) == 0
    assert "Python" in buf.getvalue()


def test_bridge_c_code_and_path_semantics(tmp_path):
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert bridge.run_argv(["-c", "import sys; print(sys.argv[1]); print(__import__('os').getcwd() == sys.path[1] or sys.path[0])", "hello"]) == 0
    lines = buf.getvalue().splitlines()
    assert lines[0] == "hello"


def test_bridge_script_sys_argv_and_exit_code(tmp_path):
    script = tmp_path / "echo_argv.py"
    script.write_text("import sys\nprint(len(sys.argv), sys.argv[0].endswith('echo_argv.py'))\n"
                      "raise SystemExit(7)\n")
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert bridge.run_argv([str(script), "a", "b"]) == 7
    assert buf.getvalue().splitlines()[0] == "3 True"


def test_bridge_script_dir_on_sys_path(tmp_path):
    pkg = tmp_path / "myhelper.py"
    pkg.write_text("VALUE = 42\n")
    script = tmp_path / "main_script.py"
    script.write_text("import myhelper; print(myhelper.VALUE)\n")
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert bridge.run_argv([str(script)]) == 0
    assert buf.getvalue().strip() == "42"


def test_bridge_module_and_missing_script():
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        assert bridge.run_argv(["-m", "json.tool", "--version"]) in (0, 2)
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        assert bridge.run_argv(["/nonexistent/nope.py"]) == 2
    assert "can't open file" in err.getvalue()


# -- DSH token URL 解析 --------------------------------------------------------
def test_url_re_parses_stdout_line():
    line = "dsh web: http://127.0.0.1:18791/?token=G0kub7ZepmatuXONSnINx-ZGFqKFN02xMnssm7QShSk"
    m = URL_RE.search(line)
    assert m and m.group(1) == "18791"
    assert URL_RE.search("unrelated line") is None


# -- config / patch（凭据绝不落盘） ---------------------------------------------
def test_config_roundtrip_and_key_never_in_patch(tmp_path):
    cfg = AppConfig(tmp_path)
    cfg.save({"api_key": "sk-secret-123", "model": "deepseek-chat",
              "provider": "deepseek"})
    assert cfg.has_key()
    assert (tmp_path / "config.json").stat().st_mode & 0o777 == 0o600
    patch = build_patch(cfg.load())
    dumped = json.dumps(patch)
    assert "sk-secret-123" not in dumped
    deepseek_entry = patch[0]
    assert deepseek_entry["config"]["apiKeyEnv"] == API_KEY_ENV
    assert patch[1]["config"]["provider"] == "deepseek-official"


def test_patch_openai_compat_requires_base_url():
    with pytest.raises(ValueError):
        build_patch({"provider": "openai-compat", "api_key": "k", "base_url": ""})
    entries = build_patch({"provider": "openai-compat", "api_key": "k",
                           "base_url": "https://gw.example/v1", "model": "m1"})
    prov = entries[0]["config"]["providers"]
    (pbody,) = prov.values()
    assert pbody["api"] == "openai-completions" and pbody["apiKeyEnv"] == API_KEY_ENV
    assert entries[1]["config"]["provider"] in prov


def test_sync_patch_empty_without_key(tmp_path):
    cfg = AppConfig(tmp_path)
    from desktop.patch_writer import sync_patch
    target = sync_patch(tmp_path, cfg)
    assert target.read_text().strip() == "[]"


# -- bootstrap 保留规则（回归：不得覆盖用户产物） -------------------------------
def _mkdirs(base: Path, rel: str) -> Path:
    p = base / rel
    p.mkdir(parents=True, exist_ok=True)
    return p


def test_sync_tree_preserves_user_outputs(tmp_path):
    src, dst = tmp_path / "src", tmp_path / "dst"
    # 出厂模板：examples/education-demo 下模板文件（outputs 不随包分发，
    # 是用户数据区；这里故意放一个"工厂示例"验证整树跳过语义）
    _mkdirs(src, "examples/education-demo/outputs/tables")
    (src / "examples/education-demo/outputs/tables/old.csv").write_text("factory\n")
    _mkdirs(src, "examples/education-demo")
    (src / "examples/education-demo/protocol.md").write_text("proto\n")
    # 用户产物：outputs 下已有 results.json 与 figures/new.png
    user_dir = _mkdirs(dst, "examples/education-demo/outputs/figures")
    (dst / "examples/education-demo/outputs/results.json").write_text("{}\n")
    (user_dir / "new.png").write_bytes(b"\x89PNG")
    # 出厂新增文件（模板新增，应同步进来）
    _mkdirs(src, "tools")
    (src / "tools/newtool.py").write_text("x = 1\n")

    _sync_tree(src, dst)

    # 用户产物保留、工厂文件不落入用户 outputs 区
    assert (dst / "examples/education-demo/outputs/results.json").read_text() == "{}\n"
    assert (user_dir / "new.png").read_bytes() == b"\x89PNG"
    assert not (dst / "examples/education-demo/outputs/tables").exists()
    # 模板文件同步（非保留区）
    assert (dst / "examples/education-demo/protocol.md").read_text() == "proto\n"
    assert (dst / "tools/newtool.py").read_text() == "x = 1\n"


def test_sync_tree_keep_matches_exact_prefix_not_substr(tmp_path):
    src, dst = tmp_path / "src", tmp_path / "dst"
    # outputs_dashboard_x 不是保留目录（部件级匹配，非字符串前缀）
    _mkdirs(src, "outputs_dashboard_x")
    (src / "outputs_dashboard_x/f.txt").write_text("v\n")
    _sync_tree(src, dst)
    assert (dst / "outputs_dashboard_x/f.txt").exists()


# -- paths（开发形态） ---------------------------------------------------------
def test_paths_dev_mode_repo_layout():
    if paths.bundled_root() is not None:
        pytest.skip("packaged build")
    assert (paths.repo_root() / "tools").is_dir()
    # DSH 为可选运行时：未安装（CI 纯测试环境）时探测应返回 None 而非抛错
    dsh_dir = paths.bundled_dsh_dir()
    if dsh_dir is not None:
        assert (dsh_dir / "lib" / "bin.js").is_file()
    shim = paths.python_shim_dir()
    assert shim and (shim / "python").exists()


# -- 窗口壳（回归：js_api 属于 create_window，不是 start） ----------------------
def test_shell_window_passes_js_api_to_create_window(monkeypatch):
    """回归：pywebview 的 js_api 是 create_window() 参数；传给 start() 会
    TypeError 且仅在打包形态暴露（冒烟不开窗口，此前漏测）。"""
    from desktop import shell

    calls = {}

    class FakeWebview:
        @staticmethod
        def create_window(title, url, **kw):
            calls["title"], calls["url"], calls["kw"] = title, url, kw

        @staticmethod
        def start(*args, **kw):
            calls["start_args"] = (args, kw)

    monkeypatch.setitem(sys.modules, "webview", FakeWebview)
    rc = shell.run_window("http://127.0.0.1:8123/")
    assert rc == 0
    assert calls["url"] == "http://127.0.0.1:8123/"
    assert isinstance(calls["kw"].get("js_api"), shell.LabApi)
    assert calls["start_args"] == ((), {})
