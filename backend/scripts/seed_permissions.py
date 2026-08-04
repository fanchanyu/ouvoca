"""Seed RBAC tables：~168 個權限 + 10 個預設角色 + 1 個 HQ tenant。

v3.50 (2026-05-24)：
- UPSERT 取代 skip-if-exists（既有部署重新跑 seed 也會拿到新權限/描述）
- 新增 EXTRA_PERMISSIONS 處理 2 段別名（accounting.tax_report, analytics.view, system.admin）
- 補齊 ~20 個 require_permission() 用到但漏定義的權限碼

v3.56 (M1-0.2, 2026-08-04)：
- 依 scripts/audit_permission_codes.py 實測（160 引用 vs 137 seed，MISSING 60）
  補齊 53 個權限碼：approval.* / tax.* / inventory.count.* / sales.quotation.* /
  crm.*.list / production.wo.* / production.workcenter.list / sales.so.update /
  crm.customer.read / accounting.ap.* / accounting.payment|receipt.record /
  dashboard.read 等。alias 對照見 backend/data/permission_alias.json。

Usage:
    python -m scripts.seed_permissions
    # 或在主 seed 中呼叫 seed_permissions()
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime

if __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import AsyncSessionLocal, init_db
from app.models.permission import (
    Tenant, PermissionDef, RoleDef, RolePermissionLink, RowFilter,
)


# ============================================================
# 95 個權限定義
# ============================================================
# (module, resource, action, name_zh, is_sensitive, risk_level)
PERMISSIONS: list[tuple[str, str, str, str, bool, str]] = [
    # --- inventory (12) ---
    ("inventory", "part", "read", "查看零件", False, "low"),
    ("inventory", "part", "list", "列出零件", False, "low"),
    ("inventory", "part", "create", "建立零件", False, "medium"),
    ("inventory", "part", "update", "修改零件", False, "medium"),
    ("inventory", "part", "delete", "刪除零件", True, "high"),
    ("inventory", "part", "export", "匯出零件", False, "low"),
    ("inventory", "transaction", "read", "查看庫存交易", False, "low"),
    ("inventory", "transaction", "list", "列出庫存交易", False, "low"),
    ("inventory", "transaction", "create", "建立庫存交易", False, "medium"),
    ("inventory", "transaction", "export", "匯出庫存交易", False, "low"),
    ("inventory", "inventory", "read", "查看庫存", False, "low"),
    ("inventory", "inventory", "adjust", "庫存調整", True, "high"),
    # M1-0.2：盤點五操作（audit MISSING）
    ("inventory", "count", "read", "查看盤點", False, "low"),
    ("inventory", "count", "create", "建立盤點", False, "medium"),
    ("inventory", "count", "record", "盤點記錄", False, "medium"),
    ("inventory", "count", "adjust", "盤點調整", True, "high"),
    ("inventory", "count", "cancel", "取消盤點", True, "high"),

    # --- purchase (11) ---
    ("purchase", "supplier", "read", "查看供應商", False, "low"),
    ("purchase", "supplier", "list", "列出供應商", False, "low"),
    ("purchase", "supplier", "create", "建立供應商", False, "medium"),
    ("purchase", "supplier", "update", "修改供應商", False, "medium"),
    ("purchase", "supplier", "delete", "刪除供應商", True, "high"),
    ("purchase", "order", "read", "查看採購單", False, "low"),
    ("purchase", "order", "list", "列出採購單", False, "low"),
    ("purchase", "order", "create", "建立採購單", False, "medium"),
    ("purchase", "order", "update", "修改採購單", False, "medium"),
    ("purchase", "order", "approve", "簽核採購單", True, "high"),
    ("purchase", "order", "receive", "收貨", False, "medium"),
    # M1-0.2：取消/單價查詢（audit MISSING）
    ("purchase", "order", "cancel", "取消採購單", False, "medium"),
    ("purchase", "price", "read", "查看進貨單價", False, "low"),
    # M1-0.2：po 短名變體（alias 見 permission_alias.json；po.update 為既有）
    ("purchase", "po", "create", "建立採購單（po 別名）", False, "medium"),
    ("purchase", "po", "approve", "簽核採購單（po 別名）", True, "high"),
    ("purchase", "po", "read", "查看採購單（po 別名）", False, "low"),

    # --- production (16) ---
    ("production", "product", "read", "查看產品", False, "low"),
    ("production", "product", "list", "列出產品", False, "low"),
    ("production", "product", "create", "建立產品", False, "medium"),
    ("production", "product", "update", "修改產品", False, "medium"),
    ("production", "product", "delete", "刪除產品", True, "high"),
    ("production", "bom", "read", "查看 BOM", False, "low"),
    ("production", "bom", "create", "建立 BOM", False, "medium"),
    ("production", "bom", "update", "修改 BOM", True, "high"),
    ("production", "work_order", "read", "查看工單", False, "low"),
    ("production", "work_order", "list", "列出工單", False, "low"),
    ("production", "work_order", "create", "建立工單", False, "medium"),
    ("production", "work_order", "release", "釋放工單", False, "medium"),
    ("production", "work_order", "complete", "完工工單", False, "medium"),
    ("production", "work_center", "list", "列出工作中心", False, "low"),
    ("production", "work_center", "create", "建立工作中心", False, "medium"),
    ("production", "operation", "create", "建立工序", False, "medium"),
    ("production", "dispatch", "create", "建立派工", False, "medium"),
    ("production", "work_order", "update", "修改工單", False, "medium"),
    # M1-0.2：audit MISSING（含 wo/workcenter 短名變體，alias 見 permission_alias.json）
    ("production", "bom", "delete", "刪除 BOM", True, "high"),
    ("production", "work_order", "cancel", "取消工單", False, "medium"),
    ("production", "workcenter", "list", "列出工作中心（別名）", False, "low"),
    ("production", "wo", "read", "查看工單（別名）", False, "low"),
    ("production", "wo", "update", "修改工單（別名）", False, "medium"),

    # --- sales (11) ---
    ("sales", "customer", "read", "查看客戶", False, "low"),
    ("sales", "customer", "list", "列出客戶", False, "low"),
    ("sales", "customer", "create", "建立客戶", False, "medium"),
    ("sales", "customer", "update", "修改客戶", False, "medium"),
    ("sales", "customer", "delete", "刪除客戶", True, "high"),
    ("sales", "order", "read", "查看銷售訂單", False, "low"),
    ("sales", "order", "list", "列出銷售訂單", False, "low"),
    ("sales", "order", "create", "建立銷售訂單", False, "medium"),
    ("sales", "order", "confirm", "確認銷售訂單", False, "medium"),
    ("sales", "order", "ship", "出貨", False, "medium"),
    ("sales", "order", "export", "匯出銷售資料", False, "low"),
    ("sales", "order", "update", "修改銷售訂單", False, "medium"),
    # M1-0.2：audit MISSING（含 quotation 五操作 / so 短名變體）
    ("sales", "order", "cancel", "取消銷售訂單", False, "medium"),
    ("sales", "quotation", "create", "建立報價單", False, "medium"),
    ("sales", "quotation", "read", "查看報價單", False, "low"),
    ("sales", "quotation", "update", "修改報價單", False, "medium"),
    ("sales", "quotation", "send", "寄送報價單", False, "medium"),
    ("sales", "quotation", "cancel", "取消報價單", False, "medium"),
    ("sales", "so", "update", "修改銷售訂單（別名）", False, "medium"),

    # --- quality (7) ---
    ("quality", "inspection", "read", "查看檢驗", False, "low"),
    ("quality", "inspection", "list", "列出檢驗", False, "low"),
    ("quality", "inspection", "create", "建立檢驗", False, "medium"),
    ("quality", "inspection", "complete", "完成檢驗", False, "medium"),
    ("quality", "nc", "read", "查看不良品", False, "low"),
    ("quality", "nc", "list", "列出不良品", False, "low"),
    ("quality", "capa", "create", "建立 CAPA", False, "medium"),
    # M1-0.2：audit MISSING（ncr 別名組見 permission_alias.json）
    ("quality", "capa", "list", "列出 CAPA", False, "low"),
    ("quality", "ncr", "create", "建立不良紀錄", False, "medium"),
    ("quality", "ncr", "read", "查看不良紀錄", False, "low"),

    # --- accounting (10 + 8 補) ---
    ("accounting", "account", "read", "查看科目", False, "low"),
    ("accounting", "account", "list", "列出科目", False, "low"),
    ("accounting", "account", "create", "建立科目", False, "medium"),
    ("accounting", "account", "update", "修改科目", False, "medium"),
    ("accounting", "journal", "read", "查看傳票", False, "medium"),
    ("accounting", "journal", "list", "列出傳票", False, "medium"),
    ("accounting", "journal", "create", "建立傳票", True, "high"),
    ("accounting", "journal", "post", "傳票過帳", True, "critical"),
    ("accounting", "journal", "export", "匯出傳票", True, "high"),
    ("accounting", "ar", "read", "查看應收", False, "medium"),
    ("accounting", "ar", "list", "列出應收", False, "medium"),
    ("accounting", "ar", "create", "建立應收", False, "medium"),
    ("accounting", "month_close", "execute", "月結結帳", True, "critical"),
    ("accounting", "tax_report", "read", "查看稅務報表", False, "medium"),
    ("accounting", "einvoice", "read", "查看電子發票", False, "low"),
    ("accounting", "einvoice", "issue", "開立電子發票", True, "high"),
    ("accounting", "einvoice", "cancel", "作廢電子發票", True, "high"),
    # M1-0.2：audit MISSING（AP/月結查詢/收付款/刪科目）
    ("accounting", "account", "delete", "刪除科目", True, "high"),
    ("accounting", "month_close", "read", "查看月結狀態", False, "medium"),
    ("accounting", "payment", "record", "記錄付款", True, "high"),
    ("accounting", "receipt", "record", "記錄收款", True, "high"),

    # --- warehouse (6 + 6 補) ---
    ("warehouse", "zone", "read", "查看倉區", False, "low"),
    ("warehouse", "zone", "list", "列出倉區", False, "low"),
    ("warehouse", "zone", "create", "建立倉區", False, "medium"),
    ("warehouse", "zone", "update", "修改倉區", False, "medium"),
    ("warehouse", "zone", "delete", "刪除倉區", True, "high"),
    ("warehouse", "bin", "read", "查看儲位", False, "low"),
    ("warehouse", "bin", "list", "列出儲位", False, "low"),
    ("warehouse", "bin", "create", "建立儲位", False, "medium"),
    ("warehouse", "pick", "create", "建立揀貨", False, "medium"),
    ("warehouse", "pick", "complete", "完成揀貨", False, "medium"),
    ("warehouse", "cycle_count", "create", "盤點", False, "medium"),
    # M1-0.2：audit MISSING（揀貨/循環盤點查詢）
    ("warehouse", "pick", "list", "列出揀貨", False, "low"),
    ("warehouse", "pick", "read", "查看揀貨", False, "low"),
    ("warehouse", "cycle_count", "list", "列出循環盤點", False, "low"),

    # --- crm (5) ---
    ("crm", "lead", "read", "查看潛在客戶", False, "low"),
    ("crm", "lead", "create", "建立潛在客戶", False, "medium"),
    ("crm", "opportunity", "read", "查看商機", False, "low"),
    ("crm", "opportunity", "create", "建立商機", False, "medium"),
    ("crm", "opportunity", "change_stage", "變更商機階段", False, "medium"),
    # M1-0.2：audit MISSING（list 系 + customer 別名）
    ("crm", "lead", "list", "列出潛在客戶", False, "low"),
    ("crm", "opportunity", "list", "列出商機", False, "low"),
    ("crm", "event", "list", "列出客戶事件", False, "low"),
    ("crm", "customer", "read", "查看客戶（別名）", False, "low"),

    # --- mps_mrp (4) ---
    ("mps_mrp", "mps", "read", "查看 MPS", False, "low"),
    ("mps_mrp", "mps", "create", "建立 MPS", False, "medium"),
    ("mps_mrp", "mrp", "read", "查看 MRP", False, "low"),
    ("mps_mrp", "mrp", "run", "執行 MRP 計算", False, "medium"),
    # M1-0.2：audit MISSING
    ("mps_mrp", "mps", "list", "列出 MPS", False, "low"),
    ("mps_mrp", "mrp", "list", "列出 MRP", False, "low"),
    ("mps_mrp", "master", "create", "建立 MPS/MRP 主檔", False, "medium"),
    ("mps_mrp", "master", "read", "查看 MPS/MRP 主檔", False, "low"),

    # --- outsource (v3.0 移除：外協 persona 砍掉) ---

    # --- organization (8 + 2 補) ---
    ("organization", "employee", "read", "查看員工", False, "low"),
    ("organization", "employee", "list", "列出員工", False, "low"),
    ("organization", "employee", "create", "建立員工", True, "high"),
    ("organization", "employee", "update", "修改員工", True, "high"),
    ("organization", "role", "read", "查看角色", False, "low"),
    ("organization", "role", "list", "列出角色", False, "low"),
    ("organization", "role", "create", "建立角色", True, "high"),
    ("organization", "role", "update", "修改角色", True, "high"),
    ("organization", "user", "read", "查看使用者帳號", True, "medium"),
    ("organization", "user", "create", "建立使用者帳號", True, "high"),
    ("organization", "user", "update", "修改使用者帳號", True, "high"),

    # --- system (8 + 2 補) ---
    ("system", "config", "read", "查看系統設定", False, "medium"),
    ("system", "config", "update", "修改系統設定", True, "critical"),
    ("system", "tenant", "create", "建立租戶", True, "critical"),
    ("system", "tenant", "list", "列出租戶", False, "low"),
    ("system", "permission", "read", "查看權限定義", False, "low"),
    ("system", "permission", "list", "列出權限定義", False, "low"),
    ("system", "permission", "grant", "授權", True, "critical"),
    ("system", "permission", "revoke", "撤權", True, "critical"),
    ("system", "admin", "all", "系統最高管理（全權）", True, "critical"),
    # M1-0.2：audit MISSING
    ("system", "health", "read", "系統健康檢查", False, "low"),

    # --- approval (M1-0.2：整族新增，audit MISSING) ---
    ("approval", "request", "read", "查看審批單", True, "high"),
    ("approval", "request", "approve", "核准審批單", True, "high"),
    ("approval", "request", "reject", "退回審批單", True, "high"),

    # --- tax (M1-0.2：整族新增；accounting.einvoice.* 為 legacy，alias 見 permission_alias.json) ---
    ("tax", "einvoice", "issue", "開立電子發票（tax 別名）", True, "high"),
    ("tax", "einvoice", "read", "查看電子發票（tax 別名）", False, "low"),
    ("tax", "einvoice", "void", "作廢電子發票（tax 別名）", True, "high"),
    ("tax", "tax_id", "validate", "驗證統一編號", False, "low"),
    ("tax", "report", "read", "查詢稅務報表", False, "medium"),

    # --- audit / chat / permission / user (M1-0.2 新模組) ---
    ("audit", "log", "read", "查看稽核日誌", True, "high"),
    ("chat", "history", "read", "查看對話紀錄", False, "low"),
    ("permission", "role", "read", "查看角色權限", False, "low"),
    ("permission", "role", "assign", "指派角色權限", True, "critical"),
    ("user", "profile", "read", "查看個人資料", False, "medium"),

    # --- ai (2) ---
    ("ai", "agent", "use", "使用 AI 助手", False, "low"),
    ("ai", "agent", "configure", "設定 AI 助手", True, "high"),

    # --- mesh (3 + 3 補) ---
    ("mesh", "factory", "read", "查看廠別", False, "low"),
    ("mesh", "factory", "list", "列出廠別", False, "low"),
    ("mesh", "factory", "query", "跨廠查詢", False, "medium"),
    ("mesh", "factory", "register", "註冊廠別節點", True, "high"),
    ("mesh", "factory", "delete", "刪除廠別節點", True, "critical"),
    ("mesh", "factory", "manage", "管理 MESH 廠別", True, "high"),

    # --- analytics (4) ---
    ("analytics", "view", "read", "查看分析儀表板", False, "low"),
    ("analytics", "view", "all", "查看全部分析（跨部門）", False, "medium"),

    # --- purchase 擴充：purchase.po.update（call-site 既有） ---
    ("purchase", "po", "update", "修改採購單（po 別名）", False, "medium"),
]


# ------------------------------------------------------------
# 額外權限：不符合 module.resource.action 3 段格式的舊呼叫點
# （e.g. accounting.tax_report, analytics.view, system.admin 為 2 段）
# 用 dict 顯式指定 code，避免破壞 call-sites。
# ------------------------------------------------------------
EXTRA_PERMISSIONS: list[dict] = [
    {"code": "accounting.tax_report", "module": "accounting", "resource": "accounting.tax_report",
     "action": "read", "name_zh": "稅務報表（2 段別名）",
     "is_sensitive": False, "risk_level": "medium"},
    {"code": "analytics.view", "module": "analytics", "resource": "analytics.view",
     "action": "read", "name_zh": "分析儀表（2 段別名）",
     "is_sensitive": False, "risk_level": "low"},
    {"code": "system.admin", "module": "system", "resource": "system.admin",
     "action": "manage", "name_zh": "系統管理（2 段別名）",
     "is_sensitive": True, "risk_level": "critical"},
    # --- v3.60 G-510：外部 DB 整合權限（3 段別名） ---
    {"code": "external_db.connection.list", "module": "external_db", "resource": "external_db.connection",
     "action": "list", "name_zh": "列出外部 DB 連接", "is_sensitive": False, "risk_level": "low"},
    {"code": "external_db.connection.write", "module": "external_db", "resource": "external_db.connection",
     "action": "write", "name_zh": "新增/修改/刪除外部 DB 連接", "is_sensitive": True, "risk_level": "high"},
    {"code": "external_db.table.list", "module": "external_db", "resource": "external_db.table",
     "action": "list", "name_zh": "列出外部 DB table", "is_sensitive": False, "risk_level": "low"},
    {"code": "external_db.query", "module": "external_db", "resource": "external_db.query",
     "action": "run", "name_zh": "跨 DB 查詢", "is_sensitive": False, "risk_level": "medium"},
    {"code": "external_db.mapping.preview", "module": "external_db", "resource": "external_db.mapping",
     "action": "preview", "name_zh": "Schema 對映預覽", "is_sensitive": False, "risk_level": "low"},
    {"code": "external_db.migrate", "module": "external_db", "resource": "external_db.migrate",
     "action": "run", "name_zh": "外部 DB 資料匯入", "is_sensitive": True, "risk_level": "high"},
    # --- v3.60 Phase B1：金流閉環權限（3 段別名） ---
    {"code": "accounting.ap.read", "module": "accounting", "resource": "accounting.ap",
     "action": "read", "name_zh": "查看應付帳款", "is_sensitive": False, "risk_level": "medium"},
    {"code": "accounting.bank.read", "module": "accounting", "resource": "accounting.bank",
     "action": "read", "name_zh": "查看銀行帳戶", "is_sensitive": False, "risk_level": "medium"},
    {"code": "accounting.bank.write", "module": "accounting", "resource": "accounting.bank",
     "action": "write", "name_zh": "新增/修改銀行帳戶", "is_sensitive": True, "risk_level": "high"},
    {"code": "accounting.payment.read", "module": "accounting", "resource": "accounting.payment",
     "action": "read", "name_zh": "查看付款/收款單", "is_sensitive": False, "risk_level": "medium"},
    {"code": "accounting.payment.create", "module": "accounting", "resource": "accounting.payment",
     "action": "create", "name_zh": "建立付款單", "is_sensitive": True, "risk_level": "high"},
    {"code": "accounting.receipt.create", "module": "accounting", "resource": "accounting.receipt",
     "action": "create", "name_zh": "建立收款單", "is_sensitive": True, "risk_level": "high"},
    # M1-0.2：2 段別名（audit MISSING）
    {"code": "dashboard.read", "module": "dashboard", "resource": "dashboard",
     "action": "read", "name_zh": "儀表板檢視（2 段別名）",
     "is_sensitive": False, "risk_level": "low"},
    # --- v3.61 M2：財務閉環權限（三大報表 / 401-405 / 3-Way Match / 票據 / 固定資產） ---
    {"code": "accounting.statement.read", "module": "accounting", "resource": "accounting.statement",
     "action": "read", "name_zh": "查看三大報表", "is_sensitive": False, "risk_level": "medium"},
    {"code": "accounting.supplier_invoice.read", "module": "accounting", "resource": "accounting.supplier_invoice",
     "action": "read", "name_zh": "查看供應商發票", "is_sensitive": False, "risk_level": "medium"},
    {"code": "accounting.supplier_invoice.create", "module": "accounting", "resource": "accounting.supplier_invoice",
     "action": "create", "name_zh": "建立供應商發票", "is_sensitive": True, "risk_level": "high"},
    {"code": "accounting.supplier_invoice.match", "module": "accounting", "resource": "accounting.supplier_invoice",
     "action": "match", "name_zh": "執行 3-Way Match", "is_sensitive": False, "risk_level": "medium"},
    {"code": "accounting.note.read", "module": "accounting", "resource": "accounting.note",
     "action": "read", "name_zh": "查看票據", "is_sensitive": False, "risk_level": "medium"},
    {"code": "accounting.note.create", "module": "accounting", "resource": "accounting.note",
     "action": "create", "name_zh": "建立票據", "is_sensitive": True, "risk_level": "high"},
    {"code": "accounting.fixed_asset.read", "module": "accounting", "resource": "accounting.fixed_asset",
     "action": "read", "name_zh": "查看固定資產", "is_sensitive": False, "risk_level": "medium"},
    {"code": "accounting.fixed_asset.create", "module": "accounting", "resource": "accounting.fixed_asset",
     "action": "create", "name_zh": "建立固定資產", "is_sensitive": True, "risk_level": "high"},
    {"code": "accounting.fixed_asset.depreciate", "module": "accounting", "resource": "accounting.fixed_asset",
     "action": "depreciate", "name_zh": "過帳折舊", "is_sensitive": True, "risk_level": "high"},
    {"code": "accounting.cost_settle.execute", "module": "accounting", "resource": "accounting.cost_settle",
     "action": "execute", "name_zh": "月結銷貨成本結轉", "is_sensitive": True, "risk_level": "high"},
    {"code": "production.work_order.cost", "module": "production", "resource": "production.work_order",
     "action": "cost", "name_zh": "查看工單成本", "is_sensitive": False, "risk_level": "medium"},
    # --- v3.62 備份管理權限 ---
    {"code": "system.backup.read", "module": "system", "resource": "system.backup",
     "action": "read", "name_zh": "查看備份清單", "is_sensitive": False, "risk_level": "medium"},
    {"code": "system.backup.create", "module": "system", "resource": "system.backup",
     "action": "create", "name_zh": "建立/刪除備份", "is_sensitive": True, "risk_level": "high"},
    {"code": "system.backup.restore", "module": "system", "resource": "system.backup",
     "action": "restore", "name_zh": "還原備份（破壞性）", "is_sensitive": True, "risk_level": "critical"},
    # --- v3.63 M3 表單工程權限 ---
    {"code": "purchase.pr.create", "module": "purchase", "resource": "purchase.pr",
     "action": "create", "name_zh": "建立請購單", "is_sensitive": False, "risk_level": "medium"},
    {"code": "purchase.pr.approve", "module": "purchase", "resource": "purchase.pr",
     "action": "approve", "name_zh": "核准請購單", "is_sensitive": False, "risk_level": "medium"},
    {"code": "purchase.pr.convert", "module": "purchase", "resource": "purchase.pr",
     "action": "convert", "name_zh": "請購轉採購", "is_sensitive": False, "risk_level": "high"},
    {"code": "purchase.grn.create", "module": "purchase", "resource": "purchase.grn",
     "action": "create", "name_zh": "建立收料單", "is_sensitive": False, "risk_level": "medium"},
    {"code": "purchase.grn.read", "module": "purchase", "resource": "purchase.grn",
     "action": "read", "name_zh": "查看收料單", "is_sensitive": False, "risk_level": "low"},
    {"code": "production.material_issue.create", "module": "production", "resource": "production.material_issue",
     "action": "create", "name_zh": "建立領料單", "is_sensitive": False, "risk_level": "medium"},
    {"code": "production.material_issue.read", "module": "production", "resource": "production.material_issue",
     "action": "read", "name_zh": "查看領料單", "is_sensitive": False, "risk_level": "low"},
    {"code": "sales.return.create", "module": "sales", "resource": "sales.return",
     "action": "create", "name_zh": "建立退貨單", "is_sensitive": False, "risk_level": "medium"},
    {"code": "sales.return.read", "module": "sales", "resource": "sales.return",
     "action": "read", "name_zh": "查看退貨單", "is_sensitive": False, "risk_level": "low"},
    {"code": "sales.return.approve", "module": "sales", "resource": "sales.return",
     "action": "approve", "name_zh": "核准退貨單", "is_sensitive": False, "risk_level": "medium"},
    {"code": "sales.return.process", "module": "sales", "resource": "sales.return",
     "action": "process", "name_zh": "退貨入庫", "is_sensitive": True, "risk_level": "high"},
    # --- v3.64 追溯 / RFQ / 標籤權限 ---
    {"code": "inventory.batch.create", "module": "inventory", "resource": "inventory.batch",
     "action": "create", "name_zh": "建立批號", "is_sensitive": False, "risk_level": "medium"},
    {"code": "inventory.batch.read", "module": "inventory", "resource": "inventory.batch",
     "action": "read", "name_zh": "查看/追溯批號", "is_sensitive": False, "risk_level": "low"},
    {"code": "inventory.serial.create", "module": "inventory", "resource": "inventory.serial",
     "action": "create", "name_zh": "登記序號", "is_sensitive": False, "risk_level": "medium"},
    {"code": "inventory.serial.read", "module": "inventory", "resource": "inventory.serial",
     "action": "read", "name_zh": "查看/追溯序號", "is_sensitive": False, "risk_level": "low"},
    {"code": "purchase.rfq.create", "module": "purchase", "resource": "purchase.rfq",
     "action": "create", "name_zh": "建立詢價單", "is_sensitive": False, "risk_level": "medium"},
    {"code": "purchase.rfq.read", "module": "purchase", "resource": "purchase.rfq",
     "action": "read", "name_zh": "查看詢價/比價", "is_sensitive": False, "risk_level": "low"},
    {"code": "purchase.rfq.award", "module": "purchase", "resource": "purchase.rfq",
     "action": "award", "name_zh": "詢價決標", "is_sensitive": True, "risk_level": "high"},
    {"code": "print.label", "module": "print", "resource": "print.label",
     "action": "run", "name_zh": "列印料件標籤", "is_sensitive": False, "risk_level": "low"},
]


# ============================================================
# 10 個預設角色 + 權限分配
# ============================================================
# 每個角色：(code, name_zh, icon, color, priority, [(permission_code_or_wildcard, scope)])

ROLES: list[dict] = [
    {
        "code": "super_admin",
        "name_zh": "系統管理員",
        "icon": "🛡️",
        "color": "red",
        "priority": 100,
        "description": "擁有全部權限的系統最高管理員",
        "permissions": [("*", "all")],
    },
    {
        "code": "boss",
        "name_zh": "老闆",
        "icon": "👔",
        "color": "purple",
        "priority": 90,
        "description": "老闆視角：跨部門全覽 + 高金額簽核",
        "permissions": [
            ("sales.*", "tenant"), ("purchase.*", "tenant"),
            ("production.*", "tenant"), ("inventory.*", "tenant"),
            ("accounting.*", "tenant"), ("mps_mrp.*", "tenant"),
            ("quality.*", "tenant"), ("warehouse.*", "tenant"),
            ("crm.*", "tenant"),
            ("organization.employee.read", "tenant"),
            ("organization.employee.list", "tenant"),
            ("organization.user.read", "tenant"),
            ("organization.user.create", "tenant"),
            ("organization.user.update", "tenant"),
            ("mesh.factory.read", "all"),
            ("mesh.factory.list", "all"),
            ("mesh.factory.query", "all"),
            ("ai.agent.use", "tenant"),
            ("ai.agent.configure", "tenant"),
            ("analytics.view", "tenant"),
            ("analytics.view.all", "tenant"),
            ("system.permission.read", "tenant"),
        ],
    },
    {
        "code": "plant_manager",
        "name_zh": "廠長",
        "icon": "👨‍🏭",
        "color": "blue",
        "priority": 70,
        "description": "生產 + 品質 + 倉儲（v3.0 移除外協）",
        "permissions": [
            ("production.*", "tenant"), ("inventory.*", "tenant"),
            ("quality.*", "tenant"), ("warehouse.*", "tenant"),
            ("mps_mrp.*", "tenant"),
            ("purchase.*.read", "tenant"), ("purchase.*.list", "tenant"),
            ("sales.order.read", "tenant"), ("sales.order.list", "tenant"),
            ("ai.agent.use", "tenant"),
        ],
    },
    {
        "code": "sales_manager",
        "name_zh": "業務主管",
        "icon": "💼",
        "color": "indigo",
        "priority": 65,
        "description": "業務主管：團隊銷售管理",
        "permissions": [
            ("sales.*", "tenant"), ("crm.*", "tenant"),
            ("inventory.part.read", "tenant"),
            ("inventory.part.list", "tenant"),
            ("inventory.inventory.read", "tenant"),
            ("accounting.ar.read", "tenant"),
            ("accounting.ar.list", "tenant"),
            ("ai.agent.use", "tenant"),
        ],
    },
    {
        "code": "sales_rep",
        "name_zh": "業務員",
        "icon": "👨‍💼",
        "color": "cyan",
        "priority": 50,
        "description": "業務員：自己客戶與訂單（小陳）",
        "permissions": [
            ("sales.customer.read", "own"), ("sales.customer.list", "own"),
            ("sales.customer.create", "tenant"),
            ("sales.customer.update", "own"),
            ("sales.order.read", "own"), ("sales.order.list", "own"),
            ("sales.order.create", "tenant"),
            ("sales.order.update", "own"),
            ("crm.lead.read", "own"), ("crm.lead.create", "tenant"),
            ("crm.opportunity.read", "own"),
            ("crm.opportunity.create", "tenant"),
            ("inventory.part.read", "tenant"),
            ("inventory.part.list", "tenant"),
            ("inventory.inventory.read", "tenant"),
            ("ai.agent.use", "tenant"),
        ],
    },
    {
        "code": "purchaser",
        "name_zh": "採購",
        "icon": "🛒",
        "color": "amber",
        "priority": 55,
        "description": "採購：供應商與採購單（阿玲採購視角）",
        "permissions": [
            ("purchase.*", "tenant"),
            ("inventory.part.read", "tenant"),
            ("inventory.part.list", "tenant"),
            ("inventory.inventory.read", "tenant"),
            ("inventory.transaction.create", "tenant"),
            ("inventory.transaction.list", "tenant"),
            ("mps_mrp.mrp.read", "tenant"),
            ("ai.agent.use", "tenant"),
        ],
    },
    {
        "code": "warehouse_keeper",
        "name_zh": "倉管",
        "icon": "📦",
        "color": "green",
        "priority": 50,
        "description": "倉管：庫存出入庫、盤點、揀貨（阿玲倉管視角）",
        "permissions": [
            ("warehouse.*", "tenant"),
            ("inventory.part.read", "tenant"),
            ("inventory.part.list", "tenant"),
            ("inventory.inventory.read", "tenant"),
            ("inventory.transaction.create", "tenant"),
            ("inventory.transaction.list", "tenant"),
            ("inventory.transaction.read", "tenant"),
            ("purchase.order.receive", "tenant"),
            ("ai.agent.use", "tenant"),
        ],
    },
    {
        "code": "accountant",
        "name_zh": "會計",
        "icon": "💰",
        "color": "yellow",
        "priority": 55,
        "description": "會計：傳票、應收、月結",
        "permissions": [
            ("accounting.*", "tenant"),
            ("accounting.tax_report", "tenant"),
            ("sales.order.read", "tenant"),
            ("sales.order.list", "tenant"),
            ("purchase.order.read", "tenant"),
            ("purchase.order.list", "tenant"),
            ("analytics.view", "tenant"),
            ("analytics.view.all", "tenant"),
            ("ai.agent.use", "tenant"),
        ],
    },
    {
        "code": "inspector",
        "name_zh": "品檢員",
        "icon": "🔬",
        "color": "rose",
        "priority": 45,
        "description": "品檢：檢驗、不良品、CAPA",
        "permissions": [
            ("quality.*", "tenant"),
            ("production.work_order.read", "tenant"),
            ("production.work_order.list", "tenant"),
            ("purchase.order.read", "tenant"),
            ("inventory.part.read", "tenant"),
            ("ai.agent.use", "tenant"),
        ],
    },
    {
        "code": "operator",
        "name_zh": "作業員",
        "icon": "👷",
        "color": "slate",
        "priority": 30,
        "description": "作業員：報工、查工單",
        "permissions": [
            ("production.work_order.read", "assigned"),
            ("production.work_order.list", "assigned"),
            ("production.work_order.complete", "assigned"),
            ("ai.agent.use", "tenant"),
        ],
    },
    # outsource_partner 角色於 v3.0 移除（外協 persona 老吳砍掉）
]


# ============================================================
# 預設 Row Filter（6 種）
# ============================================================

ROW_FILTERS = [
    {"code": "scope.all", "scope": "all", "resource": "*",
     "filter_expr": {}, "description": "無過濾"},
    {"code": "scope.tenant", "scope": "tenant", "resource": "*",
     "filter_expr": {"tenant_id": "{user.tenant_id}"},
     "description": "本租戶/廠"},
    {"code": "scope.department", "scope": "department", "resource": "*",
     "filter_expr": {"department_id": "{user.department_id}"},
     "description": "本部門"},
    {"code": "scope.team", "scope": "team", "resource": "*",
     "filter_expr": {"team_id": "{user.team_id}"}, "description": "本團隊"},
    {"code": "scope.own", "scope": "own", "resource": "*",
     "filter_expr": {"created_by": "{user.employee_id}"},
     "description": "只看自己建的"},
    {"code": "scope.assigned", "scope": "assigned", "resource": "*",
     "filter_expr": {"assigned_to": "{user.employee_id}"},
     "description": "只看派給自己的"},
]


# ============================================================
# Wildcard 展開：把 "sales.*" 變成「所有 sales.xxx 權限」
# ============================================================

def _expand_wildcard(perms_all: dict, pattern: str) -> list[str]:
    if pattern == "*":
        return list(perms_all.keys())
    if pattern.endswith(".*"):
        prefix = pattern[:-2] + "."
        return [c for c in perms_all if c.startswith(prefix) or c == pattern[:-2]]
    if pattern.startswith("*."):
        suffix = pattern[2:]
        return [c for c in perms_all if c.endswith("." + suffix)]
    return [pattern]


# ============================================================
# 主入口
# ============================================================

async def seed_permissions():
    await init_db()
    async with AsyncSessionLocal() as db:
        # --- 1. Default tenant ---
        hq = (await db.execute(select(Tenant).where(Tenant.code == "HQ"))).scalar_one_or_none()
        if not hq:
            hq = Tenant(
                id=str(uuid.uuid4()), code="HQ", name="總部 / 主廠",
                tenant_type="hq", mesh_role="central",
            )
            db.add(hq)
            await db.flush()
            print("✓ Tenant: HQ")

        # --- 2. Permissions (UPSERT: insert new, update existing 描述/scope) ---
        existing_rows = {
            row.code: row for row in (
                await db.execute(select(PermissionDef))
            ).scalars().all()
        }
        created = 0
        updated = 0

        def _upsert(code: str, module: str, resource: str, action: str,
                    name_zh: str, sensitive: bool, risk: str):
            nonlocal created, updated
            existing = existing_rows.get(code)
            if existing is None:
                db.add(PermissionDef(
                    id=str(uuid.uuid4()), code=code, resource=resource,
                    action=action, module=module, name_zh=name_zh,
                    is_sensitive=sensitive, risk_level=risk, is_system=True,
                ))
                created += 1
            else:
                # 既有 → 同步 metadata（讓重新部署可拿到新描述/風險）
                changed = False
                if existing.name_zh != name_zh:
                    existing.name_zh = name_zh
                    changed = True
                if existing.risk_level != risk:
                    existing.risk_level = risk
                    changed = True
                if existing.is_sensitive != sensitive:
                    existing.is_sensitive = sensitive
                    changed = True
                if existing.module != module:
                    existing.module = module
                    changed = True
                if existing.resource != resource:
                    existing.resource = resource
                    changed = True
                if existing.action != action:
                    existing.action = action
                    changed = True
                if changed:
                    updated += 1

        # 主清單（3 段格式）
        for module, resource, action, name_zh, sensitive, risk in PERMISSIONS:
            code = f"{module}.{resource}.{action}"
            _upsert(code, module, f"{module}.{resource}", action, name_zh, sensitive, risk)

        # 補充清單（顯式 code，含 2 段別名）
        for extra in EXTRA_PERMISSIONS:
            _upsert(
                extra["code"], extra["module"], extra["resource"],
                extra["action"], extra["name_zh"],
                extra["is_sensitive"], extra["risk_level"],
            )

        await db.flush()
        print(f"✓ Permissions: {created} new, {updated} updated "
              f"({len(existing_rows)} pre-existing)")

        # All permissions for wildcard expansion
        all_perms = {
            row.code: row.id for row in (await db.execute(select(PermissionDef))).scalars().all()
        }

        # --- 3. Roles ---
        for role_spec in ROLES:
            existing = (await db.execute(
                select(RoleDef).where(RoleDef.code == role_spec["code"], RoleDef.tenant_id.is_(None))
            )).scalar_one_or_none()
            # M1-2：系統角色全量 sync（metadata + permission links 重建）。
            # 舊安裝的系統角色若被 skip-if-exists 卡住，永遠拿不到修正；
            # 現在只要是 is_system（或與系統角色同名）就同步，
            # 自訂角色（is_system=False 且非系統 code）不動。
            if existing and not existing.is_system and not any(
                r["code"] == existing.code for r in ROLES
            ):
                continue  # 純自訂角色 → 保留不動
            if existing:
                role = existing
                changed = False
                for attr in ("name_zh", "description", "icon", "color", "priority"):
                    if getattr(role, attr) != role_spec[attr]:
                        setattr(role, attr, role_spec[attr])
                        changed = True
                role.is_system = True
                role.is_active = True
                # 重建 permission links（先清後插，修正 drift / 錯配）
                old_links = (await db.execute(
                    select(RolePermissionLink).where(RolePermissionLink.role_id == role.id)
                )).scalars().all()
                for link in old_links:
                    await db.delete(link)
                await db.flush()
                if changed:
                    print(f"↻ Role updated: {role_spec['code']} ({role_spec['name_zh']})")
            else:
                role = RoleDef(
                    id=str(uuid.uuid4()), code=role_spec["code"],
                    name_zh=role_spec["name_zh"], description=role_spec["description"],
                    icon=role_spec["icon"], color=role_spec["color"],
                    priority=role_spec["priority"], is_system=True, is_active=True,
                )
                db.add(role)
                await db.flush()
                print(f"✓ Role: {role_spec['code']} ({role_spec['name_zh']})")
            # Attach permissions（含 wildcard 展開）
            # paper-isf fix: deduplicate (perm_id) per role - overlapping
            # wildcards like "sales.*" + "sales.order.*" double-insert and
            # break the rbac_role_permissions UNIQUE constraint.
            seen_perms: set[str] = set()
            for pattern, scope in role_spec["permissions"]:
                for code in _expand_wildcard(all_perms, pattern):
                    perm_id = all_perms.get(code)
                    if not perm_id or perm_id in seen_perms:
                        continue
                    seen_perms.add(perm_id)
                    db.add(RolePermissionLink(
                        id=str(uuid.uuid4()), role_id=role.id,
                        permission_id=perm_id, scope=scope,
                    ))
            print(f"✓ Role: {role_spec['code']} ({role_spec['name_zh']})")

        # --- 4. Row Filters ---
        for rf in ROW_FILTERS:
            existing = (await db.execute(
                select(RowFilter).where(RowFilter.code == rf["code"])
            )).scalar_one_or_none()
            if existing:
                continue
            db.add(RowFilter(
                id=str(uuid.uuid4()), code=rf["code"], resource=rf["resource"],
                scope=rf["scope"], filter_expr=rf["filter_expr"],
                description=rf["description"], is_system=True,
            ))

        await db.commit()
        print("\n✓ Permission seed completed.")
        print(f"  Tenants: HQ")
        print(f"  Permissions: {len(PERMISSIONS) + len(EXTRA_PERMISSIONS)} "
              f"({len(PERMISSIONS)} main + {len(EXTRA_PERMISSIONS)} extras)")
        print(f"  Roles: {len(ROLES)}")
        print(f"  Row Filters: {len(ROW_FILTERS)}")


if __name__ == "__main__":
    asyncio.run(seed_permissions())
