# Third-party notices

本仓库包含的第三方数据与其许可声明。框架代码本身以 MIT 许可发布（见 LICENSE）。

## 1. UCI Student Performance (id=320)

- 文件：`datasets/education-student-performance/raw/`
- 作者：Paulo Cortez, Alice Silva（University of Minho）
- 引用：Cortez, P. & Silva, A. (2008). Using Data Mining to Predict Secondary
  School Student Performance. FUBUTEC 2008, pp. 5-12, EUROSIS.
- 许可：CC BY 4.0（https://creativecommons.org/licenses/by/4.0/）
- 来源：https://archive.ics.uci.edu/dataset/320/student+performance
- 分发说明：CC BY 4.0 允许再分发；本仓库保留原始文件未作修改（SHA256 见
  metadata/source.yml），并在此注明作者与来源。

## 2. UCI Heart Disease (id=45)

- 文件：`datasets/health-heart-disease/raw/`
- 来源机构：Hungarian Institute of Cardiology；V.A. Medical Center Long Beach；
  University Hospital Zurich；Cleveland Clinic Foundation；捐赠人 David W. Aha。
- 引用：Detrano, R., et al. (1989). International application of a new probability
  algorithm for the diagnosis of coronary artery disease. American Journal of
  Cardiology, 64, 304-310.
- 许可：CC BY 4.0
- 来源：https://archive.ics.uci.edu/dataset/45/heart+disease
- 使用限制（框架强制）：历史研究数据，禁止用于真实临床诊断或个体健康决策。

## 3. 运行时依赖

Python 依赖（pandas / numpy / scipy / statsmodels / scikit-learn / matplotlib / PyYAML）
各自遵循其上游许可证（均为 BSD/MIT 系宽松许可），清单与版本锁定见
`requirements.txt` 与 `pyproject.toml`。

## 4. 桌面端随包分发的第三方组件

桌面版（`scripts/build_desktop.py` 产出的 .app/dmg/zip）随包再分发以下
组件；两者均使用宽松许可，允许再分发，原始声明随包携带：

| 组件 | 版本 | 许可 | 声明位置 |
|---|---|---|---|
| DeepSeek Harness (DSH) | 0.2.1-rc.2（npm `@deepseek-ai/dsh`，整包未修改） | MIT（Copyright (c) 2026 DeepSeek） | 应用内 `Resources/licenses/DSH-LICENSE` |
| Node.js | 22.22.0（nodejs.org 官方二进制） | MIT（含第三方声明，见官方 LICENSE） | 应用内 `Resources/licenses/NODE-LICENSE.txt` |

分发说明：
- DSH 以 npm 官方源原样打包（未修改其代码），构建记录其版本与来源；
  `build/desktop/verify-report.json` 留存冒烟验证证据；
- 桌面端产物**未签名未公证**（无 Apple 开发者证书，仅 ad-hoc 签名）；
- 源码形态（本仓库）不包含 DSH 与 Node 二进制，仅在构建时从官方渠道获取。
