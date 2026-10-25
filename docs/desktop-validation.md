# Desktop Validation｜桌面端验证报告

版本：v0.3.1 ｜ 构建平台：macOS（Apple Silicon, arm64）｜ 构建日期：2026-10-25
构建命令：`python scripts/build_desktop.py --verify`（可复现；详见 docs/desktop.md）

## 1. 产物

| 产物 | 绝对路径 | 体积 | SHA256 |
|---|---|---|---|
| 应用包（tar 封装） | `/Users/leo/repos/milulab/dsh-research-lab/dist/desktop/DSH Research Lab.app` | 952 MB | `0156d54650e0567af39e87a44e459b77cf27a1dc0547921653caf46e2fe4a31a`（app.tar） |
| 镜像 | `/Users/leo/repos/milulab/dsh-research-lab/dist/desktop/dsh-research-lab-0.3.1-darwin-arm64.dmg` | 588 MB | `0cba9e443bb918b255928da2b0ff056347ba8571c570a61ece8c017ecd50ee7a` |
| 压缩包 | `/Users/leo/repos/milulab/dsh-research-lab/dist/desktop/dsh-research-lab-0.3.1-darwin-arm64.zip` | 355 MB | `9fe69b6399ff4b84240f5a8cac36f199da91be7b5745f56ca16b4bc76159ac9f` |

产物内容：PyInstaller 打包的科研栈（pandas 3.1.0 / numpy 2.5.4 / scipy 1.18.1 /
statsmodels 0.15.0 / scikit-learn 1.9.1 / matplotlib 3.11.2 / PyYAML 6.0.3）+
**真实 DSH 0.2.1-rc.2**（npm 官方包原样，674 MB）+ Node 22.22.0（nodejs.org
官方二进制，tarball sha256 `5ed4db0f…`）+ 工作台模板（双领域数据集、12 技能、
3 preset、docs）。

## 2. 自动化验证（构建内冒烟，干净环境）

命令：`<app>/Contents/MacOS/DSHResearchLab --smoke --with-dsh --home <临时目录>`
环境：`PATH=/usr/bin:/bin:/usr/sbin:/sbin`、`HOME=临时目录`（无开发机任何路径）。
报告：`build/desktop/verify-report.json`。结果 **6/6 步全绿**：

| 步骤 | 验证内容 | 结果 |
|---|---|---|
| bootstrap | 全新主目录装配：12 skills → `dsh-home/agents/skills/`，3 preset 守则可注入 | ✅ |
| env | 打包指纹：packaged 模式、DSH 0.2.1-rc.2、依赖版本 | ✅ |
| workbench-http | 本地工作台服务 `/api/health` 200 | ✅ |
| education-pipeline | 教育管线（进程内）真实运行，`results.json` 产出（≈10s） | ✅ |
| shell-env-pipelines | **DSH 子进程同款环境**（随包 `python` shim → 执行桥）运行教育+公卫双管线，产出 `results.json`（≈24s） | ✅ |
| dsh | 真实启动内置 DSH web；带 token 访问 **303**、无 token **401**（凭据栅栏）；干净停止 | ✅ |

## 3. GUI 实机验证（打包应用，截图证据）

截图目录：`build/desktop/gui-evidence/`（不入库）。流程：`open` 启动 .app →
真实 pywebview 窗口出现（`01-app-window-launch.png`，全屏截屏）→ 工作台服务
监听 `127.0.0.1` 随机端口（lsof 确认）→ 用浏览器驱动（agent-browser）对**同一
服务实例**逐项交互：

| 交互 | 证据 | 结果 |
|---|---|---|
| 工作台主页渲染：环境指纹条（版本/Python/7 依赖/DSH/数据/Key 状态）、三张管线卡、DSH 卡、产物浏览 | `02-workbench-main.png` + 可访问性快照 | ✅ |
| 点击「▶ 运行」（教育管线）→ 状态从"运行中"变"完成 rc=0"，产物浏览列出 9 个文件 | `03-pipeline-running-done.png` | ✅ |
| 打开 report.md 与产物清单 | `04-report-md.png`、`05-outputs-list.png` | ✅ |
| 「⚙ 模型设置」弹窗：提供方下拉（DeepSeek 官方 / OpenAI 兼容）、Key 密码框、BaseURL、模型、推理强度、**科研台 Preset 下拉**（edu/health/research-lab/none） | `06-settings-dialog.png` + 快照 | ✅ |
| 点击「▶ 启动 DSH」→ 状态"运行中 · 端口"，展示带 token 本机地址 | `07-dsh-running.png` | ✅ |
| 打开 DSH Web：真实 DeepSeek Harness 界面（New session / Workspaces / Plugins） | `08-dsh-web-ui.png` | ✅ |
| 「停止」→ 状态回到 stopped | `11-dsh-stopped.png` + `/api/dsh` state=stopped | ✅ |

会话级联动（GUI 内确认）：设置选择 edu-research → 启动 DSH → 用**打包内
Node+DSH 对同一 DSH_HOME 执行 `--profile web --dump-config`**，配置树中
agent 插件配置为 `name: edu-research` 及完整科研台守则——证明所选 preset
经 profile patch 实际注入 DSH 会话。

## 4. Preset 接入机制（实测校准记录）

- `.agent-presets/` 目录布局在 DSH 0.2.1-rc.2 **不被扫描**（dump-config 实测，
  仅内置 preset-ptc/minimal/cordis/standard）；
- 正确方式：profile `cordis.patch.yml` 中的 **`- id: agent` 配置条目**
  （即 `presets/*/agent.cordis.yml` 头部"方式 b"），dump-config 实测生效；
- 应用实现：设置页选择科研台 → `desktop/patch_writer.sync_patch` 将该台
  agent 段合并进 web profile patch（凭据条目之后），重启 DSH 生效。

## 5. 技能（skills）加载验证

- 目录装配（打包应用数据目录枚举）：`…/DSHResearchLab/dsh-home/agents/skills/`
  下 **12 个技能目录、12 份 SKILL.md** 全部就位（research-design …
  health-threshold-evaluation）；
- 注入链路：`DSH_AGENTS_HOME=<app-home>/dsh-home/agents`（`desktop/dsh_manager.py`
  启动 env），DSH 的 skill-filesystem 按官方语义扫描 `$DSH_AGENTS_HOME/skills/`；
- **未验证项**：DSH 会话输入框 `@` 技能自动补全的 UI 弹层未捕获成功
  （浏览器驱动与 DSH 前端的时序不稳定），不以此虚构"会话内技能列表已验证"；
  会话内实际调用技能需模型 API key（在线模型响应未验证，见 §7）。

## 6. 凭据与安全检查

- 模型 API key 仅存本机 `~/Library/Application Support/DSHResearchLab/config.json`
  （0600）；DSH 侧只经 `apiKeyEnv` 环境变量引用，patch 文件无密钥明文
  （单元测试断言 + 产物抽查）；
- 产物无开发机路径：`Resources/bin` shim 为相对定位；出厂 `datasets/*/expected/*.json`
  中构建机绝对路径在装配时确定性清洗为相对路径（已复查 0 残留）；
- 随包许可文本：`Resources/licenses/` 含 DSH-LICENSE（MIT，全文）、
  NODE-LICENSE.txt（Node 官方 LICENSE 全文，自官方 tarball 提取）、
  `python/` 41 份依赖许可（自各包 dist-info 收集）+ README 索引；
- headless 无 key 行为：`MISSING_CREDENTIAL`（DSH 正确报错，非伪造成功）。

## 7. 限制与未验证项（如实声明）

1. **在线模型响应未验证**：验证环境无模型 API key（且按规范不嵌入任何
   开发密钥），DSH 会话的实际对话、技能调用与科研台智能体端到端行为
   未经在线验证；配置层（patch 注入、技能装配）已验证。
2. **未开发者签名、未公证**：无 Apple 开发者证书，主可执行为 ad-hoc 签名
   （arm64 本机运行必需）；分发包首次打开需右键 → 打开放行 Gatekeeper。
3. **平台范围**：构建与全部验证仅覆盖 macOS 11+ Apple Silicon；Intel
   macOS / Windows / Linux 桌面包未提供、未验证。
4. **DSH 版本锁定**：0.2.1-rc.2（npm `@deepseek-ai/dsh`）；升级需重建并
   重跑 `--verify`。
5. **UI 弹层**：DSH 会话内 `@` 技能补全弹层未在自动化中稳定捕获（§5）；
   工作台自身全部按钮/弹窗已验证。
6. 产物体积约 2 GB（解压后），主要来自完整 DSH（674 MB）与科研栈；
   为"完整真实 DSH"取舍，未做组件裁剪。
