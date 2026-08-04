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
    Routing, RoutingStep,  # v3.26: capacity-aware MRP routing master
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
from app.models.attachment import Attachment, ATTACHMENT_CATEGORIES
from app.models.approval_workflow import (
    ApprovalRule, ApprovalRequestV2, ApprovalStepV2,
)
from app.models.policy_rule import (
    PolicyRule, PolicyAuditLog,
    POLICY_TRIGGERS, POLICY_CONDITION_TYPES, POLICY_ACTIONS,
)
# v3.32 進銷存深化
from app.models.quotation import Quotation, QuotationItem
from app.models.stock_count import StockCount, StockCountItem
from app.models.external_connection import ExternalConnection  # v3.60 — G-510
from app.models.document_numbering import DocumentNumbering  # v3.60 — Phase C1 集中編號
from app.models.finance import (  # v3.60 — Phase B1 金流閉環
    BankAccount, AccountsPayable, Payment, Receipt,
)
from app.models.finance import (  # v3.61 — M2 財務閉環
    SupplierInvoice, SupplierInvoiceItem, PromissoryNote, FixedAsset,
)
from app.models.documents_m3 import (  # v3.63 — M3 表單工程
    PurchaseRequisition, PurchaseRequisitionItem,
    GoodsReceiptNote, GoodsReceiptNoteItem,
    MaterialIssue, MaterialIssueItem,
    ReturnNote, ReturnNoteItem,
)
from app.models.traceability import (  # v3.64 — 批號/序號追溯
    BatchLot, SerialNumber,
)
from app.models.rfq import (  # v3.64 — RFQ 詢價比價
    RFQ, RFQItem, SupplierQuote, SupplierQuoteItem,
)

__all__ = ["Base"]
from app.models.glossary import GlossaryItem  # v3.46
from app.models.tax_tw import EInvoiceRecord  # v3.54 — Taiwan e-invoice persistence
from app.models.delivery import DeliveryNote, DeliveryNoteItem  # v3.55 — O2C chain
from app.models.system_setting import SystemSetting  # v006 (M1) — 系統組態
