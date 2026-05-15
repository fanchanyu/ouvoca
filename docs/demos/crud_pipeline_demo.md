📂 Demo DB: C:\Users\pujy1\AppData\Local\Temp\demo-crud-ndjdik5v\demo.db


# LLM-ERP 對話式 CRUD 全流程 Demo

**情境**：採購阿玲今天上班，要查庫存 + 補貨。
**測試時間**：2026-05-15T10:34:03.632262+00:00


## Demo 1 — 阿玲：「列出我們的供應商」

**LLM 解析結果**：意圖 = purchase，呼叫 `query_supplier`

**回傳**：
```json
{
  "total": 2,
  "suppliers": [
    {
      "id": "d93e78f6-a1a9-4a9c-a00e-960ebde021ef",
      "code": "SUP-001",
      "name": "長江五金",
      "tier": "T1",
      "lead_time_days": 7,
      "is_approved": true
    },
    {
      "id": "8f399cfe-a27a-4fb5-904c-53fd1cb4ab17",
      "code": "SUP-002",
      "name": "大華實業",
      "tier": "T2",
      "lead_time_days": 0,
      "is_approved": true
    }
  ]
}
```

→ 找到 2 家供應商 ✅


## Demo 2 — 阿玲：「M6 螺絲庫存還多少？」

**LLM 解析結果**：意圖 = inventory，呼叫 `query_inventory(part_no='M6-BOLT-20')`

**回傳**：
```json
{
  "part_no": "M6-BOLT-20",
  "name": "M6 螺絲",
  "qty_on_hand": 300.0,
  "qty_available": 300.0,
  "qty_allocated": 0.0,
  "safety_stock": 500.0,
  "lead_time_days": 0,
  "status": "低於安全庫存"
}
```

⚠️ **庫存 300.0 < 安全庫存 500.0 → 需要補貨！**


## Demo 3 — 阿玲：「跟長江廠下 100 個 M6 螺絲，交期 5/20」

**LLM 解析結果**：意圖 = purchase，呼叫 `create_purchase_order_with_confirm`
  - supplier_keyword = 「長江」
  - items = [{part_keyword: 'M6 螺絲', ordered_qty: 100}]  ← 注意 LLM 用人話，不是 UUID
  - expected_delivery_date = '2026-05-20'

2026-05-15T18:34:03 [INFO] app.agents.confirm_card: ConfirmCard stashed: 0abc4de7-11a7-4bf5-9dcd-075a5f04b6e9 (create_purchase_order_with_confirm) by emp-demo-001
**回傳**（注意是 ConfirmCard 而非執行）：
```json
{
  "type": "confirm_card",
  "card": {
    "id": "0abc4de7-11a7-4bf5-9dcd-075a5f04b6e9",
    "tool_name": "create_purchase_order_with_confirm",
    "title": "確認建立採購單",
    "summary": [
      "供應商：長江五金（SUP-001）",
      "品項數：1 項",
      "  • M6-BOLT-20 M6 螺絲 × 100 @ $5 = $500",
      "總金額：$500",
      "預期交期：2026-05-20"
    ],
    "slots_preview": {
      "supplier_id": "d93e78f6-a1a9-4a9c-a00e-960ebde021ef",
      "supplier_name": "長江五金",
      "items": [
        {
          "part_id": "0f3463fa-d4a7-411b-86d5-5872f07f87e4",
          "ordered_qty": 100.0,
          "unit_price": 5.0
        }
      ],
      "expected_delivery_date": "2026-05-20",
      "remark": "",
      "total_amount": 500.0
    },
    "risk_tier": "hard-write",
    "created_at": "2026-05-15T10:34:03.672368+00:00",
    "expires_at": "2026-05-15T10:39:03.672368+00:00",
    "ttl_seconds": 300
  }
}
```

✅ Tool 沒有立刻下單，**出了 ConfirmCard (0abc4de7-11a7-4bf5-9dcd-075a5f04b6e9)** 等使用者確認。
   摘要：
     供應商：長江五金（SUP-001）
     品項數：1 項
       • M6-BOLT-20 M6 螺絲 × 100 @ $5 = $500
     總金額：$500
     預期交期：2026-05-20


## Demo 4 — 阿玲在 Chat UI 點「✓ 確認執行」

**前端 API**：`POST /api/agents/confirm/{card_id}`
**後端流程**：consume_card → 執行 executor closure → 呼叫 service → 寫 DB

**執行結果**：
```json
{
  "po_no": "PO-20260515103403-0c35ed",
  "id": "6eb6b2d6-6b41-4c81-a147-8d1ef20a4ce8",
  "total_amount": 500.0,
  "status": "draft",
  "message": "✅ 採購單 PO-20260515103403-0c35ed 已建立，總金額 $500"
}
```

✅ **PO PO-20260515103403-0c35ed 已建好！** 全程 1 句話。


## Demo 5 — 阿玲：「最近的採購單?」（驗證剛建好的 PO）

**LLM 解析結果**：呼叫 `query_purchase_order()`

**回傳**：
```json
{
  "total": 1,
  "orders": [
    {
      "po_no": "PO-20260515103403-0c35ed",
      "supplier_id": "d93e78f6-a1a9-4a9c-a00e-960ebde021ef",
      "status": "draft",
      "total_amount": 500.0,
      "order_date": "2026-05-15 10:34:03.678772",
      "expected_delivery_date": "2026-05-20 00:00:00"
    }
  ]
}
```

✅ 確認 PO-20260515103403-0c35ed 真的在 DB 內。**對話 → ConfirmCard → 寫入 整個 pipeline 通了。**


## Demo 6 — 王董：「我們鼎新有哪些客戶?」

**情境**：客戶舊系統（假裝鼎新 SQLite 匯出）。
**LLM 解析結果**：
  - 先呼叫 `list_external_connections` 看有沒有連接
  - 再呼叫 `list_external_tables` 看可查的 table
  - 再呼叫 `query_external_db` 跨 DB 讀

  *(後台已 seed：legacy_dingxin → C:\Users\pujy1\AppData\Local\Temp\demo-legacy-7kjdk4hi\dingxin.db)*

**Step 1**：list_external_connections →
```json
{
  "total": 1,
  "connections": [
    {
      "name": "legacy_dingxin",
      "connector": "sqlite",
      "config_keys": [
        "path"
      ]
    }
  ],
  "available_connectors": [
    {
      "name": "sqlite",
      "label": "SQLite 檔案 DB",
      "kind": "sql"
    },
    {
      "name": "csv_folder",
      "label": "CSV 資料夾",
      "kind": "file"
    }
  ]
}
```

**Step 2**：list_external_tables(legacy_dingxin) →
```json
{
  "connection": "legacy_dingxin",
  "connector": "sqlite",
  "total": 1,
  "tables": [
    "Customer"
  ]
}
```

**Step 3**：query_external_db(table=Customer, filters={Grade: 'A'}) →
```json
{
  "connection": "legacy_dingxin",
  "connector": "sqlite",
  "table": "Customer",
  "filters": {
    "Grade": "A"
  },
  "limit": 100,
  "total": 2,
  "rows": [
    {
      "CustNo": "C001",
      "CustName": "鼎新老客戶 A",
      "Grade": "A"
    },
    {
      "CustNo": "C003",
      "CustName": "鼎新老客戶 C",
      "Grade": "A"
    }
  ]
}
```

✅ 找到鼎新 2 個 A 等級客戶，**鼎新不用砍**。


# Demo 結論


| 步驟 | 場景 | 結果 |
|---|---|---|
| 1 | 阿玲查供應商 | ✅ query_supplier 走通 |
| 2 | 阿玲查 M6 庫存 | ✅ 告知低於安全庫存 |
| 3 | 阿玲下 100 個 M6 | ✅ 出 ConfirmCard，**不直接執行** |
| 4 | 阿玲點確認 | ✅ PO PO-20260515103403-0c35ed 真的建好 |
| 5 | 驗證 PO 在 DB | ✅ query_purchase_order 看得到 |
| 6 | 王董查鼎新客戶 | ✅ 跨 DB federated query 走通 |

**3 個 demo moment 全部走通**：
- ✅ 對話式 read（moment 1）
- ✅ 對話式 hard-write + ConfirmCard（moment 2）
- ✅ 對話式 federated query 鼎新（moment 3）

📊 **Tool registry**：32 個 tools 全進新 registry（29 read + 3 hard-write）
🛡️ **安全**：hard-write 必過 ConfirmCard / 5 分鐘 TTL / table whitelist
🔌 **整合**：sqlite + csv connector PoC + 3 個 AI tool 接 Chat

> 「**自然語言取代教育訓練 + 鼎新不用砍 + 員工 30 秒下單**」
> 這就是 30 萬一年的 LLM-ERP。

