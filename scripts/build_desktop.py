"""build_desktop.py — 桌面端可复现构建（macOS arm64 当前主目标）。

产出（dist/desktop/）：
  - DSH Research Lab.app     完整桌面端：内嵌 Node + 真实 DSH + 科研栈
  - dsh-research-lab-<v>-darwin-<arch>.dmg / .zip
  - checksums.sha256

依赖装配（build/desktop-deps/，全部可离线替换）：
  - Node 22.22.0（nodejs.org 官方 tarball，或 --node-bin 指定本机）
  - @deepseek-ai/dsh@0.2.1-rc.2（npm 安装到独立 prefix，或 --dsh-src 指定）

签名：无开发者证书时做 ad-hoc 签名（codesign -s -），产物**未签名未公证**，
首次打开需右键 → 打开（见 docs/desktop.md）。

用法：
  python scripts/build_desktop.py                 # 完整构建
  python scripts/build_desktop.py --verify        # 构建后自动冒烟（含真实 DSH）
  python scripts/build_desktop.py --node-bin /path/node --dsh-src /path/dsh
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BUILD = REPO / "build" / "desktop"
DEPS = BUILD / "deps"
DIST = REPO / "dist" / "desktop"

NODE_VERSION = "22.22.0"
DSH_VERSION = "0.2.1-rc.2"
DSH_PACKAGE = "@deepseek-ai/dsh"
APP_NAME = "DSH Research Lab"
EXE_NAME = "DSHResearchLab"
APP_VERSION = "0.3.0"

LAB_INCLUDE = [
    "tools", "domains", "presets", "skills", "datasets", "templates",
    "examples", "scripts", "docs", "tests",
    "CHANGELOG.md", "LICENSE", "README.md", "THIRD_PARTY_NOTICES.md",
    "pyproject.toml", "requirements.txt",
]
LAB_EXCLUDE_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules"}

NODE_BASE = f"https://nodejs.org/dist/v{NODE_VERSION}"
NODE_TARBALL = f"node-v{NODE_VERSION}-darwin-{platform.machine()}.tar.gz"

DSH_BIN_NAMES = ("python", "python3")


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    print("  $", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


# -- 依赖装配 ------------------------------------------------------------------
def ensure_node(args) -> Path:
    if args.node_bin:
        src = Path(args.node_bin)
        assert src.is_file(), f"--node-bin 不存在: {src}"
        dest = DEPS / "node" / "bin" / "node"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return dest
    dest = DEPS / "node" / "bin" / "node"
    if dest.is_file():
        return dest
    url = f"{NODE_BASE}/{NODE_TARBALL}"
    tgz = DEPS / NODE_TARBALL
    tgz.parent.mkdir(parents=True, exist_ok=True)
    if not tgz.is_file():
        print(f"==> 下载 Node {NODE_VERSION}（{platform.machine()}）")
        with urllib.request.urlopen(url, timeout=120) as resp, tgz.open("wb") as out:
            shutil.copyfileobj(resp, out)
    print(f"    node tarball sha256 = {sha256(tgz)}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tgz) as tf:
        member = f"node-v{NODE_VERSION}-darwin-{platform.machine()}/bin/node"
        with tf.extractfile(member) as f_in, dest.open("wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    dest.chmod(0o755)
    return dest


def ensure_dsh(args) -> Path:
    dest = DEPS / "dsh"
    if args.dsh_src:
        if dest.exists():
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(args.dsh_src, dest, symlinks=True)
        return dest
    # 完整性判据：包本体 + 内嵌依赖（node_modules 至少数百 MB）。
    if (dest / "package.json").is_file() and (dest / "lib" / "bin.js").is_file() \
            and (dest / "node_modules").is_dir():
        return dest
    if dest.exists():
        shutil.rmtree(dest)
    prefix = DEPS / "npm-prefix"
    prefix.mkdir(parents=True, exist_ok=True)
    run(["npm", "install", "--prefix", prefix,
         f"{DSH_PACKAGE}@{DSH_VERSION}", "--no-audit", "--no-fund"])
    src_pkg = prefix / "node_modules" / "@deepseek-ai" / "dsh"
    if not (src_pkg / "package.json").is_file():
        raise RuntimeError(f"npm 未安装 {DSH_PACKAGE}@{DSH_VERSION}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src_pkg, dest, symlinks=True)
    # npm 平铺安装时依赖在 prefix/node_modules 顶层；合并为包内依赖布局，
    # 使 dsh 包自包含（等效 npm -g 全局布局），拷入 .app 后无需外部解析。
    top = prefix / "node_modules"
    (dest / "node_modules").mkdir(parents=True, exist_ok=True)
    for item in top.iterdir():
        target = dest / "node_modules" / item.name
        if target.exists():
            continue
        if item.is_dir() and not item.is_symlink():
            shutil.copytree(item, target, symlinks=True)
        else:
            shutil.copy2(item, target, follow_symlinks=False)
    if not (dest / "node_modules" / "@deepseek-ai").is_dir():
        raise RuntimeError("dsh 依赖合并失败（node_modules/@deepseek-ai 缺失）")
    return dest


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# -- lab 模板（工作台出厂文件） --------------------------------------------------
def copy_lab_template(dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for name in LAB_INCLUDE:
        src = REPO / name
        if not src.exists():
            continue
        if src.is_dir():
            shutil.copytree(src, dest / name,
                            ignore=shutil.ignore_patterns(
                                *[f"{d}" for d in LAB_EXCLUDE_DIRS] + ["outputs"]),
                            symlinks=True)
        else:
            shutil.copy2(src, dest / name)


def write_shims(bin_dir: Path, exe_name: str) -> None:
    """python/python3 shim → 主可执行 --python-bridge（DSH shell 工具的桥）。

    相对 shim 自身定位主可执行（bin/../../MacOS/<exe>），应用安装到任意
    目录均可用，不写死 /Applications。
    """
    bin_dir.mkdir(parents=True, exist_ok=True)
    body = ("#!/bin/sh\n"
            'DIR="$(cd "$(dirname "$0")" && pwd)"\n'
            f'exec "$DIR/../../MacOS/{exe_name}" --python-bridge "$@"\n')
    for name in DSH_BIN_NAMES:
        p = bin_dir / name
        p.write_text(body)
        p.chmod(0o755)


# -- .app 组装 ------------------------------------------------------------------
def assemble_app(pyinstaller_dist: Path, node_bin: Path, dsh_dir: Path) -> Path:
    app = DIST / f"{APP_NAME}.app"
    if app.exists():
        shutil.rmtree(app)
    contents = app / "Contents"
    macos = contents / "MacOS"
    resources = contents / "Resources"
    macos.mkdir(parents=True)
    resources.mkdir(parents=True)

    # PyInstaller windowed onedir → 官方 .app 布局（与 PyInstaller 自己生成
    # 的 windowed .app 一致，已用最小样例实证）：主可执行在 MacOS/，
    # _internal 的全部内容扁平放入 Contents/Frameworks/（bootloader 在
    # bundle 模式下把 Frameworks 当 Python home 与模块根）。
    src = pyinstaller_dist / EXE_NAME
    shutil.copy2(src / EXE_NAME, macos / EXE_NAME)
    frameworks = contents / "Frameworks"
    if (src / "_internal").is_dir():
        frameworks.mkdir(parents=True, exist_ok=True)
        for item in (src / "_internal").iterdir():
            target = frameworks / item.name
            if item.is_dir() and not item.is_symlink():
                shutil.copytree(item, target, symlinks=True)
            else:
                shutil.copy2(item, target, follow_symlinks=False)

    print("==> 拷贝出厂工作台模板（lab）")
    copy_lab_template(resources / "lab")
    print("==> 拷贝内嵌 Node 与真实 DSH")
    (resources / "node" / "bin").mkdir(parents=True, exist_ok=True)
    shutil.copy2(node_bin, resources / "node" / "bin" / "node")
    shutil.copytree(dsh_dir, resources / "dsh", symlinks=True)
    write_shims(resources / "bin", EXE_NAME)

    # 许可证集合（DSH MIT、Node、本项目 MIT）
    lic = resources / "licenses"
    lic.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dsh_dir / "LICENSE", lic / "DSH-LICENSE")
    (lic / "NODE-LICENSE.txt").write_text(
        f"Node.js v{NODE_VERSION}\nhttps://nodejs.org/dist/v{NODE_VERSION}/LICENSE\n"
        "(Node.js is packaged as a runtime; full license text available at the URL above)\n",
        encoding="utf-8")

    # 应用图标（assets/app-icon.icns，由 scripts/make_app_icon.py 生成）
    icon_src = REPO / "assets" / "app-icon.icns"
    if icon_src.is_file():
        shutil.copy2(icon_src, resources / "app-icon.icns")

    manifest = {
        "name": "DSH Research Lab Desktop",
        "version": APP_VERSION,
        "dsh_version": DSH_VERSION,
        "node_version": NODE_VERSION,
        "arch": platform.machine(),
        "platform": "darwin",
        "git_commit": git_commit(),
        "built_at": subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"],
                                   capture_output=True, text=True).stdout.strip(),
        "python": sys.version.split()[0],
        "signed": "ad-hoc (unsigned, not notarized)",
    }
    (resources / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    (contents / "Info.plist").write_text(INFO_PLIST.format(
        exe=EXE_NAME, version=APP_VERSION, commit=manifest["git_commit"]), encoding="utf-8")
    (contents / "PkgInfo").write_text("APPL????", encoding="utf-8")
    return app


INFO_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>{exe}</string>
  <key>CFBundleDisplayName</key><string>DSH Research Lab</string>
  <key>CFBundleIdentifier</key><string>net.milulab.dsh-research-lab</string>
  <key>CFBundleVersion</key><string>{commit}</string>
  <key>CFBundleShortVersionString</key><string>{version}</string>
  <key>CFBundleExecutable</key><string>{exe}</string>
  <key>CFBundleIconFile</key><string>app-icon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleInfoDictionaryVersion</key><string>6.0</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSHumanReadableCopyright</key><string>MIT License — milulab</string>
</dict></plist>
"""


# -- 验证 / 打包 ----------------------------------------------------------------
def smoke(app: Path, with_dsh: bool) -> dict:
    exe = app / "Contents" / "MacOS" / EXE_NAME
    home = Path(tempfile.mkdtemp(prefix="dshrl-verify-"))
    cmd = [str(exe), "--smoke", "--home", str(home)]
    if with_dsh:
        cmd.append("--with-dsh")
    print("==> 冒烟验证（干净 env：系统 PATH + 临时 HOME）：", " ".join(cmd))
    env = {"HOME": str(home), "USER": os.environ.get("USER", "nobody"),
           "PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "TMPDIR": "/tmp"}
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=1800)
    report = None
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                report = json.loads(proc.stdout[proc.stdout.index(line):])
                break
            except json.JSONDecodeError:
                pass
    out = {"returncode": proc.returncode, "ok": bool(report and report.get("ok")),
           "home": str(home), "report": report,
           "stdout_tail": proc.stdout[-2000:], "stderr_tail": proc.stderr[-800:]}
    (BUILD / "verify-report.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def make_dmg_and_zip(app: Path) -> tuple[Path, Path]:
    stage = DIST / "dmg-stage"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    shutil.copytree(app, stage / f"{APP_NAME}.app", symlinks=True)
    (stage / "README.txt").write_text(
        "DSH Research Lab（桌面端）\n\n"
        "拖拽「DSH Research Lab.app」到「应用程序」文件夹。\n"
        f"首次打开（未公证）：在「应用程序」中右键 → 打开 → 再点「打开」。\n"
        f"详见 https://github.com/milulab/dsh-research-lab（docs/desktop.md）。\n",
        encoding="utf-8")
    dmg = DIST / f"dsh-research-lab-{APP_VERSION}-darwin-{platform.machine()}.dmg"
    if dmg.exists():
        dmg.unlink()
    run(["hdiutil", "create", "-volname", APP_NAME, "-srcfolder", stage,
         "-ov", "-format", "UDZO", dmg])
    zipped = DIST / f"dsh-research-lab-{APP_VERSION}-darwin-{platform.machine()}.zip"
    if zipped.exists():
        zipped.unlink()
    run(["ditto", "-c", "-k", "--keepParent", app, zipped])
    shutil.rmtree(stage)
    return dmg, zipped


def codesign_adhoc(dist_dir: Path) -> None:
    """ad-hoc 签名主可执行（arm64 运行必需）——在 .app 组装**之前**做。

    PyInstaller 在 EXE 阶段签的是 bundle 形态签名，onedir 装配后资源
    断言失效；且在 .app 内重签会因祖先 Info.plist 触发 bundle 语义而
    失败。于是在 dist 阶段（.app 外）按文件移除并重签，装配后仅校验。
    不做 --deep：PyInstaller 的 .so、Node 官方二进制与 DSH 原生扩展
    各自已带签名。产物整体**未公证**。
    """
    exe = dist_dir / EXE_NAME / EXE_NAME
    print("==> ad-hoc 签名主可执行（dist 阶段；无开发者证书，产物未公证）")
    subprocess.run(["codesign", "--remove-signature", str(exe)], capture_output=True)
    run(["codesign", "--force", "--sign", "-", exe])
    run(["codesign", "--verify", exe])


def verify_signature(app: Path) -> bool:
    """装配后仅做登记性校验（app 内路径会触发 codesign 的 bundle 语义，
    静态 --verify 可能误报；实际签名有效性已在 dist 阶段验证，拷贝不改字节）。"""
    exe = app / "Contents" / "MacOS" / EXE_NAME
    proc = subprocess.run(["codesign", "--display", str(exe)], capture_output=True)
    return proc.returncode == 0


# -- 主流程 ---------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--node-bin", type=Path, default=None,
                        help="使用本机 node 二进制（跳过官方 tarball 下载）")
    parser.add_argument("--dsh-src", type=Path, default=None,
                        help="使用本机已安装的 @deepseek-ai/dsh 包目录（跳过 npm）")
    parser.add_argument("--skip-pyinstaller", action="store_true")
    parser.add_argument("--skip-verify", action="store_true")
    parser.add_argument("--skip-dmg", action="store_true")
    parser.add_argument("--verify", action="store_true", help="构建后运行完整冒烟（含真实 DSH）")
    args = parser.parse_args()

    DEPS.mkdir(parents=True, exist_ok=True)
    DIST.mkdir(parents=True, exist_ok=True)

    node_bin = ensure_node(args)
    dsh_dir = ensure_dsh(args)
    print(f"==> node: {node_bin}")
    dsh_mb = sum(f.stat().st_size for f in dsh_dir.rglob("*") if f.is_file()) // (1 << 20)
    print(f"==> dsh:  {dsh_dir}（约 {dsh_mb} MB）")

    if not args.skip_pyinstaller:
        print("==> PyInstaller 打包（onedir）")
        run([sys.executable, "-m", "PyInstaller", "desktop.spec",
             "--noconfirm", "--distpath", str(BUILD / "pyinstaller"),
             "--workpath", str(BUILD / "pyinstaller-work")], cwd=REPO)

    codesign_adhoc(BUILD / "pyinstaller")
    app = assemble_app(BUILD / "pyinstaller", node_bin, dsh_dir)
    if not verify_signature(app):
        print("!! 主可执行签名缺失", file=sys.stderr)
        return 1

    verify_ok = True
    if not args.skip_verify:
        result = smoke(app, with_dsh=args.verify)
        verify_ok = result["ok"]
        print(f"==> 冒烟：ok={result['ok']} rc={result['returncode']}"
              f"（报告：{BUILD / 'verify-report.json'}）")
        if not result["ok"]:
            print(result["stdout_tail"])
            print(result["stderr_tail"], file=sys.stderr)

    if verify_ok and not args.skip_dmg:
        dmg, zipped = make_dmg_and_zip(app)
    else:
        dmg = zipped = None

    # 校验和：对分发产物整体（.app / dmg / zip）计算，而非逐文件
    lines = []
    if app.is_dir():
        app_tar = BUILD / "app.tar"
        if app_tar.exists():
            app_tar.unlink()
        run(["tar", "-cf", app_tar, "-C", DIST, app.name])
        lines.append(f"{sha256(app_tar)}  {app.name}.tar")
        app_tar.unlink()
    for p in (dmg, zipped):
        if p is not None and p.is_file():
            lines.append(f"{sha256(p)}  {p.name}")
    (DIST / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n==> 产物（dist/desktop/）")
    for p in [app] + ([dmg, zipped] if dmg else []):
        if p is None:
            continue
        size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) \
            if p.is_dir() else p.stat().st_size
        print(f"  {p}  ({size / (1 << 20):.0f} MB)")
    return 0 if verify_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
