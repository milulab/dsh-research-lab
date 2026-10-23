"""build_package.py — 构建分发包（打包与发布入口）

产出（dist/ 下）：
  dsh-research-lab-<version>-<platform>-<arch>.<zip|tar.gz>   平台分发包
  dsh-research-lab-<version>-checksums.sha256                 全部校验和

平台差异（Python + 模板框架，无原生编译产物）：
  - Windows → .zip（PowerShell 友好）；
  - macOS / Linux → .tar.gz；
包内容一致：presets/ skills/ domains/ datasets/ tools/ scripts/ templates/
examples/ docs/ tests/ + README/LICENSE/requirements/pyproject + website/。
排除：.git .venv __pycache__ examples/*/outputs .github dist。

用法：python scripts/build_package.py [--out dist]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INCLUDE_DIRS = [
    "presets", "skills", "domains", "datasets", "tools", "scripts",
    "templates", "examples", "docs", "tests", "website", ".github",
]
INCLUDE_FILES = [
    "README.md", "README.en.md", "LICENSE", "THIRD_PARTY_NOTICES.md",
    "CHANGELOG.md", "pyproject.toml", "requirements.txt", ".gitignore",
]
EXCLUDE_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", "outputs", "dist"}
EXCLUDE_SUFFIX = {".pyc", ".DS_Store"}


def version_of() -> str:
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("version"):
            return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("version not found in pyproject.toml")


def collect_staging(staging: Path) -> int:
    n = 0
    for name in INCLUDE_DIRS:
        src = REPO / name
        if not src.exists():
            continue
        for root, dirs, files in src.walk(on_error=None):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_PARTS]
            rel_dir = root.relative_to(REPO)
            (staging / rel_dir).mkdir(parents=True, exist_ok=True)
            for f in files:
                if f in EXCLUDE_PARTS or f.startswith(".DS_Store") or f.endswith(tuple(EXCLUDE_SUFFIX)):
                    continue
                shutil.copy2(root / f, staging / rel_dir / f)
                n += 1
    for name in INCLUDE_FILES:
        src = REPO / name
        if src.exists():
            shutil.copy2(src, staging / name)
            n += 1
    return n


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="dist")
    args = parser.parse_args()
    out = REPO / args.out
    out.mkdir(exist_ok=True)

    version = version_of()
    system = platform.system().lower()          # darwin / windows / linux
    machine = platform.machine().lower()        # arm64 / x86_64 / amd64
    base = f"dsh-research-lab-{version}-{system}-{machine}"

    staging = REPO / f".package-{base}"
    if staging.exists():
        shutil.rmtree(staging)
    pkg_root = staging / f"dsh-research-lab-{version}"
    pkg_root.mkdir(parents=True)
    n_files = collect_staging(pkg_root)

    artifacts: list[Path] = []
    if system == "windows":
        target = out / f"{base}.zip"
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(pkg_root.rglob("*")):
                zf.write(p, p.relative_to(staging))
        artifacts.append(target)
    else:
        target = out / f"{base}.tar.gz"
        with tarfile.open(target, "w:gz") as tf:
            tf.add(pkg_root, arcname=f"dsh-research-lab-{version}")
        artifacts.append(target)

    shutil.rmtree(staging)

    # 校验和清单
    lines = []
    for a in artifacts:
        digest = hashlib.sha256(a.read_bytes()).hexdigest()
        lines.append(f"{digest}  {a.name}")
    sum_file = out / f"dsh-research-lab-{version}-checksums.sha256"
    sum_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    artifacts.append(sum_file)

    # 冒烟验收随包说明（CI 会在三大平台实际执行）
    smoke = {
        "package": target.name,
        "files": n_files,
        "sha256": {a.name: hashlib.sha256(a.read_bytes()).hexdigest() for a in artifacts},
        "smoke": [
            "unzip/untar → pip install -r requirements.txt",
            "python examples/education-demo/run_t1_t5.py",
            "python examples/health-demo/run_h1_h5.py",
            "python scripts/verify.py",
        ],
    }
    (out / "package_manifest.json").write_text(
        json.dumps(smoke, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "artifacts": [a.name for a in artifacts],
                      "files": n_files}, ensure_ascii=False))


if __name__ == "__main__":
    main()
