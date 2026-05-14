"""
MESH (多廠協同) HQ-side endpoints.

設計原則：
1. HQ 持有「廠別註冊表」(in-memory + optional DB persist)
2. Factory node 上線時 POST /api/factory/register 自報
3. HQ 用 /api/factory/aggregate 平行 fan-out 到所有廠、聚合回應
4. **HQ 永遠只收聚合數字**（total/sum/count），不收原始 row

⚠️  生產環境注意：
- 註冊驗證：建議搭配 mTLS 或 shared secret，避免有人冒充註冊
- 聚合超時：預設 5 秒，超時的廠視為離線
- factory 端必須回傳「聚合數字」格式（防止資料外流到 HQ）
"""
from __future__ import annotations
import asyncio
import time
from typing import Any
from dataclasses import dataclass, field, asdict

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.logging import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/api/factory", tags=["MESH"])


# ─── In-memory registry ─────────────────────────────────────
# 生產要持久化到 FactoryConfig DB table；MVP 用 in-memory 就夠。
@dataclass
class FactoryRecord:
    factory_id: str
    name: str
    endpoint: str
    registered_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    healthy: bool = True


_registry: dict[str, FactoryRecord] = {}


# ─── Schemas ────────────────────────────────────────────────
class FactoryRegisterRequest(BaseModel):
    factory_id: str
    name: str
    endpoint: str  # e.g. http://factory-a:8001


class FactoryInfo(BaseModel):
    factory_id: str
    name: str
    endpoint: str
    healthy: bool
    last_seen_seconds_ago: float


class AggregateResponse(BaseModel):
    domain: str
    query: dict
    total: float
    per_factory: dict  # {factory_id: number | None (if offline)}
    factories_queried: int
    factories_responded: int
    elapsed_ms: int


# ─── Endpoints ──────────────────────────────────────────────
@router.post("/register", response_model=FactoryInfo)
async def register_factory(req: FactoryRegisterRequest):
    """Factory node 上線時呼叫，HQ 記下端點以後可以查它。
    冪等：同一個 factory_id 重複註冊 = 更新 endpoint + last_seen。
    """
    rec = _registry.get(req.factory_id)
    if rec is None:
        rec = FactoryRecord(
            factory_id=req.factory_id,
            name=req.name,
            endpoint=req.endpoint,
        )
        _registry[req.factory_id] = rec
        log.info("Factory registered: %s (%s)", req.factory_id, req.endpoint)
    else:
        rec.name = req.name
        rec.endpoint = req.endpoint
        rec.last_seen = time.time()
        rec.healthy = True
        log.info("Factory re-registered: %s", req.factory_id)

    return FactoryInfo(
        factory_id=rec.factory_id, name=rec.name, endpoint=rec.endpoint,
        healthy=rec.healthy,
        last_seen_seconds_ago=time.time() - rec.last_seen,
    )


@router.get("/list", response_model=list[FactoryInfo])
async def list_factories():
    """列出所有已註冊的 factory node。"""
    now = time.time()
    return [
        FactoryInfo(
            factory_id=r.factory_id, name=r.name, endpoint=r.endpoint,
            healthy=r.healthy,
            last_seen_seconds_ago=now - r.last_seen,
        )
        for r in _registry.values()
    ]


@router.delete("/{factory_id}")
async def unregister_factory(factory_id: str):
    """取消註冊（factory 下線或 admin 手動移除）。"""
    if factory_id not in _registry:
        raise HTTPException(404, f"factory_id={factory_id} 不存在")
    del _registry[factory_id]
    return {"detail": f"{factory_id} unregistered"}


@router.post("/aggregate", response_model=AggregateResponse)
async def aggregate(
    domain: str = Query(..., description="要查詢的 domain，如 inventory"),
    part_no: str | None = Query(None, description="可選：限定某零件"),
    timeout_seconds: float = Query(5.0, ge=0.5, le=30.0),
):
    """
    跨廠聚合查詢的核心 endpoint。

    流程：
    1. 平行 fan-out 到所有 healthy 廠
    2. 每廠回傳「該廠的聚合數字」（不是原始 row）
    3. HQ 加總後回傳

    回傳：total、per_factory 明細、響應廠數。
    """
    if not _registry:
        raise HTTPException(404, "尚無 factory 註冊，無法聚合")

    t0 = time.time()

    async def _query_one(rec: FactoryRecord) -> tuple[str, float | None]:
        """從單一廠拿聚合數字。連不上回 None。"""
        url = f"{rec.endpoint}/api/factory/mesh/query"
        params = {"domain": domain, "agg": "sum"}
        if part_no:
            params["part_no"] = part_no
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                r = await client.get(url, params=params)
            if r.status_code != 200:
                log.warning("factory %s returned %d", rec.factory_id, r.status_code)
                rec.healthy = False
                return (rec.factory_id, None)
            data = r.json()
            rec.last_seen = time.time()
            rec.healthy = True
            # factory 回傳結構：{factory_id, domain, query, results: {total, items}}
            total = float(data.get("results", {}).get("total", 0))
            return (rec.factory_id, total)
        except Exception as e:
            log.warning("factory %s unreachable: %s", rec.factory_id, e)
            rec.healthy = False
            return (rec.factory_id, None)

    # fan-out
    targets = list(_registry.values())
    results = await asyncio.gather(*(_query_one(r) for r in targets))

    per_factory = dict(results)
    responded = sum(1 for v in per_factory.values() if v is not None)
    total = sum(v for v in per_factory.values() if v is not None)
    elapsed_ms = int((time.time() - t0) * 1000)

    return AggregateResponse(
        domain=domain,
        query={"part_no": part_no} if part_no else {},
        total=total,
        per_factory=per_factory,
        factories_queried=len(targets),
        factories_responded=responded,
        elapsed_ms=elapsed_ms,
    )


# ─── 測試/開發輔助 ─────────────────────────────────────────
@router.post("/_reset", include_in_schema=False)
async def _reset():
    """測試用：清空註冊表。"""
    _registry.clear()
    return {"detail": "registry cleared"}
