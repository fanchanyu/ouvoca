"""病毒掃描掛鉤（審計 P2）— 外部 AV 服務整合點。

設定 AV_SCAN_URL（如 ClamAV REST / clamd）後，上傳檔案會先送掃描；
未設定時回 None（no-op，不擋上傳）。掃到病毒回 {"infected": True}。
"""
from __future__ import annotations

from typing import Optional

import httpx

from app.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


async def scan_bytes(content: bytes, filename: str = "") -> Optional[dict]:
    """掃描檔案內容。回 None = 未設定 AV（不擋）；回 dict = 掃描結果。"""
    url = (settings.AV_SCAN_URL or "").strip()
    if not url:
        return None
    try:
        async with httpx.AsyncClient(timeout=settings.AV_SCAN_TIMEOUT) as client:
            resp = await client.post(
                url,
                files={"file": (filename or "upload", content)},
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "infected": bool(data.get("infected")),
                "virus_name": data.get("virus_name"),
                "scanner": data.get("scanner", "external"),
            }
    except Exception as exc:
        # 掃描服務掛掉：保守起見記錄警告，不擋上傳（可改為 fail-closed 設定）
        log.warning("AV scan failed (uploads allowed): %s", exc)
        return {"infected": False, "error": str(exc), "fail_open": True}
