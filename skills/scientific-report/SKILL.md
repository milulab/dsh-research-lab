---
name: scientific-report
description: 把已验证的统计结果组装成规范科研报告：表格/图/结果段/局限/复现说明；数字只引用不生成
---

# scientific-report｜科研报告技能

## 适用条件

model-validation 通过后。职责是把 results.json 翻译成人读的报告，**不产生任何
新数字**。

## 输入契约

- results.json（含审计、统计、验证记录）
- figures/ 与 tables/ 产物路径

## 工作步骤

1. 调用 `tools/report_builder.py --education|--health results.json --out report.md`
   生成骨架（数字全部从 JSON 引用）；
2. **结果段写作纪律**：每个统计量三件套——效应值+区间+p（回归）或
   指标+不确定度+样本量（分类）；语言用"关联/一致/不排除"，禁因果词；
3. **局限段必填**：观察性数据、样本边界、诊断异常、任务定义（泄漏对照）、
   数据年代与外部效度；
4. **复现说明必填**：一键命令、expected/ 位置、verify 命令、数据引用与许可；
5. 报告尾部声明"教学演示产物，不代表真实培训效果"（对外场合必须保留）。

## 输出

- report.md（可转 docx/PDF）
- 报告摘要段（≤200 字，供课堂投屏）

## 验证条件

- 报告中每个数字能在 results.json 中找到（抽查 5 个）；
- 无因果措辞；复现命令可执行。

## 失败处理

- 数字对不上 results.json → 以 JSON 为准改报告，绝反向改数；
- 图缺失 → 报告占位并注明生成命令，不使用无来源截图。
