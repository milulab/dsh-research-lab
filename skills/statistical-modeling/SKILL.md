---
name: statistical-modeling
description: 按研究设计选择并执行统计方法：相关/t检验/ANOVA/OLS回归/Logistic回归；模型只能经由 tools/ 真实执行
---

# statistical-modeling｜统计建模技能

## 适用条件

数据通过质量审计、研究协议已锁定。**方法选择由协议决定**，本技能不"替学员挑
更好看的模型"。

## 输入契约

- 质量审计通过的数据 + protocol.md 的分析计划段
- 明确的角色变量（outcome/exposure/covariate）

## 方法映射（本项目两条管线的标准选择）

| 场景 | 方法 | 执行入口 |
|---|---|---|
| 有序暴露 × 连续结局 | Spearman + Kruskal-Wallis | tools/regression.py 辅助 / 管线 T2 |
| 连续暴露 × 连续结局 | Pearson（同时报 Spearman 稳健性） | 同上 |
| 多协变量连续结局 | OLS（分类变量 C() 编码；报 HC3 稳健 SE 敏感性） | `python tools/regression.py <csv> --formula …` |
| 二元结局 | Logistic（Pipeline 标准化+拟合，只在训练折内） | `python tools/classification.py …` |

## 工作步骤

1. 对照协议确认公式/特征集，**逐字使用协议锁定的公式**，不得现场增删变量；
2. 调用 tools/ 真实执行，取回结构化 JSON（系数、CI、p、R²、VIF、BP、JB /
   AUC、混淆矩阵、Brier）；
3. 诊断三查：异方差（BP）、正态性（JB）、共线性（VIF>10 才算问题）——异常
   不是失败，是报告素材（如本仓库 M1 的 BP 显著→HC3 敏感性检查）；
4. 交叉验证口径分离：CV 指标与留出集指标分开陈述，禁止混报一个"AUC"。

## 输出

- 结构化结果 JSON（全量保存进 results.json 对应段落）
- 表格 CSV（系数表/混淆矩阵/阈值扫描）与图 PNG

## 验证条件

- 数字全部来自工具输出；复算（重跑命令）结果逐位一致（确定性）或按 seed 复现；
- 头条指标已过 scripts/verify.py 的双实现交叉验证。

## 失败处理

- 公式在数据上不可估（共线/零方差列）→ 报告具体列与原因，回到协议修订，
  不静默丢变量；
- 收敛失败（GLM 不收敛）→ 报告迭代记录，建议标准化或正则化并作为协议修订项。
