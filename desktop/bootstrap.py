"""bootstrap.py — 桌面应用首启装配。

把出厂模板（.app 内只读 Resources/lab）落到用户可写主目录：
- lab/        科研工作台（工作区，管线在此产出、DSH 以此为 cwd）
- dsh-home/   DSH 主目录（skills / .agent-presets / profiles）
- logs/

幂等：按出厂 manifest 版本标记；升级时刷新模板但保留 outputs/ 与
dsh-home 中的用户凭据引用（cordis.patch.yml 由 patch_writer 管理）。
"""
from __future__ import annotations

import shutil
from pathlib import Path

from . import paths, patch_writer
from .config import AppConfig

_MARK = ".bootstrap-version"
# 同步时保留 dst 侧的目录（用户产物/本机环境），以路径部件做前缀匹配，
# 任何层级递归都基于完整相对路径判断——不会因子目录层重置而误覆盖。
_KEEP_PARTS: tuple[tuple[str, ...], ...] = (
    ("outputs_dashboard",),
    ("examples", "education-demo", "outputs"),
    ("examples", "health-demo", "outputs"),
)
_KEEP_NAMES = frozenset({".git", ".venv", "__pycache__", ".pytest_cache"})


class BootstrapResult(dict):
    pass


def ensure_home(manifest: dict | None = None, home: Path | None = None,
                app_config: AppConfig | None = None) -> BootstrapResult:
    """确保主目录可用并返回装配结果（幂等）。"""
    manifest = manifest or paths.manifest()
    home = Path(home) if home else paths.app_home()
    app_config = app_config or AppConfig(home)
    home.mkdir(parents=True, exist_ok=True)

    result = BootstrapResult(home=str(home), version=manifest.get("version", "?"),
                             copied=False, skills=0, presets=0)

    template = paths.bundled_lab_template()
    lab = home / "lab"
    if template is not None:
        current = (home / _MARK).read_text(encoding="utf-8").strip() \
            if (home / _MARK).is_file() else ""
        if not lab.exists() or current != manifest.get("version", ""):
            _sync_tree(template, lab)
            (home / _MARK).write_text(manifest.get("version", ""), encoding="utf-8")
            result["copied"] = True

    # DSH 主目录：skills 与 presets 从工作台安装（与 install.sh 等价的
    # 正确位置：$DSH_HOME/skills 与 $DSH_HOME/.agent-presets）。
    # 打包形态源为只读出厂模板；开发形态源即仓库本身。
    install_src = template if template is not None else paths.repo_root()
    skills_src = install_src / "skills"
    presets_src = install_src / "presets"
    if skills_src.is_dir():
        n = 0
        for skill in sorted(skills_src.iterdir()):
            if skill.is_dir() and (skill / "SKILL.md").is_file():
                _sync_tree(skill, home / "dsh-home" / "skills" / skill.name)
                n += 1
        result["skills"] = n
    if presets_src.is_dir():
        n = 0
        for preset in sorted(presets_src.iterdir()):
            if preset.is_dir() and (preset / "preset.yml").is_file():
                _sync_tree(preset, home / "dsh-home" / ".agent-presets" / preset.name)
                n += 1
        result["presets"] = n

    # web profile 凭据引用 patch（未配 key 时为空数组，DSH 正常启动）
    patch_writer.sync_patch(home, app_config)

    (home / "logs").mkdir(exist_ok=True)
    return result


def _sync_tree(src: Path, dst: Path, _rel: tuple[str, ...] = ()) -> None:
    """目录同步：新增/覆盖出厂文件，保留 dst 侧的用户产物。

    _rel 为当前节点相对同步根的部件路径，跨层级累积，用于按完整相对
    路径匹配 _KEEP_PARTS（避免每层重置导致覆盖用户 outputs）。
    """
    dst.mkdir(parents=True, exist_ok=True)
    for item in sorted(src.iterdir()):
        rel = _rel + (item.name,)
        if item.name in _KEEP_NAMES:
            continue
        if any(rel[:len(keep)] == keep for keep in _KEEP_PARTS):
            continue
        target = dst / item.name
        if item.is_dir():
            _sync_tree(item, target, rel)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
