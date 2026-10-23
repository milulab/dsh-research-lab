---
name: health-risk-modeling
description: 公卫领域技能：以 UCI Heart Disease（Cleveland 303 例）为基准数据执行风险分类建模（协议 H1–H5，防泄漏）
---

# health-risk-modeling｜公卫风险建模领域技能

## 适用条件

preset=health-research；工作数据为 processed.cleveland.data 或学员替换的
健康二分类数据集（替换后先走 research-design 重出协议）。

## 输入契约

- datasets/health-heart-disease/（raw 只读 + 字典 + 协议 V1.0）
- 协议强制项：标签映射规则显式记录（num==0→0，1–4→1）；缺失按完整案例法

## 标准执行流（协议 H1–H5）

1. **H1 审计**：`python examples/health-demo/run_h1_h5.py` 或分步；
   锚点：303 例原始；ca 缺失 4、thal 缺失 2（"?" 编码）；完整案例 297；
   标签 160 阴性 / 137 阳性；
2. **H2/H3 建模**：Pipeline(StandardScaler + LogisticRegression)，
   训练 237 / 测试 60（分层 80/20，seed=42）；5 折分层 CV AUC=0.869±0.069；
3. **H4 评价**：留出集 AUC=0.950；0.5 阈值混淆矩阵（tn28/fp4/fn6/tp22，
   敏感度 0.786/特异度 0.875）；Youden 阈值 0.186（敏感度 1.00/特异度 0.781）；
   19 档阈值扫描表；Brier=0.094 + 校准曲线；
4. **H5 交付**：results.json / 系数表（标准化空间）/ 阈值表 / ROC+校准图 /
   report.md。

## 验证条件

- `python scripts/verify.py --suite health` 全绿；
- 防泄漏：预处理只在训练折内；CV 与留出集指标分开报告；
- 每个 AUC 同时报样本量与不确定度（测试集 n=60，禁止裸引点估计）。

## 失败处理

- 学员数据缺失结构不同 → 缺失策略先入协议再建模，禁止沿用"完整案例法"默认值；
- 类别特征语义不明（如 thal 编码含义）→ 按字典核对，未登记的编码先审计后使用。

## 临床边界（不可协商）

历史研究数据；不得用于真实临床诊断或个体健康决策；因子关联不得表述为因果。
