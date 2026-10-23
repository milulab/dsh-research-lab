"""stat_tests.py — 统计检验与效应量工具（检查表 T2/T4 覆盖层）

第一性原理：每项检验都对应真实研究问题（EDU：性别/父母教育与成绩；HEALTH：
基线特征与患病状态），不引入数据不支持的方法（生存/纵向/因果在协议层显式
标为不适用）。

内容：
- two_group_continuous：Welch t + Mann-Whitney U + Cohen's d（两组连续结局）
- welch_anova：多组不等方差均值比较（statsmodels anova_oneway）
- chi2_assoc：卡方独立性 + 期望频数检查 + Cramér's V
- multiplicity：Bonferroni / BH-FDR 校正
- regression_cv_metrics：固定 seed 的 80/20 + K 折 CV 的 MAE/RMSE/R²（连续预测）
- or_table_glm：Logistic 的 OR 与 95%CI（流行病学惯例，GLM/IRLS 路径）
- permutation_importance_table：置换重要性（模型无关）
- env_fingerprint：可复现环境指纹（版本/seed/平台）

设计约束与其他工具一致：函数返回纯 Python 结构（可 JSON 序列化），无打印。
"""
from __future__ import annotations

import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def two_group_continuous(y1: np.ndarray, y0: np.ndarray) -> dict:
    """两组连续结局：Welch t、Mann-Whitney U、Cohen's d（合并 SD）。"""
    y1 = np.asarray(y1, dtype=float)
    y0 = np.asarray(y0, dtype=float)
    t_w, p_w = stats.ttest_ind(y1, y0, equal_var=False)
    u, p_u = stats.mannwhitneyu(y1, y0, alternative="two-sided")
    n1, n0 = len(y1), len(y0)
    s_pooled = np.sqrt(((n1 - 1) * y1.std(ddof=1) ** 2 + (n0 - 1) * y0.std(ddof=1) ** 2)
                       / (n1 + n0 - 2)) if (n1 + n0 - 2) > 0 else np.nan
    d = float((y1.mean() - y0.mean()) / s_pooled) if s_pooled and s_pooled > 0 else None
    return {
        "group1": {"n": n1, "mean": round(float(y1.mean()), 4),
                   "sd": round(float(y1.std(ddof=1)), 4)},
        "group0": {"n": n0, "mean": round(float(y0.mean()), 4),
                   "sd": round(float(y0.std(ddof=1)), 4)},
        "welch_t": {"t": round(float(t_w), 4), "p_value": float(p_w),
                    "df": round(float(_welch_df(y1, y0)), 2)},
        "mann_whitney_u": {"u": float(u), "p_value": float(p_u)},
        "cohens_d": None if d is None else round(d, 4),
        "mean_diff": round(float(y1.mean() - y0.mean()), 4),
    }


def _welch_df(a: np.ndarray, b: np.ndarray) -> float:
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    return (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))


def welch_anova(groups: list[np.ndarray]) -> dict:
    """多组均值比较（不等方差 Welch 校正）。"""
    from statsmodels.stats.oneway import anova_oneway

    groups = [np.asarray(g, dtype=float) for g in groups if len(g) >= 2]
    res = anova_oneway(groups, use_var="unequal")
    kw_h, kw_p = stats.kruskal(*groups)
    return {
        "n_groups": len(groups),
        "group_ns": [int(len(g)) for g in groups],
        "group_means": [round(float(g.mean()), 4) for g in groups],
        "welch_f": round(float(res.statistic), 4),
        "df_num": round(float(res.df_num), 2),
        "df_denom": round(float(res.df_denom), 2),
        "p_value": float(res.pvalue),
        "kruskal_wallis": {"h": round(float(kw_h), 4), "p_value": float(kw_p)},
    }


def chi2_assoc(table: pd.DataFrame | np.ndarray, min_expected: float = 5.0) -> dict:
    """卡方独立性 + 期望频数检查 + Cramér's V。"""
    table = np.asarray(table)
    chi2, p, dof, expected = stats.chi2_contingency(table)
    n = table.sum()
    v = float(np.sqrt(chi2 / (n * (min(table.shape) - 1)))) if min(table.shape) > 1 else 0.0
    return {
        "table": table.tolist(),
        "expected_min": round(float(expected.min()), 4),
        "pct_cells_expected_lt_5": round(float((expected < min_expected).mean()), 4),
        "chi2": round(float(chi2), 4),
        "dof": int(dof),
        "p_value": float(p),
        "n": int(n),
        "cramers_v": round(v, 4),
        "expected_frequency_ok": bool(expected.min() >= min_expected),
    }


def multiplicity(pvals: list[float]) -> dict:
    """Bonferroni 与 BH-FDR 双校正。"""
    from statsmodels.stats.multitest import multipletests

    reject_bonf, p_bonf, _, _ = multipletests(pvals, alpha=0.05, method="bonferroni")
    reject_fdr, p_fdr, _, _ = multipletests(pvals, alpha=0.05, method="fdr_bh")
    return {
        "n_tests": len(pvals),
        "bonferroni_p": [float(v) for v in p_bonf],
        "bonferroni_significant": [bool(v) for v in reject_bonf],
        "bh_fdr_p": [float(v) for v in p_fdr],
        "bh_fdr_significant": [bool(v) for v in reject_fdr],
    }


def regression_cv_metrics(df: pd.DataFrame, formula: str, seed: int = 42,
                          n_splits: int = 5) -> dict:
    """连续结局预测指标：固定 seed 的 80/20 + 分层不适用（连续），用 K 折 CV。"""
    import patsy
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import KFold, train_test_split

    y_dm, X_dm = patsy.dmatrices(formula, df, return_type="dataframe")
    X = np.asarray(X_dm, dtype=float)
    y = np.asarray(y_dm).ravel()
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=seed)
    model = LinearRegression().fit(X_tr, y_tr)
    pred_te = model.predict(X_te)
    mse_te = float(np.mean((y_te - pred_te) ** 2))
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    fold = []
    for tr_i, va_i in kf.split(X):
        m = LinearRegression().fit(X[tr_i], y[tr_i])
        pv = m.predict(X[va_i])
        fold.append({
            "mae": round(float(mean_absolute_error(y[va_i], pv)), 4),
            "rmse": round(float(np.sqrt(np.mean((y[va_i] - pv) ** 2))), 4),
            "r2": round(float(r2_score(y[va_i], pv)), 4),
        })
    return {
        "holdout": {
            "n_train": int(len(y_tr)), "n_test": int(len(y_te)),
            "mae": round(float(mean_absolute_error(y_te, pred_te)), 4),
            "rmse": round(float(np.sqrt(mse_te)), 4),
            "r2": round(float(r2_score(y_te, pred_te)), 4),
        },
        "cv": {
            "folds": n_splits,
            "mae_mean": round(float(np.mean([f["mae"] for f in fold])), 4),
            "rmse_mean": round(float(np.mean([f["rmse"] for f in fold])), 4),
            "r2_mean": round(float(np.mean([f["r2"] for f in fold])), 4),
            "fold_detail": fold,
        },
    }


def or_table_glm(df: pd.DataFrame, formula: str) -> dict:
    """Logistic OR 表（95%CI），statsmodels GLM(Binomial)/IRLS 路径（流行病学惯例）。"""
    import statsmodels.api as sm
    from statsmodels.formula.api import glm

    fit = glm(formula=formula, data=df, family=sm.families.Binomial()).fit()
    ci = fit.conf_int()
    rows = []
    for term in fit.params.index:
        if term == "Intercept":
            continue
        orv = float(np.exp(fit.params[term]))
        lo, hi = float(np.exp(ci.loc[term, 0])), float(np.exp(ci.loc[term, 1]))
        rows.append({
            "term": term, "or": round(orv, 4),
            "ci_low": round(lo, 4), "ci_high": round(hi, 4),
            "p_value": float(fit.pvalues[term]),
        })
    return {"n_obs": int(fit.nobs), "or_table": rows,
            "note": "OR 来自未标准化系数；与 Pipeline(scaler) 求解器不同（IRLS vs lbfgs），"
                    "AUC 容差 0.005 内应一致（scripts/verify.py 对账）"}


def permutation_importance_table(model, X_te, y_te, features: list[str],
                                 n_repeats: int = 30, seed: int = 42,
                                 scoring: str = "roc_auc") -> dict:
    """置换重要性（模型无关）。默认评分 roc_auc；连续结局传 scoring="r2"。"""
    from sklearn.inspection import permutation_importance

    r = permutation_importance(model, X_te, y_te, n_repeats=n_repeats,
                               random_state=seed, scoring=scoring)
    rows = sorted(
        [
            {"feature": f, "importance_mean": round(float(m), 6),
             "importance_std": round(float(s), 6)}
            for f, m, s in zip(features, r.importances_mean, r.importances_std)
        ],
        key=lambda x: -x["importance_mean"],
    )
    return {"n_repeats": n_repeats, "scoring": scoring, "table": rows}


def env_fingerprint(seed: int) -> dict:
    """复现环境指纹：解释器/核心库版本/平台/随机种子。"""
    import matplotlib
    import scipy
    import sklearn
    import statsmodels

    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "seed": seed,
        "packages": {
            "numpy": np.__version__, "pandas": pd.__version__,
            "scipy": scipy.__version__, "statsmodels": statsmodels.__version__,
            "scikit-learn": sklearn.__version__, "matplotlib": matplotlib.__version__,
        },
    }


def design_matrix_diagnostics(df: pd.DataFrame, formula: str) -> dict:
    """设计矩阵秩 + 完全共线检查（回归前提的显式断言）。"""
    import patsy

    y_dm, X_dm = patsy.dmatrices(formula, df, return_type="dataframe")
    X = np.asarray(X_dm, dtype=float)
    rank = int(np.linalg.matrix_rank(X))
    return {
        "n_columns": int(X.shape[1]),
        "rank": rank,
        "full_rank": bool(rank == X.shape[1]),
        "column_names": [str(c) for c in X_dm.columns],
    }


def cooks_distance_summary(df: pd.DataFrame, formula: str, top_k: int = 5) -> dict:
    """Cook 距离：影响点审计（阈值 4/n 计数 + 前 K 名）。"""
    from statsmodels.formula.api import ols
    from statsmodels.stats.outliers_influence import OLSInfluence

    fit = ols(formula=formula, data=df).fit()
    infl = OLSInfluence(fit)
    d = np.asarray(infl.cooks_distance[0], dtype=float)
    threshold = 4.0 / len(d)
    top_idx = np.argsort(d)[::-1][:top_k]
    return {
        "n": int(len(d)),
        "threshold_4_over_n": round(float(threshold), 6),
        "n_above_threshold": int((d > threshold).sum()),
        "top": [{"row_index": int(i), "cooks_d": round(float(d[i]), 6)}
                for i in top_idx],
    }
