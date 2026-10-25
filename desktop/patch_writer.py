"""patch_writer.py — 生成 DSH web profile 的 cordis.patch.yml。

只写"凭据引用 + 默认模型"，真实 key 经 apiKeyEnv 指向的环境变量在
启动 DSH 子进程时注入（见 config.credential_env）。本文件永不携带密钥。

两种凭据模式（与 DSH 0.2.1-rc.2 适配器文档一致）：
- deepseek（官方直连）：
    - name: '@deepseek-ai/dsh-llm-deepseek-api-key'
      config: { apiKeyEnv: DSHRL_MODEL_API_KEY }
- openai-compat（OpenAI 兼容网关，如智谱/火山/自托管）：
    - name: '@deepseek-ai/dsh-llm-pi-ai'
      config.providers.<name>: { apiKeyEnv, api: openai-completions, baseURL, models }
"""
from __future__ import annotations

from pathlib import Path

import yaml

from .config import API_KEY_ENV, PROVIDER_DEEPSEEK, PROVIDER_OPENAI_COMPAT, AppConfig

COMPAT_PROVIDER_NAME = "lab-gateway"


def build_patch(cfg: dict) -> list[dict]:
    """根据应用配置生成 patch 条目数组（无密钥）。"""
    entries: list[dict] = []
    model = cfg.get("model") or "deepseek-chat"
    effort = cfg.get("reasoning_effort") or "high"

    if cfg.get("provider") == PROVIDER_OPENAI_COMPAT:
        base_url = (cfg.get("base_url") or "").strip()
        if not base_url:
            raise ValueError("OpenAI 兼容模式必须填写 baseURL")
        entries.append({
            "name": "@deepseek-ai/dsh-llm-pi-ai",
            "config": {
                "providers": {
                    COMPAT_PROVIDER_NAME: {
                        "displayName": "科研台模型网关",
                        "apiKeyEnv": API_KEY_ENV,
                        "api": "openai-completions",
                        "baseURL": base_url,
                        "models": [{"id": model}],
                    }
                }
            },
        })
        provider_ref = COMPAT_PROVIDER_NAME
    else:
        entries.append({
            "name": "@deepseek-ai/dsh-llm-deepseek-api-key",
            "config": {"apiKeyEnv": API_KEY_ENV},
        })
        provider_ref = "deepseek-official"

    entries.append({
        "id": "agent-default-model",
        "config": {
            "provider": provider_ref,
            "model": model,
            "reasoningEffort": effort,
        },
    })
    return entries


def _lab_agent_entry(lab: Path, preset: str) -> dict | None:
    """读取工作台 preset 的 agent.cordis.yml，转成 `- id: agent` patch 条目。

    DSH 0.2.1-rc.2 不扫描 .agent-presets 目录布局（实测 dump-config 验证），
    preset 的正确接入方式是 profile patch 中的 agent 插件配置条目（同
    presets/*/agent.cordis.yml 头部"方式 b"）。
    """
    import yaml as _yaml

    src = Path(lab) / "presets" / preset / "agent.cordis.yml"
    if not src.is_file():
        return None
    data = _yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    agent = data.get("agent")
    if not isinstance(agent, dict) or not agent.get("instructions"):
        return None
    return {"id": "agent", "config": agent}


def sync_patch(home: Path, app_config: AppConfig) -> Path:
    """按当前应用配置同步 web profile patch（<home>/dsh-home/profiles/web/）。

    组成：凭据引用 + 默认模型（未配置 key 时省略凭据条目）+ 所选科研台的
    agent 配置段（preset ∈ research-lab / edu-research / health-research，
    可设为 "none" 关闭）。路径与 DSH 首启生成的模板一致，首启前写入即生效。
    """
    cfg = app_config.load()
    entries: list[dict] = []
    if cfg.get("api_key"):
        entries.extend(build_patch(cfg))
    lab = (Path(home) / "lab") if (Path(home) / "lab" / "presets").is_dir() \
        else Path(__file__).resolve().parents[1]
    preset = str(cfg.get("preset") or "edu-research")
    if preset != "none":
        entry = _lab_agent_entry(lab, preset)
        if entry is not None:
            entries.append(entry)
    payload = yaml.safe_dump(entries, allow_unicode=True, sort_keys=False) \
        if entries else "[]\n"
    target = Path(home) / "dsh-home" / "profiles" / "web" / "cordis.patch.yml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload, encoding="utf-8")
    return target
