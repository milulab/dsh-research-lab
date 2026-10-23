# Quickstart｜安装与首跑

目标：10 分钟内跑通教育科研管线并完成总验收。

## 0. 前置

- Python 3.11+（含 pip）
- 可选（接入 DSH 智能体时）：Node 18+ 与 `npm i -g @deepseek-ai/dsh`
  （本仓库验证基线：0.2.1-rc.2）

## 1. 安装

```bash
git clone https://github.com/milulab/dsh-research-lab.git
cd dsh-research-lab
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

或运行平台脚本（自动完成上述步骤）：

```bash
bash scripts/install.sh          # macOS / Linux
powershell -File scripts/install.ps1   # Windows
```

## 2. 首跑（真实数据，~10 秒）

```bash
python examples/education-demo/run_t1_t5.py   # T1–T5 全管线
python examples/health-demo/run_h1_h5.py      # H1–H5 全管线
open examples/education-demo/outputs/report.md
```

产物：`results.json`（机器可读全量）、`report.md`（人读报告）、
`tables/*.csv`、`figures/*.png`。

## 3. 总验收

```bash
python scripts/verify.py        # 31 项：数据 SHA256 / 确定性复跑 / 双实现交叉验证
```

## 4. 接入 DSH 智能体（可选）

```bash
bash scripts/install.sh --preset research-lab   # 装三个 preset + skills
dsh web                                         # 工作区指向本仓库根目录
```

- 模型凭据：写 `$DSH_HOME/profiles/web/cordis.patch.yml`（web）与
  `profiles/headless/cordis.patch.yml`（headless）——两份独立，参考 docs/teaching-guide.md；
- 验证注册：`dsh --profile <p> --dump-config`；
- 无 key 时 headless 报 `MISSING_CREDENTIAL` 属预期行为。

## 5. 常见问题

| 现象 | 处理 |
|---|---|
| `ModuleNotFoundError: tools` | 在仓库根目录运行脚本（各脚本已内置 sys.path 处理） |
| verify 的 SHA256 不匹配 | raw 文件被改动；用 `python scripts/fetch_data.py --restore` 重取官方原件 |
| matplotlib 无图 | 检查 figures/ 目录权限；本仓库强制 Agg 后端（无窗口依赖） |
| Windows 下 `--sep ';'` 报错 | 用 `--sep ";"`（PowerShell 引号规则），或直接跑 examples 一键脚本 |
