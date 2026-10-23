# DSH Research Lab

**开源高校科研智能体框架**：基于 [DeepSeek Harness (DSH)](https://github.com/deepseek-ai/deepseek-harness)
的通用科研工作台模板。教师与研究生下载即可运行完整科研分析管线，并在领域模板上
定制自己的科研 Agent——而不是从零开发复杂应用。

[![verify](https://github.com/milulab/dsh-research-lab/actions/workflows/verify.yml/badge.svg)](./.github/workflows/verify.yml)
License: MIT ｜ 当前版本 v0.2.0（双领域 + 全谱方法 + 数据复现）

## 这是什么

一个"脚本生成一切、统计全部真实"的科研智能体框架：

- **两套完整领域模板**：EduResearch（教育科研，UCI Student Performance，649 名
  中学生真实数据）与 HealthResearch（公共卫生，UCI Heart Disease，303 例真实历史
  病例数据）——全部为真实公开数据，非模拟数据；
- **8 个通用科研技能** + 4 个领域技能（含统计检验/效应量/多重校正/预测评价全谱）（research-design / data-intake / data-quality /
  exploratory-analysis / statistical-modeling / model-validation / scientific-report /
  evidence-traceability + edu-* / health-*）；
- **三个层级 Preset**：通用科研台 research-lab / 教育科研台 edu-research /
  公卫科研台 health-research；
- **端到端可复核管线**：每套数据从审计到报告全流程脚本化，`python scripts/verify.py`
  49 项验收全绿——统计值来自真实执行，statsmodels 与独立手写实现逐位互证；
- **定制路径**：`templates/new-domain/` 七步复制出自己的学科 Agent。

## 60 秒上手

```bash
# 0) 环境：Python 3.11+，DSH 0.2.1-rc.2（npm i -g @deepseek-ai/dsh）
pip install -r requirements.txt

# 1) 跑通教育科研管线（真实数据，约 10 秒）
python examples/education-demo/run_t1_t5.py
# → examples/education-demo/outputs/{results.json, report.md, tables/, figures/}

# 2) 跑通公卫分类管线
python examples/health-demo/run_h1_h5.py

# 3) 总验收（数据完整性 + 确定性复跑 + 独立实现交叉验证）
python scripts/verify.py            # 31/31 checks passed — ALL GREEN

# 4) 让 DSH 驱动这套工作台（详见 docs/quickstart.md）
dsh web      # 工作区指向本仓库根目录，选择 edu-research preset
```

## 学习路径（建议 60–90 分钟）

1. **安装启动**（10 min）：装环境、跑通管线，看到真实输出文件；
2. **观察一次完整研究**（15–20 min）：数据审计→关联分析→回归→泄漏对照→报告，
   全部产物可在 `outputs/` 里逐个打开核对；
3. **拆解框架**（15 min）：Preset / Skill / Tool / Knowledge / 运行轨迹各自承担什么，
   与"提示词管理"的本质区别；
4. **定制自己的 Agent**（15–25 min）：`templates/new-domain` 复制 → 改 domain.yml →
   换研究问题 → 换一个领域 Skill → 用自己的数据跑通；
5. **迁移验证**（10–15 min）：把教育 Agent 的方法迁到公卫数据，检验是否真实复用。

## 仓库结构

```text
dsh-research-lab/
├── presets/          research-lab（通用）/ edu-research / health-research
├── skills/           8 通用 + 4 领域 SKILL.md（含适用条件与输入输出契约）
├── tools/            Python 计算层：data_audit / regression / classification
│                     / stat_tests / report_builder
├── domains/          education / public-health（domain.yml + knowledge + protocols）
├── datasets/         education-student-performance / health-heart-disease
│   │                 （raw 只读 + processed + metadata + protocol + expected）
├── templates/        new-domain：七步定制自己的学科 Agent
├── examples/         education-demo（T1–T5）/ health-demo（H1–H5）端到端管线
├── scripts/          verify.py 总验收 / reference_* 独立参考实现 / install.sh
├── tests/            unit / integration / golden / security
└── docs/             quickstart / customize-agent / data-governance / teaching-guide
```

## 教学铁律（框架内置，不可绕过）

1. **原始数据只读**：`datasets/*/raw/` 永不改写，SHA256 锁定于 `metadata/source.yml`；
2. **统计值只能来自真实执行**：模型不得生成任何 p 值/AUC——全部数字出自
   `tools/` 计算层，Agent 只负责调度与解读；
3. **双实现互证**：每个头条指标都有第二条独立实现路径（手写 OLS / 秩和法 AUC），
   `verify.py` 强制对账（49 项：SHA256 → 确定性复跑 → 交叉验证 → 协议断言）；
4. **因果表述禁令**：观察性数据的全部结论按"关联"表述；健康数据不得用于真实临床；
5. **缺列即拒绝**：数据不满足契约时 Agent 必须提出修正要求，禁止编造。

## 数据来源与许可

| 数据集 | UCI ID | 规模 | 许可 |
|---|---|---|---|
| [Student Performance](https://archive.ics.uci.edu/dataset/320/student+performance) | 320 | 649×33（葡语课） | CC BY 4.0 |
| [Heart Disease](https://archive.ics.uci.edu/dataset/45/heart+disease) | 45 | 303×14（Cleveland） | CC BY 4.0 |

引用要求见 `datasets/*/metadata/source.yml`；`THIRD_PARTY_NOTICES.md` 汇总全部第三方声明。
`datasets/*/raw/` 直接分发原始文件（CC BY 4.0 允许），`scripts/fetch_data.py` 可校验或重新获取。

## 文档

- [docs/quickstart.md](docs/quickstart.md) — 安装、运行、接入 DSH
- [docs/customize-agent.md](docs/customize-agent.md) — 七步定制自己的学科 Agent
- [docs/teaching-guide.md](docs/teaching-guide.md) — 授课手册（时序、指令、验收）
- [docs/method-checklist.md](docs/method-checklist.md) — 方法验证检查表（逐项映射与锚点）
- [docs/data-governance.md](docs/data-governance.md) — 数据治理与许可
- [docs/architecture.md](docs/architecture.md) — 分层架构与设计决策

## 版本

见 [CHANGELOG.md](CHANGELOG.md)。当前 v0.2.0；DSH 兼容基线 0.2.1-rc.2（升级前请跑
`python scripts/verify.py` 与 DSH 冒烟清单）。

## License

MIT。第三方数据与文档的许可与引用见 `THIRD_PARTY_NOTICES.md`。
