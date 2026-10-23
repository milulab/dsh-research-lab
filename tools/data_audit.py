"""data_audit.py — 数据审计工具（EduResearch T1 / HealthResearch H1 共用）

对一份 CSV 做只读审计：行列规模、逐列类型（含"字符串形态的数值列"检出）、
缺失审计、完全重复行审计、类别/有序变量的取值域核对、数值列基本分布与异常扫描。

设计约束（与 skills/data-intake、skills/data-quality 的契约一致）：
- stdout 只输出 JSON（stdout-only-JSON 约定，供 DSH 工具层解析）；
- 任何错误也以结构化 JSON 输出（error 键），绝不打印半截文本；
- 只读：本工具不写任何文件，除非显式 --out 指定审计报告路径。

用法：
  python tools/data_audit.py <csv> [--sep ';'] [--no-header]
       [--expect-rows N] [--names c1,c2,...] [--out report.json]
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


def _string_shaped_numeric(series: pd.Series) -> bool:
    """列以字符串存储但绝大多数取值可解析为数字（如 student-por 的 G1/G2）。"""
    if pd.api.types.is_numeric_dtype(series):
        return False
    s = series.dropna().astype(str).str.strip().str.strip('"').str.strip("'")
    if s.empty:
        return False
    numeric_like = pd.to_numeric(s, errors="coerce")
    return numeric_like.notna().mean() >= 0.95


def audit_dataframe(df: pd.DataFrame) -> dict:
    """对已加载的 DataFrame 执行完整审计，返回结构化结果。"""
    n_rows, n_cols = df.shape
    columns = []
    for col in df.columns:
        s = df[col]
        missing = int(s.isna().sum())
        entry: dict = {
            "name": str(col),
            "dtype": str(s.dtype),
            "missing": missing,
            "missing_pct": round(missing / n_rows * 100, 4) if n_rows else 0.0,
            "n_unique": int(s.nunique(dropna=True)),
        }
        if not pd.api.types.is_numeric_dtype(s):
            raw_values = s.dropna().astype(str).str.strip()
            entry["top_values"] = raw_values.value_counts().head(12).to_dict()
            entry["string_shaped_numeric"] = _string_shaped_numeric(s)
            entry["sentinel_values"] = sorted(
                {v for v in raw_values.unique() if v.strip() in {"?", "", "NA", "N/A", "null", "None"}}
            )
        else:
            num = pd.to_numeric(s, errors="coerce")
            q1, q3 = (num.quantile(0.25), num.quantile(0.75)) if num.notna().any() else (np.nan, np.nan)
            iqr = q3 - q1
            entry.update(
                {
                    "min": None if num.isna().all() else float(num.min()),
                    "max": None if num.isna().all() else float(num.max()),
                    "mean": None if num.isna().all() else round(float(num.mean()), 6),
                    "std": None if num.isna().all() else round(float(num.std(ddof=1)), 6),
                    "quartiles": None
                    if num.isna().all()
                    else [round(float(q), 6) for q in num.quantile([0.25, 0.5, 0.75])],
                    "outliers_iqr": int(
                        ((num < q1 - 1.5 * iqr) | (num > q3 + 1.5 * iqr)).sum()
                    )
                    if num.notna().any() and float(iqr) > 0
                    else 0,
                }
            )
        columns.append(entry)

    dup_mask = df.duplicated(keep=False)
    exact_dups = int(df.duplicated().sum())

    return {
        "ok": True,
        "n_rows": int(n_rows),
        "n_cols": int(n_cols),
        "columns": columns,
        "exact_duplicate_rows": exact_dups,
        "exact_duplicate_rows_involved": int(dup_mask.sum()),
        "total_missing_cells": int(df.isna().sum().sum()),
        "rows_with_any_missing": int(df.isna().any(axis=1).sum()),
    }


def audit_csv(path: str | Path, sep: str = ",", no_header: bool = False,
              names: list[str] | None = None) -> dict:
    p = Path(path)
    if not p.is_file():
        return _fail("load", f"file not found: {p}")
    try:
        if no_header or names:
            df = pd.read_csv(p, sep=sep, header=None, names=names, skipinitialspace=True)
        else:
            df = pd.read_csv(p, sep=sep, skipinitialspace=True)
    except Exception as exc:  # noqa: BLE001 — 工具边界：异常转结构化 JSON
        return _fail("parse", f"{type(exc).__name__}: {exc}")
    result = audit_dataframe(df)
    result["source"] = str(p)
    result["sha256"] = __import__("hashlib").sha256(p.read_bytes()).hexdigest()
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Read-only CSV data audit (JSON out)")
    parser.add_argument("csv", help="CSV 文件路径")
    parser.add_argument("--sep", default=",", help="字段分隔符（student 数据用 ';'）")
    parser.add_argument("--no-header", action="store_true", help="无表头文件（如 cleveland）")
    parser.add_argument("--names", default="", help="无表头时的列名，逗号分隔")
    parser.add_argument("--out", default="", help="审计 JSON 另存路径（stdout 始终输出 JSON）")
    args = parser.parse_args(argv)

    names = [c.strip() for c in args.names.split(",")] if args.names else None
    result = audit_csv(args.csv, sep=args.sep, no_header=args.no_header, names=names)
    payload = json.dumps(result, ensure_ascii=False, indent=2, default=str)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    sys.stdout.write(payload + "\n")


if __name__ == "__main__":
    main()
