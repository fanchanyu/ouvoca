"""v3.60 G-510 tests — 外部 DB 連線加密儲存。

驗證：
  1. encrypt_json / decrypt_json round-trip + 密文不含明文
  2. DB 儲存的 config_encrypted 是密文（AES-GCM），資料庫裡看不到明文
  3. DB-backed connections service round-trip（register → get → list → delete）
"""
from __future__ import annotations

import json

import pytest
import pytest_asyncio

from app.core.crypto import decrypt_json, encrypt_json


@pytest_asyncio.fixture
async def db(client):
    # app 已啟動（client fixture）；每個 test 用獨立 AsyncSession
    from app.core.tenant_context import set_current_tenant
    from app.database import AsyncSessionLocal
    set_current_tenant("HQ")
    async with AsyncSessionLocal() as session:
        yield session


def test_crypto_roundtrip():
    data = {"host": "10.0.0.5", "user": "sa", "password": "SuperSecret!", "database": "erp"}
    cipher = encrypt_json(data)
    assert "SuperSecret" not in cipher, "密文不應含明文"
    assert "10.0.0.5" not in cipher
    assert decrypt_json(cipher) == data


def test_crypto_same_value_different_ciphertext():
    data = {"password": "x"}
    c1, c2 = encrypt_json(data), encrypt_json(data)
    assert c1 != c2, "每次加密應帶新 nonce（同值不得產生同密文）"
    assert decrypt_json(c1) == decrypt_json(c2) == data


def test_crypto_tamper_detected():
    cipher = encrypt_json({"password": "secret"})
    tampered = cipher[:-4] + ("AAAA" if not cipher.endswith("AAAA") else "BBBB")
    with pytest.raises(Exception):
        decrypt_json(tampered)


@pytest.mark.asyncio
async def test_db_connection_store_roundtrip(db):
    from sqlalchemy import select

    from app.models.external_connection import ExternalConnection
    from app.services.connections import (
        get_connection_info_db,
        list_connections_db,
        register_connection_db,
        unregister_connection_db,
    )

    await register_connection_db(
        db, "test_legacy_db", "sqlite",
        {"path": "/data/legacy.db", "password": "P@ssw0rd!"},
        description="測試連接",
        user={"employee_id": "e-g510"},
    )

    # 資料庫內必須是密文
    row = (await db.execute(
        select(ExternalConnection).where(ExternalConnection.name == "test_legacy_db")
    )).scalar_one_or_none()
    assert row is not None
    assert "P@ssw0rd" not in row.config_encrypted, "DB 內不得存明文密碼"

    # 解密讀回
    info = await get_connection_info_db(db, "test_legacy_db")
    assert info is not None
    assert info["config"]["password"] == "P@ssw0rd!"
    assert info["connector"] == "sqlite"

    # list 不含明文
    listing = await list_connections_db(db)
    entry = next(c for c in listing if c["name"] == "test_legacy_db")
    assert "P@ssw0rd" not in json.dumps(listing)
    assert entry["config_keys"] == sorted(["path", "password"])

    assert await unregister_connection_db(db, "test_legacy_db") is True
    assert await get_connection_info_db(db, "test_legacy_db") is None


def test_api_and_tools_registered(seeded_client):
    """管理 API + AI tool 應存在（grep smoke）。"""
    from pathlib import Path
    api_src = (Path(__file__).resolve().parents[2] / "app" / "api" /
               "external_connections.py").read_text(encoding="utf-8")
    assert "/api/external-connections" in api_src
    assert 'require_permission("external_db.connection.list")' in api_src
    assert 'require_permission("external_db.connection.write")' in api_src

    tools_src = (Path(__file__).resolve().parents[2] / "app" / "agents" / "domains" /
                 "external_db_tools.py").read_text(encoding="utf-8")
    assert "save_external_connection_with_confirm" in tools_src
    assert "delete_external_connection_with_confirm" in tools_src
