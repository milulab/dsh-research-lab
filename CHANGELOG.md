# Changelog

## v0.2.0 — 2026-10-23

双领域 + 全谱方法 + 数据复现版本。

- 方法谱系按"数据验证检查表"从第一性原理补齐：两独立组（Welch t/Mann-Whitney
  +Cohen's d）、Welch ANOVA/Kruskal-Wallis、卡方+Cramér's V（含期望频数检查）、
  Bonferroni/BH-FDR 多重校正、连续预测 MAE/RMSE/R²+K 折 CV、Logistic OR 表
  （GLM/IRLS 流行病学惯例）、F1、置换重要性、设计矩阵秩、Cook's 距离、
  模型设定敏感性分析、复现环境指纹、**不适用方法显式声明段**
  （生存/纵向/因果/调查加权等数据不支持的方法逐条说明拒绝理由）
- `scripts/verify.py` 扩至 **49 项对账全绿**；新增 `docs/method-checklist.md`
  逐项映射（检查表→实现→锚点值→不适用理由）

- 新增 HealthResearch 领域模板与 heart-disease 数据包（H1–H5 完整管线）：
  审计（缺失 ca=4/thal=2，完整案例 297）→ Logistic 基线 → 防泄漏划分与 5 折 CV
  （AUC 0.869±0.069）→ 留出集评价（AUC 0.950、Youden 阈值、Brier 0.094、校准曲线）
- 独立参考实现双路互证：教育侧 numpy-OLS vs statsmodels 逐位一致（|Δcoef|=0）；
  健康侧 GLM/IRLS + 秩和 AUC vs sklearn（跨求解器容差 0.005，同概率秩和差 0.0）
- `scripts/verify.py` 总验收 31 项全绿（SHA256 完整性 / 确定性复跑 / 交叉验证 / 协议断言）
- Presets：research-lab / edu-research / health-research（DSH 0.2.1-rc.2 基线）

## v0.1.0 — 2026-10-23

可运行单领域版本。

- EduResearch 教学管线 T1–T5 端到端（真实数据 649×33）：
  审计（649 行 0 缺失 0 重复；raw 字节级核查发现 G1/G2 引号数字——类型漂移教学点）
  → 单变量关联（studytime Spearman ρ=0.275）→ M1 多变量回归（调整 R²=0.263，
  studytime +0.51 / failures −1.67，异方差与残差非正态诊断在案）
  → M2 泄漏对照（含 G1/G2 后调整 R²=0.850，任务定义变化讲解）
  → 报告/图表/日志交付
- 通用 Skills 八件 + 教育领域 Skills；templates/new-domain 定制模板
