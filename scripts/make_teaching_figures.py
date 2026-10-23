"""make_teaching_figures.py — 生成教学可视化图（全部来自真实数据与真实管线结果）

教育：G3 分布、studytime×G3 箱线、M1 系数森林图（含 HC3 对照）、M1/M2 泄漏对照、
     相关热图。
公卫：标签/年龄分布、阈值扫描权衡、双阈值混淆矩阵、ROC（复用）、校准（复用）。

输出：examples/*/outputs/figures/（管线产物目录），另 --site-dir 同步到网站资产。
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _setup_cjk_font() -> None:
    """解析本机可用的中文字体（mac/win/linux 常见字体回退链）。"""
    from matplotlib import font_manager

    candidates = ["PingFang SC", "Hiragino Sans GB", "Microsoft YaHei",
                  "Noto Sans CJK SC", "Noto Sans SC", "WenQuanYi Zen Hei",
                  "Source Han Sans SC", "Arial Unicode MS"]
    installed = {f.name for f in font_manager.fontManager.ttflist}
    chosen = [c for c in candidates if c in installed]
    if chosen:
        plt.rcParams["font.sans-serif"] = chosen + plt.rcParams["font.sans-serif"]
    plt.rcParams["axes.unicode_minus"] = False


_setup_cjk_font()

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

EDU_RAW = REPO / "datasets/education-student-performance/raw/student-por.csv"
EDU_OUT = REPO / "examples/education-demo/outputs"
HEALTH_RAW = REPO / "datasets/health-heart-disease/raw/processed.cleveland.data"
HEALTH_OUT = REPO / "examples/health-demo/outputs"

INK = "#0b1524"
BLUE, CYAN, LIME, GOLD, PINK, VIOLET, RED = ("#38bdf8", "#67e8f9", "#a3e635",
                                             "#fbbf24", "#f472b6", "#a78bfa", "#f87171")


def style_ax(ax):
    ax.set_facecolor("none")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#94a3b8")
    ax.tick_params(colors="#94a3b8", labelsize=9)
    ax.xaxis.label.set_color("#cbd5e1")
    ax.yaxis.label.set_color("#cbd5e1")
    ax.title.set_color("#e2e8f0")
    ax.grid(axis="y", color="#334155", alpha=.35, lw=.6)


def save(fig, out_dir: Path, name: str, site_dir: Path | None):
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / name
    fig.savefig(p, dpi=150, bbox_inches="tight", facecolor=INK)
    plt.close(fig)
    if site_dir:
        site_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, site_dir / name)
    print("fig:", name)


def edu_figures(site_dir: Path | None) -> None:
    df = pd.read_csv(EDU_RAW, sep=";", skipinitialspace=True)
    gold = json.loads((REPO / "datasets/education-student-performance/expected/education_results.json")
                      .read_text(encoding="utf-8"))
    figs = EDU_OUT / "figures"

    # 1) G3 分布
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.hist(df["G3"], bins=21, color=BLUE, alpha=.85, edgecolor=INK)
    ax.axvline(df["G3"].mean(), color=GOLD, ls="--", lw=1.4,
               label=f"均值 {df['G3'].mean():.2f}")
    ax.set_xlabel("G3 最终成绩（0–20）"); ax.set_ylabel("学生数")
    ax.set_title(f"G3 分布 · 649 名中学生（0 缺失 / 0 重复）")
    ax.legend(frameon=False)
    style_ax(ax); save(fig, figs, "edu_g3_distribution.png", site_dir)

    # 2) studytime × G3 箱线 + 组均值
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    groups = [g["G3"].values for _, g in df.groupby("studytime")]
    bp = ax.boxplot(groups, tick_labels=[f"{i} 档" for i in range(1, 5)],
                    patch_artist=True, widths=.55,
                    medianprops=dict(color=GOLD, lw=1.6))
    for b, c in zip(bp["boxes"], [CYAN, BLUE, VIOLET, PINK]):
        b.set(facecolor=c, alpha=.55, edgecolor="#94a3b8")
    means = [float(np.mean(g)) for g in groups]
    ax.plot(range(1, 5), means, "o--", color=LIME, lw=1.4, ms=5, label="组均值")
    ax.set_xlabel("每周学习时间（1 <2h · 2 2–5h · 3 5–10h · 4 >10h）")
    ax.set_ylabel("G3"); ax.set_title("学习时间 × G3（Spearman ρ=+0.275，p≈1.1e-12）")
    ax.legend(frameon=False)
    style_ax(ax); save(fig, figs, "edu_studytime_box.png", site_dir)

    # 3) M1 系数森林图（经典 SE 与 HC3 对照）
    m1c = {c["term"]: c for c in gold["t3_model_m1"]["coefficients"]}
    hc3 = gold["t3_model_m1"]["hc3_se"]
    rows = [t for t in m1c if t != "Intercept"]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    y = np.arange(len(rows))
    for i, t in enumerate(rows):
        c = m1c[t]
        color = LIME if c["p_value"] < .05 else "#94a3b8"
        ax.plot([c["ci_low"], c["ci_high"]], [i, i], color=color, lw=2, alpha=.9)
        ax.plot(c["coef"], i, "o", color=color, ms=6)
        ax.plot(c["coef"] - 1.96 * hc3[t], i, "|", color=GOLD, ms=8)
        ax.plot(c["coef"] + 1.96 * hc3[t], i, "|", color=GOLD, ms=8)
    ax.axvline(0, color="#64748b", lw=1, ls="--")
    ax.set_yticks(y, rows, fontsize=9)
    ax.set_xlabel("M1 系数（绿=p<0.05；竖须=HC3 稳健 95%CI）")
    ax.set_title("M1 回归系数森林图 · studytime +0.51 / failures −1.67")
    style_ax(ax); ax.grid(axis="x", color="#334155", alpha=.35, lw=.6); ax.grid(axis="y", alpha=0)
    save(fig, figs, "edu_m1_forest.png", site_dir)

    # 4) M1/M2 泄漏对照
    fig, ax = plt.subplots(figsize=(5.6, 3.8))
    bars = ax.bar(["M1\n行为+家庭", "M2\nM1+G1+G2"],
                  [gold["t3_model_m1"]["adj_r_squared"], gold["t4_model_m2"]["adj_r_squared"]],
                  color=[BLUE, PINK], width=.5, alpha=.9)
    ax.bar_label(bars, fmt="%.3f", fontsize=11, color="#e2e8f0", padding=3)
    ax.annotate(f"Δ = +{gold['t4_adj_r2_delta']:.3f}",
                xy=(1, gold["t4_model_m2"]["adj_r_squared"]),
                xytext=(0.42, 0.72), textcoords="axes fraction",
                color=GOLD, fontsize=13, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=GOLD))
    ax.set_ylim(0, 1.0); ax.set_ylabel("调整 R²")
    ax.set_title("泄漏对照：解释力暴涨 ≠ 模型变好，是任务被换掉")
    style_ax(ax); save(fig, figs, "edu_leakage_bar.png", site_dir)

    # 5) 数值变量相关热图
    cols = ["studytime", "failures", "absences", "Medu", "Fedu", "G1", "G2", "G3"]
    corr = df[cols].corr(method="spearman")
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(cols)), cols, rotation=45, ha="right", fontsize=9, color="#cbd5e1")
    ax.set_yticks(range(len(cols)), cols, fontsize=9, color="#cbd5e1")
    for i in range(len(cols)):
        for j in range(len(cols)):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center",
                    fontsize=8, color="#e2e8f0" if abs(corr.iloc[i, j]) > .55 else "#94a3b8")
    ax.set_title("Spearman 相关热图（G1/G2 与 G3 强相关——T4 泄漏的视觉证据）")
    fig.colorbar(im, ax=ax, shrink=.8)
    save(fig, figs, "edu_corr_heatmap.png", site_dir)


def health_figures(site_dir: Path | None) -> None:
    cols = ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg", "thalach",
            "exang", "oldpeak", "slope", "ca", "thal", "num"]
    df = pd.read_csv(HEALTH_RAW, header=None, names=cols, na_values=["?"],
                     skipinitialspace=True)
    df["target"] = (df["num"] > 0).astype(int)
    clean = df.dropna()
    gold = json.loads((REPO / "datasets/health-heart-disease/expected/health_results.json")
                      .read_text(encoding="utf-8"))
    figs = HEALTH_OUT / "figures"

    # 1) 标签分布 + 年龄按结局
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6))
    axes[0].bar(["阴性 (num=0)", "阳性 (num 1–4)"],
                [gold["h1_audit"]["target_counts"]["0"], gold["h1_audit"]["target_counts"]["1"]],
                color=[BLUE, PINK], alpha=.9, width=.5)
    for i, v in enumerate([160, 137]):
        axes[0].text(i, v + 2, str(v), ha="center", color="#e2e8f0", fontsize=11)
    axes[0].set_ylim(0, 185); axes[0].set_title("标签分布（303 例中完整案例 297）")
    for t, c in [(0, BLUE), (1, PINK)]:
        axes[1].hist(clean.loc[clean["target"] == t, "age"], bins=15, alpha=.65,
                     color=c, label=f"target={t}")
    axes[1].set_xlabel("年龄"); axes[1].set_ylabel("例数"); axes[1].legend(frameon=False)
    axes[1].set_title("年龄 × 结局（Welch t，d=0.47）")
    for ax in axes:
        style_ax(ax)
    save(fig, figs, "health_overview.png", site_dir)

    # 2) 阈值扫描权衡
    sweep = pd.DataFrame(gold["test"]["threshold_sweep"])
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.plot(sweep["threshold"], sweep["sensitivity"], "o-", color=LIME, ms=4, label="敏感度")
    ax.plot(sweep["threshold"], sweep["specificity"], "s-", color=CYAN, ms=4, label="特异度")
    yd = gold["test"]["youden"]["threshold"]
    ax.axvline(yd, color=GOLD, ls="--", lw=1.4, label=f"Youden 阈值 {yd:.3f}")
    ax.axvline(0.5, color="#64748b", ls=":", lw=1.2, label="默认 0.5")
    ax.set_xlabel("判定阈值"); ax.set_ylabel("比率")
    ax.set_title("阈值即决策：敏感度–特异度此消彼长（19 档扫描）")
    ax.legend(frameon=False, fontsize=9)
    style_ax(ax); save(fig, figs, "health_threshold_sweep.png", site_dir)

    # 3) 双阈值混淆矩阵
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.9))
    for ax, (name, blk) in zip(axes, [("阈值 0.5", gold["test"]["threshold_05"]),
                                      (f"Youden {yd:.3f}", gold["test"]["youden"])]):
        cm = blk["confusion_matrix"]
        m = np.array([[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]])
        ax.imshow(m, cmap="Blues", vmin=0, vmax=30)
        labels = [["TN", "FP"], ["FN", "TP"]]
        for i in range(2):
            for j in range(2):
                ax.text(j, i, f"{labels[i][j]}\n{m[i, j]}", ha="center", va="center",
                        fontsize=13, color="#0b1524" if m[i, j] > 15 else "#e2e8f0")
        ax.set_xticks([0, 1], ["判阴性", "判阳性"], fontsize=9, color="#cbd5e1")
        ax.set_yticks([0, 1], ["真阴性", "真阳性"], fontsize=9, color="#cbd5e1")
        ax.set_title(f"{name} · 敏感度 {blk['sensitivity']:.3f} / 特异度 {blk['specificity']:.3f} / F1 {blk['f1']:.3f}",
                     fontsize=10.5)
    save(fig, figs, "health_confusion.png", site_dir)

    # 4) OR 森林图
    ors = [r for r in gold["h2_or_table"]["or_table"]]
    ors = sorted(ors, key=lambda r: r["or"])
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    y = np.arange(len(ors))
    for i, r in enumerate(ors):
        sig = r["ci_low"] > 1 or r["ci_high"] < 1
        color = LIME if sig and r["or"] > 1 else (PINK if sig else "#94a3b8")
        ax.plot([r["ci_low"], r["ci_high"]], [i, i], color=color, lw=2)
        ax.plot(r["or"], i, "D", color=color, ms=5)
    ax.axvline(1, color="#64748b", lw=1, ls="--")
    ax.set_yticks(y, [r["term"] for r in ors], fontsize=9)
    ax.set_xscale("log")
    ax.set_xlabel("OR（对数轴，95%CI；绿=风险↑ 粉=保护/风险↓ 且显著）")
    ax.set_title("Logistic OR 森林图 · ca OR=3.55 [2.11, 5.98] 最强")
    style_ax(ax); ax.grid(axis="x", color="#334155", alpha=.35, lw=.6); ax.grid(axis="y", alpha=0)
    save(fig, figs, "health_or_forest.png", site_dir)


def main() -> None:
    site_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    edu_figures(site_dir)
    health_figures(site_dir)
    print("done")


if __name__ == "__main__":
    main()
