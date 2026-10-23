"""reference_health.py — HealthResearch 头条指标的独立参考实现

与 tools/classification.py（sklearn Pipeline）不同的库路径：
- 划分：同样的分层 80/20（seed=42，划分层必须一致，否则比较无意义）；
- 模型：statsmodels GLM(Binomial)（MLE/IRLS 求解器 vs sklearn lbfgs）；
- AUC：秩和法（Mann-Whitney）独立实现，不经 sklearn.metrics。
三组数在浮点容差内一致即视为交叉验证通过。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "datasets/health-heart-disease/raw/processed.cleveland.data"

COLUMNS = ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg", "thalach",
           "exang", "oldpeak", "slope", "ca", "thal", "num"]
FEATURES = ["age", "trestbps", "chol", "thalach", "oldpeak", "ca",
            "sex", "cp", "fbs", "restecg", "exang", "slope", "thal"]


def rank_auc(y: np.ndarray, s: np.ndarray) -> float:
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(len(s), dtype=float)
    ss = s[order]
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and ss[j + 1] == ss[i]:
            j += 1
        ranks[order[i : j + 1]] = (i + j + 2) / 2.0
        i = j + 1
    n_pos, n_neg = int((y == 1).sum()), int((y == 0).sum())
    u = ranks[y == 1].sum() - n_pos * (n_pos + 1) / 2.0
    return float(u / (n_pos * n_neg))


def main() -> None:
    from sklearn.model_selection import train_test_split
    import statsmodels.api as sm

    df = pd.read_csv(RAW, header=None, names=COLUMNS, na_values=["?"],
                     skipinitialspace=True)
    df["target"] = (df["num"] > 0).astype(int)
    clean = df.dropna(subset=FEATURES)
    X = clean[FEATURES].astype(float)
    y = clean["target"].astype(float)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2,
                                              random_state=42, stratify=y)

    # GLM Binomial（IRLS/MLE）——标准化与否不影响 AUC（单调变换），系数报原始空间
    X_tr_c = sm.add_constant(X_tr)
    X_te_c = sm.add_constant(X_te)
    glm = sm.GLM(y_tr, X_tr_c, family=sm.families.Binomial()).fit()
    proba_te = np.asarray(glm.predict(X_te_c))
    auc = rank_auc(np.asarray(y_te), proba_te)

    out = {
        "ok": True,
        "method": "statsmodels GLM(Binomial) IRLS + rank-based AUC (independent of sklearn metrics)",
        "n_train": int(len(y_tr)),
        "n_test": int(len(y_te)),
        "test_auc_rank_method": round(auc, 6),
        "cv_note": "CV 交叉验证依赖 sklearn 折切分实现，参考口径只锁定留出集 AUC 与系数",
        "coefficients_raw_space": {
            t: round(float(v), 6) for t, v in glm.params.items()
        },
    }
    out_path = REPO / "datasets/health-heart-disease/expected/reference_results.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
