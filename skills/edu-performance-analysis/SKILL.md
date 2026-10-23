---
name: edu-performance-analysis
description: 教育领域技能：以 UCI Student Performance（649×33）为基准数据执行学习行为-成绩关联研究（协议 T1–T5）
---

# edu-performance-analysis｜教育科研领域技能

## 适用条件

preset=edu-research；工作数据为 student-por.csv 或学员替换的教育数据集
（替换后先走 research-design 重新出协议）。

## 输入契约

- datasets/education-student-performance/（raw 只读 + 字典 + 协议 V1.0）
- 输出目录 examples/education-demo/outputs/（可换，建议带 outputs_ 前缀隔离）

## 标准执行流（协议 T1–T5，一键或分步）

1. **T1 审计**：`python tools/data_audit.py <csv> --sep ';'`
   预期：649×33、0 缺失、0 重复；raw 字节级检查确认 G1/G2 带引号；
2. **T2 关联**（一键：`python examples/education-demo/run_t1_t5.py`）：
   锚点值（expected/ 已锁定）——studytime ρ=+0.275（p≈1.1e-12）、
   failures ρ=−0.448、absences Pearson −0.091（弱）、Medu ρ=+0.284；
3. **T3 M1 回归**：协议公式
   `G3 ~ C(school)+C(sex)+Medu+Fedu+studytime+failures+absences`；
   锚点：调整 R²=0.263；studytime +0.511 [0.239, 0.783] p=2.5e-4；
   failures −1.667 p≈2.2e-17；absences −0.050 p=0.039；
   诊断：BP 显著（异方差）→ 报 HC3 敏感性；JB 拒绝正态；VIFmax=1.80（无共线）；
4. **T4 泄漏对照**：M2=M1+G1+G2 → 调整 R²=0.850，Δ=+0.587；
   讲解纪律：M2 回答"期末解释/含泄漏预测"，M1 才回答研究问题；
5. **T5 交付**：results.json / tables / figures / report.md / 运行日志五件套。

## 验证条件

- `python scripts/verify.py --suite education` 全绿（31 项中的教育段）；
- 教学铁律：分类变量不得未经编码入模；两课程数据不合并。

## 失败处理

- 学员换数据 → 禁止沿用本协议数值锚点，走 research-design 重出协议；
- 解析报错 → 按 data-intake 的字节检查法先看原始文件，报告错误行原文。
