# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec：DSH Research Lab 桌面端（onedir，macOS arm64 主构建目标）
#
# 入口 desktop_main.py 双模式：
#   默认 → 桌面工作台；--python-bridge → 随包 Python 执行桥。
#
# 管线脚本由 runpy 在进程内动态执行，其依赖静态分析不可见，
# 因此 hiddenimports 显式列出 tools/* 与全部科研栈；pywebview 的
# cocoa 平台后端与 pip（供桥内 `python -m pip --user`）同样显式声明。
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

a = Analysis(
    ["desktop_main.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=[
        # 桌面层
        "desktop",
        "desktop.app",
        "desktop.bridge",
        "desktop.bootstrap",
        "desktop.config",
        "desktop.dsh_manager",
        "desktop.patch_writer",
        "desktop.paths",
        "desktop.runner",
        "desktop.shell",
        # 本地服务（工作台 UI/API）
        "scripts.server",
        # 科研计算栈（runpy 动态执行管线脚本所需）
        "pandas",
        "numpy",
        "scipy",
        "statsmodels",
        "sklearn",
        "sklearn.utils._weight_vector",  # sklearn 部分子模块运行时加载
        "matplotlib",
        "yaml",
        # 计算层（管线脚本 import）
        "tools",
        "tools.data_audit",
        "tools.regression",
        "tools.classification",
        "tools.stat_tests",
        "tools.report_builder",
        # 可选窗口壳与 pip（桥内 -m pip）
        "webview",
        "webview.platforms.cocoa",
        "webview.platforms.winforms",
        "webview.platforms.gtk",
        "pip",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "PyQt5", "PyQt6", "PySide2", "PySide6"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DSHResearchLab",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # windowed：macOS 直接产出标准 .app（bootloader 按 bundle 布局定位 libpython）
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="DSHResearchLab",
)
