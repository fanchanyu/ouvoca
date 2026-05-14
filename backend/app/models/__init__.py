"""Model package — all models share a single Base from app.core.base."""
from app.core.base import Base

from app.models.organization import (
    Department, Employee, User, Role, Permission,
    ApprovalFlow, ApprovalRequest, ApprovalRecord,
    employee_roles, role_permissions, EmployeeRoleType,
)
from app.models.inventory import (
    Part, Inventory, InventoryTransaction, InventoryTransfer,
    UnitOfMeasure, PartCategory,
)
from app.models.purchase import (
    Supplier, PurchaseOrder, PurchaseOrderItem,
    SupplierPrice, SupplierEvaluation,
)
from app.models.product import Product, BOMItem
from app.models.production import (
    ProductionOrder, WorkCenter, Operation, DispatchLog,
)
from app.models.mps_mrp import (
    MpsMaster, MpsEntry, TimeFence, MrpMaster, MrpItem,
)
from app.models.quality import (
    InspectionOrder, InspectionResult, NonConformance, CAPARecord,
)
from app.models.accounting import (
    Account, JournalEntry, JournalLine, AccountsReceivable, MonthEndClose,
)
from app.models.crm_sales import (
    Customer, SalesOrder, SalesOrderItem, Lead, Opportunity,
    Contract, ContractPricing, CrmEvent,
)
from app.models.warehouse import (
    WarehouseZone, BinLocation, PickTask, CycleCount,
)
from app.models.supplier_plus import (
    ReorderRule, ReplenishSuggestion,
)
from app.models.ai_governance import (
    ConversationLog, AuditLog, DecisionLog,
    AfterActionReview, FactoryConfig,
)
from app.models.permission import (
    Tenant, PermissionDef, RoleDef,
    RolePermissionLink, UserRoleAssignment, PermissionOverride,
    RowFilter, PermissionAudit,
)

__all__ = ["Base"]
