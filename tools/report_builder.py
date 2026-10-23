"""report_builder.py — 由结构化统计结果组装研究报告（T5/H5）

输入 examples 管线产出的 results JSON（t1_audit/t2_t4/h1_h4 段），输出
Markdown 报告。规则：所有数字只从传入 JSON 引用，本模块不产生任何统计值；
局限声明为必填段，来源与映射规则自动附在文末。

用法：
  python tools/report_builder.py --education results.json --out report.md
  python tools/report_builder.py --health results.json --out report.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

EDUCATION_FOOTER = """## 数据与复现

- 数据：UCI Student Performance（Cortez & Silva 2008，CC BY 4.0），葡萄牙语课程
  649 名中学学生；原始文件 SHA256 见 metadata/source.yml。
- 复现：`python examples/education-demo/run_t1_t5.py`；校验：
  `python scripts/verify.py --suite education`。
- 本报告为教学演示产物，不代表任何真实培训效果。"""

HEALTH_FOOTER = """## 数据与复现

- 数据：UCI Heart Disease processed Cleveland 子集（Detrano et al. 1989，CC BY 4.0），
  303 例历史研究数据；原始文件 SHA256 见 metadata/source.yml。
- 复现：`python examples/health-demo/run_h1_h5.py`；校验：
  `python scripts/verify.py --suite health`。
- **不得用于真实临床诊断**；本报告为教学演示产物。"""


def _fmt(x, nd=4):
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def build_education_report(r: dict) -> str:
    t1 = r["t1_audit"]
    t2 = r["t2_associations"]
    m1 = r["t3_model_m1"]
    m2 = r["t4_model_m2"]
    lines = [
        "# 学习行为与学业成绩的关联分析（EduResearch 教学报告）",
        "",
        f"样本：葡萄牙语课程 {t1['n_rows']} 名学生 × {t1['n_cols']} 字段；"
        f"完全重复行 {t1['exact_duplicate_rows']}；缺失单元格 {t1['total_missing_cells']}。",
        "",
        "## T2 单变量关联（仅表述关联，不作因果解释）",
        "",
        "| 变量 | 方法 | 统计量 | p 值 |",
        "|---|---|---|---|",
    ]
    for row in t2:
        lines.append(
            f"| {row['variable']} | {row['method']} | {row['statistic']} | {_fmt(row['p_value'])} |"
        )
    t2b = r.get("t2b_group_tests") or {}
    if t2b:
        sex = t2b["sex_g3_two_group"]
        wa = t2b["medu_g3_welch_anova"]
        fam = t2b["multiplicity_over_family"]
        n_fdr = int(sum(fam["bh_fdr_significant"]))
        lines += [
            "",
            "## T2b 组间检验与效应量（含多重比较校正）",
            "",
            f"- **性别两组比较**：男 {sex['group1']['mean']} vs 女 {sex['group0']['mean']}；"
            f"差值 {sex['mean_diff']}，Cohen's d = {_fmt(sex['cohens_d'])}；"
            f"Welch t p={_fmt(sex['welch_t']['p_value'])}，Mann-Whitney p={_fmt(sex['mann_whitney_u']['p_value'])}",
            f"- **母亲教育（0–4 组）Welch ANOVA**：F={_fmt(wa['welch_f'])}，"
            f"p={_fmt(wa['p_value'])}（各组 n={wa['group_ns']}）；Kruskal-Wallis p={_fmt(wa['kruskal_wallis']['p_value'])}",
            f"- **卡方**：school×higher V={_fmt(t2b['school_x_higher']['cramers_v'])}"
            f"（p={_fmt(t2b['school_x_higher']['p_value'])}）；"
            f"schoolsup×sex V={_fmt(t2b['schoolsup_x_sex']['cramers_v'])}"
            f"（p={_fmt(t2b['schoolsup_x_sex']['p_value'])}）",
            f"- **多重比较**：{fam['n_tests']} 项检验家族，Bonferroni 后显著 "
            f"{int(sum(fam['bonferroni_significant']))} 项，BH-FDR 后显著 {n_fdr} 项",
        ]
    lines += [
        "",
        f"## T3 多变量回归 M1（不含 G1/G2）：n={m1['n_obs']}，"
        f"R²={_fmt(m1['r_squared'])}，调整 R²={_fmt(m1['adj_r_squared'])}",
        "",
        "| 项 | 系数 | 95% CI | p 值 |",
        "|---|---|---|---|",
    ]
    for c in m1["coefficients"]:
        lines.append(
            f"| {c['term']} | {_fmt(c['coef'])} | [{_fmt(c['ci_low'])}, {_fmt(c['ci_high'])}] "
            f"| {_fmt(c['p_value'])} |"
        )
    lines += [
        "",
        f"诊断：Breusch-Pagan LM p={_fmt(m1['breusch_pagan']['lm_pvalue'])}（异方差提示）；"
        f"Jarque-Bera p={_fmt(m1['jarque_bera']['pvalue'])}（残差非正态提示）；"
        f"最大解释变量 VIF={_fmt(m1.get('vif_max'))}（共线性）。",
        "",
    ]
    t3x = r.get("t3_diagnostics_extra") or {}
    if t3x:
        dm = t3x["design_matrix"]
        ck = t3x["cooks_distance"]
        lines += [
            f"设计矩阵秩 {dm['rank']}/{dm['n_columns']}"
            f"（{'满秩' if dm['full_rank'] else '秩亏——禁止直接求解'}）；"
            f"Cook 距离 >4/n 的观测 {ck['n_above_threshold']} 例"
            f"（阈值 {_fmt(ck['threshold_4_over_n'])}），"
            f"最大 Cook's d={_fmt(ck['top'][0]['cooks_d'])}（行 {ck['top'][0]['row_index']}）。",
            "",
        ]
    t4b = r.get("t4b_prediction") or {}
    if t4b:
        ho = t4b["holdout"]
        cv = t4b["cv"]
        top = t4b["permutation_importance"]["table"][:3]
        lines += [
            f"## T4b 连续预测（80/20，seed={42}）：MAE={_fmt(ho['mae'])}，"
            f"RMSE={_fmt(ho['rmse'])}，R²={_fmt(ho['r2'])}；"
            f"5 折 CV：RMSE={_fmt(cv['rmse_mean'])}，R²={_fmt(cv['r2_mean'])}",
            "",
            "置换重要性（r²，测试集，30 次重复）："
            + "；".join(f"{x['feature']}={_fmt(x['importance_mean'])}" for x in top),
            "",
            f"## T4 目标信息时点对照：M2（含 G1/G2）调整 R²={_fmt(m2['adj_r_squared'])}，"
            f"较 M1 提升 {_fmt(m2['adj_r_squared'] - m1['adj_r_squared'])}",
            "",
            "解读：G1/G2 纳入后解释力大幅上升，但任务定义随之改变——M2 回答的是"
            "“期末解释/含泄漏预测”，不能用于解释学习行为的独立作用；回答 RQ1 的只有 M1。",
            "",
        ]
    na = r.get("not_applicable") or []
    env = r.get("env") or {}
    lines += ["## 不适用方法（显式声明，防方法错配）", ""]
    lines += [f"- {x['method']}：{x['reason']}" for x in na]
    if env:
        pk = env.get("packages", {})
        lines += [
            "",
            f"## 复现环境（seed={env.get('seed')}）",
            "",
            f"Python {env.get('python')}｜"
            + "，".join(f"{k} {v}" for k, v in pk.items())
            + f"｜平台 {env.get('platform', '')}",
        ]
    lines += [
        "",
        "## 局限",
        "",
        "观察性数据，全部结论为关联而非因果；样本限于 2008 年葡萄牙两所中学的葡语课程；"
        "异方差与残差非正态提示应同时报告稳健标准误作为敏感性检查（见 run_t1_t5 输出）。",
        "",
        EDUCATION_FOOTER,
    ]
    return "\n".join(lines) + "\n"


def build_health_report(r: dict) -> str:
    a = r["h1_audit"]
    cv = r["cv"]
    t = r["test"]
    t05 = t["threshold_05"]
    yd = t["youden"]
    lines = [
        "# 心脏病风险分类模型验证（HealthResearch 教学报告）",
        "",
        f"H1 审计：原始 {a['n_rows']} 例；缺失 ca={a['missing_by_column'].get('ca', 0)}、"
        f"thal={a['missing_by_column'].get('thal', 0)}；完整案例 {a['n_after_complete_case']} 例；"
        f"标签映射规则：{a['label_mapping']}。",
        f"标签分布：阴性 {a['target_counts']['0']} / 阳性 {a['target_counts']['1']}。",
        "",
        f"H3 划分与 CV：训练 {r['n_train']} / 测试 {r['n_test']}（分层 80/20，seed={r['seed']}）；"
        f"{cv['folds']} 折分层 CV AUC = {_fmt(cv['mean_auc'])} ± {_fmt(cv['std_auc'])}。",
        "",
        f"H4 测试集 ROC-AUC = {_fmt(t['roc_auc'])}",
        "",
        "| 阈值 | TP | FP | FN | TN | 敏感度 | 特异度 | 准确率 | F1 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for name, blk in [("0.5", t05), (f"Youden {_fmt(yd['threshold'], 3)}", yd)]:
        cm = blk["confusion_matrix"]
        lines.append(
            f"| {name} | {cm['tp']} | {cm['fp']} | {cm['fn']} | {cm['tn']} "
            f"| {_fmt(blk['sensitivity'])} | {_fmt(blk['specificity'])} | {_fmt(blk['accuracy'])} "
            f"| {_fmt(blk.get('f1'))} |"
        )
    lines += [
        "",
        f"Brier 分数 = {_fmt(t['brier'])}（校准曲线见 outputs/figures/calibration.png）；"
        f"阈值扫描表（19 档）见 outputs/tables/threshold_sweep.csv。",
    ]
    scr = r.get("h2_covariate_screen") or {}
    if scr:
        num = scr["numeric_by_target"]
        cat = scr["categorical_by_target"]
        fam = scr["multiplicity_over_family"]
        n_fdr = int(sum(fam["bh_fdr_significant"]))
        lines += [
            "",
            "## H2 协变量筛查（基线特征与患病状态，含多重校正）",
            "",
            "连续特征（Welch t / Mann-Whitney / Cohen's d，阳性 vs 阴性）：",
            "",
            "| 特征 | 阳性均值 | 阴性均值 | 差值 | d | Welch p | MWU p |",
            "|---|---|---|---|---|---|---|",
        ]
        for f in ["age", "trestbps", "chol", "thalach", "oldpeak", "ca"]:
            b = num.get(f)
            if not b:
                continue
            lines.append(
                f"| {f} | {b['group1']['mean']} | {b['group0']['mean']} | {b['mean_diff']} "
                f"| {_fmt(b['cohens_d'])} | {_fmt(b['welch_t']['p_value'])} "
                f"| {_fmt(b['mann_whitney_u']['p_value'])} |"
            )
        lines += [
            "",
            "分类特征（卡方 / Cramér's V）：",
            "",
            "| 特征 | χ² | p 值 | V | 期望频数<5 单元占比 |",
            "|---|---|---|---|---|",
        ]
        for f in ["sex", "cp", "fbs", "restecg", "exang", "slope", "thal"]:
            b = cat.get(f)
            if not b:
                continue
            lines.append(
                f"| {f} | {_fmt(b['chi2'], 2)} | {_fmt(b['p_value'])} | {_fmt(b['cramers_v'])} "
                f"| {_fmt(b['pct_cells_expected_lt_5'])} |"
            )
        lines += [
            "",
            f"多重比较：{fam['n_tests']} 项检验家族；Bonferroni 后显著 "
            f"{int(sum(fam['bonferroni_significant']))} 项，BH-FDR 后显著 {n_fdr} 项。",
        ]
    orb = r.get("h2_or_table") or {}
    if orb:
        lines += [
            "",
            f"## H2b Logistic OR 表（GLM/IRLS，n={orb['n_obs']}，95%CI）",
            "",
            "| 项 | OR | 95% CI | p 值 |",
            "|---|---|---|---|",
        ]
        for row in orb["or_table"]:
            lines.append(
                f"| {row['term']} | {_fmt(row['or'])} | [{_fmt(row['ci_low'])}, {_fmt(row['ci_high'])}] "
                f"| {_fmt(row['p_value'])} |"
            )
    imp = r.get("h4_permutation_importance") or {}
    if imp:
        lines += [
            "",
            "## H4b 置换重要性（测试集，AUC 降幅，30 次重复）",
            "",
            "；".join(
                f"{x['feature']}={_fmt(x['importance_mean'])}"
                for x in imp["table"][:5]
            ),
        ]
    sens = r.get("h4_sensitivity_model") or {}
    if sens:
        lines += [
            "",
            f"## H4c 模型设定敏感性：剔除 {sens['dropped_features']} 后 "
            f"AUC 变化 {_fmt(sens['auc_change'])}"
            f"（完整 {sens['variants']['full']['test_auc']} → 精简 "
            f"{sens['variants']['reduced']['test_auc']}）；"
            f"共有特征符号翻转 {sorted(sens.get('sign_flips_on_common_features', [])) or '无'}。",
        ]
    na = r.get("not_applicable") or []
    env = r.get("env") or {}
    lines += ["", "## 不适用方法（显式声明，防方法错配）", ""]
    lines += [f"- {x['method']}：{x['reason']}" for x in na]
    if env:
        pk = env.get("packages", {})
        lines += [
            "",
            f"## 复现环境（seed={env.get('seed')}）",
            "",
            f"Python {env.get('python')}｜"
            + "，".join(f"{k} {v}" for k, v in pk.items())
            + f"｜平台 {env.get('platform', '')}",
        ]
    lines += [
        "",
        "## 局限",
        "",
        f"测试集仅 {r['n_test']} 例，指标存在明显抽样波动（CV 标准差 ±{_fmt(cv['std_auc'], 3)}）；"
        "历史研究数据与现代临床环境不可比；预测因子关联不构成因果；**不得用于真实临床诊断**；"
        "类别特征沿用上游整数编码的简化需在正式研究中重新审视。",
        "",
        HEALTH_FOOTER,
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Assemble teaching report from results JSON")
    parser.add_argument("--education", default="", help="education results.json")
    parser.add_argument("--health", default="", help="health results.json")
    parser.add_argument("--out", required=True, help="输出 Markdown 路径")
    args = parser.parse_args(argv)

    if bool(args.education) == bool(args.health):
        sys.stdout.write(
            json.dumps({"ok": False, "error": "exactly one of --education/--health required"}) + "\n"
        )
        return
    src = Path(args.education or args.health)
    r = json.loads(src.read_text(encoding="utf-8"))
    report = build_education_report(r) if args.education else build_health_report(r)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    sys.stdout.write(json.dumps({"ok": True, "report": str(out), "chars": len(report)}) + "\n")


if __name__ == "__main__":
    main()
