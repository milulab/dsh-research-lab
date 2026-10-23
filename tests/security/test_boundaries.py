"""安全边界测试：raw 只读不可破、数据审计不落盘、verify 能抓篡改"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.data_audit import audit_csv  # noqa: E402

RAW_FILES = [
    "datasets/education-student-performance/raw/student-por.csv",
    "datasets/education-student-performance/raw/student-mat.csv",
    "datasets/health-heart-disease/raw/processed.cleveland.data",
]


def _digests():
    return {
        f: hashlib.sha256((REPO / f).read_bytes()).hexdigest() for f in RAW_FILES
    }


def test_raw_immutable_during_pipelines():
    before = _digests()
    for script in ["examples/education-demo/run_t1_t5.py",
                   "examples/health-demo/run_h1_h5.py"]:
        p = subprocess.run([sys.executable, script], cwd=REPO,
                           capture_output=True, text=True, timeout=300)
        assert p.returncode == 0, p.stderr[-800:]
    assert _digests() == before, "管线运行改动了 raw/ —— 违反只读铁律"


def test_audit_does_not_write(tmp_path):
    target = REPO / RAW_FILES[0]
    before = target.read_bytes()
    audit_csv(target, sep=";")
    assert target.read_bytes() == before
    assert list(tmp_path.iterdir()) == []


def test_verify_catches_hash_tampering(tmp_path, monkeypatch):
    """把一个 raw 文件暂时替换为空内容 → verify 必须失败；测完恢复。"""
    victim = REPO / RAW_FILES[2]
    original = victim.read_bytes()
    try:
        victim.write_bytes(b"tampered\n")
        p = subprocess.run([sys.executable, "scripts/verify.py"], cwd=REPO,
                           capture_output=True, text=True, timeout=600)
        assert p.returncode == 1, "verify 未能抓住 raw 篡改"
        assert "sha256" in p.stdout
    finally:
        victim.write_bytes(original)
    # 恢复后全绿
    p2 = subprocess.run([sys.executable, "scripts/verify.py"], cwd=REPO,
                        capture_output=True, text=True, timeout=600)
    assert p2.returncode == 0
