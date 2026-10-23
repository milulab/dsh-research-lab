# Customize your Agent｜七步定制自己的学科科研智能体

原则：**改造而非重造**——复用框架的计算层、Skills 与验收设施，只替换"领域
知识 + 协议 + 数据包"三件事。

## 七步流程

### 1. 复制模板

```bash
cp -r templates/new-domain domains/my-domain
cp -r templates/new-domain skills/my-domain-analysis   # 按需
mkdir -p datasets/my-domain/{raw,processed,metadata,expected}
```

### 2. 写 domain.yml

替换 `templates/new-domain/domain.yml` 里的占位符：研究问题、方法（从 tools/
已支持清单选）、数据路径、**boundaries（措辞与用途边界）**。

### 3. 登记数据与知识

- `raw/` 放官方原始文件（许可允许分发时），`metadata/source.yml` 记 URL/
  作者/引用/许可/**SHA256**（`shasum -a 256 raw/*`）；许可不允许分发时改为
  `scripts/fetch_data.py` 下载清单；
- `metadata/data_dictionary.csv` 逐列登记（类型/编码/缺失定义/角色）；
- `knowledge/methodology.md` 逐条登记知识并标注性质（教科书/文献/本项目实测）。

### 4. 写协议（先于看数据）

复制 `templates/new-domain/protocol.md`：研究问题→观察单位→预处理规则→
**精确到公式的分析计划**→假设→局限。锁定为 V1.0 后不再静默修改。

### 5. 建一个领域 Skill

复制 `templates/new-domain/SKILL.md`：写清适用条件、输入契约、执行流、
**验证条件（含你数据集的锚点值）**、失败处理。Skill 是调度规范不是提示词——
它必须指明调用哪些 tools、产出哪些文件。

### 6. 跑通并锁定 expected/

```bash
# 仿照 examples/education-demo/run_t1_t5.py 写你的 run_*.py
python examples/my-domain-demo/run_a1_a5.py
# 把全量结果与独立参考实现（仿 scripts/reference_education.py）存入 expected/
python scripts/verify.py --suite my-domain     # 在 verify.py 注册新 suite
```

验收标准不是"回答像专家"，而是：设计可识别、执行真实、坏数据处理有痕、
来源可溯、复算一致、换数据可复用。

### 7. 打包为可共享 Preset

```bash
cp -r presets/research-lab presets/my-domain   # 改 preset.yml + agent.cordis.yml
python scripts/build_package.py                # 产出分发包 + SHA256
```

## 迁移自检清单（换第二份数据检验）

- [ ] 不改 tools/ 一行代码能跑通（计算层复用）
- [ ] 新协议/新字典生成，旧数值锚点全部失效清空
- [ ] 缺列/坏编码场景下按 Skill 要求"提出修正"而非编造
- [ ] verify 新 suite 全绿
- [ ] 分发包在他人机器按 README 跑通
