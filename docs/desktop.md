# Desktop｜桌面端（内置真实 DSH）

DSH Research Lab 桌面版：一个开箱可用的 macOS 应用，**随包内置**：

| 组件 | 说明 |
|---|---|
| 科研工作台 | tools/ 计算层 + pandas/statsmodels 等全部科研依赖（PyInstaller 打包） |
| DeepSeek Harness | **真实 DSH 0.2.1-rc.2**（npm 官方包整包内置，非模拟），MIT 许可 |
| Node.js 22 LTS | DSH 运行时（官方发行版 node 二进制） |
| 数据与模板 | 双领域真实数据集、3 个 preset、12 个技能，首启自动装配 |

最终用户**无需预装 Node / Python / DSH**——桌面包内自带全部运行时与依赖。

## 安装（macOS，Apple Silicon）

1. 下载 `dsh-research-lab-<版本>-darwin-arm64.dmg`（或 .zip）；
2. 打开 dmg，把 **DSH Research Lab.app** 拖入「应用程序」；
3. 首次打开（**本产物未签名未公证**）：在「应用程序」中右键 →
   「打开」→ 再点「打开」；macOS 会保留该许可，之后正常双击启动。

> 无 Apple 开发者证书，产物为 ad-hoc 签名（`codesign -s -`）。
> Gatekeeper 首次拦截是预期行为，上述步骤即可绕过；仅在本机构建自用时无此问题。

## 首次使用

1. 启动后进入本地工作台（仅监听 127.0.0.1，随机端口）；
2. 点「▶ 运行」跑通教育/公卫管线（真实数据，约 10 秒），在「产物浏览」
   打开 report.md / tables / figures；
3. 点「⚙ 模型设置」填入模型 API Key：
   - **DeepSeek 官方**：填 key，默认模型 `deepseek-chat`；
   - **OpenAI 兼容端点**（智谱 / 火山 / 自托管）：选对应提供方，填
     Base URL 与 key；
   - Key 只保存在本机应用目录（`config.json`，权限 0600），**绝不打包进
     应用、不写入日志、不上传**；DSH 通过 `apiKeyEnv` 环境变量引用。
4. 在「⚙ 模型设置」选择**科研台 Preset**（edu-research / health-research /
   research-lab / none），保存后点「▶ 启动 DSH」→「打开 DSH 窗口」：
   在真实 DSH Web UI 里以所选科研台的智能体守则（经 profile patch 注入，
   重启 DSH 生效）与 12 个技能驱动智能体；
   会话内 DSH 的 shell 工具调用 `python` 命中的是**随包执行桥**
   （带全部科研依赖），可直接运行 `examples/*` 管线脚本与 `tools/`。

## 科研台 Preset 的接入机制

DSH 0.2.1-rc.2 实测（`--dump-config` 校准）：

- `~/.agent-presets/` 目录布局**不被扫描**（仅内置
  preset-ptc / minimal / cordis / standard）；
- 科研台守则的正确接入方式是 profile patch（`dsh-home/profiles/web/
  cordis.patch.yml`）中的 `- id: agent` 配置条目，内容即
  `presets/<科研台>/agent.cordis.yml` 的 `agent` 段（同该文件头部
  "方式 b"）；
- 工作台设置保存所选 preset 后由 `desktop/patch_writer.sync_patch`
  重写 patch，**重启 DSH 生效**；设为 `none` 时不注入（通用助手）。
- 12 个技能装配在 `dsh-home/agents/skills/`（`$DSH_AGENTS_HOME/skills`，
  skill-filesystem 的共享 agents 根扫描位置）。

## 数据存放位置

| 内容 | 路径（macOS） |
|---|---|
| 应用主目录 | `~/Library/Application Support/DSHResearchLab/` |
| 工作台（管线在此产出） | `…/DSHResearchLab/lab/` |
| DSH 主目录（agents/skills、profiles、会话） | `…/DSHResearchLab/dsh-home/` |
| 模型配置 | `…/DSHResearchLab/config.json`（0600） |
| 运行日志 | `…/DSHResearchLab/logs/` |

应用内 Resources 为只读出厂模板；每次升级会把新模板同步到 `lab/`，
**永远不会触碰你的管线产物（`examples/*/outputs/`）与模型配置**。
卸载应用只需删除上述主目录。

## 构建（可复现）

```bash
# 完整构建 + 冒烟验证（含真实启动内置 DSH、双管线产出断言）
python scripts/build_desktop.py --verify

# 离线/固定来源构建
python scripts/build_desktop.py --verify \
  --node-bin /path/to/node --dsh-src /path/to/@deepseek-ai/dsh
```

构建步骤：PyInstaller onedir（科研栈 + 桌面层，windowed 产出标准 .app 布局）
→ 主可执行 ad-hoc 签名 → 装配 .app（官方 Frameworks 布局 + lab 模板 +
node + dsh + python shim + manifest + licenses + 应用图标
`assets/app-icon.icns`，由 `scripts/make_app_icon.py` 生成）→ **干净环境冒烟**
（`PATH=/usr/bin:/bin:/usr/sbin:/sbin` 且 **HOME 指向临时目录**：
装配 → 教育管线（进程内）→ 双管线（DSH 子进程同款环境）→ 真实启动
DSH web → token 访问 303/401 断言 → 停止）→ dmg/zip → checksums。

冒烟报告留在 `build/desktop/verify-report.json`。

## 无界面冒烟（交付自检）

```bash
/Applications/DSH\ Research\ Lab.app/Contents/MacOS/DSHResearchLab/DSHResearchLab \
  --smoke --with-dsh
```

输出 JSON（`ok: true` 即全部通过）；退出码 0/1。

## 随包 Python 执行桥

DSH 的 shell 工具与终端里 `python`/`python3` 指向
`Contents/Resources/bin/python`（shim）→ 主可执行 `--python-bridge` 模式：

- 复刻 CPython 语义：`script.py`（sys.path[0]=脚本目录）、`-c`、`-m`、
  `--version`、退出码与 traceback；
- `sys.path` 含工作台根（`import tools` 可用）与用户扩展目录
  `…/DSHResearchLab/pylibs`（`PYTHONUSERBASE`，`pip install --user` 落点）；
- 只在 DSH 子进程环境注入，不污染系统 PATH。

## 已知限制

- 当前构建/验证目标为 **macOS 11+ Apple Silicon (arm64)**；未在其他
  平台验证，Intel macOS / Windows / Linux 桌面包尚未提供；
- 产物**未签名未公证**（无开发者证书），分发需用户手动放行首启；
- `dsh` 版本锁定 0.2.1-rc.2（与仓库兼容基线一致），升级 DSH 需重新
  构建并跑 `--verify` 冒烟；
- 首次启动 DSH 时其 Web UI 可正常打开，未配置 Key 时代理对话会返回
  `MISSING_CREDENTIAL`（这是 DSH 的正确行为，非故障）。
