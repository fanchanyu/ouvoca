"""租戶上下文 — 把當前 request 的 tenant_id 注入到新建 ORM 物件中。

使用方式
--------
- 在 service / API 層，呼叫 `set_current_tenant(tenant_id)` 設定當前 tenant
- 任何 `db.add(SomeBusinessModel())` 時，會自動填入該 tenant_id
- 用 contextvar 確保 async 安全

如果未設定（如 demo / system 任務），預設為 "HQ"。
"""
from contextvars import ContextVar
from sqlalchemy import event

from app.core.logging import get_logger

log = get_logger(__name__)

# 用 ContextVar 確保 async/await 跨 task 安全
_current_tenant: ContextVar[str] = ContextVar("current_tenant", default="HQ")


def set_current_tenant(tenant_id: str) -> None:
    _current_tenant.set(tenant_id or "HQ")


def get_current_tenant() -> str:
    return _current_tenant.get()


def install_tenant_auto_injection():
    """掛上 SQLAlchemy event listener — 新建物件自動帶 tenant_id。

    僅對含 tenant_id 欄位的 model 生效（透過 TenantMixin 引入）。
    若呼叫方已顯式設定，不覆蓋。
    """
    from app.core.base import Base

    @event.listens_for(Base, "init", propagate=True)
    def _on_init(target, args, kwargs):
        if hasattr(target.__class__, "tenant_id") and "tenant_id" not in kwargs:
            current = _current_tenant.get()
            if current:
                kwargs["tenant_id"] = current

    log.debug("Tenant auto-injection installed on SQLAlchemy Base")
