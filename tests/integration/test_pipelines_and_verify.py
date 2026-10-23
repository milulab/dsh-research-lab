"""集成测试：端到端管线 × expected/ 黄金对账 × verify 总验收桥"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _run(script: str) -> str:
    p = subprocess.run([sys.executable, script], cwd=REPO,
                       capture_output=True, text=True, timeout=300)
    assert p.returncode == 0, f"{script} failed:\n{p.stderr[-1500:]}"
    return p.stdout.strip().splitlines()[-1]


def test_education_pipeline_against_golden():
    live = json.loads(_run("examples/education-demo/run_t1_t5.py"))
    gold = json.loads((REPO / "datasets/education-student-performance/expected/education_results.json")
                      .read_text(encoding="utf-8"))
    assert abs(live["t3_m1_adj_r2"] - gold["t3_model_m1"]["adj_r_squared"]) < 1e-6
    assert abs(live["t4_m2_adj_r2"] - gold["t4_model_m2"]["adj_r_squared"]) < 1e-6
    assert abs(live["delta"] - gold["t4_adj_r2_delta"]) < 1e-6
    assert live["t1"]["n"] == 649 and live["t1"]["dups"] == 0


def test_health_pipeline_against_golden():
    live = json.loads(_run("examples/health-demo/run_h1_h5.py"))
    gold = json.loads((REPO / "datasets/health-heart-disease/expected/health_results.json")
                      .read_text(encoding="utf-8"))
    assert abs(live["cv_auc"] - gold["cv"]["mean_auc"]) < 1e-6
    assert abs(live["test_auc"] - gold["test"]["roc_auc"]) < 1e-6
    assert live["auc_crosscheck_diff"] < 1e-9


def test_verify_suite_all_green():
    p = subprocess.run([sys.executable, "scripts/verify.py"], cwd=REPO,
                       capture_output=True, text=True, timeout=600)
    assert p.returncode == 0, p.stdout[-2000:]
    assert "ALL GREEN" in p.stdout
