# DSH Research Lab — 高校科研智能体框架

面向高校教师与研究生的**开源科研智能体框架**：下载即用，跑通完整的
科研分析管线（数据审计 → 统计建模 → 报告生成 → 交叉验证），并在学科
模板上定制自己的科研 Agent——而不是从零开发复杂应用。

**四大原则：证据可追溯 · 计算可复现 · 统计全真实 · 数据可治理。**

| 平台 | 下载 | 说明 |
|---|---|---|
| **macOS 桌面端（推荐）** | [dsh-research-lab-\*-darwin-arm64.dmg](https://github.com/milulab/dsh-research-lab/releases/latest) | 内置真实 DSH + Node 22 + 全部科研栈，开箱即用 |
| 源码包（三平台） | [dsh-research-lab-\*.tar.gz / .zip](https://github.com/milulab/dsh-research-lab/releases/latest) | 框架模板包（需自配 Python 3.11+），开发者接入 |
| 教学资源包 | [teaching-pack（v0.2.0 附件，内容在 v0.3.0 无变化）](https://github.com/milulab/dsh-research-lab/releases/tag/v0.2.0) | 12 技能 + 双数据包 + 9 张教学图 + 指令卡 |

[![verify](https://github.com/milulab/dsh-research-lab/actions/workflows/verify.yml/badge.svg)](./.github/workflows/verify.yml)
[![desktop-build](https://github.com/milulab/dsh-research-lab/actions/workflows/desktop-build.yml/badge.svg)](./.github/workflows/desktop-build.yml)
License: MIT ｜ 当前稳定版 **v0.3.1** ｜ DSH 兼容基线 0.2.1-rc.2

## 设计定位

**科研工作台（桌面端 / CLI）+ [DeepSeek Harness (DSH)](https://github.com/deepseek-ai/deepseek-harness) 运行时
+ DeepSeek 等基础模型（可替换为任意 OpenAI 兼容端点）+ 学科数据与知识包 + 教学铁律。**

| 模块 | 能力 |
|---|---|
| **教育科研台 EduResearch** | UCI Student Performance（649 名中学生真实数据）T1–T5 全流程：审计 → 单变量关联 → 多变量回归 → 泄漏对照 → 报告图表交付 |
| **公卫科研台 HealthResearch** | UCI Heart Disease（303 例真实历史病例）H1–H5 全流程：缺失审计 → Logistic 基线 → 防泄漏划分与 5 折 CV → 留出集评价与阈值分析 |
| **统计方法谱** | 两独立组 / Welch ANOVA / Kruskal-Wallis / 卡方+Cramér's V / 多重校正（Bonferroni / BH-FDR）/ 效应量 / 连续与分类预测评价 / Logistic OR 表 / 置换重要性；**数据不支持的方法显式声明拒绝理由** |
| **验证体系** | `scripts/verify.py` **49 项三方对账**：SHA256 完整性 → 确定性复跑 → 双独立实现交叉验证（statsmodels vs 手写 OLS 逐位一致）→ 协议断言；CI 三平台 × 双 Python 版本背书 |
| **桌面端** | 一个 .app 装下全部：**真实 DSH 0.2.1-rc.2（npm 官方包整包内置）+ Node 22 + Python 科研栈**，管线一键运行、DSH 智能体窗口、模型 Key 本机配置（不打包任何密钥） |
| **定制路径** | `templates/new-domain/` 七步复制出自己的学科 Agent：换知识 + 协议 + 数据三件事，`tools/` 计算层与验收设施零改动 |

三条设计底线：**零模拟数据**（两套基准均为 UCI 真实公开研究数据，数值全部锁定可复核）；
**模型不碰数字**（语言模型只调度与解读，全部统计值出自 `tools/` 计算层的真实执行）；
**换数据可复用**（用第二份数据证明学科迁移是"真实复用"而非"复制粘贴结果"）。

## 版本

- **v0.3.1（当前）**：桌面端 DSH 集成校准——技能装配位置修复（v0.3.0 中
  技能未被 DSH 扫描）、科研台 preset 经 profile patch 实际注入会话、
  随包许可补全；全量实机验证报告 docs/desktop-validation.md
- v0.3.0：macOS 桌面端——内置真实 DSH + Node 22 + 科研栈，
  干净环境冒烟随构建执行；随包 Python 执行桥让 DSH 会话内 `python examples/…`
  直接命中随包依赖；产物未签名未公证
- v0.2.0：HealthResearch 领域 + 全谱统计方法补齐（49 项对账）+ 教学资源包
  （9 张真实数据图 / 本地工作台 / 指令卡 p1–p9）
- v0.1.0：EduResearch 单领域可运行版（T1–T5 端到端）

详见 [CHANGELOG.md](CHANGELOG.md)。

## 快速开始

### 桌面端（推荐，开箱可用）

1. 下载 `.dmg`（或 `.zip`），打开后把 **DSH Research Lab.app** 拖入「应用程序」；
2. 首次打开（产物**未公证**）：在「应用程序」中右键 → 「打开」→ 再点「打开」；
3. 点「⚙ 模型设置」填入模型 API Key（DeepSeek 官方或任意 OpenAI 兼容端点）——
   Key 仅存本机（0600），不打包、不写日志、不上传；
4. 点「▶ 运行」跑通双管线（真实数据约 10 秒）并浏览报告；在「⚙ 模型设置」
   选择科研台 Preset（edu-research / health-research / research-lab / none），
   点「▶ 启动 DSH」在真实 DSH Web UI 里以所选科研台守则与 12 个技能驱动
   智能体，会话内 `python` 直接命中随包科研依赖。

安装、数据存放位置与构建细节见 [docs/desktop.md](docs/desktop.md)。
当前桌面端验证平台为 **macOS 11+ Apple Silicon**；Intel macOS / Windows / Linux 暂未提供。

### 开发者 / 高级用户（源码接入）

```bash
# 环境：Python 3.11+
git clone https://github.com/milulab/dsh-research-lab.git
cd dsh-research-lab
pip install -r requirements.txt

# ① 跑通教育科研管线（真实数据，约 10 秒）
python examples/education-demo/run_t1_t5.py
# → examples/education-demo/outputs/{results.json, report.md, tables/, figures/}

# ② 跑通公卫分类管线
python examples/health-demo/run_h1_h5.py

# ③ 总验收（数据完整性 + 确定性复跑 + 双实现交叉验证）
python scripts/verify.py            # 49/49 checks passed — ALL GREEN
```

### 接入 DSH 智能体（可选）

```bash
npm i -g @deepseek-ai/dsh          # DSH 0.2.1-rc.2（兼容基线）
bash scripts/install.sh --preset research-lab
dsh web                            # 工作区指向仓库根目录，选择 edu-research preset
```

### 常见使用方式

- **课堂演示**：跑 `run_t1_t5.py`，用 M1（调整 R²=0.263）与 M2（含期中成绩
  0.850）对照讲"什么是数据泄漏"；`docs/teaching-guide.md` 含完整时序与指令卡；
- **智能体问答**：DSH 会话内问"学习时间与成绩的关系"——Agent 调用 `tools/`
  计算 Spearman ρ=0.2747 并按教学铁律以"关联"表述，不生成任何数字；
- **定制学科 Agent**：`templates/new-domain` 复制 → 写 domain.yml →
  协议先锁定 → 换领域 Skill → 用自己的数据跑通并锁锚点（七步详见
  [docs/customize-agent.md](docs/customize-agent.md)）；
- **迁移验证**：把教育 Agent 的方法迁到公卫数据跑通 H1–H5，检验框架级复用。

## 数据集与治理

| 数据集 | UCI ID | 规模 | 许可 | 关键锚点（expected/ 锁定） |
|---|---|---|---|---|
| [Student Performance](https://archive.ics.uci.edu/dataset/320/student+performance) | 320 | 649×33（葡语课） | CC BY 4.0 | Spearman ρ=0.2747；M1 调整 R²=0.2629；M2 泄漏对照 0.8500 |
| [Heart Disease](https://archive.ics.uci.edu/dataset/45/heart+disease) | 45 | 303×14（Cleveland） | CC BY 4.0 | 5 折 CV AUC 0.869±0.069；留出 AUC 0.950；Brier 0.094；ca OR=3.55 [2.11, 5.98] |

治理规则：`datasets/*/raw/` 只读（SHA256 锁定于 `metadata/source.yml`）；
协议先于数据（`protocol.md` 锁定后不得静默修改）；分析计划、方法检查表与
"不适用方法声明"见 `datasets/*/protocol/` 与 [docs/method-checklist.md](docs/method-checklist.md)；
引用要求见 `datasets/*/metadata/source.yml`，全部第三方声明汇总于
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)；`scripts/fetch_data.py` 可校验或重新获取数据。

## 教学铁律（框架内置，不可绕过）

1. **原始数据只读**：`datasets/*/raw/` 永不改写，改动立即被 verify 抓住（有专门的安全测试）；
2. **统计值只能来自真实执行**：模型不得生成任何 p 值 / AUC——全部数字出自
   `tools/` 计算层，Agent 只负责调度与解读；
3. **双实现互证**：每个头条指标都有第二条独立实现路径（手写 OLS / 秩和法 AUC），
   `verify.py` 强制对账（49 项：SHA256 → 确定性复跑 → 交叉验证 → 协议断言）；
4. **因果表述禁令**：观察性数据的全部结论按"关联"表述；健康数据不得用于真实临床；
5. **缺列即拒绝**：数据不满足契约时 Agent 必须提出修正要求，禁止编造。

## 目录结构

```text
dsh-research-lab/
├── desktop/          桌面端（窗口壳 / 首启装配 / DSH 生命周期 / 执行桥）
├── presets/          research-lab（通用）/ edu-research / health-research
├── skills/           8 通用 + 4 领域 SKILL.md（含适用条件与输入输出契约）
├── tools/            Python 计算层：data_audit / regression / classification
│                     / stat_tests / report_builder
├── domains/          education / public-health（domain.yml + knowledge + protocols）
├── datasets/         education-student-performance / health-heart-disease
│   │                 （raw 只读 + processed + metadata + protocol + expected）
├── templates/        new-domain：七步定制自己的学科 Agent
├── examples/         education-demo（T1–T5）/ health-demo（H1–H5）端到端管线
├── scripts/          build_desktop.py 桌面构建 / verify.py 总验收 / reference_* 独立参考实现
├── tests/            unit / integration / golden / security
├── docs/             desktop / quickstart / customize-agent / teaching-guide …
└── .github/workflows/  verify（3 平台 × 2 Python）/ desktop-build / release（含桌面产物）
```

## 文档

- [docs/desktop.md](docs/desktop.md) — 桌面端：安装、使用、数据位置、构建与验证
- [docs/quickstart.md](docs/quickstart.md) — 安装、运行、接入 DSH
- [docs/customize-agent.md](docs/customize-agent.md) — 七步定制自己的学科 Agent
- [docs/teaching-guide.md](docs/teaching-guide.md) — 授课手册（时序、指令、验收）
- [docs/method-checklist.md](docs/method-checklist.md) — 方法验证检查表（逐项映射与锚点）
- [docs/data-governance.md](docs/data-governance.md) — 数据治理与许可
- [docs/architecture.md](docs/architecture.md) — 分层架构与设计决策

## 声明

- 本项目为**教学与研究辅助工具**：所有统计结论须由领域专家复核后方可用于实际决策；
- 两套数据均为真实研究数据，但**仅作课堂演示**：观察性数据只谈关联，
  健康数据不得用于真实临床诊断，每份产物尾注随附该边界；
- 桌面端随包分发的 DSH（MIT）与 Node.js（MIT）分别为 DeepSeek 与 OpenJS
  基金会项目，本项目与两者**无官方隶属关系**；
- 项目由 milulab 维护，许可证 MIT，第三方数据与文档许可见
  [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
