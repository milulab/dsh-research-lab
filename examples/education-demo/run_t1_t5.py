"""run_t1_t5.py — EduResearch 教学管线（协议 datasets/education-student-performance/protocol.md）

T1 审计 → T2 单变量关联 + 组间检验/效应量/多重校正 → T3 M1 回归（诊断+影响点）
→ T4 M2 泄漏对照 + 连续预测指标（MAE/RMSE/R² + CV + 置换重要性）→ T5 复现交付。
确定性：仅 T4b 的划分/CV 使用 seed=42，可精确复现。产物写入 outputs/（tables/figures）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.data_audit import audit_csv  # noqa: E402
from tools.regression import fit_ols, public_view, save_residual_figure  # noqa: E402
from tools.stat_tests import (  # noqa: E402
    chi2_assoc,
    cooks_distance_summary,
    design_matrix_diagnostics,
    env_fingerprint,
    multiplicity,
    permutation_importance_table,
    regression_cv_metrics,
    two_group_continuous,
    welch_anova,
)
from tools.report_builder import build_education_report  # noqa: E402

RAW = REPO / "datasets/education-student-performance/raw/student-por.csv"

if hasattr(sys.stdout, "reconfigure") and (sys.stdout.encoding or "").lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")
OUT = REPO / "examples/education-demo/outputs"

M1_FORMULA = "G3 ~ C(school) + C(sex) + Medu + Fedu + studytime + failures + absences"
M2_FORMULA = M1_FORMULA + " + G1 + G2"


def t1_audit() -> dict:
    audit = audit_csv(RAW, sep=";")
    assert audit["ok"], audit
    assert audit["n_rows"] == 649 and audit["n_cols"] == 33, "样本规模与来源声明不符"

    # 原始字节检查：G1/G2 取值带引号（静默类型漂移的教学证据）
    lines = RAW.read_text(encoding="utf-8-sig").splitlines()
    header = lines[0].split(";")
    second = lines[1].split(";")
    g1_i, g2_i = header.index("G1"), header.index("G2")
    quoted_g1 = second[g1_i].strip().startswith('"')
    quoted_g2 = second[g2_i].strip().startswith('"')
    assert quoted_g1 and quoted_g2, "预期 raw 文件中 G1/G2 带引号（类型漂移教学点缺失）"

    df = pd.read_csv(RAW, sep=";", skipinitialspace=True)
    # 类型断言：解析层显式核查，不信任静默推断
    int_cols = ["age", "Medu", "Fedu", "traveltime", "studytime", "failures",
                "famrel", "freetime", "goout", "Dalc", "Walc", "health",
                "absences", "G1", "G2", "G3"]
    for col in int_cols:
        assert pd.api.types.is_integer_dtype(df[col]), f"{col} 应为整数型，实测 {df[col].dtype}"
    cat_cols = ["school", "sex", "address", "famsize", "Pstatus", "Mjob", "Fjob",
                "reason", "guardian", "schoolsup", "famsup", "paid", "activities",
                "nursery", "higher", "internet", "romantic"]
    for col in cat_cols:
        assert pd.api.types.is_string_dtype(df[col]), f"{col} 应为类别型"
    assert set(df["school"].unique()) <= {"GP", "MS"}
    assert df["G3"].between(0, 20).all()

    audit["raw_bytes_check"] = {
        "g1_quoted_in_raw": quoted_g1,
        "g2_quoted_in_raw": quoted_g2,
        "lesson": "引号数字被标准解析器静默吸收为整数——解析层必须显式断言目标类型",
    }
    audit["dtype_assertions_passed"] = True
    return audit


def t2_associations(df: pd.DataFrame) -> list[dict]:
    rows = []
    for var in ["studytime", "failures", "Medu", "Fedu"]:
        rho, p = stats.spearmanr(df[var], df["G3"])
        rows.append({"variable": var, "method": "spearman",
                     "statistic": round(float(rho), 6), "p_value": float(p)})
    r_p, p_p = stats.pearsonr(df["absences"], df["G3"])
    rho_a, p_a = stats.spearmanr(df["absences"], df["G3"])
    rows.append({"variable": "absences", "method": "pearson",
                 "statistic": round(float(r_p), 6), "p_value": float(p_p)})
    rows.append({"variable": "absences", "method": "spearman",
                 "statistic": round(float(rho_a), 6), "p_value": float(p_a)})
    return rows


def t2b_group_tests(df: pd.DataFrame) -> dict:
    """检查表 T2 覆盖：两独立组 / 多组 Welch ANOVA / 卡方 + 效应量 + 多重校正。"""
    g_f = df.loc[df["sex"] == "F", "G3"].to_numpy()
    g_m = df.loc[df["sex"] == "M", "G3"].to_numpy()
    sex_test = two_group_continuous(g_m, g_f)

    medu_groups = [g["G3"].to_numpy() for _, g in df.groupby("Medu")]
    medu_anova = welch_anova(medu_groups)

    chi_school_higher = chi2_assoc(pd.crosstab(df["school"], df["higher"]))
    chi_schoolsup_sex = chi2_assoc(pd.crosstab(df["schoolsup"], df["sex"]))

    family = {
        "studytime_spearman": t2_studytime_p(df),
        "failures_spearman": float(stats.spearmanr(df["failures"], df["G3"])[1]),
        "absences_pearson": float(stats.pearsonr(df["absences"], df["G3"])[1]),
        "sex_welch_t": float(sex_test["welch_t"]["p_value"]),
        "sex_mann_whitney": float(sex_test["mann_whitney_u"]["p_value"]),
        "medu_welch_anova": float(medu_anova["p_value"]),
        "school_x_higher_chi2": float(chi_school_higher["p_value"]),
        "schoolsup_x_sex_chi2": float(chi_schoolsup_sex["p_value"]),
    }
    corrected = multiplicity(list(family.values()))
    corrected["family"] = family
    return {
        "sex_g3_two_group": sex_test,
        "medu_g3_welch_anova": medu_anova,
        "school_x_higher": chi_school_higher,
        "schoolsup_x_sex": chi_schoolsup_sex,
        "multiplicity_over_family": corrected,
    }


def t2_studytime_p(df: pd.DataFrame) -> float:
    return float(stats.spearmanr(df["studytime"], df["G3"])[1])


def t3_extras(df: pd.DataFrame) -> dict:
    return {
        "design_matrix": design_matrix_diagnostics(df, M1_FORMULA),
        "cooks_distance": cooks_distance_summary(df, M1_FORMULA),
    }


def t4b_prediction(df: pd.DataFrame) -> dict:
    """检查表 T4 覆盖：连续预测（MAE/RMSE/R²，seed=42）+ K 折 CV + 置换重要性。"""
    import patsy
    from sklearn.inspection import permutation_importance
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import train_test_split

    metrics = regression_cv_metrics(df, M1_FORMULA, seed=42, n_splits=5)

    y_dm, X_dm = patsy.dmatrices(M1_FORMULA, df, return_type="dataframe")
    X, y = np.asarray(X_dm, dtype=float), np.asarray(y_dm).ravel()
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
    lin = LinearRegression().fit(X_tr, y_tr)
    imp = permutation_importance(lin, X_te, y_te, n_repeats=30, random_state=42,
                                 scoring="r2")
    table = sorted(
        [{"feature": str(c), "importance_mean": round(float(m), 6),
          "importance_std": round(float(s), 6)}
         for c, m, s in zip(X_dm.columns, imp.importances_mean, imp.importances_std)],
        key=lambda x: -x["importance_mean"],
    )
    metrics["permutation_importance"] = {
        "n_repeats": 30, "scoring": "r2", "table": table[:8],
    }
    return metrics


NOT_APPLICABLE = [
    {"method": "survival_analysis", "reason": "无生存时间/删失字段（横断面成绩数据）"},
    {"method": "longitudinal_mixed_models", "reason": "单时点横断面设计，无重复测量"},
    {"method": "causal_inference", "reason": "观察性数据且无识别策略；全部结论限关联表述"},
    {"method": "survey_weighted_estimation", "reason": "非复杂抽样设计（无权重/分层/聚类字段）"},
    {"method": "ordinal_logistic_as_primary",
     "reason": "G3 有界离散但近似连续，OLS 为协议主模型；序数模型仅可作为课后扩展"},
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    (OUT / "tables").mkdir(exist_ok=True)
    (OUT / "figures").mkdir(exist_ok=True)

    t1 = t1_audit()
    df = pd.read_csv(RAW, sep=";", skipinitialspace=True)
    t2 = t2_associations(df)
    t2b = t2b_group_tests(df)

    m1 = fit_ols(df, M1_FORMULA, label="M1_without_prior_grades")
    # HC3 稳健标准误（异方差的敏感性检查，系数不变、SE 变）
    import statsmodels.formula.api as smf
    m1_hc3_fit = smf.ols(M1_FORMULA, data=df).fit(cov_type="HC3")
    m1["hc3_se"] = {t: round(float(m1_hc3_fit.bse[t]), 6) for t in m1_hc3_fit.params.index}
    m2 = fit_ols(df, M2_FORMULA, label="M2_with_prior_grades_leakage_audit")
    t3x = t3_extras(df)
    t4b = t4b_prediction(df)

    results = {
        "suite": "education-student-performance",
        "protocol_version": "V1.0",
        "data_file": "raw/student-por.csv",
        "env": env_fingerprint(seed=42),
        "t1_audit": t1,
        "t2_associations": t2,
        "t2b_group_tests": t2b,
        "t3_model_m1": public_view(m1),
        "t3_diagnostics_extra": t3x,
        "t4_model_m2": public_view(m2),
        "t4_adj_r2_delta": round(m2["adj_r_squared"] - m1["adj_r_squared"], 6),
        "t4b_prediction": t4b,
        "not_applicable": NOT_APPLICABLE,
        "reading_note": (
            "M2 含 G1/G2：调整 R² 大幅上升但任务定义改变为期末解释/含泄漏预测；"
            "回答研究问题 RQ1 的只有 M1。所有结论为关联，不构成因果。"
        ),
    }

    fig_m1 = save_residual_figure(m1, OUT / "figures/m1_residuals.png",
                                  "M1 residuals vs fitted (G3 model)")
    fig_m2 = save_residual_figure(m2, OUT / "figures/m2_residuals.png",
                                  "M2 residuals vs fitted (with G1/G2)")
    results["figures"] = {"m1_residuals": fig_m1, "m2_residuals": fig_m2}

    pd.DataFrame(t2).to_csv(OUT / "tables/t2_associations.csv", index=False)
    sex = t2b["sex_g3_two_group"]
    pd.DataFrame([{
        "comparison": "G3 by sex (M vs F)", "mean_diff": sex["mean_diff"],
        "cohens_d": sex["cohens_d"],
        "welch_t_p": sex["welch_t"]["p_value"],
        "mwu_p": sex["mann_whitney_u"]["p_value"],
    }]).to_csv(OUT / "tables/t2b_group_tests.csv", index=False)
    pd.DataFrame(m1["coefficients"]).to_csv(OUT / "tables/m1_coefficients.csv", index=False)
    pd.DataFrame(m2["coefficients"]).to_csv(OUT / "tables/m2_coefficients.csv", index=False)
    pd.DataFrame(t4b["permutation_importance"]["table"]).to_csv(
        OUT / "tables/t4b_permutation_importance.csv", index=False)

    (OUT / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    (OUT / "report.md").write_text(build_education_report(results), encoding="utf-8")

    # 控制台摘要（供课堂投屏核对）
    fam = t2b["multiplicity_over_family"]
    print(json.dumps({
        "ok": True,
        "t1": {"n": t1["n_rows"], "dups": t1["exact_duplicate_rows"],
               "missing": t1["total_missing_cells"]},
        "t2_studytime_rho": t2[0]["statistic"],
        "t2b_sex_d": t2b["sex_g3_two_group"]["cohens_d"],
        "t2b_fdr_significant": int(sum(fam["bh_fdr_significant"])),
        "t3_m1_adj_r2": m1["adj_r_squared"],
        "t4_m2_adj_r2": m2["adj_r_squared"],
        "delta": results["t4_adj_r2_delta"],
        "t4b_holdout_rmse": t4b["holdout"]["rmse"],
        "t4b_cv_r2_mean": t4b["cv"]["r2_mean"],
        "outputs": str(OUT),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
