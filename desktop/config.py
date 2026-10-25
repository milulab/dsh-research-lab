"""config.py — 桌面应用配置（模型凭据与偏好）。

安全约定：
- API key 仅存于本机应用主目录的 config.json（0600 权限），绝不打包、
  绝不写入日志、绝不随 patch.yml 落盘——DSH 侧只通过 apiKeyEnv 引用
  环境变量名，真实 key 在启动 DSH 子进程时注入。
- HTTP 接口对 key 只写不读（GET 返回 has_key 布尔，不回显内容）。
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from . import paths

PROVIDER_DEEPSEEK = "deepseek"
PROVIDER_OPENAI_COMPAT = "openai-compat"

DEFAULTS: dict = {
    "provider": PROVIDER_DEEPSEEK,
    "api_key": "",
    "base_url": "",
    "model": "deepseek-chat",
    "reasoning_effort": "high",
    "preset": "edu-research",
}

API_KEY_ENV = "DSHRL_MODEL_API_KEY"


class AppConfig:
    def __init__(self, home: Path | None = None):
        self.home = Path(home) if home else paths.app_home()
        self.path = self.home / "config.json"

    def load(self) -> dict:
        data = dict(DEFAULTS)
        if self.path.is_file():
            try:
                data.update(json.loads(self.path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                pass
        return data

    def save(self, updates: dict) -> dict:
        data = self.load()
        for k in DEFAULTS:
            if k in updates and updates[k] is not None:
                data[k] = str(updates[k]).strip()
        self.home.mkdir(parents=True, exist_ok=True)
        self._atomic_write(self.path, json.dumps(data, ensure_ascii=False, indent=2))
        os.chmod(self.path, 0o600)
        return data

    # -- 派生视图 -----------------------------------------------------------
    def has_key(self) -> bool:
        return bool(self.load().get("api_key"))

    def summary(self) -> dict:
        d = self.load()
        return {
            "provider": d["provider"],
            "base_url": d["base_url"],
            "model": d["model"],
            "reasoning_effort": d["reasoning_effort"],
            "preset": d.get("preset", "edu-research"),
            "has_key": bool(d["api_key"]),
        }

    def credential_env(self) -> dict[str, str]:
        """启动 DSH 子进程时注入的环境变量（key → 指定 env 名）。"""
        key = self.load().get("api_key", "")
        return {API_KEY_ENV: key} if key else {}

    @staticmethod
    def _atomic_write(path: Path, text: str) -> None:
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".config-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
