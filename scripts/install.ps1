# dsh-research-lab — Windows 安装脚本（PowerShell 5.1+）
# 用法：
#   powershell -File scripts\install.ps1
#   powershell -File scripts\install.ps1 -Preset research-lab
param(
    [string]$Preset = ""
)

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "==> [1/3] Python 虚拟环境" -ForegroundColor Cyan
$Venv = Join-Path $Here ".venv"
if (-not (Test-Path $Venv)) {
    python -m venv $Venv
}
$Activate = Join-Path $Venv "Scripts\Activate.ps1"
. $Activate
python -m pip install --upgrade pip -q
python -m pip install -r (Join-Path $Here "requirements.txt") -q

Write-Host "==> [2/3] 验收（真实数据 + 双实现交叉验证）" -ForegroundColor Cyan
Push-Location $Here
python scripts\verify.py
Pop-Location

Write-Host "==> [3/3] DSH preset 安装" -ForegroundColor Cyan
if ($Preset -ne "") {
    $Candidates = @()
    if ($env:DSH_DIR) { $Candidates += $env:DSH_DIR }
    $Candidates += (Join-Path $env:USERPROFILE ".dsh\runtime\dsh")
    $DshDir = $null
    foreach ($c in $Candidates) {
        if ($c -and (Test-Path (Join-Path $c "apps\cli\config\agent-presets"))) {
            $DshDir = $c; break
        }
    }
    if (-not $DshDir) {
        Write-Warning "未找到 DSH，跳过 preset 安装。安装后重跑：install.ps1 -Preset $Preset"
    } else {
        $PresetsDst = Join-Path $DshDir "apps\cli\config\agent-presets"
        $SkillsDst = Join-Path $DshDir ".agents\skills"
        New-Item -ItemType Directory -Force -Path $PresetsDst, $SkillsDst | Out-Null
        Copy-Item -Recurse -Force (Join-Path $Here "presets\$Preset") $PresetsDst
        $GenericSkills = @("research-design","data-intake","data-quality",
            "exploratory-analysis","statistical-modeling","model-validation",
            "scientific-report","evidence-traceability")
        foreach ($s in $GenericSkills) {
            Copy-Item -Recurse -Force (Join-Path $Here "skills\$s") $SkillsDst
        }
        switch ($Preset) {
            "edu-research" {
                foreach ($s in @("edu-performance-analysis","edu-leakage-audit")) {
                    $p = Join-Path $Here "skills\$s"
                    if (Test-Path $p) { Copy-Item -Recurse -Force $p $SkillsDst }
                }
            }
            "health-research" {
                foreach ($s in @("health-risk-modeling","health-threshold-evaluation")) {
                    $p = Join-Path $Here "skills\$s"
                    if (Test-Path $p) { Copy-Item -Recurse -Force $p $SkillsDst }
                }
            }
        }
        Write-Host "  preset=$Preset skills → $SkillsDst" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "完成。快速开始：" -ForegroundColor Green
Write-Host "  cd $Here; .\.venv\Scripts\Activate.ps1"
Write-Host "  python examples\education-demo\run_t1_t5.py"
Write-Host "  python examples\health-demo\run_h1_h5.py"
