#!/usr/bin/env bash
# dsh-research-lab — macOS / Linux 安装脚本
# 用法：
#   bash scripts/install.sh                 # 仅装 Python 环境并验收
#   bash scripts/install.sh --preset research-lab   # 同时把 preset/skills 装进 DSH
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PRESET=""

for arg in "$@"; do
  case "$arg" in
    --preset) shift_flag=1 ;;
  esac
done
# 简单解析：--preset <name>
while [[ $# -gt 0 ]]; do
  case "$1" in
    --preset) PRESET="${2:-research-lab}"; shift 2 ;;
    *) echo "未知参数: $1" >&2; exit 1 ;;
  esac
done

echo "==> [1/3] Python 虚拟环境"
if [ ! -d "$HERE/.venv" ]; then
  python3 -m venv "$HERE/.venv"
fi
# shellcheck disable=SC1091
source "$HERE/.venv/bin/activate"
python -m pip install --upgrade pip -q
python -m pip install -r "$HERE/requirements.txt" -q

echo "==> [2/3] 验收（真实数据 + 双实现交叉验证）"
(cd "$HERE" && python scripts/verify.py)

echo "==> [3/3] DSH preset 安装"
if [ -n "$PRESET" ]; then
  DSH_DIR_CANDIDATES=(
    "${DSH_DIR:-}"
    "$HOME/.dsh/runtime/dsh"
  )
  DSH_DIR_RESOLVED=""
  for d in "${DSH_DIR_CANDIDATES[@]}"; do
    if [ -n "$d" ] && [ -d "$d/apps/cli/config/agent-presets" ]; then
      DSH_DIR_RESOLVED="$d"; break
    fi
  done
  if [ -z "$DSH_DIR_RESOLVED" ]; then
    echo "  ⚠ 未找到 DSH（$HOME/.dsh/runtime/dsh），跳过 preset 安装。"
    echo "    安装 dsh 后重跑：DSH_DIR=<dsh目录> bash scripts/install.sh --preset $PRESET"
  else
    PRESETS_DST="$DSH_DIR_RESOLVED/apps/cli/config/agent-presets"
    SKILLS_DST="$DSH_DIR_RESOLVED/.agents/skills"
    mkdir -p "$PRESETS_DST" "$SKILLS_DST"
    cp -R "$HERE/presets/$PRESET" "$PRESETS_DST/"
    for s in research-design data-intake data-quality exploratory-analysis \
             statistical-modeling model-validation scientific-report \
             evidence-traceability; do
      cp -R "$HERE/skills/$s" "$SKILLS_DST/"
    done
    # 领域 skills 按 preset 追加
    case "$PRESET" in
      edu-research)
        for s in edu-performance-analysis edu-leakage-audit; do
          [ -d "$HERE/skills/$s" ] && cp -R "$HERE/skills/$s" "$SKILLS_DST/"
        done ;;
      health-research)
        for s in health-risk-modeling health-threshold-evaluation; do
          [ -d "$HERE/skills/$s" ] && cp -R "$HERE/skills/$s" "$SKILLS_DST/"
        done ;;
    esac
    echo "  ✓ preset=$PRESET skills → $SKILLS_DST"
    echo "  验证：dsh --profile <p> --dump-config | grep -A2 preset"
  fi
fi

echo ""
echo "完成。快速开始："
echo "  cd $HERE && source .venv/bin/activate"
echo "  python examples/education-demo/run_t1_t5.py"
echo "  python examples/health-demo/run_h1_h5.py"
