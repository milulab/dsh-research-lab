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
`requirements.txt` 与 `pyproject.toml`。DSH（DeepSeek Harness）为外部运行时，
按其自身许可证条款安装使用，本仓库不对其进行再分发。
