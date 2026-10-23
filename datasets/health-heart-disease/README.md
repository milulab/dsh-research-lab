# health-heart-disease 数据包

UCI Heart Disease（id=45）教学数据包：processed Cleveland 子集，303 例 × 14 字段。
真实历史研究数据（CC BY 4.0），含真实缺失（ca 4 例、thal 2 例，编码 "?"）。

## 目录

```
raw/                 官方原始下载（只读；无表头 CSV + 官方 .names 说明）
processed/           版本化教学数据（build_processed.py 产物，可重建）
metadata/source.yml  来源/引用/许可证/SHA256
metadata/data_dictionary.csv   14 字段字典（类型/编码/缺失定义/角色）
protocol.md          预登记研究协议（H1–H5，含二元标签映射规则）
expected/            独立参考计算结果（golden 校验基准）
```

## 一键复现

```bash
python datasets/health-heart-disease/build_processed.py   # 重建 processed/
python examples/health-demo/run_h1_h5.py                  # 全管线 H1–H5
python scripts/verify.py --suite health                   # golden 校验
```

## 引用

Detrano, R., et al. (1989). International application of a new probability
algorithm for the diagnosis of coronary artery disease. American Journal of
Cardiology, 64, 304-310. 数据经 UCI Machine Learning Repository 分发，CC BY 4.0。

## 注意事项

1. 标签二元化规则必须显式记录：num==0 → 0；num∈{1,2,3,4} → 1。
2. "?" 是缺失编码，不是合法取值；ca 的 4 与 thal 的 7? 一律不当作水平。
3. 历史研究数据，输出不得用于真实临床诊断；预测因子关联不得表述为因果。
4. 预处理只在训练折内拟合（Pipeline），交叉验证结果与留出集结果分开报告。
