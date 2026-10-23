# 教学指令卡（p1–p9）｜DSH 对话逐条粘贴版

配套教程页：https://milulab.com/course/ai-data-analyse/dsh.html
用法：在 `dsh web` 对话框逐条粘贴；每条之后都有"预期产出"，对不上就停下来排查。
仓库根约定：`$REPO`（下同）= 你 clone 的 dsh-research-lab 目录绝对路径。

## 教育案例（UCI Student Performance，649 名中学生）

### p1 · T1 数据审计
```
用 $REPO/.venv/bin/python 运行 $REPO/tools/data_audit.py 审计
$REPO/datasets/education-student-performance/raw/student-por.csv（--sep ';'），
然后亲自 head 原始文件第 2 行，检查 G1/G2 两列的取值有什么形态学特征。
回答：行列规模、缺失与重复计数、以及这个"引号数字"说明了什么。
```
预期：649×33、0 缺失 0 重复；G1/G2 取值带引号→静默类型漂移教学点。

### p2 · T2 关联与可视化
```
运行 $REPO/scripts/make_teaching_figures.py 生成教学图，然后解读两张：
① figures/edu_g3_distribution.png：G3 分布形状？对 OLS 建模意味着什么？
② figures/edu_studytime_box.png：四档学习时间的箱线怎么读？
   Spearman ρ=+0.275 如何向家长做"关联"表述（禁因果词）？
```
预期：0 分堆积（有界离散）；档位均值单调上升但组内重叠大。

### p3 · T3 回归与诊断
```
按协议公式 G3 ~ C(school)+C(sex)+Medu+Fedu+studytime+failures+absences
跑 $REPO/examples/education-demo/run_t1_t5.py，解读 edu_m1_forest.png：
① studytime 与 failures 的系数、95%CI、p 值；
② BP 与 JB 都显著时为什么必须同时报 HC3 稳健标准误？
③ 对照 results.json 的 hc3_se 字段验证结论方向是否改变。
```
预期：studytime +0.511 [0.239, 0.783] p=2.5e-4；failures −1.667 p≈2e-17；HC3 下显著性不变。

### p4 · T4 泄漏对照（灵魂环节）
```
看 edu_leakage_bar.png 和 edu_corr_heatmap.png，回答：
M2 比 M1 调整 R² 高 0.587 能写成"模型改进"吗？
结合 G1/G2 与 G3 的相关，用三句话向审稿人解释为什么是泄漏、
M2 在什么问题定义下才合法。
```
预期：M1 0.263 / M2 0.850 / Δ+0.587=信息时点非法进入；M2 只合法于"期末解释"。

### p5 · T5 独立复核（复核义务）
```
对你刚才报告里最重要的一个数字（建议 studytime 系数）：
写一段不依赖 statsmodels 的独立复核代码并运行（numpy 最小二乘即可），
与 results.json 对账。一致给出 |Δ|；不一致停下说明，不许择优采信。
```
预期：|Δ系数| = 0（与 expected/reference_results.json 同源锁定）。

## 公卫案例（UCI Heart Disease，303 例真实历史病例）

### p6 · H1 审计
```
审计 $REPO/datasets/health-heart-disease/raw/processed.cleveland.data（无表头，"?" 是缺失编码）。
回答：①ca 与 thal 各缺几例？完整案例剩多少？②标签 num 0–4 如何二元化？
160/137 怎么一步步来的？③为什么"?" 不能当作 thal 的合法水平？
```
预期：ca=4、thal=2 → 297；num==0→0，1–4→1；160 阴/137 阳（剔除 4 阴 2 阳）。

### p7 · H2 基线筛查 + OR 表
```
运行管线后解读 health_or_forest.png：
①哪些特征显著为风险因子（OR>1 且 CI 不跨 1）？ca 的 OR=3.55 怎么理解？
②19 项检验家族 Bonferroni 与 BH-FDR 后各剩几项？筛查场景为何常用 FDR？
```
预期：ca OR=3.55 [2.11, 5.98]、exang 2.24、thalach 0.98；Bonferroni 13 / FDR 16。

### p8 · H3–H4 防泄漏与评价
```
解读 health_threshold_sweep.png 与 health_confusion.png：
①0.5 阈值漏诊 6 例（敏感度 0.786），筛查语境为何不可接受？
②Youden 阈值 0.186 敏感度 1.00，代价是什么？"最优阈值"这种说法对吗？
③CV AUC 0.869 与留出集 0.950 为什么必须分开报告？标准化为什么必须在 Pipeline 里？
```
预期：阈值=决策非统计；代价是 FP 4→7；防预处理泄漏是正确性要求而非风格。

### p9 · H5 三重互证与边界
```
results.json 里有三重互证：sklearn vs 秩和法 AUC（同概率差应=0）、
statsmodels GLM 参考口径（跨求解器容差 0.005）、Brier+校准曲线。
逐一核对字段并解释：判别与校准分别回答什么问题？
为什么历史研究数据不能用于真实诊断？
```
预期：roc_auc=0.9498、auc_crosscheck.abs_diff=0.0、brier=0.0938；判别=排序能力，校准=概率可信度。

## 迁移讨论题（收尾）

```
把教育案例的方法迁移到公卫数据：哪些环节可以直接复用（tools/通用技能/验收设施），
哪些必须重做（协议/字典/锚点/领域技能）？为什么生存分析和因果推断在两个数据上都"不适用"？
```
预期：tools 与 8 件通用技能复用；领域四件套重做；不适用理由见 results.json 的 not_applicable 段。
