"""Sensitive-value encryption helpers (G-510 — 外部 DB 連線資訊加密儲存).

使用 AES-256-GCM：
  - 金鑰優先取 settings.CONNECTION_ENCRYPTION_KEY（hex 32 bytes 或任意字串），
    未設定時從 JWT_SECRET SHA-256 衍生（向後相容；正式環境建議設專用 key）。
  - 每個密文帶獨立 12-byte nonce，重複加密同值不會得到相同密文。
  - 密文格式：base64(nonce || ciphertext || tag)。

用途：
  - external_connections.config_encrypted（連線字串含 DB 帳密，禁止明文落庫）
  - 未來其它敏感設定（SMTP 密碼、API token…）比照辦理。
"""
from __future__ import annotations

import base64
import hashlib
import json
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings


def _encryption_key() -> bytes:
    """取得 32-byte AES-256 金鑰。"""
    raw = (settings.CONNECTION_ENCRYPTION_KEY or "").strip()
    if raw:
        # 64 hex chars = 32 bytes；否則視為任意字串用 SHA-256 收斂
        if len(raw) == 64:
            try:
                return bytes.fromhex(raw)
            except ValueError:
                pass
        return hashlib.sha256(raw.encode("utf-8")).digest()
    # 未設定專用 key → 從 JWT_SECRET 衍生（向後相容；production 建議設專用 key）
    return hashlib.sha256(settings.JWT_SECRET.encode("utf-8")).digest()


def encrypt_json(data: dict) -> str:
    """把 dict 序列化 + AES-GCM 加密，回傳 base64 字串。"""
    nonce = os.urandom(12)
    plaintext = json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ciphertext = AESGCM(_encryption_key()).encrypt(nonce, plaintext, None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt_json(payload: str) -> dict:
    """解密 encrypt_json 的產物，回傳原始 dict。"""
    raw = base64.b64decode(payload)
    if len(raw) < 12:
        raise ValueError("ciphertext too short")
    nonce, ciphertext = raw[:12], raw[12:]
    plaintext = AESGCM(_encryption_key()).decrypt(nonce, ciphertext, None)
    return json.loads(plaintext.decode("utf-8"))
