# education-student-performance 数据包

UCI Student Performance（id=320）教学数据包：葡萄牙两所中学、葡萄牙语课程
649 名学生 × 33 个字段。**这是中学数据**（授课对象是高校教师，研究主题是教育
科研方法本身）；真实采集的公开研究数据（CC BY 4.0），非模拟数据。

## 目录

```
raw/                 官方原始下载（只读；分号分隔 CSV + 官方变量说明）
processed/           版本化教学数据（build_processed.py 产物，可重建）
metadata/source.yml  来源/引用/许可证/SHA256
metadata/data_dictionary.csv   33 字段字典（类型/编码/缺失定义/角色）
protocol.md          预登记研究协议（T1–T5）
expected/            独立参考计算结果（golden 校验基准）
```

## 一键复现

```bash
python datasets/education-student-performance/build_processed.py   # 重建 processed/
python examples/education-demo/run_t1_t5.py                        # 全管线 T1–T5
python scripts/verify.py --suite education                          # golden 校验
```

## 引用

Cortez, P. & Silva, A. (2008). Using Data Mining to Predict Secondary School
Student Performance. FUBUTEC 2008, pp. 5-12, EUROSIS. 数据经 UCI Machine
Learning Repository 分发，CC BY 4.0。

## 注意事项

1. raw/ 永远只读；T1 审计发现的问题在报告中留痕，不静默修改。
2. student-por.csv 的 G1/G2 是带引号字符串——这是刻意保留的真实数据特征，
   用于训练显式类型核查（data-intake Skill 的课堂示例）。
3. 不得与 student-mat.csv 合并当独立样本（382 名学生两课均有记录）。
4. 分类变量不得未经编码直接入模。
5. 教学演示用途；关联结论不得表述为因果效应。
