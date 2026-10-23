"""run_h1_h5.py — HealthResearch 教学管线（协议 datasets/health-heart-disease/protocol.md）

H1 审计 → H2 基线（含协变量筛查：t/MWU/Cohen's d、卡方/Cramér's V、OR 表）
→ H3 划分/CV（防泄漏）→ H4 评价（ROC/阈值/F1/校准/置换重要性/敏感性分析）
→ H5 复现交付。随机性锁定 seed=42；独立口径 ROC-AUC 交叉核验（秩和法）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.classification import (  # noqa: E402
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    load_heart_csv,
    run_pipeline,
    save_figures,
)
from tools.report_builder import build_health_report  # noqa: E402
from tools.stat_tests import (  # noqa: E402
    chi2_assoc,
    env_fingerprint,
    multiplicity,
    or_table_glm,
    permutation_importance_table,
    two_group_continuous,
)

RAW = REPO / "datasets/health-heart-disease/raw/processed.cleveland.data"

if hasattr(sys.stdout, "reconfigure") and (sys.stdout.encoding or "").lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")
OUT = REPO / "examples/health-demo/outputs"

GLM_FORMULA = ("target ~ age + sex + cp + trestbps + chol + fbs + restecg "
               "+ thalach + exang + oldpeak + slope + ca + thal")
SENSITIVITY_DROP = ["fbs", "restecg"]  # 敏感性分析：剔除弱变量的精简设定


def independent_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    """与 sklearn 无关的 ROC-AUC 口径：Mann-Whitney U / 秩和法（含并列平均秩）。"""
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty(len(scores), dtype=float)
    sorted_scores = scores[order]
    i = 0
    while i < len(scores):
        j = i
        while j + 1 < len(scores) and sorted_scores[j + 1] == sorted_scores[i]:
            j += 1
        ranks[order[i : j + 1]] = (i + j + 2) / 2.0
        i = j + 1
    n_pos = int((y_true == 1).sum())
    n_neg = int((y_true == 0).sum())
    u = ranks[y_true == 1].sum() - n_pos * (n_pos + 1) / 2.0
    return float(u / (n_pos * n_neg))


def f1_from_cm(cm: dict) -> float | None:
    tp, fp, fn = cm["tp"], cm["fp"], cm["fn"]
    denom = 2 * tp + fp + fn
    return None if denom == 0 else round(2 * tp / denom, 4)


def covariate_screen(clean: pd.DataFrame) -> dict:
    """检查表 T2 覆盖：基线特征表（连续：Welch t/MWU/Cohen's d；分类：卡方/Cramér's V）+ 多重校正。"""
    pos = clean[clean["target"] == 1]
    neg = clean[clean["target"] == 0]
    numeric = {}
    categorical = {}
    for f in NUMERIC_FEATURES:
        numeric[f] = two_group_continuous(pos[f].to_numpy(), neg[f].to_numpy())
    for f in CATEGORICAL_FEATURES:
        categorical[f] = chi2_assoc(pd.crosstab(clean[f].astype(int), clean["target"]))

    family: dict[str, float] = {}
    for f, r in numeric.items():
        family[f"{f}_welch_t"] = float(r["welch_t"]["p_value"])
        family[f"{f}_mann_whitney"] = float(r["mann_whitney_u"]["p_value"])
    for f, r in categorical.items():
        family[f"{f}_chi2"] = float(r["p_value"])
    corrected = multiplicity(list(family.values()))
    corrected["family"] = family
    return {
        "numeric_by_target": numeric,
        "categorical_by_target": categorical,
        "multiplicity_over_family": corrected,
    }


def sensitivity_model(clean: pd.DataFrame) -> dict:
    """模型设定敏感性分析：完整设定 vs 剔除弱变量的精简设定（同一划分，seed=42）。"""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    features_full = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    features_reduced = [f for f in features_full if f not in SENSITIVITY_DROP]
    out = {"dropped_features": SENSITIVITY_DROP, "variants": {}}
    for name, feats in [("full", features_full), ("reduced", features_reduced)]:
        X = clean[feats]
        y = clean["target"]
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2,
                                                  random_state=42, stratify=y)
        pipe = Pipeline([("scaler", StandardScaler()),
                         ("clf", LogisticRegression(max_iter=1000))]).fit(X_tr, y_tr)
        auc = float(roc_auc_score(y_te, pipe.predict_proba(X_te)[:, 1]))
        sign = {f: 1 if float(c) > 0 else -1
                for f, c in zip(feats, pipe.named_steps["clf"].coef_[0])}
        out["variants"][name] = {
            "features": feats,
            "test_auc": round(auc, 6),
            "coefficient_signs": sign,
        }
    full_sign = out["variants"]["full"]["coefficient_signs"]
    red_sign = out["variants"]["reduced"]["coefficient_signs"]
    common = [f for f in red_sign if f in full_sign]
    out["sign_flips_on_common_features"] = [f for f in common if full_sign[f] != red_sign[f]]
    out["auc_change"] = round(
        out["variants"]["reduced"]["test_auc"] - out["variants"]["full"]["test_auc"], 6)
    return out


NOT_APPLICABLE = [
    {"method": "survival_analysis_cox", "reason": "无随访时间/删失字段，不是时间-事件数据"},
    {"method": "longitudinal_mixed_models", "reason": "单时点横断面记录，无重复测量"},
    {"method": "causal_effect_estimation", "reason": "观察性数据无识别策略；OR 只表述关联"},
    {"method": "survey_weighted_estimation",
     "reason": "非复杂抽样（NHANES 类权重/分层/聚类方法不适用本数据）"},
    {"method": "imputation_as_primary",
     "reason": "协议主分析为完整案例法（n=297）；任何填补策略须修订协议后另行验证"},
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    (OUT / "tables").mkdir(exist_ok=True)
    (OUT / "figures").mkdir(exist_ok=True)

    loaded = load_heart_csv(RAW)
    assert loaded["ok"], loaded
    clean = loaded["data"]
    result = run_pipeline(clean, seed=42, cv_folds=5)
    result["h1_audit"] = loaded["audit"]

    # H2 覆盖：协变量筛查（基线表）+ OR 表（流行病学惯例，GLM/IRLS 路径）
    screen = covariate_screen(clean)
    result["h2_covariate_screen"] = screen
    result["h2_or_table"] = or_table_glm(clean, GLM_FORMULA)

    # H3：划分复用（与 run_pipeline 完全一致），供 OR/置换/敏感性共用
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    features = result["features"]
    X = clean[features]
    y = clean["target"]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2,
                                              random_state=42, stratify=y)
    pipe = Pipeline([("scaler", StandardScaler()),
                     ("clf", LogisticRegression(max_iter=1000))]).fit(X_tr, y_tr)
    proba_te = pipe.predict_proba(X_te)[:, 1]

    # H4 增补①：独立口径 AUC 交叉核验（sklearn vs 秩和法，须一致到浮点容差）
    auc_sklearn = float(roc_auc_score(y_te, proba_te))
    auc_rank = independent_auc(np.asarray(y_te), np.asarray(proba_te))
    result["test"]["auc_crosscheck"] = {
        "sklearn": round(auc_sklearn, 6),
        "rank_method": round(auc_rank, 6),
        "abs_diff": round(abs(auc_sklearn - auc_rank), 9),
    }
    assert abs(auc_sklearn - auc_rank) < 1e-9, "两套 AUC 口径不一致，禁止发布结果"

    # H4 增补②：F1（0.5 与 Youden 两阈值）
    result["test"]["threshold_05"]["f1"] = f1_from_cm(result["test"]["threshold_05"]["confusion_matrix"])
    result["test"]["youden"]["f1"] = f1_from_cm(result["test"]["youden"]["confusion_matrix"])

    # H4 增补③：置换重要性（模型无关，测试集，scoring=roc_auc）
    result["h4_permutation_importance"] = permutation_importance_table(
        pipe, X_te, y_te, features, n_repeats=30, seed=42, scoring="roc_auc")

    # H4 增补④：模型设定敏感性分析（完整 vs 精简）
    result["h4_sensitivity_model"] = sensitivity_model(clean)

    # 系数方向表（标准化空间 → 解读顺序参考，不输出为临床效应量）
    coef_rows = [
        {"feature": f, "coef_scaled": c}
        for f, c in sorted(result["model"]["coefficients_scaled_space"].items(),
                           key=lambda kv: -abs(kv[1]))
    ]
    pd.DataFrame(coef_rows).to_csv(OUT / "tables/coefficients_scaled.csv", index=False)
    pd.DataFrame(result["test"]["threshold_sweep"]).to_csv(
        OUT / "tables/threshold_sweep.csv", index=False)
    pd.DataFrame(result["h2_or_table"]["or_table"]).to_csv(
        OUT / "tables/or_table.csv", index=False)
    pd.DataFrame(result["h4_permutation_importance"]["table"]).to_csv(
        OUT / "tables/permutation_importance.csv", index=False)

    # 复现环境 + 不适用方法声明
    result["env"] = env_fingerprint(seed=42)
    result["not_applicable"] = NOT_APPLICABLE

    figs = save_figures(result, OUT / "figures")
    result["figures"] = figs

    (OUT / "results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    (OUT / "report.md").write_text(build_health_report(result), encoding="utf-8")

    screen_corr = screen["multiplicity_over_family"]
    print(json.dumps({
        "ok": True,
        "h1": {"n_raw": loaded["audit"]["n_rows"],
               "missing": loaded["audit"]["missing_by_column"],
               "n_complete": loaded["audit"]["n_after_complete_case"],
               "target": loaded["audit"]["target_counts"]},
        "screen_fdr_significant": int(sum(screen_corr["bh_fdr_significant"])),
        "or_ca": next(r["or"] for r in result["h2_or_table"]["or_table"] if r["term"] == "ca"),
        "cv_auc": result["cv"]["mean_auc"],
        "test_auc": result["test"]["roc_auc"],
        "auc_crosscheck_diff": result["test"]["auc_crosscheck"]["abs_diff"],
        "f1_at_05": result["test"]["threshold_05"]["f1"],
        "youden": result["test"]["youden"],
        "brier": result["test"]["brier"],
        "sensitivity_auc_change": result["h4_sensitivity_model"]["auc_change"],
        "outputs": str(OUT),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
