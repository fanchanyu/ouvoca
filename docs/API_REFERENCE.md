# API Reference 開發者 API 參考

> **互動式文件**：啟動後端後直接訪問 http://localhost:8000/docs（OpenAPI / Swagger UI）
> 本檔提供整體概覽與常用範例。

---

## 通用規範 · Common Conventions

### 認證 Authentication

所有 `/api/*` 路徑（除少數公開）都需 Bearer Token：

```http
Authorization: Bearer <JWT_TOKEN>
```

Token 從 `POST /api/auth/login` 取得。
若後端 demo bypass 啟用，可用 `Bearer demo` 作為超級管理員。

### 公開端點 Public Endpoints

| 端點 | 用途 |
|---|---|
| `GET /` | 基本資訊 |
| `GET /api/health` | 健康檢查 |
| `POST /api/auth/login` | 登入 |
| `GET /api/events/recent` | 最近事件 |
| `GET /api/events/stream` | SSE 即時事件流 |

### 錯誤回應 Error Response Format

```json
{
  "code": "business_rule_blocked",
  "detail": "庫存不足",
  "part_id": "...",
  "requested": 100,
  "available": 50
}
```

| HTTP Code | 意義 |
|---|---|
| 200 | 成功 |
| 401 | 未認證 / Token 無效 |
| 403 | 已認證但無權限 |
| 404 | 資源不存在 |
| 422 | 業務規則阻擋（ConstraintChecker BLOCK） / 驗證失敗 |
| 409 | 資料衝突（unique / FK 違反） |
| 500 | 系統錯誤 |

---

## 1. 認證 · Auth

### POST /api/auth/login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "...",
    "username": "admin",
    "employee_id": "...",
    "is_superuser": true
  }
}
```

---

## 2. 庫存 · Inventory

### GET /api/inventory/parts
```bash
curl http://localhost:8000/api/inventory/parts \
  -H "Authorization: Bearer demo"
```

Query: `?category=raw_material&skip=0&limit=100`

### POST /api/inventory/parts
```bash
curl -X POST http://localhost:8000/api/inventory/parts \
  -H "Authorization: Bearer demo" -H "Content-Type: application/json" \
  -d '{
    "part_no": "M6-BOLT-NEW",
    "name": "M6 新螺絲",
    "category": "raw_material",
    "unit": "pcs",
    "safety_stock": 1000,
    "unit_cost": 2.5,
    "lead_time_days": 7
  }'
```

### GET /api/inventory/below-safety
列出所有低於安全庫存的零件（dashboard 警示用）。

### POST /api/inventory/transactions
```bash
curl -X POST http://localhost:8000/api/inventory/transactions \
  -H "Authorization: Bearer demo" -H "Content-Type: application/json" \
  -d '{
    "part_id": "<part-id>",
    "transaction_type": "outbound",
    "qty": 50,
    "remark": "領用至工單 WO-001"
  }'
```

`transaction_type`: `inbound` / `outbound` / `allocate` / `deallocate` / `adjustment_in` / `adjustment_out`

---

## 3. 採購 · Purchase

### POST /api/purchase/orders
```bash
curl -X POST http://localhost:8000/api/purchase/orders \
  -H "Authorization: Bearer demo" -H "Content-Type: application/json" \
  -d '{
    "supplier_id": "<sup-id>",
    "expected_delivery_date": "2026-06-01T00:00:00",
    "items": [
      {"part_id": "<part-id>", "ordered_qty": 1000, "unit_price": 2.5}
    ]
  }'
```

### POST /api/purchase/orders/{po_id}/approve
要 `purchase.order.approve` 權限。

### POST /api/purchase/orders/{po_id}/receive
```bash
curl -X POST http://localhost:8000/api/purchase/orders/<po-id>/receive \
  -H "Authorization: Bearer demo" -H "Content-Type: application/json" \
  -d '{
    "receipts": [
      {"item_id": "<po-item-id>", "received_qty": 1000}
    ]
  }'
```
收貨會自動：增加庫存 + 標記 PO 為 received + emit `po.received` event。

---

## 4. 生產 · Production

### POST /api/production/work-orders
```bash
curl -X POST http://localhost:8000/api/production/work-orders \
  -H "Authorization: Bearer demo" -H "Content-Type: application/json" \
  -d '{"product_id":"<id>","ordered_qty":500,"priority":5}'
```

### POST /api/production/work-orders/{wo_id}/release
釋放工單。會檢查 BOM 是否完整、emit `wo.released`。

### POST /api/production/work-orders/{wo_id}/complete
```bash
curl -X POST http://localhost:8000/api/production/work-orders/<wo-id>/complete \
  -H "Authorization: Bearer demo" -H "Content-Type: application/json" \
  -d '{"completed_qty":500}'
```

---

## 5. 銷售 · Sales

### POST /api/sales/customers
```bash
curl -X POST http://localhost:8000/api/sales/customers \
  -H "Authorization: Bearer demo" -H "Content-Type: application/json" \
  -d '{"code":"CUST-NEW","name":"新客戶","grade":"B","credit_limit":1000000}'
```

### POST /api/sales/orders
類似 PO，含 `items` 陣列。

### POST /api/sales/orders/{so_id}/confirm
### POST /api/sales/orders/{so_id}/ship

---

## 6. AI 助手 · Chat

### POST /api/chat-v2
```bash
curl -X POST http://localhost:8000/api/chat-v2 \
  -H "Authorization: Bearer demo" -H "Content-Type: application/json" \
  -d '{"message":"庫存最低的 5 個零件","session_id":"test-1"}'
```

```json
{
  "reply": "根據查詢，目前庫存最低的是...",
  "agent": "inventory",
  "session_id": "test-1",
  "tool_calls": [
    {"tool": "list_below_safety", "args": {...}, "result": "..."}
  ]
}
```

> ⚠️ 沒設定 `LLM_API_KEY` 時會回 fallback 訊息。

### GET /api/chat/sessions/{session_id}/history
取得對話歷史。

---

## 7. 即時事件 · Events

### GET /api/events/recent
```bash
curl "http://localhost:8000/api/events/recent?limit=20" \
  -H "Authorization: Bearer demo"
```

### GET /api/events/stream (SSE)
```javascript
const es = new EventSource('/api/events/stream')
es.addEventListener('stock.below_safety', (e) => {
  const data = JSON.parse(e.data)
  console.log('Low stock alert:', data)
})
```

主要事件列表：

| Event | Domain | Description |
|---|---|---|
| `inventory.changed` | inventory | 庫存交易 |
| `stock.below_safety` | inventory | 庫存低於安全水位 |
| `po.created` / `.approved` / `.received` | purchase | 採購單生命週期 |
| `wo.created` / `.released` / `.completed` | production | 工單生命週期 |
| `so.created` / `.confirmed` / `.shipped` | sales | 銷售單生命週期 |
| `nc.created` | quality | 不良品 |
| `permission.role_granted` | permission | 角色授權 |

---

## 8. 權限管理 · Permissions

### GET /api/permission/roles
列出所有角色。

### GET /api/permission/permissions
列出 109 個權限定義。

### POST /api/permission/assignments
指派角色給使用者：
```bash
curl -X POST http://localhost:8000/api/permission/assignments \
  -H "Authorization: Bearer demo" -H "Content-Type: application/json" \
  -d '{
    "user_id": "<user-id>",
    "role_id": "<role-id>",
    "tenant_id": "<tenant-id>",
    "expires_at": "2026-12-31T23:59:59",
    "reason": "正式員工角色"
  }'
```

### POST /api/permission/overrides
個別授權（例外授權 / 撤銷）：
```bash
curl -X POST http://localhost:8000/api/permission/overrides \
  -H "Authorization: Bearer demo" -H "Content-Type: application/json" \
  -d '{
    "user_id": "<user-id>",
    "permission_code": "purchase.order.export",
    "grant_or_revoke": "grant",
    "reason": "臨時協助",
    "expires_at": "2026-05-31T23:59:59"
  }'
```

### GET /api/permission/users/{user_id}/effective
查看某使用者的「實際生效權限」（含角色 + override）。

### GET /api/permission/me/effective
查看自己的權限。

---

## 9. MPS / MRP

### POST /api/mps-mrp/mps
建立主排程。

### POST /api/mps-mrp/mrp/run/{mps_id}
執行 MRP 物料展開。

### GET /api/mps-mrp/mrp/{mrp_id}/items
取得 MRP 計算結果（採購建議 / 工單建議）。

---

## 10. 完整端點清單

啟動後訪問 http://localhost:8000/docs 取得互動式 OpenAPI 文件。

**目前共 102 個 endpoints，分布如下**：

| Domain | 端點數 | 主要操作 |
|---|---|---|
| Auth | 2 | login / register |
| Organization | 6 | department / employee / role |
| Inventory | 8 | part / inventory / transaction |
| Purchase | 7 | supplier / order / approve / receive |
| Production | 13 | product / bom / wo / work_center / operation |
| Sales | 7 | customer / order / confirm / ship |
| Quality | 5 | inspection / nc / capa |
| MPS/MRP | 6 | mps / mrp / run |
| Accounting | 8 | account / journal / ar / month_close |
| Warehouse | 8 | zone / bin / pick / cycle_count |
| CRM | 8 | lead / opportunity / event |
| Chat (AI) | 3 | chat / sessions / health |
| Events | 2 | recent / stream |
| Permission | 15 | tenants / permissions / roles / assignments / overrides |
| Misc | 4 | root / docs / openapi.json / redoc |

---

## 11. Rate Limits

目前無 rate limit（Phase 7 規劃）。生產建議：
- 在 nginx 加 `limit_req`
- 或用 `slowapi` middleware

---

## 12. SDK 範例

### JavaScript / TypeScript（前端用）

見 `frontend-desktop/src/lib/api.ts`：

```typescript
import { api, apiListParts, apiCreatePart } from './lib/api'

const parts = await apiListParts()
const newPart = await apiCreatePart({ part_no: '...', name: '...' })
```

### Python（後端 / 腳本用）

```python
import httpx

async with httpx.AsyncClient() as client:
    login = await client.post(
        "http://localhost:8000/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    token = login.json()["access_token"]

    parts = await client.get(
        "http://localhost:8000/api/inventory/parts",
        headers={"Authorization": f"Bearer {token}"},
    )
    print(parts.json())
```

---

## 13. 變更通知

API 重大變更會在 [WORKLOG.md](./WORKLOG.md) 註明。
v2.x 內保證 backward compatible，v3.0 可能有 breaking changes（屆時提早 30 天公告）。
