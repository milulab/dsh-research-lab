"""make_app_icon.py — 生成桌面端应用图标（assets/app-icon.icns）。

设计：品牌渐变圆角方底（sky→indigo）+ 白色锥形烧瓶 + 青柠液面与上浮气泡，
与项目页视觉一致。macOS 专属产物：iconset → iconutil -c icns。

用法：
  python scripts/make_app_icon.py            # 生成 assets/app-icon.icns
  python scripts/make_app_icon.py --preview  # 额外输出 build/desktop/icon-preview.png
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Polygon  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
OUT_ICNS = REPO / "assets" / "app-icon.icns"

SIZE = 1024
CORNER = 232            # macOS 大圆角观感
SKY = "#38bdf8"
INDIGO = "#6366f1"
LIME = "#a3e635"


def draw_master(path: Path) -> None:
    fig = plt.figure(figsize=(10.24, 10.24), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, SIZE)
    ax.set_ylim(0, SIZE)
    ax.axis("off")

    # 底：纵向渐变填充圆角方（imshow zorder 高于底 patch，经 clip_path 裁剪）
    grad = np.linspace(0, 1, 256).reshape(-1, 1)
    brand_cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
        "brand", ["#4f46e5", SKY])
    ax.add_patch(FancyBboxPatch((0, 0), SIZE, SIZE,
                                boxstyle=f"round,pad=0,rounding_size={CORNER}",
                                linewidth=0, facecolor=SKY, zorder=1))
    im = ax.imshow(grad, extent=(0, SIZE, 0, SIZE), origin="lower",
                   aspect="auto", cmap=brand_cmap, zorder=2)
    clip = FancyBboxPatch((0, 0), SIZE, SIZE,
                          boxstyle=f"round,pad=0,rounding_size={CORNER}",
                          linewidth=0, facecolor="none")
    ax.add_patch(clip)
    im.set_clip_path(clip)

    # 锥形瓶（白色）：平颈 → 斜肩 → 平底，圆角连接柔化转折
    cx = SIZE / 2
    neck_half = 40
    neck_top = 712
    shoulder = 596
    body_half = 196
    body_bot = 316
    flask = Polygon(
        [(cx - neck_half, neck_top), (cx + neck_half, neck_top),
         (cx + neck_half, shoulder), (cx + body_half, body_bot),
         (cx - body_half, body_bot)],
        closed=True, facecolor="white", edgecolor="white", linewidth=30,
        joinstyle="round", zorder=3)
    ax.add_patch(flask)

    # 液体（青柠）：按锥形斜率内缩的梯形
    liq_y = 436
    liq_half = neck_half + (shoulder - liq_y) / (shoulder - body_bot) * (body_half - neck_half) - 26
    liquid = Polygon(
        [(cx - liq_half, liq_y), (cx + liq_half, liq_y),
         (cx + body_half + 12, body_bot + 12), (cx - body_half - 12, body_bot + 12)],
        closed=True, facecolor=LIME, edgecolor="none", zorder=4, alpha=0.95)
    ax.add_patch(liquid)

    # 上浮气泡（青柠，液面之上）
    for (bx, by, r) in ((cx - 58, 508, 24), (cx + 64, 552, 17), (cx + 6, 480, 12)):
        ax.add_patch(Circle((bx, by), r, facecolor=LIME,
                            edgecolor="none", zorder=5, alpha=0.85))

    # 瓶口沿
    ax.add_patch(FancyBboxPatch((cx - neck_half - 24, neck_top - 10),
                                (neck_half + 24) * 2, 28,
                                boxstyle="round,pad=0,rounding_size=14",
                                facecolor="white", edgecolor="none", zorder=6))

    fig.savefig(path, format="png", transparent=True)
    plt.close(fig)


def make_icns(master_png: Path, out: Path, preview: Path | None) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "app.iconset"
        iconset.mkdir()
        for s in (16, 32, 64, 128, 256, 512, 1024):
            subprocess.run(["sips", "-z", str(s), str(s), str(master_png),
                            "--out", str(iconset / f"icon_{s}x{s}.png")],
                           check=True, capture_output=True)
            if s <= 512:
                s2 = s * 2
                subprocess.run(["sips", "-z", str(s2), str(s2), str(master_png),
                                "--out", str(iconset / f"icon_{s}x{s}@2x.png")],
                               check=True, capture_output=True)
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["iconutil", "-c", "icns", str(iconset),
                        "-o", str(out)], check=True, capture_output=True)
    if preview is not None:
        preview.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(master_png, preview)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        master = Path(tmp) / "master-1024.png"
        draw_master(master)
        preview = REPO / "build" / "desktop" / "icon-preview.png" if args.preview else None
        make_icns(master, OUT_ICNS, preview)

    print(f"==> 生成 {OUT_ICNS}（{OUT_ICNS.stat().st_size // 1024} KB）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
