# Data Governance｜数据治理与许可

## 数据包规范（每个公开数据集必须齐全）

```
datasets/<name>/
├── raw/                      官方原件（只读；SHA256 锁定）
├── processed/                版本化派生数据 + 重建脚本（build_processed.py）
├── metadata/source.yml       URL/作者/引用/许可/访问日期/SHA256/版本
├── metadata/data_dictionary.csv  字段/类型/单位/编码/缺失定义/角色
├── protocol.md               预登记协议（V1.0 后改须升版）
├── expected/                 管线黄金结果 + 独立参考实现结果
└── README.md                 获取/引用/注意事项
```

## 许可现状

| 数据 | 许可 | 分发方式 | 引用义务 |
|---|---|---|---|
| UCI Student Performance | CC BY 4.0 | raw 直接分发（许可允许） | Cortez & Silva 2008 |
| UCI Heart Disease | CC BY 4.0 | raw 直接分发 | Detrano et al. 1989 |

两条均已在 `THIRD_PARTY_NOTICES.md` 与各 source.yml 落实"作者+来源+许可"三要素。
新增数据集时：许可允许分发→raw 入库+SHA256；不允许→入库 `fetch_data.py`
下载清单与校验和，仓库不留原件。

## 只读与留痕铁律

1. `raw/` 任何脚本不得写入；`verify.py` 每次运行先复算 SHA256；
2. 缺失/重复/异常的处理动作必须出现在 quality report（谁/依据/动作/行号）；
3. 标签映射等规则性转换显式写入结果 JSON（如 `label_mapping` 字段）；
4. 教学质控挑战包（人为加缺失/坏编码）必须标 `synthetic_modified`，
   禁止冒充真实记录——本仓库当前不含此类数据。

## 隐私边界

两个基准数据集均为去标识化公开研究数据。接入任何含个人信息的数据前：
确认合法依据与知情同意范围；默认本地处理、禁自动上传；交付物脱敏。
框架不收集任何遥测。

## 用途边界（随每份报告输出）

教学演示数据与产物；观察性数据只谈关联；健康数据不得用于真实临床；
报告尾注"不代表真实培训效果"必须保留。
