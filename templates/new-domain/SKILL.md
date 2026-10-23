---
name: <your-domain-analysis>
description: <一句话：这个技能在什么数据上完成什么分析流程>
---

# <your-domain-analysis>｜<学科>领域技能

## 适用条件

- 什么 preset、什么数据、什么时候调用（写清楚"不适用"的情形同样重要）

## 输入契约

- 数据包路径与结构（对齐 datasets/ 数据包规范：raw 只读 + metadata + protocol + expected）
- 协议版本；输出目录约定

## 标准执行流（编号步骤，每步可独立验收）

1. **审计**：`python tools/data_audit.py <csv> …`，写明本数据集的
   预期规模/缺失结构锚点（来自你的 expected/，不是猜的）；
2. **主分析**：写明公式/特征集与理由（协议锁定，不许现场加变量）；
3. **验证**：写明本域的防泄漏要求与诊断清单（对照 model-validation）；
4. **交付**：results.json / tables / figures / report.md 四件套 + verify 命令。

## 验证条件

- 数字锚点全部来自 expected/；`python scripts/verify.py` 新增 suite 全绿；
- 措辞边界（boundaries）体现在每份交付物。

## 失败处理

- 换数据/换问题的哪些情形必须回到 research-design 重出协议，逐条列出。
