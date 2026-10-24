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


def sync_patch(home: Path, app_config: AppConfig) -> Path:
    """按当前应用配置同步 web profile patch（<home>/dsh-home/profiles/web/）。

    已配置 key → 写凭据引用 + 默认模型；未配置 → 写空数组（DSH 正常启动，
    会话内调用模型时按 MISSING_CREDENTIAL 提示）。路径与 DSH 首启生成的
    模板一致，首启前写入即生效。
    """
    cfg = app_config.load()
    if cfg.get("api_key"):
        payload = yaml.safe_dump(build_patch(cfg), allow_unicode=True, sort_keys=False)
    else:
        payload = "[]\n"
    target = Path(home) / "dsh-home" / "profiles" / "web" / "cordis.patch.yml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload, encoding="utf-8")
    return target
