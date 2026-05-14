# 開發 SOP（Standard Operating Procedures）

> **本檔目的**：定義「新增/修改 X」的標準步驟，確保不同會話、不同開發者執行的方式一致，避免架構漂移。

---

## SOP-1：新增一個 Domain 模組

> 場景：例如要新增「Maintenance（設備維護）」domain。

### 步驟

1. **建立 Model**（`app/models/maintenance.py`）
   ```python
   from sqlalchemy import Column, String, DateTime, ForeignKey
   from app.core.base import Base
   import uuid
   from datetime import datetime

   class MaintenanceOrder(Base):
       __tablename__ = "maintenance_orders"
       id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
       work_center_id = Column(String(36), ForeignKey("work_centers.id"), nullable=False)
       maintenance_type = Column(String(30))  # preventive / corrective / predictive
       scheduled_at = Column(DateTime, nullable=False)
       completed_at = Column(DateTime)
       status = Column(String(20), default="scheduled")
       created_at = Column(DateTime, default=datetime.utcnow)
   ```

2. **註冊到 `app/models/__init__.py`**
   ```python
   from app.models.maintenance import MaintenanceOrder
   ```

3. **建立 Schema**（`app/schemas/maintenance.py`）
   - `MaintenanceOrderCreate` / `MaintenanceOrderResponse`

4. **建立 Service**（`app/services/maintenance.py`）
   - CRUD + 業務邏輯
   - 在改寫類操作時 `await EventBus.emit(DomainEvent(...))`

5. **建立 API**（`app/api/maintenance.py`）
   - 注入 `Depends(get_db)`、`Depends(get_current_user)`
   - 路徑前綴 `/api/maintenance`

6. **註冊 Router 到 `app/main.py`**
   ```python
   from app.api import maintenance
   app.include_router(maintenance.router)
   ```

7. **建立 Agent + Tools**（`app/agents/domains/maintenance_tools.py`）
   - 註冊至少 3 個 tools
   - 註冊 agent `register_agent("maintenance", ...)`
   - 在 `app/agents/tools.py` import 此 module

8. **更新 IntentClassifier**（`app/agents/engine.py:INTENT_KEYWORDS`）
   ```python
   "maintenance": [("維護", 6), ("保養", 5), ("故障", 5), ("PM", 4)],
   ```

9. **加入 Constraint Rules**（若有）（`app/events/rules.py`）

10. **加入 Notification 路由**（`app/events/engine.py:NotificationDispatcher.role_routes`）

11. **前端**：新增 page、加入 Layout 導航

12. **Seed 範例資料**（`scripts/seed.py`）

13. **驗收 smoke test**：跑 curl 確認 endpoint 200

14. **更新文件**：
    - `CLAUDE.md §4` 進度看板
    - `docs/WORKLOG.md` 追加條目
    - `docs/KNOWLEDGE_MAP.md` 新增對映

---

## SOP-2：新增一個 LLM Tool

> 場景：例如要加「查詢過去 7 天的異常事件」工具給 QualityAgent。

### 步驟

1. **選定 domain 檔**：`app/agents/domains/quality_tools.py`

2. **寫函式**（必須是 async，必須有 `db, user` 兩個前綴參數）
   ```python
   async def _recent_nc_events(db, user, days: int = 7):
       from datetime import datetime, timedelta
       from sqlalchemy import select
       from app.models.quality import NonConformance
       cutoff = datetime.utcnow() - timedelta(days=days)
       rows = (await db.execute(
           select(NonConformance).where(NonConformance.reported_at >= cutoff)
       )).scalars().all()
       return {"total": len(rows), "nc_list": [
           {"nc_no": n.nc_no, "severity": n.severity, "reported_at": str(n.reported_at)}
           for n in rows
       ]}
   ```

3. **註冊 tool**
   ```python
   register_tool(
       "recent_nc_events",
       "查詢過去 N 天內的不良品 (NC) 事件",
       {"type": "object", "properties": {
           "days": {"type": "integer", "description": "回溯天數，預設 7"}
       }},
       _recent_nc_events,
   )
   ```

4. **加入對應 agent 的 `tool_names`**
   ```python
   register_agent("quality", "QualityAgent",
       system_prompt="...",
       tool_names=["list_inspections", "list_non_conformances", "list_capa", "recent_nc_events"],
   )
   ```

5. **重啟 backend**（auto-reload 會生效）

6. **驗收**：在 AI 助手問「過去 3 天的不良事件」→ 應觸發此工具

---

## SOP-3：新增一條 Constraint Rule

> 場景：例如「PO 金額超過 100 萬必須有總經理簽核」。

### 步驟

1. **在 `app/events/rules.py` 新增函式**
   ```python
   async def check_large_po_approval(domain, action, data, user=None):
       if domain != "purchase" or action != "approve":
           return None
       amount = data.get("total_amount", 0)
       if amount >= 1_000_000:
           if not user or "ceo" not in user.get("roles", []):
               return {"rule": "check_large_po_approval", "status": "BLOCK",
                       "message": f"PO 金額 {amount:,} ≥ 100 萬，需總經理簽核"}
       return {"rule": "check_large_po_approval", "status": "PASS"}
   ```

2. **註冊到 `register_all_rules()`**
   ```python
   def register_all_rules():
       rules = [..., check_large_po_approval]
       for r in rules:
           ConstraintChecker.register(r)
   ```

3. **service 層觸發檢查**（在 `app/services/purchase.py:approve_purchase_order`）
   ```python
   from app.events.engine import ConstraintChecker
   result = await ConstraintChecker.check("purchase", "approve",
       {"total_amount": po.total_amount}, user)
   if result["status"] == "BLOCK":
       from app.core.exceptions import BusinessRuleError
       raise BusinessRuleError(result["blocked"][0]["message"], **result)
   ```

4. **驗收**：建 PO 金額 200 萬 → 一般員工 approve → 422 BLOCK

---

## SOP-4：新增一個排程演算法

> 場景：例如要實作模擬退火（SA）。

### 步驟

1. **建立檔案** `app/scheduling/algorithms/simulated_annealing.py`

2. **遵守介面**（規範待 Phase 4 制定）
   ```python
   from typing import Protocol

   class Scheduler(Protocol):
       def schedule(self, jobs: list, resources: list, constraints: dict) -> ScheduleResult:
           ...

   class SimulatedAnnealingScheduler:
       def __init__(self, T0=1000, alpha=0.95, max_iter=10000):
           ...
       def schedule(self, jobs, resources, constraints):
           # 1. 初始解
           # 2. 鄰域搜尋
           # 3. 接受/拒絕
           # 4. 降溫
           ...
   ```

3. **註冊到引擎**（`app/scheduling/__init__.py`）
   ```python
   ALGO_REGISTRY = {
       "GA": GeneticAlgorithm,
       "SA": SimulatedAnnealing,
       ...
   }
   ```

4. **API**：`POST /api/scheduling/run?algorithm=SA`

5. **驗收**：對標準測試集（如 LA01-LA40 Job Shop benchmark）跑出合理結果

---

## SOP-5：每次會話收尾的標準動作

> **這是最重要的 SOP**——確保專案不漂移。

### 必做 5 步

1. **跑 smoke test 確認沒壞**（依現況選擇）
   ```bash
   # 後端
   cd backend && python -c "from app.main import app; print('OK')"

   # 或更深入
   cd backend && uvicorn app.main:app --port 8000 &
   sleep 3
   curl -fsS http://localhost:8000/api/health
   ```

2. **更新進度看板**（`CLAUDE.md §4`）
   - 對動到的模組，更新百分比進度條
   - 例：`L3 MRP  🟡 [████  ] 45%` → `🟢 [██████████] 90%`

3. **追加 WORKLOG 條目**（`docs/WORKLOG.md`）
   - 倒序（最新放最上面）
   - 用模板填寫：日期、會話 #、目標、完成、影響、後續、Blocker

4. **若解鎖 Gap，更新 GAP_ANALYSIS**（`docs/GAP_ANALYSIS.md`）
   - 把對應的 `[ ]` 改成 `[x]`
   - 若整個 G-XXX 完成，加上 `✅ 完成於 YYYY-MM-DD`

5. **若有新模組，更新 KNOWLEDGE_MAP**（`docs/KNOWLEDGE_MAP.md`）
   - 將狀態 ❌ → 🟡 → 🟢

### 額外建議

- 重大變更請建立一個 git commit（如果有用 git）
- 若改動超過 5 個檔案，在 WORKLOG 追加「總計檔案數 N 個」備註

---

## SOP-6：當使用者提出新需求時的判斷流程

```
使用者提出需求
      │
      ▼
這個需求對應 PDF 哪一章？
      │
      ├─ 找不到對應 → 與使用者確認屬於「PDF 範圍外」or「新章節」
      │
      ▼
查 docs/GAP_ANALYSIS.md
      │
      ├─ 已在某 Gap (G-XXX) 中 → 依該 Gap 的 Phase 排序
      │     │
      │     ├─ 屬當前 Phase → 直接執行
      │     └─ 屬未來 Phase → 與使用者確認是否插單
      │
      └─ 不在 Gap 中 → 新增一個 G-XXX 條目，估工時、定 Phase
      │
      ▼
執行（依 SOP-1~4）
      │
      ▼
收尾（依 SOP-5）
```

---

## SOP-7：當系統壞掉時的除錯流程

1. **看 logs**
   ```bash
   docker compose logs -f backend --tail 100
   # 或本地：uvicorn 的 stderr
   ```

2. **進 DB 看資料**
   ```bash
   docker compose exec backend python -c "
   import asyncio
   from app.database import AsyncSessionLocal
   from sqlalchemy import text
   async def q():
       async with AsyncSessionLocal() as db:
           r = await db.execute(text('SELECT COUNT(*) FROM parts'))
           print(r.scalar())
   asyncio.run(q())
   "
   ```

3. **驗 ConstraintChecker**
   ```python
   from app.events.engine import ConstraintChecker
   await ConstraintChecker.check("inventory", "deduct", {"part_id": "x", "qty": 100})
   ```

4. **驗 Tool**
   ```python
   from app.agents import execute_tool
   r = await execute_tool("query_inventory", {"part_no": "M6-BOLT-20"}, db=db, user={})
   print(r)
   ```

5. **驗 EventBus**
   ```python
   from app.events import EventBus
   print(EventBus.get_history(limit=10))
   ```

---

## SOP-8：與使用者溝通的原則

1. **語言**：一律繁體中文，技術名詞可保留英文（如 MPS / MRP / API）
2. **長度**：
   - 「執行型」任務（請做 X）→ 做完後簡潔回報（重點 3-5 條）
   - 「諮詢型」任務（請建議）→ 完整分析（列方案、比較、推薦）
3. **格式**：
   - 用表格呈現比較
   - 用代碼塊呈現指令與結構
   - 用粗體標出關鍵字
4. **進度透明**：每次工作前先說「我會做 1、2、3」，做完後說「完成 1、2、3，下次該 X」
5. **遇阻塞**：明確說「目前卡在 X，建議方案 A 或 B」，不要靜默掙扎
