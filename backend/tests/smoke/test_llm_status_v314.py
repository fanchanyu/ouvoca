"""
Smoke: LLM status / configure（Sprint H v3.14）

驗收：
  - /api/llm/status 永遠回（公開）
  - 未設 key 時 configured=false
  - configure 寫進 .env 後即時生效（status 變 true、聊天 OK）
  - test 不存 key，純試打
  - chat 在沒 key 時回 setup_required=true 結構化 flag（非 raw error）
"""
from __future__ import annotations

from pathlib import Path

import pytest


def test_status_public_when_no_key(seeded_client, admin_headers):
    """登入後查 /api/llm/status 應該回有效 schema（不爆）。"""
    r = seeded_client.get("/api/llm/status", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert "configured" in body
    assert "provider" in body
    assert body["provider"] in ("deepseek", "openai", "anthropic", "ollama")


def test_chat_returns_setup_required_when_no_key(seeded_client, admin_headers, monkeypatch):
    """v3.14 重點：沒 key 時 chat 回結構化 setup_required，前端 render 引導卡。"""
    from app.config import settings

    # 模擬沒設 key（測試 fixture 預設可能有設）
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    monkeypatch.setattr(settings, "LLM_PROVIDER", "deepseek")

    r = seeded_client.post(
        "/api/chat-v2",
        headers=admin_headers,
        json={"message": "列出庫存", "session_id": "test-no-key"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("setup_required") is True
    assert body.get("setup_reason") == "no_api_key"
    # 回覆要友善 / 帶引導文字
    assert "AI" in body["reply"] or "啟用" in body["reply"]


def test_configure_writes_env_and_updates_settings(seeded_client, admin_headers, tmp_path, monkeypatch):
    """configure 寫進 .env + 即時更新 settings 記憶體。"""
    from app.api import llm_status as ls
    from app.config import settings

    # 重導向 .env 路徑到 tmp（避免測試污染真 env）
    fake_env = tmp_path / ".env"
    original_path_calc = ls._update_env_file

    def fake_writer(path, updates):
        original_path_calc(fake_env, updates)

    monkeypatch.setattr(ls, "_update_env_file", fake_writer)

    r = seeded_client.post(
        "/api/llm/configure",
        headers=admin_headers,
        json={
            "provider": "deepseek",
            "api_key": "sk-test-key-12345678",
            "verify_ssl": False,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["saved"] is True
    # 即時生效
    assert settings.LLM_API_KEY == "sk-test-key-12345678"
    assert settings.LLM_PROVIDER == "deepseek"
    assert settings.LLM_VERIFY_SSL is False
    # 寫進磁碟
    env_content = fake_env.read_text(encoding="utf-8")
    assert "LLM_API_KEY=sk-test-key-12345678" in env_content
    assert "LLM_VERIFY_SSL=false" in env_content


def test_unauthorized_configure_rejected(seeded_client):
    """無 token 不能改設定。"""
    r = seeded_client.post(
        "/api/llm/configure",
        json={"provider": "deepseek", "api_key": "x"},
    )
    assert r.status_code == 401


def test_status_returns_correct_provider(seeded_client, admin_headers, monkeypatch):
    """改了 settings 後，status 也要反映。"""
    from app.config import settings

    monkeypatch.setattr(settings, "LLM_PROVIDER", "anthropic")
    monkeypatch.setattr(settings, "LLM_MODEL", "claude-3-5-sonnet")

    r = seeded_client.get("/api/llm/status", headers=admin_headers)
    body = r.json()
    assert body["provider"] == "anthropic"
    assert body["model"] == "claude-3-5-sonnet"
