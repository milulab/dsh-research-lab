# HealthResearch 研究协议｜心脏病风险分类模型的验证式教学

数据集：UCI Heart Disease（processed Cleveland，303 例）
版本：V1.0｜2026-10-23｜与 `expected/` 参考结果配套锁定

## 研究问题

RQ1 基于 13 项常规临床检查特征（age、sex、cp、trestbps、chol、fbs、restecg、
thalach、exang、oldpeak、slope、ca、thal），能否构建可复核的心脏病阳性预测模型？
RQ2 该模型在留出集上的 ROC-AUC、敏感度、特异度如何？阈值移动如何权衡两者？

## 观察单位与样本

- 观察单位：就诊病例记录，n=303（Cleveland 子集）。
- 标签定义（显式锁定）：原 `num` 字段 0-4；二元化规则 num==0 → 0（阴性），
  num∈{1,2,3,4} → 1（阳性）。映射规则必须随每次结果输出记录，禁止隐式转换。
- 缺失处理：`ca` 缺失 4 例、`thal` 缺失 2 例（原始编码 "?"）。主分析采用"完整案例"
  策略：仅剔除含缺失记录，预期 n=297；剔除数必须写入质量报告，不得静默。
- 禁止事项：本数据为 1989 年前后历史研究数据，任何输出不得用于真实临床诊断；
  预测变量与标签的关联不得表述为因果效应。

## 预处理规则（先于分析锁定）

P1 解析：逗号分隔、无表头（列名按 heart-disease.names 顺序注入）、"?" 按缺失读入。
P2 类型：数值列转 float；cp/restecg/slope/thal/fbs/exang/sex 在建模时按类别/二值处理。
P3 划分：训练/测试 80/20 分层抽样，random_state=42；预处理（标准化、编码）只在
  训练折内拟合（sklearn Pipeline），杜绝数据泄漏。
P4 交叉验证：5 折分层 CV 报告训练侧 AUC 均值±标准差。
P5 结果只读：raw/ 只读，派生数据写 processed/。

## 主要分析计划

H1 字段、缺失与标签审计：14 列类型断言、缺失计数（ca=4、thal=2 为协议预期值）、
  标签分布（0/1 计数与占比）、映射规则记录。
H2 Logistic 回归基线：Pipeline(StandardScaler + LogisticRegression(max_iter=1000))，
  全 13 特征；输出标准化前系数与测试集预测概率。
H3 划分与 CV：80/20 分层留出（seed=42）+ 5 折分层 CV（同一 Pipeline），AUC 两侧报告。
H4 评价：测试集 ROC-AUC、0.5 阈值混淆矩阵、敏感度/特异度；Youden 最优阈值及对应
  敏感度/特异度；阈值扫描表（0.05-0.95 步长 0.05）；Brier 分数与校准曲线数据。
H5 复现交付：统计表 CSV、ROC/校准图 PNG、results JSON、执行日志、报告 Markdown，
  全部写入 examples/health-demo/outputs/ 并与 datasets/.../expected/ 对齐。

## 局限声明（必须随结果输出）

历史数据且样本量小（测试集约 60 例），指标有抽样波动；AUC 区间估计仅作提示；
"风险关联"不等于因果；模型不校准到现代临床环境，不可用于真实诊断决策；教学演示用途。
