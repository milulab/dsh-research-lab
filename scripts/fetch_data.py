"""fetch_data.py — 从 UCI 官方源获取/校验/恢复原始数据

行为：
  --check     校验 raw/ 与 metadata/source.yml 的 SHA256（默认）
  --fetch     缺文件时从官方 URL 下载并校验（已有且哈希一致则跳过）
  --restore   用官方原件覆盖本地 raw/（本地被改动后的恢复手段）

许可说明：两个数据集均为 CC BY 4.0，仓库直接分发原件；本脚本同时是
"许可不允许分发"类数据集的接入模板（只下载、校验、不入库）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

SOURCES = {
    "education-student-performance": {
        "base": "https://archive.ics.uci.edu/static/public/320/student+performance.zip",
        "archive_members": {
            "student-por.csv": "student-por.csv",
            "student-mat.csv": "student-mat.csv",
            "student.txt": "student.txt",
        },
    },
    "health-heart-disease": {
        "base": "https://archive.ics.uci.edu/static/public/45/heart+disease.zip",
        "archive_members": {
            "processed.cleveland.data": "processed.cleveland.data",
            "heart-disease.names": "heart-disease.names",
        },
    },
}


def sha256_of(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def declared_hashes(dataset: str) -> dict[str, str]:
    import yaml

    meta = yaml.safe_load(
        (REPO / f"datasets/{dataset}/metadata/source.yml").read_text(encoding="utf-8")
    )
    return {Path(f["path"]).name: f["sha256"] for f in meta["files"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--restore", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report: list[dict] = []
    for dataset, src in SOURCES.items():
        raw = REPO / f"datasets/{dataset}/raw"
        want = declared_hashes(dataset)
        for fname, digest in want.items():
            f = raw / fname
            if f.is_file() and sha256_of(f) == digest and not args.restore:
                report.append({"dataset": dataset, "file": fname, "status": "ok"})
                continue
            if not args.fetch and not args.restore:
                report.append({"dataset": dataset, "file": fname, "status": "mismatch_or_missing"})
                continue
            import io
            import zipfile

            print(f"downloading {src['base']} …", file=sys.stderr)
            with urllib.request.urlopen(src["base"], timeout=60) as resp:
                blob = resp.read()
            with zipfile.ZipFile(io.BytesIO(blob)) as zf:
                inner = src["archive_members"][fname]
                data = zf.read(inner)
            got = hashlib.sha256(data).hexdigest()
            if got != digest:
                report.append({"dataset": dataset, "file": fname,
                               "status": "upstream_hash_mismatch", "got": got})
                continue
            f.write_bytes(data)
            report.append({"dataset": dataset, "file": fname,
                           "status": "restored" if args.restore else "fetched"})

    ok = all(r["status"] == "ok" for r in report)
    payload = {"ok": ok, "files": report}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
