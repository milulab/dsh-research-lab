# Changelog

## v0.3.1 — 2026-10-25

桌面端 DSH 集成校准版：修复技能装配位置与 preset 接入方式（均经 DSH
0.2.1-rc.2 `--dump-config` 实测校准），补全随包许可文本。**v0.3.0 的
dmg/zip 中技能实际未被 DSH 扫描加载，本版修复**。

- **技能装配位置修复**：skills 从 `dsh-home/skills`（不被 0.2.1-rc.2
  skill-filesystem 扫描）改挂到 `$DSH_AGENTS_HOME/skills`（即
  `dsh-home/agents/skills/`）；首启自动清理两处旧布局残留；
- **科研台 preset 接入方式修复**：`.agent-presets/` 目录布局在该版本
  同样不被扫描（dump-config 实测仅内置 preset-ptc/minimal/cordis/standard），
  改为 profile patch 的 `- id: agent` 配置条目注入所选科研台的
  `agent.cordis.yml` 守则（同 presets 头部"方式 b"）；
- **工作台设置新增「科研台 Preset」下拉**：edu-research（默认）/
  health-research / research-lab / none（通用助手），保存后重启 DSH 生效；
- **随包许可补全**：`Resources/licenses/` 增 Node 官方 LICENSE 全文
  （自 nodejs.org tarball 提取）与 41 份 Python 依赖许可（自各包
  dist-info 收集，含 README 索引）；
- 出厂 `datasets/*/expected/*.json` 中构建机绝对路径在装配时确定性
  清洗为仓库相对路径（产物不携带开发机目录信息）；
- **全量实机验证**：`docs/desktop-validation.md`——干净环境冒烟 6/6 步、
  GUI 实机交互截图证据、preset 经 dump-config 确认注入 DSH 会话配置、
  凭据无明文落盘抽查；如实记录未验证项（在线模型响应、未公证等）；
- build_desktop 修复重复的图标拷贝块（仅产物冗余，无行为影响）。

## v0.3.0 — 2026-10-24

桌面端版本：开箱可用、内置真实 DSH 的 macOS 应用。

- **桌面端（macOS arm64）**：`scripts/build_desktop.py` 产出 .app/dmg/zip——
  PyInstaller 打包科研栈与工作台，随包内置 Node 22.22.0（官方二进制）与
  **真实 DSH 0.2.1-rc.2**（npm 官方包，MIT），最终用户无需预装
  Node / Python / DSH；
- **DSH 完整集成**：工作台一键启动 `dsh web`（DSH_HOME 隔离于应用主目录、
  工作区指向可写 lab/、自动解析带 token 的本机地址并校验 303/401 凭据栅栏）、
  preset（3）与技能（12）首启自动安装、凭据经 `apiKeyEnv` 环境变量注入
  （key 仅存本机 `config.json` 0600，绝不打包/不落盘/不进日志）；
- **随包 Python 执行桥**：主可执行 `--python-bridge` 模式 + `python`/`python3`
  shim 注入 DSH 子进程 PATH——DSH 会话内 `python examples/…` 直接命中随包
  科研依赖（复刻 CPython 的 sys.path/argv/退出码语义；`-m pip --user` 落
  用户扩展目录）；
- **干净环境验证**：构建冒烟在 `PATH=/usr/bin:/bin` + 临时主目录下完成
  装配→进程内教育管线→DSH 子进程同款环境双管线产出→真实 DSH 启动→
  token 访问断言（`build/desktop/verify-report.json`）；
- 本地工作台（stdlib-only Web UI）升级：环境指纹、DSH 面板（启动/停止/
  带窗口打开/日志）、模型设置（只写不读 key）、产物浏览；`python
  scripts/dashboard.py` 命令行入口保留；
- bootstrap 装配幂等且按**完整相对路径**保留用户产物（`examples/*/outputs/`
  永不覆盖，回归测试在案）；
- 测试：desktop 单元 12 项（桥语义/URL 解析/凭据不落盘/同步保留规则）+
  集成 4 项（服务 API/DSH 子进程管线）；CI `desktop-build.yml`
  （macOS 构建 + 冒烟）；THIRD_PARTY_NOTICES 增补桌面随包分发声明
  （DSH/Node，均为 MIT）；
- **发布链路**：`release.yml` 新增 desktop job——打 tag 时在 macOS runner
  完整构建桌面端（含冒烟），.dmg/.zip 随源码包一并附到 GitHub Release
  并计入 checksums；README 按发布形态重构（下载入口前置、分层快速开始、
  数据锚点、声明收尾）；verify.yml 过时注释更正（31 → 49）；
- **应用图标**：`scripts/make_app_icon.py` 生成品牌渐变 + 锥形瓶图标
  （`assets/app-icon.icns`），构建时注入 .app（CFBundleIconFile）；
  desktop-build CI 测试 job 补装 pytest；
- **窗口流程运行时修复**（真实启动验证发现）：pywebview `js_api` 归位到
  `create_window()`（此前误传 `start(js_api=…)`，打包形态 TypeError、窗口
  无法建立）；工作台 HTTP 服务改由后台线程 `serve_forever`（此前只绑定
  不循环，主窗口整窗不可达）；冒烟新增 `workbench-http` 步骤（真实起服务
  断言 `/api/health` 200），服务级缺陷不再依赖开窗才能发现；
- 产物**未签名未公证**（无开发者证书，主可执行 ad-hoc 签名），分发文档
  明确首启放行步骤；当前仅验证 macOS 11+ Apple Silicon。

## v0.2.0 — 2026-10-23

双领域 + 全谱方法 + 数据复现版本。

- 方法谱系按"数据验证检查表"从第一性原理补齐：两独立组（Welch t/Mann-Whitney
  +Cohen's d）、Welch ANOVA/Kruskal-Wallis、卡方+Cramér's V（含期望频数检查）、
  Bonferroni/BH-FDR 多重校正、连续预测 MAE/RMSE/R²+K 折 CV、Logistic OR 表
  （GLM/IRLS 流行病学惯例）、F1、置换重要性、设计矩阵秩、Cook's 距离、
  模型设定敏感性分析、复现环境指纹、**不适用方法显式声明段**
  （生存/纵向/因果/调查加权等数据不支持的方法逐条说明拒绝理由）
- `scripts/verify.py` 扩至 **49 项对账全绿**；新增 `docs/method-checklist.md`
  逐项映射（检查表→实现→锚点值→不适用理由）

- 新增 HealthResearch 领域模板与 heart-disease 数据包（H1–H5 完整管线）：
  审计（缺失 ca=4/thal=2，完整案例 297）→ Logistic 基线 → 防泄漏划分与 5 折 CV
  （AUC 0.869±0.069）→ 留出集评价（AUC 0.950、Youden 阈值、Brier 0.094、校准曲线）
- 独立参考实现双路互证：教育侧 numpy-OLS vs statsmodels 逐位一致（|Δcoef|=0）；
  健康侧 GLM/IRLS + 秩和 AUC vs sklearn（跨求解器容差 0.005，同概率秩和差 0.0）
- `scripts/verify.py` 总验收 31 项全绿（SHA256 完整性 / 确定性复跑 / 交叉验证 / 协议断言）
- Presets：research-lab / edu-research / health-research（DSH 0.2.1-rc.2 基线）

## v0.1.0 — 2026-10-23

可运行单领域版本。

- EduResearch 教学管线 T1–T5 端到端（真实数据 649×33）：
  审计（649 行 0 缺失 0 重复；raw 字节级核查发现 G1/G2 引号数字——类型漂移教学点）
  → 单变量关联（studytime Spearman ρ=0.275）→ M1 多变量回归（调整 R²=0.263，
  studytime +0.51 / failures −1.67，异方差与残差非正态诊断在案）
  → M2 泄漏对照（含 G1/G2 后调整 R²=0.850，任务定义变化讲解）
  → 报告/图表/日志交付
- 通用 Skills 八件 + 教育领域 Skills；templates/new-domain 定制模板

### 教学配套（v0.2.0 同日追加）

- `scripts/make_teaching_figures.py`：9 张教学可视化（G3 分布、学习时间箱线、
  M1 森林图、泄漏对照柱、Spearman 热图；标签/年龄概览、阈值扫描、双阈值混淆、
  OR 森林图），全部由真实数据与 expected 锚点生成，CJK 字体跨平台回退
- `scripts/dashboard.py`：本地工作台（纯标准库 Web UI，一键运行两管线与总验收，
  产物沙箱浏览防路径穿越；127.0.0.1 绑定）
- `docs/teaching-prompts.md`：教学指令卡 p1–p9（对话逐条粘贴版）
- GitHub Release v0.2.0 附教学资源包（12 技能 + 两数据包 + 图 + 指令卡）
  与 SHA256SUMS；教程页 milulab.com/course/ai-data-analyse/dsh.html
