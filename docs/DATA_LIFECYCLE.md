# 資料生命週期管理（Data Lifecycle Management, DLM）

> **本檔目的**：把「資料庫膨脹」這個系統性風險拆解為可執行的策略，從 Day 1 就在 schema 與 service 設計上預留空間。
>
> **核心信念**：**運算是便宜的，I/O 與儲存空間才是貴的**。資料分類、分層、定期清理是長期可持續的根本。

---

## 1. 為什麼這是真實風險

### 1.1 5 年資料量推估（100 人廠典型）

| 表 | 日寫入量 | 5 年累積 | 風險 |
|---|---|---|---|
| `audit_logs` | 5,000 | **913 萬筆** | 🔴 查詢變慢、備份變大 |
| `inventory_transactions` | 500 | **91 萬筆** | 🟡 索引膨脹 |
| `conversation_logs` | 200 | **36 萬筆** | 🟡 LLM context 載入慢 |
| `events` (in-memory) | 1,000 | （ring buffer 500）| ✅ 已有上限 |
| `decision_logs` | 100 | **18 萬筆** | 🟢 可控 |
| `permission_audit` | 20 | **3.6 萬筆** | 🟢 可控 |
| `journal_lines` | 50 | **9 萬筆** | 🟢 可控 |

**總體**：5 年後核心 DB ~1.1 GB（SQLite 可撐但很慢），audit_logs 單表就 900 萬列。

### 1.2 不處理會發生的事
1. **查詢退化**：`SELECT * FROM audit_logs WHERE ...` 從 50ms → 5 秒
2. **備份巨大**：dump 100MB → 5GB，凌晨備份打到日間
3. **Migration 風險**：alembic upgrade 鎖表 30 分鐘
4. **SQLite 撐不住**：超過 1GB 寫入時鎖檔，多人併發爆掉
5. **使用者抱怨**：「為什麼查上週資料要 30 秒？」

---

## 2. 資料分類（5 大類）

| 類別 | 範例 | 變動頻率 | 保留期 | 策略 |
|---|---|---|---|---|
| **A. 主檔** | parts / customers / products / suppliers | 低（少改） | 永久 | 全表保留 |
| **B. 交易** | sales_orders / purchase_orders / work_orders | 中 | 永久（法定 5-7 年） | 主表 + 月結歸檔 |
| **C. 事件** | inventory_transactions / dispatch_logs | 高 | 5-7 年 | 冷熱分層 |
| **D. 日誌** | audit_logs / permission_audit / decision_logs | 極高 | 1-3 年（依合規） | 冷熱分層 + 壓縮 |
| **E. AI/快取** | conversation_logs / event_buffer | 極高 | 6-12 月 | TTL 自動清理 |

---

## 3. 三大策略

### 策略 1：冷熱分層（Hot/Cold Tiered Storage）

> **適用**：日誌類、事件類（D + C）

#### 3.1 概念

```
┌────────────────────────────────┐
│  Hot Table（高頻訪問）           │
│  audit_logs                    │
│  最近 90 天 / ~45 萬筆 / index 小 │
│  查詢 < 50ms                    │
└──────────┬─────────────────────┘
           │ 月初 cron 搬移
           ▼
┌────────────────────────────────┐
│  Cold Table（歷史歸檔）          │
│  audit_logs_archive            │
│  90 天前 / 累積數百萬筆 / index 大 │
│  查詢 200ms-2s（可接受）         │
└────────────────────────────────┘
```

#### 3.2 實作藍圖（待 Phase 5+ 啟用）

```python
# app/services/data_lifecycle.py（規劃中）

async def archive_audit_logs(db, cutoff_date):
    """每月 1 號 03:00 跑：把 90 天前的 audit_logs 搬到 audit_logs_archive。"""
    # 1. INSERT INTO audit_logs_archive SELECT * FROM audit_logs WHERE created_at < :cutoff
    # 2. DELETE FROM audit_logs WHERE created_at < :cutoff
    # 3. VACUUM audit_logs（PG 用 pg_repack）

# 查詢函式：自動 UNION 兩張表
async def query_audit_logs(db, start, end, **filters):
    if end < 90_days_ago():
        return query_from(audit_logs_archive, ...)
    if start > 90_days_ago():
        return query_from(audit_logs, ...)
    return UNION(audit_logs, audit_logs_archive, ...)  # 跨期
```

#### 3.3 適用表清單

| Hot 表 | Cold 表 | 切割天數 | 保留總計 |
|---|---|---|---|
| `audit_logs` | `audit_logs_archive` | 90 | 3 年 |
| `inventory_transactions` | `inventory_transactions_archive` | 180 | 7 年 |
| `dispatch_logs` | `dispatch_logs_archive` | 90 | 3 年 |
| `permission_audit` | `permission_audit_archive` | 365 | 7 年 |

---

### 策略 2：TTL 自動清理（Auto-Expire）

> **適用**：AI 對話、快取（E）

#### 4.1 概念

```python
# 每天 04:00 跑
async def cleanup_expired():
    # 1. ConversationLog 超過 365 天 → 刪
    cutoff = datetime.utcnow() - timedelta(days=365)
    await db.execute(
        delete(ConversationLog).where(ConversationLog.created_at < cutoff)
    )
    # 2. 軟刪除的 user_role_assignments 超過 180 天 → 真刪
    await db.execute(
        delete(UserRoleAssignment).where(
            UserRoleAssignment.is_active == False,
            UserRoleAssignment.granted_at < datetime.utcnow() - timedelta(days=180),
        )
    )
```

#### 4.2 適用表清單

| 表 | 保留期 | 觸發 |
|---|---|---|
| `conversation_logs` | 365 天 | 每日 cron |
| `events`（in-memory buffer） | 500 條 | EventBus deque maxlen |
| 軟刪 `user_role_assignments` | 180 天 | 每日 cron |
| 過期 `permission_overrides` | 90 天 | 每日 cron |
| 過期的 `replenish_suggestions` | 60 天（已轉 PO） | 每日 cron |

---

### 策略 3：壓縮 + 索引最佳化（Compress + Optimize）

> **適用**：歸檔表（B + C + D 的 Cold 表）

#### 5.1 PostgreSQL：用 `pg_repack` 與 partial index

```sql
-- 歸檔表只查詢時間範圍，索引可精簡
CREATE INDEX idx_audit_archive_date ON audit_logs_archive (created_at);
-- 不需要 GIN index for JSON（歸檔表少查 JSON）

-- 月結後 vacuum
SELECT pg_repack('audit_logs_archive');
```

#### 5.2 SQLite：用 VACUUM + 月歸檔成獨立 .db 檔

```python
# 每月底執行
async def archive_to_separate_db():
    # 1. 將 audit_logs 中超過 90 天的搬到 archive_2025_01.db
    # 2. 在主 DB 刪掉
    # 3. 對主 DB 跑 VACUUM
```

---

## 4. 索引策略

### 6.1 必要索引（已在 model 中）

| 表 | 索引欄位 | 目的 |
|---|---|---|
| `audit_logs` | `user_id`, `created_at`, `entity_type` | 「誰在何時做了什麼」查詢 |
| `inventory_transactions` | `part_id`, `created_at`, `tenant_id` | 「某零件最近異動」 |
| `permission_audit` | `target_user_id`, `created_at` | 「某員工權限歷史」 |
| `conversation_logs` | `session_id`, `created_at` | 「某 session 對話」 |
| 所有業務表 | `tenant_id`（已透過 TenantMixin 加 index） | Row-Level Filter |

### 6.2 複合索引（待加）

```python
# 給「某 tenant 在某時段內的特定 entity_type 變更」查詢
Index("idx_audit_tenant_type_time",
      "tenant_id", "entity_type", "created_at")
```

### 6.3 不該加的索引

- **永遠不查的欄位**（如 `user_agent`）
- **高基數但少查**（如 `params` JSON 內部）
- **常變動的欄位**（會拖慢寫入）

---

## 5. 監控指標（Phase 7+ 啟用 Prometheus 後）

| 指標 | 警戒線 | 處理 |
|---|---|---|
| `audit_logs` 列數 | > 100 萬 | 觸發 archive |
| 單筆查詢 p95 latency | > 500ms | 加索引或 archive |
| DB 檔案大小 | > 2GB（SQLite）| 強制切 PG |
| Disk usage | > 70% | 加儲存 / 加 archive 頻率 |
| Vacuum 時間 | > 5 分鐘 | 改用 pg_repack |

---

## 6. 災難復原（DR）

### 8.1 資料分級

| 等級 | 內容 | RTO | RPO | 備份策略 |
|---|---|---|---|---|
| **L1 核心** | 主檔 + 進行中訂單 | 1 小時 | 15 分鐘 | 同步副本（PG streaming） |
| **L2 交易** | 歷史交易 / journal | 4 小時 | 1 天 | 每日 pg_dump |
| **L3 日誌** | audit / event / conversation | 24 小時 | 7 天 | 每週 dump + 雲端冷存 |

### 8.2 備份流程（待 Phase 7 自動化）

```bash
# 每日 03:00（已有 cron 範例）
pg_dump erp | gzip > /backup/daily/erp-$(date +%F).sql.gz
# 保留 7 天

# 每週日 04:00
pg_dump erp | gzip > /backup/weekly/erp-week$(date +%U).sql.gz
# 保留 12 週

# 每月 1 號 05:00
pg_dump erp | gzip > /backup/monthly/erp-$(date +%Y%m).sql.gz
# 永久保留（上傳 S3 / MinIO）
```

---

## 7. 與多廠 MESH 的關係

MESH 場景的資料生命週期：

```
┌──────────────────┐
│   HQ (中央)       │
│  - 聚合資料（小）  │
│  - 每月 archive   │
└────────┬─────────┘
         │
   ┌─────┴─────────────────────────┐
   │                               │
┌──▼────────┐  ┌──▼────────┐  ┌──▼────────┐
│ 工廠 A     │  │ 工廠 B     │  │ 工廠 C    │
│ 各自管理   │  │ 各自管理   │  │ 各自管理   │
│ - 本地交易 │  │ - 本地交易 │  │ - 本地交易 │
│ - 本地日誌 │  │ - 本地日誌 │  │ - 本地日誌 │
│ - 7 年保留 │  │ - 7 年保留 │  │ - 7 年保留 │
└───────────┘  └───────────┘  └───────────┘
```

**核心安全**：
- 各廠原始日誌**不上傳 HQ**（資料主權）
- 只上傳聚合結果（如「本月 OEE = 85%」）
- 每廠各自負責歸檔
- 法律稽核時，HQ 委派該廠查詢

---

## 8. 實作優先級

> 對應到 [GAP_ANALYSIS.md](./GAP_ANALYSIS.md) 新增的 G-DLM 系列。

| # | 任務 | 觸發條件 | Phase | 工時 |
|---|---|---|---|---|
| G-DLM-01 | 加複合索引（tenant_id + created_at） | 立即 | P1 | 0.5d |
| G-DLM-02 | `conversation_logs` 365 天 TTL cron | DB > 100 MB | P3 | 0.5d |
| G-DLM-03 | `audit_logs` 90 天歸檔 cron | DB > 500 MB | P5 | 1.5d |
| G-DLM-04 | `audit_logs_archive` 表 + service | 同上 | P5 | 1d |
| G-DLM-05 | 跨表 UNION 查詢輔助函式 | 同上 | P5 | 0.5d |
| G-DLM-06 | Prometheus 監控指標 | 5+ 客戶 | P7 | 1d |
| G-DLM-07 | 自動備份 cron | 第一個 prod 客戶 | P7 | 1d |
| G-DLM-08 | 跨廠 MESH 歸檔協同 | MESH 真實落地 | P6 | 2d |

---

## 9. 給開發者的紀律

### 9.1 每次新增業務表時必問

1. 這個表寫入頻率多高？（事件級 / 交易級 / 主檔級）
2. 需要保留幾年？（法規？業務？）
3. 查詢模式？（最近 / 全期 / 跨期）
4. 需要 index 哪些欄位？
5. 要納入哪個歸檔策略？

### 9.2 三條鐵則

1. **所有業務表都要有 `created_at` 與 `tenant_id`**
2. **大表（預估 > 10 萬筆/年）要規劃 archive 策略**
3. **不要在熱表加重 index（拖慢寫入）**

---

**最後更新**：2026-05-14
**設計者**：Claude
**Review**：需要與真實客戶對話確認保留期需求
