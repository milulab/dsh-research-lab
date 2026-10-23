"""tools 层单元测试 — 全部跑基准真实数据（无合成夹具）"""
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.data_audit import audit_csv  # noqa: E402
from tools.classification import load_heart_csv, run_pipeline  # noqa: E402
from tools.regression import fit_ols  # noqa: E402

POR = REPO / "datasets/education-student-performance/raw/student-por.csv"
CLEV = REPO / "datasets/health-heart-disease/raw/processed.cleveland.data"


def test_audit_student_por():
    r = audit_csv(POR, sep=";")
    assert r["ok"]
    assert (r["n_rows"], r["n_cols"]) == (649, 33)
    assert r["exact_duplicate_rows"] == 0
    assert r["total_missing_cells"] == 0


def test_audit_cleveland_sentinel_values():
    names = "age,sex,cp,trestbps,chol,fbs,restecg,thalach,exang,oldpeak,slope,ca,thal,num"
    r = audit_csv(CLEV, no_header=True, names=names.split(","))
    assert r["ok"] and r["n_rows"] == 303
    by_name = {c["name"]: c for c in r["columns"]}
    assert by_name["ca"]["missing"] == 0 and by_name["thal"]["missing"] == 0
    assert by_name["ca"]["sentinel_values"] == ["?"]
    assert by_name["thal"]["sentinel_values"] == ["?"]


def test_audit_missing_file_structured_error():
    r = audit_csv(REPO / "datasets/nope.csv")
    assert r["ok"] is False and "error" in r


def test_regression_m1_matches_golden():
    df = pd.read_csv(POR, sep=";", skipinitialspace=True)
    fit = fit_ols(df, "G3 ~ C(school) + C(sex) + Medu + Fedu + studytime + failures + absences")
    gold = json.loads((REPO / "datasets/education-student-performance/expected/education_results.json")
                      .read_text(encoding="utf-8"))
    assert abs(fit["adj_r_squared"] - gold["t3_model_m1"]["adj_r_squared"]) < 1e-6
    coefs = {c["term"]: c for c in fit["coefficients"]}
    assert abs(coefs["studytime"]["coef"] - 0.510601) < 1e-5
    assert abs(coefs["failures"]["coef"] - (-1.667389)) < 1e-5
    assert fit["breusch_pagan"]["lm_pvalue"] < 1e-6   # 异方差真实存在（教学锚点）
    assert fit["vif_max"] < 2.5                        # 无共线性问题


def test_classification_deterministic():
    clean = load_heart_csv(CLEV)
    assert clean["ok"]
    a = clean["audit"]
    assert a["n_after_complete_case"] == 297
    assert a["missing_by_column"] == {"ca": 4, "thal": 2}
    r1 = run_pipeline(clean["data"], seed=42)
    r2 = run_pipeline(clean["data"], seed=42)
    assert r1["test"]["roc_auc"] == r2["test"]["roc_auc"]
    assert 0.85 < r1["test"]["roc_auc"] < 1.0
    assert abs(r1["test"]["brier"] - 0.093786) < 1e-5
    assert r1["test"]["youden"]["sensitivity"] >= 0.95
