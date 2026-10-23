# Teaching Guide｜授课手册（第7讲·科研数据分析智能体开发与应用实战）

配套教案：`第7讲_科研数据分析智能体开发与应用实战_教案初稿.md`（培训资料目录）。
本手册只写"课堂怎么用本仓库"。

## 课前检查单（教师）

1. **冻结环境**：Python 3.12 venv + requirements.txt 已装；`python scripts/verify.py`
   在教师机全绿（49/49）；
2. **冻结版本**：DSH 0.2.1-rc.2（`dsh --version`）；模型凭据已写入 web 与
   headless 两个 profile（**两份独立**，各配各的）；
3. **预跑三遍**：`run_t1_t5.py`、`run_h1_h5.py`、`dsh headless` 各一次，产物留存；
4. **断网备份**：数据在仓库内（raw 已分发），管线离线可跑；录屏备用；
5. **投屏要点**：report.md 渲染、results.json 关键字段、ROC 图、
   M1/M2 对照表各开一个窗口。

## 课堂时序（180 分钟主线）

| 时段 | 环节 | 用仓库的什么 |
|---|---|---|
| 0–15 | 框架认识 + 安装 | README 架构图 → `bash scripts/install.sh` → `verify.py` 首跑 |
| 15–40 | 跑通一次完整研究 | `run_t1_t5.py`；逐件打开 outputs/ 产物；讲 T1 字节级审计的引号数字 |
| 40–75 | 拆解框架分层 | skills/ 12 件 + tools/ 四件 + expected/ 对账（双实现逐位一致现场演示） |
| 75–115 | 统计深水区（三选一讲透） | ①M1 回归+HC3（异方差真实存在）②T4 泄漏对照 Δ0.587 ③H 管线防泄漏 CV |
| 115–145 | 持续使用与追问 | results.json 追问演练；缺列防御（讲 data-intake 失败处理） |
| 145–165 | 定制自己的 Agent | templates/new-domain 七步；现场改 domain.yml 一个字段跑通 |
| 165–180 | 迁移验收 + 布置 | 教育台→公卫台迁移讲演；verify 三方对账收束 |

## 授课指令（实测可用，直接念）

- **指令A｜认识项目**："阅读本仓库 README 与 datasets/education-student-performance/
  的 protocol.md 和数据字典，不改任何文件。告诉我 T1–T5 各自做什么、
  expected/ 里锁定了哪些数值锚点。"
- **指令B｜跑基线**："运行 examples/education-demo/run_t1_t5.py，然后对照
  datasets/…/expected/education_results.json 核对 t3_model_m1 的系数表，
  报告 studytime 与 failures 的系数、95%CI、p 值，并说明 BP/JB 诊断含义。"
- **指令C｜复核**："对你刚才报告中最重要的一个数字，写一段独立复核代码并运行；
  如果不一致，停下来说明差异，不要择优采信。"
- **指令D｜迁移提问**："把同样的方法迁移到 health-heart-disease：哪些环节
  可以复用，哪些必须重做？（预期：tools 全复用，协议/字典/锚点全重做）"

## 验收（学员必过）

1. 本机 `verify.py` 全绿；2. 能指出 report.md 任一数字在 results.json 的出处；
3. 能说出 T4 为什么不是"更好的模型"；4. 缺列样例下智能体拒绝编造（演示）；
5. 七步清单完成度 ≥5 步。

## 常见课堂事故预案

- 无网：一切照常（数据/脚本全在本地）；录屏兜底；
- DSH 凭据失效：改用 headless 前先 `--dump-config` 验证；仍失败则演示
  outputs/ 留存产物（全部数字真实可查）；
- 学员改了 raw：`git checkout -- datasets/*/raw` 或 `fetch_data.py --restore`，
  verify 的 SHA256 检查会当场抓住——这本身就是教学点。
