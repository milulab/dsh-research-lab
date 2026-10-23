"""regression.py — 线性回归与诊断工具（EduResearch T3/T4 共用）

基于 statsmodels 的 OLS：系数表（95%CI、p 值）、R²/调整 R²/F 检验、VIF 共线性、
Breusch-Pagan 异方差、Jarque-Bera 残差正态性、残差拟合图。

设计约束：stdout 只输出 JSON；公式由调用方（协议/研究问题）给出，本工具不做任何
"自动选变量"，保证分析口径由协议锁定、可复核。

用法：
  python tools/regression.py <csv> --formula "G3 ~ C(school) + Medu + studytime" \
      [--sep ';'] [--out results.json] [--fig residuals.png] [--label M1]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def _fail(stage: str, message: str) -> dict:
    return {"ok": False, "stage": stage, "error": message}


def fit_ols(df: pd.DataFrame, formula: str, label: str = "model") -> dict:
    import statsmodels.api as sm
    from statsmodels.formula.api import ols
    from statsmodels.stats.diagnostic import het_breuschpagan
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    from statsmodels.stats.stattools import jarque_bera

    import patsy

    result: dict = {"ok": True, "label": label, "formula": formula}
    try:
        model = ols(formula=formula, data=df).fit()
    except Exception as exc:  # noqa: BLE001
        return _fail("fit", f"{type(exc).__name__}: {exc}")

    result["n_obs"] = int(model.nobs)
    result["df_resid"] = int(model.df_resid)
    result["r_squared"] = round(float(model.rsquared), 6)
    result["adj_r_squared"] = round(float(model.rsquared_adj), 6)
    result["f_statistic"] = round(float(model.fvalue), 6)
    result["f_pvalue"] = float(model.f_pvalue)
    result["aic"] = round(float(model.aic), 4)
    result["bic"] = round(float(model.bic), 4)

    ci = model.conf_int()
    result["coefficients"] = [
        {
            "term": term,
            "coef": round(float(model.params[term]), 6),
            "std_err": round(float(model.bse[term]), 6),
            "ci_low": round(float(ci.loc[term, 0]), 6),
            "ci_high": round(float(ci.loc[term, 1]), 6),
            "t": round(float(model.tvalues[term]), 4),
            "p_value": float(model.pvalues[term]),
        }
        for term in model.params.index
    ]

    # VIF：仅对公式设计矩阵中的数值列计算（分类列展开后 VIF 无解释意义）
    try:
        y_dm, X_dm = patsy.dmatrices(formula, df, return_type="dataframe")
        numeric_cols = [c for c in X_dm.columns if pd.api.types.is_numeric_dtype(X_dm[c])]
        vif_rows = []
        if len(numeric_cols) >= 2:
            X_num = X_dm[numeric_cols].astype(float)
            for i, col in enumerate(X_num.columns):
                vif_rows.append(
                    {
                        "term": str(col),
                        "vif": round(float(variance_inflation_factor(X_num.values, i)), 4),
                    }
                )
        result["vif"] = vif_rows
        # 截距的 VIF 无解释意义，vif_max 只看解释变量
        result["vif_max"] = max(
            (r["vif"] for r in vif_rows if r["term"] != "Intercept"), default=None
        )
    except Exception as exc:  # noqa: BLE001
        result["vif"] = None
        result["vif_error"] = f"{type(exc).__name__}: {exc}"

    try:
        exog = model.model.exog
        endog = model.model.endog
        bp_lm, bp_lm_p, bp_f, bp_f_p = het_breuschpagan(endog, exog)
        result["breusch_pagan"] = {
            "lm_stat": round(float(bp_lm), 6),
            "lm_pvalue": float(bp_lm_p),
            "f_stat": round(float(bp_f), 6),
            "f_pvalue": float(bp_f_p),
        }
        jb_stat, jb_p, skew, kurt = jarque_bera(model.resid)
        result["jarque_bera"] = {
            "stat": round(float(jb_stat), 6),
            "pvalue": float(jb_p),
            "skew": round(float(skew), 4),
            "kurtosis": round(float(kurt), 4),
        }
    except Exception as exc:  # noqa: BLE001
        result["diagnostics_error"] = f"{type(exc).__name__}: {exc}"

    result["_resid"] = model.resid
    result["_fitted"] = model.fittedvalues
    return result


def save_residual_figure(fit: dict, path: str | Path, title: str) -> str | None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:  # noqa: BLE001
        return None
    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=150)
    ax.scatter(fit["_fitted"], fit["_resid"], s=12, alpha=0.55, edgecolors="none")
    ax.axhline(0.0, color="#c0392b", lw=1, ls="--")
    ax.set_xlabel("Fitted values")
    ax.set_ylabel("Residuals")
    ax.set_title(title)
    fig.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return str(path)


def public_view(fit: dict) -> dict:
    """剥掉不可 JSON 序列化的内部数组，只留可交付字段。"""
    return {k: v for k, v in fit.items() if not k.startswith("_")}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="OLS regression with diagnostics (JSON out)")
    parser.add_argument("csv")
    parser.add_argument("--formula", required=True)
    parser.add_argument("--sep", default=",")
    parser.add_argument("--label", default="model")
    parser.add_argument("--out", default="")
    parser.add_argument("--fig", default="")
    parser.add_argument("--fig-title", default="Residuals vs fitted")
    args = parser.parse_args(argv)

    try:
        df = pd.read_csv(args.csv, sep=args.sep, skipinitialspace=True)
    except Exception as exc:  # noqa: BLE001
        sys.stdout.write(json.dumps(_fail("load", f"{type(exc).__name__}: {exc}")) + "\n")
        return

    # 与数据包约定一致：字符串形态的数值列（如 student-por 的 G1/G2）显式强转
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            stripped = df[col].astype(str).str.strip().str.strip('"').str.strip("'")
            coerced = pd.to_numeric(stripped, errors="coerce")
            if coerced.notna().mean() >= 0.95:
                df[col] = coerced

    fit = fit_ols(df, args.formula, label=args.label)
    if fit.get("ok"):
        if args.fig:
            fig_path = save_residual_figure(fit, args.fig, args.fig_title)
            fit["figure"] = fig_path
        fit = public_view(fit)
    payload = json.dumps(fit, ensure_ascii=False, indent=2, default=str)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    sys.stdout.write(payload + "\n")


if __name__ == "__main__":
    main()
