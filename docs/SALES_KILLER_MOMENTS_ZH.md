# LLM-ERP 業務 demo 一頁紙 — 9 個 killer moments（v3.5）

> **給銷售團隊**：客戶 demo 30 分鐘 走完這 9 個畫面 = 30 萬簽約
> **產品狀態**：~91% MVP，193 tests 全綠 / 38 tools registered / 8 PDF + 33 份雙語文件

---

## 一句話 Pitch

> **「給 50-100 人廠的對話式 ERP——桌機 Chrome 開著 Chat，用講的就能查 / 增 / 改 / 刪所有單據，鼎新舊資料 AI 自動搬，30 萬一年。」**

---

## 客戶痛點 → 我們的解法

| 客戶說 | 我們答 |
|---|---|
| 「太貴（SAP 200萬+）」 | 30 萬一年，全包 |
| 「太難用（要學幾百個畫面）」 | 用講的，2 小時就會 |
| 「IT 人員不會用」 | AI 反問教你下一步 |
| 「員工誤操作怎麼辦」 | 寫入有確認卡 + 90 秒 Undo |
| 「我舊資料怎麼搬」 | AI Schema Mapping，1 hour 跑完，零停機 |
| 「沒手機版?」 | 桌機就夠，員工 80% 時間都在電腦前 |

---

## 9 個 killer moments（demo 順序）

### Moment 1 — 對話式 read（最暖身）

```
王董：「今天工廠狀況?」

AI 自動跑：preview_email_digest tool
    ┌─ ⚠️ 關鍵警示 (2 項)
    │   🔴 M6-BOLT-20：剩 300 / 安全 500（短缺 200）
    │   💰 應收 INV-2026-005 逾期 15 天，未收 $128,000
    ├─ 📅 今日事件 (8 個)
    │   so: 3 / po: 2 / wo: 3
    └─ 📊 KPI 快照
        📦 30 日出貨：12 筆，金額 $580K
        🛒 進行中採購單：5 張

★ 「不用問員工，老闆 30 秒看完今天狀況」★
```

### Moment 2 — 對話式 hard-write（核心）

```
阿玲：「跟長江廠下 100 個 M6 螺絲，交期 5/20」

AI（slot-filling 已滿足 / glossary 自動翻譯）：
    供應商：長江五金 (SUP-001)  ← glossary auto-resolved
    料件：M6-BOLT-20             ← glossary auto-resolved
    
出 ConfirmCard：
    ┌──────────────────────────────┐
    │ 確認建立採購單                  │
    │ 供應商：長江五金 (SUP-001)     │
    │ 品項：M6-BOLT-20 × 100        │
    │ 金額：$500                     │
    │ 交期：2026-05-20              │
    │ [取消]              [✓ 確認]  │
    └──────────────────────────────┘

阿玲點確認 → 「✅ PO-XXX 已建立」

★ 「員工不用學系統，講話就下單」★★
```

### Moment 3 — Slot-filling 反問

```
阿玲：「下單」

AI（偵測缺欄位）：
    「執行 create_purchase_order_with_confirm 需要先知道
     4 個欄位：供應商、料件清單、預期交期。
     請問是哪一家供應商? 要訂什麼料件? 多少數量? 交期幾號?」

★ 「AI 不會編造，缺什麼就問什麼」★
```

### Moment 4 — Glossary 智能對映

```
阿玲：「跟長江下 100 個鋼釘」

AI 自動：
    1. lookup_term("鋼釘", "part") → M6-BOLT-20 (alias, confidence 0.9)
    2. lookup_term("長江", "supplier") → SUP-001 (alias, confidence 0.9)
    3. → create_purchase_order_with_confirm 走通

★ 「老師傅講話 AI 聽得懂」★
```

### Moment 5 — Undo 90 秒撤銷

```
阿玲（剛建好 PO 後 30 秒，發現品項錯了）：「取消剛剛那筆」

AI（找最近 90 秒內由阿玲建的 PO）：
    出反向 ConfirmCard：
      將撤銷採購單 PO-XXX
      建立於 30 秒前
      金額 $500
      狀態 draft → cancelled
      剩餘可撤銷時間：60 秒
    [取消]              [✓ 確認]

★ 「不怕點錯，90 秒內隨時可撤銷」★
```

### Moment 6 — 跨 DB Federated Query

```
王董：「我們鼎新的 5 月份訂單金額多少?」

AI 自動 chain：
    list_external_connections → legacy_dingxin
    list_external_tables → OrderHeader
    query_external_db (filters={order_date_gte: 2026-05-01})
    → 加總 Amount

AI：「鼎新 5 月份 $3.2M（45 筆）+ LLM-ERP $580K（12 筆）= 合計 $3.78M」

★ 「鼎新不用砍，繼續跑」★
```

### Moment 7 — Schema Mapping + Migration（🏆 重磅）

```
阿玲：「把鼎新的客戶都搬過來」

AI 自動 chain：
    1. preview_schema_mapping (target=customer)
       → 自動推薦：
           CustNo   → code   (0.95) ✅
           CustName → name   (0.95) ✅
           Grade    → grade  (1.0)  ✅
           Phone    → contact_phone (0.85) ⚠️
       → 找到 6/9 個欄位對映，required 100% 滿足
    2. migrate_from_external_with_confirm
       → 出 ConfirmCard：
           來源：legacy_dingxin.Customer
           目標：customer
           總筆數：124 筆
           高信心對映 6 / 中信心 2 / 找不到 1
           衝突策略：skip
           預覽前 5 筆…
           [取消]   [✓ 確認執行]

阿玲點確認 → 「✅ 匯入完成：新增 124 筆 / 略過 0 / 失敗 0」

★★★ 客戶當場簽約 ★★★
「我舊資料有救了，不用 IT 不用顧問」
```

### Moment 8 — 桌面 Toast 主動推播

```
（阿玲離開電腦去開會）

後端 EventBus：emit stock.below_safety
                emit so.created
                emit po.received

桌面：
    🔔 ⚠️ M6 螺絲低於安全水位
        M6-BOLT-20：剩 300 / 安全 500
    
    🔔 📥 新銷售訂單
        SO-2026-018  金額 $24,000

Chat 右上角：banner 滑入（5 秒後自動消失）

★ 「不用一直盯電腦，重要事 AI 主動跳通知」★
```

### Moment 9 — Email 每日摘要（給老闆收）

```
王董：「以後每天 7 點寄一份摘要給我 wang@example.com」

AI：preview_email_digest → 出當下摘要
    send_email_digest_with_confirm → ConfirmCard
        收件人：wang@example.com
        區間：最近 24 小時
        主旨：[LLM-ERP] 最近 24 小時摘要：⚠️ 今日 2 項警示需注意
        段落：⚠️ 關鍵警示（2 項）/ 📅 今日事件（8 個）/ 📊 KPI 快照
        [取消]    [✓ 確認寄送]

王董點確認 → 「✅ Email 已寄出給 wang@example.com」

★ 「老闆下班吃飯也看得到工廠狀況」★
```

---

## 簽約後的 onboarding（給銷售講）

| Day | 活動 |
|---|---|
| Day 1 | Docker 一鍵部署 + 連 DB |
| Day 2 | 連客戶舊系統（鼎新 / 正航 / 叡揚 / Excel） + Migration 預覽 |
| Day 3-4 | RBAC 角色設定 + Glossary 教 AI 客戶的俗稱 |
| Day 5 | 客戶 5 個關鍵員工 2 小時上手訓練 |
| Day 6-10 | 並行運作（舊系統 + LLM-ERP），客戶熟悉 |
| Day 11 | 全廠正式切換 / 舊系統 read-only |
| Day 12-14 | 線上支援 + 微調 + 補 Glossary |

**vs SAP 6-18 月導入時間：縮 95%**

---

## 競品比較

| 競品 | 價格 | 行動端 | AI | 連舊系統 |
|---|---|---|---|---|
| **SAP B1** | 200 萬+ | 弱 | 無 | DI API 自己寫 |
| **正航** | 50-100 萬 | 弱 | 無 | 同 SAP |
| **鼎新 Workflow** | 80-150 萬 | 弱 | 無 | 不接 |
| **Odoo** | 0-30 萬 | 中 | 弱 | 寫 module |
| **Excel + LINE** | 0 | 強 | 無 | 無 |
| **LLM-ERP** | **30 萬** | 桌機+Toast | **內建 38 tools** | **AI Schema Mapping** |

---

## 給客戶的 30 秒結論

> **「我們不是又一個 ERP，我們是 ERP 的 AI 上層介面。」**
>
> 員工不用學系統，用講的就會。
> 你的鼎新不用砍，我們直接讀 + 慢慢搬。
> 30 萬一年，2 週上線，2 小時上手。
>
> **要試用嗎? 我們週四下午過去 demo 30 分鐘給你看。**

---

**最後更新**：2026-05-15（v3.5 — 9 killer moments + Email digest）
**對應 demo 腳本**：`docs/demos/crud_pipeline_demo.md`
**對應 commits**：v3.0~v3.5 共 7 個 sprint commits
