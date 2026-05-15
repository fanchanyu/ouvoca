"""Seed RBAC tables：95 個權限 + 10 個預設角色 + 1 個 HQ tenant。

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

    # --- quality (7) ---
    ("quality", "inspection", "read", "查看檢驗", False, "low"),
    ("quality", "inspection", "list", "列出檢驗", False, "low"),
    ("quality", "inspection", "create", "建立檢驗", False, "medium"),
    ("quality", "inspection", "complete", "完成檢驗", False, "medium"),
    ("quality", "nc", "read", "查看不良品", False, "low"),
    ("quality", "nc", "list", "列出不良品", False, "low"),
    ("quality", "capa", "create", "建立 CAPA", False, "medium"),

    # --- accounting (10) ---
    ("accounting", "account", "read", "查看科目", False, "low"),
    ("accounting", "account", "list", "列出科目", False, "low"),
    ("accounting", "journal", "read", "查看傳票", False, "medium"),
    ("accounting", "journal", "list", "列出傳票", False, "medium"),
    ("accounting", "journal", "create", "建立傳票", True, "high"),
    ("accounting", "journal", "post", "傳票過帳", True, "critical"),
    ("accounting", "journal", "export", "匯出傳票", True, "high"),
    ("accounting", "ar", "read", "查看應收", False, "medium"),
    ("accounting", "ar", "list", "列出應收", False, "medium"),
    ("accounting", "month_close", "execute", "月結結帳", True, "critical"),

    # --- warehouse (6) ---
    ("warehouse", "zone", "read", "查看倉區", False, "low"),
    ("warehouse", "zone", "list", "列出倉區", False, "low"),
    ("warehouse", "bin", "read", "查看儲位", False, "low"),
    ("warehouse", "bin", "list", "列出儲位", False, "low"),
    ("warehouse", "pick", "create", "建立揀貨", False, "medium"),
    ("warehouse", "cycle_count", "create", "盤點", False, "medium"),

    # --- crm (5) ---
    ("crm", "lead", "read", "查看潛在客戶", False, "low"),
    ("crm", "lead", "create", "建立潛在客戶", False, "medium"),
    ("crm", "opportunity", "read", "查看商機", False, "low"),
    ("crm", "opportunity", "create", "建立商機", False, "medium"),
    ("crm", "opportunity", "change_stage", "變更商機階段", False, "medium"),

    # --- mps_mrp (4) ---
    ("mps_mrp", "mps", "read", "查看 MPS", False, "low"),
    ("mps_mrp", "mps", "create", "建立 MPS", False, "medium"),
    ("mps_mrp", "mrp", "read", "查看 MRP", False, "low"),
    ("mps_mrp", "mrp", "run", "執行 MRP 計算", False, "medium"),

    # --- outsource (v3.0 移除：外協 persona 砍掉) ---

    # --- organization (8) ---
    ("organization", "employee", "read", "查看員工", False, "low"),
    ("organization", "employee", "list", "列出員工", False, "low"),
    ("organization", "employee", "create", "建立員工", True, "high"),
    ("organization", "employee", "update", "修改員工", True, "high"),
    ("organization", "role", "read", "查看角色", False, "low"),
    ("organization", "role", "list", "列出角色", False, "low"),
    ("organization", "role", "create", "建立角色", True, "high"),
    ("organization", "role", "update", "修改角色", True, "high"),
    ("organization", "user", "read", "查看使用者帳號", True, "medium"),

    # --- system (6) ---
    ("system", "config", "read", "查看系統設定", False, "medium"),
    ("system", "config", "update", "修改系統設定", True, "critical"),
    ("system", "tenant", "create", "建立租戶", True, "critical"),
    ("system", "tenant", "list", "列出租戶", False, "low"),
    ("system", "permission", "read", "查看權限定義", False, "low"),
    ("system", "permission", "list", "列出權限定義", False, "low"),
    ("system", "permission", "grant", "授權", True, "critical"),
    ("system", "permission", "revoke", "撤權", True, "critical"),

    # --- ai (2) ---
    ("ai", "agent", "use", "使用 AI 助手", False, "low"),
    ("ai", "agent", "configure", "設定 AI 助手", True, "high"),

    # --- mesh (3) ---
    ("mesh", "factory", "read", "查看廠別", False, "low"),
    ("mesh", "factory", "list", "列出廠別", False, "low"),
    ("mesh", "factory", "query", "跨廠查詢", False, "medium"),
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
            ("mesh.*", "all"), ("ai.agent.use", "tenant"),
            ("ai.agent.configure", "tenant"),
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
            ("sales.order.read", "tenant"),
            ("sales.order.list", "tenant"),
            ("purchase.order.read", "tenant"),
            ("purchase.order.list", "tenant"),
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

        # --- 2. Permissions ---
        existing_codes = {
            row[0] for row in (await db.execute(select(PermissionDef.code))).all()
        }
        created = 0
        for module, resource, action, name_zh, sensitive, risk in PERMISSIONS:
            code = f"{module}.{resource}.{action}"
            if code in existing_codes:
                continue
            db.add(PermissionDef(
                id=str(uuid.uuid4()), code=code, resource=f"{module}.{resource}",
                action=action, module=module, name_zh=name_zh,
                is_sensitive=sensitive, risk_level=risk, is_system=True,
            ))
            created += 1
        await db.flush()
        print(f"✓ Permissions: {created} new ({len(existing_codes)} existed)")

        # All permissions for wildcard expansion
        all_perms = {
            row.code: row.id for row in (await db.execute(select(PermissionDef))).scalars().all()
        }

        # --- 3. Roles ---
        for role_spec in ROLES:
            existing = (await db.execute(
                select(RoleDef).where(RoleDef.code == role_spec["code"], RoleDef.tenant_id.is_(None))
            )).scalar_one_or_none()
            if existing:
                continue
            role = RoleDef(
                id=str(uuid.uuid4()), code=role_spec["code"],
                name_zh=role_spec["name_zh"], description=role_spec["description"],
                icon=role_spec["icon"], color=role_spec["color"],
                priority=role_spec["priority"], is_system=True, is_active=True,
            )
            db.add(role)
            await db.flush()
            # Attach permissions（含 wildcard 展開）
            for pattern, scope in role_spec["permissions"]:
                for code in _expand_wildcard(all_perms, pattern):
                    perm_id = all_perms.get(code)
                    if not perm_id:
                        continue
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
        print(f"  Permissions: {len(PERMISSIONS)}")
        print(f"  Roles: {len(ROLES)}")
        print(f"  Row Filters: {len(ROW_FILTERS)}")


if __name__ == "__main__":
    asyncio.run(seed_permissions())
