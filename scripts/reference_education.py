"""reference_education.py — EduResearch 头条指标的独立参考实现

刻意不使用 statsmodels：OLS 用 numpy 最小二乘 + 显式设计矩阵（哑变量手工编码），
标准误用经典公式，t/p 用 scipy 分布函数；T2 关联直接用 scipy 非参数检验。
用途：与 tools/regression.py（statsmodels 路径）交叉验证，两套独立实现必须一致。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "datasets/education-student-performance/raw/student-por.csv"

M1_TERMS = ["Intercept", "school_MS", "sex_M", "Medu", "Fedu", "studytime",
            "failures", "absences"]


def design_matrix(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """与协议 M1 公式一致的显式设计矩阵（参考水平 school=GP, sex=F）。"""
    n = len(df)
    X = np.column_stack([
        np.ones(n),
        (df["school"] == "MS").astype(float),
        (df["sex"] == "M").astype(float),
        df["Medu"].astype(float),
        df["Fedu"].astype(float),
        df["studytime"].astype(float),
        df["failures"].astype(float),
        df["absences"].astype(float),
    ])
    y = df["G3"].astype(float).values
    return X, y, M1_TERMS


def main() -> None:
    df = pd.read_csv(RAW, sep=";", skipinitialspace=True)
    X, y, names = design_matrix(df)
    n, k = X.shape

    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    rank = np.linalg.matrix_rank(X)
    df_resid = n - rank
    sigma2 = float(resid @ resid) / df_resid
    cov = sigma2 * np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(cov))
    t_stats = beta / se
    p_vals = 2 * stats.t.sf(np.abs(t_stats), df_resid)

    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - float(resid @ resid) / ss_tot
    adj_r2 = 1 - (1 - r2) * (n - 1) / df_resid

    spearman = {}
    for var in ["studytime", "failures", "Medu", "Fedu"]:
        rho, p = stats.spearmanr(df[var], df["G3"])
        spearman[var] = {"rho": round(float(rho), 6), "p": float(p)}
    r_p, p_p = stats.pearsonr(df["absences"], df["G3"])
    spearman["absences_pearson"] = {"rho": round(float(r_p), 6), "p": float(p_p)}

    out = {
        "ok": True,
        "method": "numpy lstsq + classic OLS SE (independent of statsmodels)",
        "n": int(n),
        "df_resid": int(df_resid),
        "r_squared": round(r2, 6),
        "adj_r_squared": round(adj_r2, 6),
        "coefficients": [
            {"term": nm, "coef": round(float(b), 6), "std_err": round(float(s), 6),
             "t": round(float(tv), 4), "p_value": float(pv)}
            for nm, b, s, tv, pv in zip(names, beta, se, t_stats, p_vals)
        ],
        "t2_spearman": spearman,
    }
    out_path = REPO / "datasets/education-student-performance/expected/reference_results.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))
    if "--quiet" not in sys.argv:
        pass


if __name__ == "__main__":
    main()
