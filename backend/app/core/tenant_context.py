"""租戶上下文 — 兩道防線：
  ① 寫入：任何新建 TenantMixin 物件都自動帶當前 tenant_id
  ② 讀取：任何 SELECT 帶 TenantMixin 的 model 都自動加 WHERE tenant_id = X

寫入靠 ORM `init` event；讀取靠 `do_orm_execute` event + with_loader_criteria。

bypass 機制：
  - set_current_tenant("*") 或 ALL_TENANTS = 跨租戶查詢（給 MESH aggregate / system seed）
  - execution_options(skip_tenant_filter=True) = 該 query 特定跳過
"""
from contextvars import ContextVar
from sqlalchemy import event
from sqlalchemy.orm import with_loader_criteria, Session

from app.core.logging import get_logger

log = get_logger(__name__)

# 特殊值：'*' = 跨租戶（system / cross-tenant 用）；其他值 = 該租戶
ALL_TENANTS = "*"

# 用 ContextVar 確保 async/await 跨 task 安全
_current_tenant: ContextVar[str] = ContextVar("current_tenant", default="HQ")


def set_current_tenant(tenant_id: str) -> None:
    _current_tenant.set(tenant_id or "HQ")


def get_current_tenant() -> str:
    return _current_tenant.get()


def install_tenant_auto_injection():
    """寫入防線：新建 TenantMixin 物件自動填 tenant_id。"""
    from app.core.base import Base

    @event.listens_for(Base, "init", propagate=True)
    def _on_init(target, args, kwargs):
        if hasattr(target.__class__, "tenant_id") and "tenant_id" not in kwargs:
            current = _current_tenant.get()
            if current and current != ALL_TENANTS:
                kwargs["tenant_id"] = current

    log.debug("Tenant auto-injection (write) installed")


def install_auto_tenant_filter():
    """讀取防線：所有 SELECT 自動加 WHERE Cls.tenant_id == current_tenant。

    覆蓋所有走 ORM SELECT 的 TenantMixin 子類別 — 不需要手動在每個 endpoint
    呼叫 apply_tenant_filter()。

    跳過時機：
      1. 當前 tenant = ALL_TENANTS（'*'）→ 跨租戶查詢
      2. 該 query 帶 execution_options(skip_tenant_filter=True)
      3. session._tenant_filter_bypass = True（contextual bypass）
    """
    from app.models._mixins import TenantMixin

    @event.listens_for(Session, "do_orm_execute")
    def _add_tenant_filter(execute_state):
        # 只攔截 SELECT（不影響 INSERT/UPDATE/DELETE）
        if not execute_state.is_select:
            return
        # 跳過 relationship lazy/eager load（with_loader_criteria 對它們的處理另有規則）
        if execute_state.is_relationship_load:
            return
        # 跳過顯式 opt-out
        if execute_state.execution_options.get("skip_tenant_filter"):
            return

        tenant = _current_tenant.get()
        # ALL_TENANTS = 跨租戶（system / MESH aggregate / seed）
        if not tenant or tenant == ALL_TENANTS:
            return

        # 對所有 TenantMixin 子類別自動加 WHERE
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(
                TenantMixin,
                lambda cls: cls.tenant_id == tenant,
                include_aliases=True,
            )
        )

    log.debug("Auto tenant filter (read) installed")
