"""LLM status & configuration API（Sprint H v3.14）。

Endpoints:
  GET  /api/llm/status     公開：當前 provider / 是否已設 key / 是否有過成功呼叫
  POST /api/llm/test       admin：用「未持久化」的候選 key 試打一次 API
  POST /api/llm/configure  admin：寫進 backend/.env + 即時更新 settings 記憶體

設計重點：
  - 不存 key 進 DB（避免 backup / log 外洩）；寫 .env file 是磁碟本地
  - admin 只能透過 UI 改 key；普通使用者只能查 status
  - test 不 persist：先試打，OK 才呼 configure 真的寫
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.core.deps import get_optional_user
from app.core.logging import get_logger
from app.core.security import UserContext, require_permission

log = get_logger(__name__)
router = APIRouter(prefix="/api/llm", tags=["LLM Status"])


# ── 內部狀態（in-memory，記錄上次 test 結果）──────────────
_last_test_result: dict = {
    "tested_at": None,
    "success": None,
    "error": None,
    "provider": None,
}


# ── Schemas ────────────────────────────────────────────────
class LlmStatusResponse(BaseModel):
    configured: bool                          # 有沒有設 LLM_API_KEY
    provider: str                             # deepseek / openai / anthropic / ollama
    model: str
    base_url: str
    verify_ssl: bool
    last_test_success: Optional[bool] = None  # 上次 test 結果
    last_test_error: Optional[str] = None
    setup_url: str = "/settings"              # 提示前端去哪裡設定


class LlmTestRequest(BaseModel):
    provider: Literal["deepseek", "openai", "anthropic", "ollama"] = "deepseek"
    api_key: str = Field(..., min_length=1, description="候選 key，不寫進磁碟")
    base_url: Optional[str] = None
    verify_ssl: bool = True


class LlmTestResponse(BaseModel):
    success: bool
    message: str
    detail: Optional[str] = None
    response_ms: Optional[int] = None


class LlmConfigureRequest(BaseModel):
    provider: Literal["deepseek", "openai", "anthropic", "ollama"] = "deepseek"
    api_key: str = Field(..., min_length=1)
    base_url: Optional[str] = None
    model: Optional[str] = None
    verify_ssl: bool = True


class LlmConfigureResponse(BaseModel):
    saved: bool
    requires_restart: bool
    message: str


# ── 預設值 by provider ─────────────────────────────────────
_DEFAULT_BASE_URL = {
    "deepseek": "https://api.deepseek.com/v1",
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "ollama": "http://localhost:11434",
}
_DEFAULT_MODEL = {
    "deepseek": "deepseek-chat",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-20241022",
    "ollama": "llama3.2",
}


# ── 公開狀態查詢 ──────────────────────────────────────────
@router.get("/status", response_model=LlmStatusResponse)
async def llm_status(_user=Depends(get_optional_user)):
    """公開：任何登入者都能查 AI 狀態（用來決定 UI 要不要顯示「請申請 key」提示）。"""
    return LlmStatusResponse(
        configured=bool(settings.LLM_API_KEY) or settings.LLM_PROVIDER == "ollama",
        provider=settings.LLM_PROVIDER,
        model=settings.LLM_MODEL,
        base_url=settings.LLM_BASE_URL,
        verify_ssl=settings.LLM_VERIFY_SSL,
        last_test_success=_last_test_result.get("success"),
        last_test_error=_last_test_result.get("error"),
    )


# ── 測試連線（不 persist）──────────────────────────────────
@router.post("/test", response_model=LlmTestResponse)
async def llm_test(
    body: LlmTestRequest,
    user: UserContext = Depends(require_permission("system.config.update")),
):
    """用候選 key 試打一次 API，不寫進磁碟。

    讓 admin 在 UI 按「測試」鈕看 key 對不對，OK 才按「儲存」。
    """
    import time as _t

    base_url = body.base_url or _DEFAULT_BASE_URL.get(body.provider, "")
    start = _t.time()

    try:
        async with httpx.AsyncClient(timeout=15.0, verify=body.verify_ssl) as client:
            if body.provider == "ollama":
                # Ollama: 試打 /api/tags
                resp = await client.get(f"{base_url}/api/tags")
                resp.raise_for_status()
                msg = "✅ Ollama 連線成功"

            elif body.provider == "anthropic":
                # Anthropic: 用最便宜的 model + 1 token 試
                resp = await client.post(
                    f"{base_url}/messages",
                    headers={
                        "x-api-key": body.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-3-haiku-20240307",
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "hi"}],
                    },
                )
                resp.raise_for_status()
                msg = "✅ Anthropic Claude 連線成功"

            else:
                # OpenAI / DeepSeek (相容 OpenAI 格式)
                model = _DEFAULT_MODEL.get(body.provider, "gpt-3.5-turbo")
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {body.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "hi"}],
                    },
                )
                resp.raise_for_status()
                msg = f"✅ {body.provider.capitalize()} 連線成功"

        elapsed_ms = int((_t.time() - start) * 1000)
        _last_test_result.update({
            "tested_at": _t.time(), "success": True,
            "error": None, "provider": body.provider,
        })
        return LlmTestResponse(success=True, message=msg, response_ms=elapsed_ms)

    except httpx.HTTPStatusError as e:
        # 401 = 錯 key / 403 = 權限 / 429 = quota
        err_map = {
            401: "API key 無效或已過期",
            403: "API key 沒有此 model 權限",
            429: "API quota 用完或被限速",
        }
        msg = err_map.get(e.response.status_code, f"HTTP {e.response.status_code}")
        detail = e.response.text[:200] if e.response.text else None
        _last_test_result.update({
            "tested_at": _t.time(), "success": False,
            "error": msg, "provider": body.provider,
        })
        return LlmTestResponse(success=False, message=f"❌ {msg}", detail=detail)

    except httpx.RequestError as e:
        msg = f"連線失敗：{type(e).__name__}（檢查網路 / base_url / SSL）"
        _last_test_result.update({
            "tested_at": _t.time(), "success": False,
            "error": msg, "provider": body.provider,
        })
        return LlmTestResponse(success=False, message=f"❌ {msg}", detail=str(e)[:200])

    except Exception as e:  # pylint: disable=broad-except
        log.exception("LLM test unexpected error")
        return LlmTestResponse(success=False, message="❌ 未預期錯誤", detail=str(e)[:200])


# ── 寫進 .env + 即時生效 ──────────────────────────────────
def _update_env_file(env_path: Path, updates: dict[str, str]) -> None:
    """讀 .env、替換 key=value、不存在就 append。保持其他 lines 不動。"""
    if not env_path.exists():
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text("")

    lines = env_path.read_text(encoding="utf-8").splitlines()
    remaining = dict(updates)

    new_lines: list[str] = []
    for line in lines:
        m = re.match(r"^([A-Z_][A-Z0-9_]*)=", line)
        if m and m.group(1) in remaining:
            key = m.group(1)
            new_lines.append(f"{key}={remaining.pop(key)}")
        else:
            new_lines.append(line)

    for key, val in remaining.items():
        new_lines.append(f"{key}={val}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


@router.post("/configure", response_model=LlmConfigureResponse)
async def llm_configure(
    body: LlmConfigureRequest,
    user: UserContext = Depends(require_permission("system.config.update")),
):
    """寫進 backend/.env + 即時更新 settings 記憶體（不需重啟）。"""
    base_url = body.base_url or _DEFAULT_BASE_URL.get(body.provider, "")
    model = body.model or _DEFAULT_MODEL.get(body.provider, "")

    # 寫磁碟（持久）
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    try:
        _update_env_file(env_path, {
            "LLM_PROVIDER": body.provider,
            "LLM_API_KEY": body.api_key,
            "LLM_BASE_URL": base_url,
            "LLM_MODEL": model,
            "LLM_VERIFY_SSL": "true" if body.verify_ssl else "false",
        })
    except OSError as e:
        log.error("Write .env failed: %s", e)
        raise HTTPException(500, f"寫 .env 失敗：{e}") from e

    # 即時更新記憶體（無需重啟即生效）
    settings.LLM_PROVIDER = body.provider
    settings.LLM_API_KEY = body.api_key
    settings.LLM_BASE_URL = base_url
    settings.LLM_MODEL = model
    settings.LLM_VERIFY_SSL = body.verify_ssl

    log.info("LLM configured by %s: provider=%s model=%s",
             getattr(user, "username", "?"), body.provider, model)

    return LlmConfigureResponse(
        saved=True,
        requires_restart=False,
        message=f"✅ 已儲存（即時生效）。Provider={body.provider}, Model={model}",
    )
