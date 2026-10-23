# EduResearch 研究协议｜学习行为与学业成绩的关联分析

数据集：UCI Student Performance（葡萄牙语课程 student-por.csv，649 名学生）
版本：V1.0｜2026-10-23｜与 `expected/` 参考结果配套锁定

## 研究问题

RQ1 学习时间（studytime）、缺勤（absences）、既往不及格次数（failures）、父母教育水平
（Medu/Fedu）与最终成绩 G3 是否存在可检出的关联？
RQ2 纳入 G1/G2 期中成绩后，模型解释力变化多少？这如何改变研究问题的性质（早期预测 vs
期末解释）？

## 观察单位与样本

- 观察单位：学生×课程（葡萄牙语课程），n=649。
- 纳入：raw/student-por.csv 全部记录；仅允许按协议声明的规则处理解析与类型问题。
- 排除：无（T1 审计后如发现记录级问题，须在 quality_report 中留痕并说明，不静默删除）。
- 禁止事项：不得与 student-mat.csv（数学课）合并后当作独立样本——上游声明 382 名学生
  两门课都有记录，合并会违反独立性假设。

## 预处理规则（先于分析锁定）

P1 解析：分号分隔，UTF-8，首行为表头。
P2 类型：raw 文件中 G1/G2 的取值带引号（如 "0"）；解析层不得信任静默推断，
  必须显式校验目标列为整数并做类型断言，防引号数字被无声吸收。
P3 类别变量：school/sex/address/famsize/Pstatus/Mjob/Fjob/reason/guardian 及全部
  yes/no 列一律按类别处理，禁止直接当数值；有序变量（studytime/traveltime/failures/
  Medu/Fedu/1-5 量表）按有序处理并在方法说明中声明。
P4 缺失：T1 审计声明实际缺失水平；本协议下不允许对缺失记录静默填补或删除。
P5 结果只读：raw/ 下的文件任何脚本不得修改；所有派生数据写入 processed/。

## 主要分析计划

T1 数据导入与字段语义核查：行/列数、类型逐列断言、缺失审计、重复行审计、类别取值域
  核对（对照 data_dictionary.csv），输出 quality_report。
T2 单变量关联（不涉及因果识别，全部按"关联"表述）：
  - studytime × G3：Spearman 秩相关 + Kruskal-Wallis 四组比较；
  - absences × G3：Pearson + Spearman；
  - failures × G3：Spearman；
  - Medu、Fedu × G3：Spearman。
T3 多变量线性回归（模型 M1，不含 G1/G2）：
  G3 ~ C(school) + C(sex) + Medu + Fedu + studytime + failures + absences
  报告：系数、95% CI、p 值、R²、调整 R²、F 检验、VIF、Breusch-Pagan 异方差检验、
  Jarque-Bera 残差正态检验。分类变量以 GP/参考组编码。
T4 目标信息时点对照（M1 vs M2）：
  M2 = M1 + G1 + G2。比较调整 R² 变化；M2 系数不用于解释"学习时间效应"。
  明确教学结论框架：M2 是"期末解释/含泄漏预测"，M1 才回答 RQ1。
T5 复现交付：统计表 CSV、图表 PNG、results JSON、执行日志、报告 Markdown，
  全部写入 examples/education-demo/outputs/ 并与 datasets/.../expected/ 对齐。

## 假设与检验水位

H1：学习时间与 G3 正相关（秩相关 > 0）；H2：缺勤与 G3 负相关；H3：failures 与 G3
负相关。检验水位 α=0.05，双侧；多重比较仅作描述性提示，不作为主结论门槛。

## 局限声明（必须随结果输出）

观察性数据：所有关联不构成因果效应估计；结果限于 2008 年葡萄牙两所中学的葡萄牙语
课程情境；G1/G2 纳入改变的是任务定义而不是模型质量；教学演示用途。
