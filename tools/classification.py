"""classification.py — 心脏病风险分类管线（HealthResearch H1–H4 核心）

按 datasets/health-heart-disease/protocol.md 的锁定规则实现：
- 解析无表头 CSV，"?" 读为缺失；二元标签 num==0→0，num∈{1,2,3,4}→1（显式记录）；
- 完整案例策略（预期剔除 6 例 → n=297），剔除数写入结果；
- 80/20 分层划分（random_state=42）；StandardScaler+LogisticRegression 放入同一
  Pipeline，标准化只在训练侧拟合（防泄漏）；另报 5 折分层 CV AUC；
- 测试集 ROC-AUC、0.5 阈值混淆矩阵/敏感度/特异度、Youden 最优阈值、阈值扫描表、
  Brier 分数与校准曲线数据。

设计约束：stdout 只输出 JSON；错误结构化；图表 Agg 后端落盘并返回路径。

用法：
  python tools/classification.py <processed.csv> --out results.json --fig-dir outputs/figures
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HEART_COLUMNS = [
    "age", "sex", "cp", "trestbps", "chol", "fbs", "restecg", "thalach",
    "exang", "oldpeak", "slope", "ca", "thal", "num",
]
CATEGORICAL_FEATURES = ["sex", "cp", "fbs", "restecg", "exang", "slope", "thal"]
NUMERIC_FEATURES = ["age", "trestbps", "chol", "thalach", "oldpeak", "ca"]
LABEL_MAPPING = "num==0 -> 0 (negative); num in {1,2,3,4} -> 1 (positive)"


def _fail(stage: str, message: str) -> dict:
    return {"ok": False, "stage": stage, "error": message}


def load_heart_csv(path: str | Path) -> dict:
    """H1：加载 + 审计 + 标签二元化（规则显式记录）。"""
    p = Path(path)
    if not p.is_file():
        return _fail("load", f"file not found: {p}")
    try:
        df = pd.read_csv(p, header=None, names=HEART_COLUMNS, na_values=["?"], skipinitialspace=True)
    except Exception as exc:  # noqa: BLE001
        return _fail("parse", f"{type(exc).__name__}: {exc}")

    audit = {
        "n_rows": int(len(df)),
        "n_cols": int(df.shape[1]),
        "missing_by_column": {c: int(df[c].isna().sum()) for c in df.columns if df[c].isna().any()},
        "rows_with_any_missing": int(df.isna().any(axis=1).sum()),
        "num_value_counts": {str(k): int(v) for k, v in df["num"].value_counts().sort_index().items()},
    }
    df["target"] = (df["num"] > 0).astype(int)  # 显式映射规则见 LABEL_MAPPING
    clean = df.dropna(subset=[c for c in HEART_COLUMNS if c != "num"]).copy()
    audit["n_after_complete_case"] = int(len(clean))
    audit["target_counts"] = {
        "0": int((clean["target"] == 0).sum()),
        "1": int((clean["target"] == 1).sum()),
    }
    audit["label_mapping"] = LABEL_MAPPING
    return {"ok": True, "audit": audit, "data": clean}


def run_pipeline(clean: pd.DataFrame, seed: int = 42, cv_folds: int = 5) -> dict:
    """H2–H4：基线模型、防泄漏划分、CV 与评价。"""
    from sklearn.calibration import calibration_curve
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (
        brier_score_loss,
        confusion_matrix,
        roc_auc_score,
        roc_curve,
    )
    from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    features = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    X = clean[features].copy()
    # thal/ca 为数值编码的类别（3/6/7、0-3），logistic 按数值处理即可；
    # cp/restecg/slope 同理保持上游整数编码，Pipeline 内标准化不改变其序关系，
    # 该简化的局限写入 report 的 limitations。
    y = clean["target"]

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y
    )
    pipe = Pipeline(
        [("scaler", StandardScaler()), ("clf", LogisticRegression(max_iter=1000))]
    )
    pipe.fit(X_tr, y_tr)

    skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=seed)
    cv_scores = cross_val_score(pipe, X_tr, y_tr, cv=skf, scoring="roc_auc")

    proba = pipe.predict_proba(X_te)[:, 1]
    auc = float(roc_auc_score(y_te, proba))
    fpr, tpr, roc_thr = roc_curve(y_te, proba)

    cm05 = confusion_matrix(y_te, (proba >= 0.5).astype(int))
    tn, fp, fn, tp = (int(v) for v in cm05.ravel())
    sens05 = tp / (tp + fn) if (tp + fn) else None
    spec05 = tn / (tn + fp) if (tn + fp) else None

    youden = tpr - fpr
    i_best = int(np.argmax(youden[:-1]))
    thr_best = float(roc_thr[i_best])
    cm_best = confusion_matrix(y_te, (proba >= thr_best).astype(int))
    tn_b, fp_b, fn_b, tp_b = (int(v) for v in cm_best.ravel())

    sweep = []
    for thr in np.arange(0.05, 1.0, 0.05):
        pred = (proba >= thr).astype(int)
        tp_s = int(((pred == 1) & (y_te == 1)).sum())
        fn_s = int(((pred == 0) & (y_te == 1)).sum())
        tn_s = int(((pred == 0) & (y_te == 0)).sum())
        fp_s = int(((pred == 1) & (y_te == 0)).sum())
        sweep.append(
            {
                "threshold": round(float(thr), 2),
                "sensitivity": round(tp_s / (tp_s + fn_s), 4) if (tp_s + fn_s) else None,
                "specificity": round(tn_s / (tn_s + fp_s), 4) if (tn_s + fp_s) else None,
                "accuracy": round((tp_s + tn_s) / len(y_te), 4),
            }
        )

    frac_pos, mean_pred = calibration_curve(y_te, proba, n_bins=8, strategy="uniform")
    brier = float(brier_score_loss(y_te, proba))

    coefs = pipe.named_steps["clf"].coef_[0]
    intercept = float(pipe.named_steps["clf"].intercept_[0])
    scaler_mean = pipe.named_steps["scaler"].mean_

    return {
        "ok": True,
        "seed": seed,
        "n_train": int(len(y_tr)),
        "n_test": int(len(y_te)),
        "features": features,
        "label_mapping": LABEL_MAPPING,
        "cv": {
            "folds": cv_folds,
            "scoring": "roc_auc",
            "mean_auc": round(float(cv_scores.mean()), 6),
            "std_auc": round(float(cv_scores.std()), 6),
            "fold_aucs": [round(float(s), 6) for s in cv_scores],
        },
        "test": {
            "roc_auc": round(auc, 6),
            "threshold_05": {
                "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
                "sensitivity": None if sens05 is None else round(float(sens05), 4),
                "specificity": None if spec05 is None else round(float(spec05), 4),
                "accuracy": round(float((tp + tn) / len(y_te)), 4),
            },
            "youden": {
                "threshold": round(thr_best, 4),
                "confusion_matrix": {"tn": tn_b, "fp": fp_b, "fn": fn_b, "tp": tp_b},
                "sensitivity": round(tp_b / (tp_b + fn_b), 4) if (tp_b + fn_b) else None,
                "specificity": round(tn_b / (tn_b + fp_b), 4) if (tn_b + fp_b) else None,
                "accuracy": round(float((tp_b + tn_b) / len(y_te)), 4),
            },
            "threshold_sweep": sweep,
            "brier": round(brier, 6),
            "calibration_curve": {
                "mean_predicted": [round(float(v), 4) for v in mean_pred],
                "fraction_positive": [round(float(v), 4) for v in frac_pos],
            },
            "roc_curve": {
                "fpr": [round(float(v), 6) for v in fpr],
                "tpr": [round(float(v), 6) for v in tpr],
            },
        },
        "model": {
            "type": "Pipeline(StandardScaler, LogisticRegression(max_iter=1000))",
            "intercept_scaled_space": round(intercept, 6),
            "coefficients_scaled_space": {
                f: round(float(c), 6) for f, c in zip(features, coefs)
            },
            "scaler_mean": {f: round(float(m), 6) for f, m in zip(features, scaler_mean)},
        },
    }


def save_figures(result: dict, fig_dir: str | Path) -> dict:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:  # noqa: BLE001
        return {}
    fig_dir = Path(fig_dir)
    fig_dir.mkdir(parents=True, exist_ok=True)
    paths = {}

    t = result["test"]
    fig, ax = plt.subplots(figsize=(5.2, 5.2), dpi=150)
    ax.plot(t["roc_curve"]["fpr"], t["roc_curve"]["tpr"], lw=2,
            label=f"ROC (AUC={t['roc_auc']:.3f})")
    ax.plot([0, 1], [0, 1], ls="--", lw=1, color="#888")
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("Heart disease classifier — held-out ROC")
    ax.legend(loc="lower right")
    fig.tight_layout()
    p = fig_dir / "roc_curve.png"
    fig.savefig(p)
    plt.close(fig)
    paths["roc"] = str(p)

    fig, ax = plt.subplots(figsize=(5.2, 5.2), dpi=150)
    cc = t["calibration_curve"]
    ax.plot(cc["mean_predicted"], cc["fraction_positive"], marker="o", lw=1.5)
    ax.plot([0, 1], [0, 1], ls="--", lw=1, color="#888")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Observed fraction positive")
    ax.set_title(f"Calibration (Brier={t['brier']:.3f})")
    fig.tight_layout()
    p = fig_dir / "calibration.png"
    fig.savefig(p)
    plt.close(fig)
    paths["calibration"] = str(p)
    return paths


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Heart-disease logistic pipeline (JSON out)")
    parser.add_argument("csv", help="processed.cleveland.data 路径（或 processed/ 产物）")
    parser.add_argument("--out", default="")
    parser.add_argument("--fig-dir", default="")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    loaded = load_heart_csv(args.csv)
    if not loaded.get("ok"):
        sys.stdout.write(json.dumps(loaded, ensure_ascii=False) + "\n")
        return
    result = run_pipeline(loaded["data"], seed=args.seed)
    result["h1_audit"] = loaded["audit"]
    if args.fig_dir:
        result["figures"] = save_figures(result, args.fig_dir)
    payload = json.dumps(result, ensure_ascii=False, indent=2, default=str)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    sys.stdout.write(payload + "\n")


if __name__ == "__main__":
    main()
