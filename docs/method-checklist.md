# 方法验证检查表｜实现映射与锚点（对照 DSH Research Lab 方法清单）

原则：**按实际分析需求、从第一性原理出发**——每个方法都对应两个基准数据集
真实存在的字段与研究问题；数据不支持的方法显式声明"不适用"，不硬塞。
全部锚点值来自真实执行（expected/ 锁定，`python scripts/verify.py` 49 项对账）。

数据集：EDU-01 = UCI Student Performance（student-por.csv，649×33）；
HEALTH-01 = UCI Heart Disease（processed.cleveland.data，303×14）。

## T1｜数据管理与探索性分析

| 检查项 | 数据集 | 实现与锚点 |
|---|---|---|
| 数据导入与变量识别 | 两者 | `tools/data_audit.py`（分隔符/表头/类型断言）+ 字典；EDU raw 字节级检查发现 G1/G2 引号数字（类型漂移教学点） |
| 数据质量检查 | 两者 | 缺失/重复/哨兵值审计：EDU 649 行 0 缺失 0 重复；HEALTH ca=4、thal=2（"?" 哨兵）；故障注入以 tests/security 的 raw 篡改-捕获测试实现（verify 必须抓住） |
| 描述性统计 | 两者 | audit 的 min/max/mean/SD/四分位/频数逐列输出 |
| EDA 与可视化 | 两者 | `save_residual_figure`（残差图）、`save_figures`（ROC+校准）、探索性分组统计入 T2/T2b 表 |
| Pearson / Spearman | EDU | absences 双报（Pearson −0.0914 / Spearman −0.1585）演示两种口径；有序变量只用 Spearman（ρ：studytime +0.2747） |

## T2｜统计检验与推断

| 检查项 | 数据集 | 实现与锚点 |
|---|---|---|
| 独立样本 t 检验 | 两者 | `stat_tests.two_group_continuous`（Welch）：EDU G3 by sex（p=0.0011）；HEALTH age by disease（阳性更高） |
| Mann–Whitney U | 两者 | 同函数并行输出：EDU sex p=0.0006 |
| ANOVA / Welch ANOVA | EDU | `welch_anova`：G3 across Medu（F=9.85，p<0.001）；多组不等方差用 Welch 而非经典 F |
| Kruskal–Wallis | 两者 | EDU studytime 4 组 + Medu 组（WA 函数内并行输出，教学对照） |
| 卡方独立性 | 两者 | `chi2_assoc`：EDU school×higher（V=0.1309）、schoolsup×sex；HEALTH 全部 7 个分类特征 vs disease |
| 效应量与 CI | 两者 | Cohen's d（EDU sex d=−0.2643；HEALTH age d=0.4662）、Cramér's V、回归系数 95%CI、OR 95%CI |
| 多重比较校正 | 两者 | `multiplicity`：Bonferroni + BH-FDR 双报。EDU 家族 8 项（FDR 后 8 显著）；HEALTH 基线家族 19 项（FDR 后 16 显著） |

## T3｜回归分析与模型诊断

| 检查项 | 数据集 | 实现与锚点 |
|---|---|---|
| 多元线性回归 OLS | EDU | M1：调整 R²=0.2629；系数+95%CI+p 全表；M2（含 G1/G2）仅作泄漏对照 |
| Logistic 回归 | HEALTH | Pipeline（预测）+ OR 表（`or_table_glm`，GLM/IRLS 流行病学惯例）：ca OR=3.55 [2.11, 5.98] |
| 回归显著性检验 | 两者 | 系数/SE/t/p/CI 全量入 results.json |
| 多重共线性诊断 | 两者 | VIF（截距除外，EDU VIFmax=1.80）+ `design_matrix_diagnostics` 设计矩阵秩断言（满秩） |
| OLS 残差诊断 | EDU | BP（LM p≈2e-33）+ JB（p≈1.9e-70）+ 残差-拟合图 + `cooks_distance_summary`（>4/n 计数与 top5） |
| 稳健标准误 | EDU | HC3 全表（`hc3_se`）随 M1 输出 |
| 模型设定敏感性 | 两者 | EDU：M1 vs M2（任务定义）+ HC3（协方差设定）；HEALTH：剔除 fbs/restecg 的精简设定（ΔAUC=+0.0045，符号零翻转） |

## T4｜机器学习与模型评价

| 检查项 | 数据集 | 实现与锚点 |
|---|---|---|
| 训练/测试划分 | 两者 | 固定 seed=42 分层 80/20；标准化只在训练折内（Pipeline）——防泄漏 |
| 交叉验证 | 两者 | EDU：5 折 K 折（回归，R² 均值 0.2377）；HEALTH：5 折分层（AUC 0.8694±0.0685） |
| 连续变量预测 | EDU | `regression_cv_metrics`：holdout MAE/RMSE=2.8262/R² 与 CV 两种口径分开报告 |
| 二分类预测 | HEALTH | Logistic 基线（13 特征） |
| 混淆矩阵 | HEALTH | 0.5 与 Youden 两阈值全矩阵 |
| ROC 与 ROC-AUC | HEALTH | AUC=0.9498；同概率秩和法差 0.0，跨求解器容差 0.005 |
| 灵敏度/特异度/F1 | HEALTH | 0.5 阈值：0.7857/0.8750/F1=0.8148；Youden：1.0/0.7812/F1=0.8889 |
| 阈值敏感性 | HEALTH | 19 档扫描表 + Youden 点；报告显式"无语境不谈最优阈值" |
| 概率校准与 Brier | HEALTH | Brier=0.0938 + 校准曲线数据 |
| 特征重要性与解释 | 两者 | EDU：系数 + 置换重要性（r²）；HEALTH：系数 + 置换重要性（AUC 降幅，top=ca 0.0748）+ OR 表 |

## T5｜科研复现与质量验证

| 检查项 | 数据集 | 实现与锚点 |
|---|---|---|
| 研究设计与变量字典 | 两者 | protocol.md（V1.0 锁定）+ data_dictionary.csv + 变量角色列 |
| 样本筛选与缺失日志 | 两者 | 样本链：EDU 649→649；HEALTH 303→(−4−2)→297；全部动作入 quality/audit 段 |
| 结果与参考程序复算 | 两者 | 双实现互证：statsmodels vs numpy-OLS（|Δcoef|=0）；sklearn vs GLM+秩和（ΔAUC=0.0011<0.005） |
| 分析代码与环境复现 | 两者 | `env_fingerprint`（解释器/库版本/平台/seed）入 results.json；requirements + verify.py + CI 三平台矩阵 |
| 图表与 Results 一致 | 两者 | report_builder 只从 results.json 引用数字（抽查条款见 scientific-report Skill） |
| 不适用方法识别 | 两者 | results.json `not_applicable` 段：生存分析（无时间-事件字段）、纵向/混合模型（无重复测量）、因果估计（观察性无识别策略）、调查加权（非复杂抽样）、（HEALTH）填补主分析（协议为完整案例法）——**数据不支持的方法不硬塞，显式说明原因** |

## 与检查表的刻意差异（第一性原理说明）

1. **EDU 不做 Logistic 主分析**：G3（0–20）是近似连续的有界分数，OLS 是协议主
   模型；序数化+Logistic 只作为课后扩展，不冒充主分析。
2. **HEALTH 的 ANOVA 不适用**：结局是二分类，组间比较的正确形态是"按结局分组
   比较特征"（基线表），而不是按某特征分组比较结局；前者已全覆盖。
3. **"故障注入数据"以测试形式实现**：数据完整性由 `tests/security` 的
   raw-篡改-必须-被抓用例保证，不污染真实教学数据。
4. **两独立组/多组检验的对象选择**：全部来自数据字典里真实记录的分组变量
   （sex/Medu/school/higher/schoolsup/disease），不为凑方法而人为分组。
