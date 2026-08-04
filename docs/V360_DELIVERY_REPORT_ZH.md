# Ouvoca v3.60 交付報告（2026-08-04）

> 本報告對應 `fixProblem.txt`（審計）、`Ouvoca vs.txt`（市場比較）、
> `TURNKEY_PHASE0.txt`（開機即用種子）三份文件的落地執行記錄。

---

## 一、P0 資安缺陷（全數修復）

| 缺陷 | 修復內容 | 驗證 |
|---|---|---|
| P0-1 Chat 管線繞過 tool 級 RBAC | `execute_tool()` 內建 `required_permission` 檢查（chat-v2 / agents_exec / scripts 共用）；chat 改從 DB 載入真實權限並注入 system prompt；權限快取 TTL 300s→30s | `test_v360_chat_rbac.py`（8 支，含 HTTP 路徑） |
| P0-2 20+ 細表未隔離 tenant | 16 張明細表補 `TenantMixin`（BOM/傳票行/SO 行/合約定價/審批步驟/報價行/盤點行/檢驗結果/工序/派工/製程步驟/PO 行/MPS/MRP/補貨規則/補貨建議）+ migration v007（含 backfill HQ） | `test_v360_tenant_child_tables.py` + `test_tenant_coverage.py` 更新分類 |
| P0-3 外部 DB 連線明文/易失 | 新增 `ExternalConnection` 模型 + AES-256-GCM 加密（`app/core/crypto.py`）；connections service 改 DB-backed（保留 in-memory fallback）；新增管理 API + 2 支 AI tool | `test_v360_external_connection_encryption.py`（DB 內無明文、tamper 偵測） |

## 二、P1 / Phase C 表單工程（C1/C2 完成）

| 項目 | 內容 |
|---|---|
| C1 集中單據編號 | `document_numbering` 表 + 原子計數器（`INSERT ... ON CONFLICT ... RETURNING`，SQLite/PostgreSQL 雙支援）；SO/PO/JE/DN/PY/RC 全部改走集中編號，格式 `{PREFIX}-{TENANT}-{PERIOD}-{SEQ:04d}` 保證全域唯一 |
| C2 狀態機框架 | `app/core/status_machine.py`：8 類單據合法轉換表 + `assert_transition()` 強制驗證；SO/PO/JE 的 confirm/ship/cancel/approve/receive/post 已接入 |

## 三、Phase B1 金流閉環基礎

新增 `BankAccount` / `AccountsPayable` / `Payment` / `Receipt` 模型 + `app/services/finance.py`
（付款沖 AP、收款沖 AR、銀行餘額原子更新）+ 6 支 AI tool（query_payables / query_bank_accounts /
query_payments / create_bank_account / record_payment / record_receipt，全部 ConfirmCard 保護）。

## 四、Turnkey Phase 0 / M1 整合（並行工作流合併）

| 項 | 內容 | 驗證 |
|---|---|---|
| M1-0 權限審計 | `scripts/audit_permission_codes.py` AST 掃描 + alias 對照；**MISSING=0** | 實測通過 |
| M1-1 TW 科目表 | 86 科 + `fs_line`/`is_system` + PUT/DELETE 保護 | `test_seed_accounts.py` 9/9 |
| M1-2 角色矩陣 | 10 角色 × 198 權限碼；系統角色改**全量 sync**（metadata + links 重建），自訂角色保留 | seed 實測 |
| M1-3 系統組態 | `system_settings` 表 + 14 項預設 + GET/PUT API（env > DB > default） | `test_v360_system_settings.py` |
| M1-4 seed 串接 | `scripts/seed.py` 依序執行 權限 → 科目 → 組態 | 實測 |

## 五、基礎設施修復（測試能跑的關鍵）

1. **uvloop policy**：沙箱/容器環境下 CPython selector loop 的 `call_soon_threadsafe`
   跨執行緒喚醒失效（aiosqlite 每個操作 hang 數十秒）→ `app/database.py` +
   `tests/conftest.py` + `alembic/env.py` 統一安裝 uvloop policy。
2. **pytest-asyncio 相容**：conftest 在 plugin 快取 policy 之前設 uvloop。
3. **Migration 鏈修復**：v001 baseline 的 `create_all` 與增量 migration 衝突
   （glossary/einvoice 重複建表）→ v002/v003/v004/v006-v010 全部 inspector 冪等化；
   全新安裝與 v3.55 升級兩條路徑實測通過（90 張表）。
4. **測試隔離**：`test_tool_registry` 清 registry 後還原；`test_confirm_card` 改比對前後筆數；
   route 檢查測試改用 lazy-router 展開 helper；mesh 網路測試在無 socket 環境自動 skip。

## 六、最終驗證

```
pytest:  838 passed, 7 skipped（5 為 sandbox socket 限制）, 0 failed
alembic: fresh install ✅（001→010, 90 tables）
         v3.55 upgrade ✅（005→010）
ruff:    新檔案無新增錯誤（既有風格 B008/BLE001 與全專案一致）
```

## 七、下一步（M2 — 財務閉環，4-6 週）

## 八、v3.61 M2 財務閉環（本次交付）

| 項 | 內容 | 驗證 |
|---|---|---|
| M2-1 三大報表 | `app/services/financial_statements.py`：試算表 / 損益表 / 資產負債表（`accounts.fs_line` 分組，自動驗證借貸平衡與資產=負債+權益）+ GET API + AI tool | `test_v361`（6/6） |
| M2-2 401/405 | `app/services/tax_report_tw.py`：401 銷項（電子發票）+ 405 進項（AP，舊資料 5% 拆算）+ 應納稅額 | 同上 |
| M2-3 3-Way Match | `SupplierInvoice`/`SupplierInvoiceItem` + `app/services/three_way_match.py`（PO↔收貨↔發票勾稽，matched/qty_variance/price_variance/unmatched）+ API + AI tool | 同上 |
| M2-4 票據管理 | `PromissoryNote`（應收/應付票據、託收狀態）+ API + 2 支 AI tool | 同上 |
| M2-5 固定資產 | `FixedAsset` 直線折舊 + 自動產傳票（DR 折舊費用 / CR 累計折舊）+ API + AI tool | 同上 |
| M2-6 WO 成本 + 銷貨成本結轉 | `app/services/production_cost.py`：工單三要素成本（材料 BOM×unit_cost + 人工 工序時數×時薪 + 製造費用 30%）；月結出貨成本 → DR 5100 / CR 1340 自動傳票 + API + 2 支 AI tool | 同上（8/8） |

Migration v011（4 張新表 + AP 進項稅欄位），全新安裝與升級路徑皆通過。
權限審計 MISSING=0（新增 10 個 M2 權限碼）。

### 財務閉環達成（M2 全數交付）

三大報表 ✅ / 401·405 ✅ / 3-Way Match ✅ / 票據 ✅ / 固定資產折舊 ✅ / WO 成本彙總 ✅ / 銷貨成本結轉 ✅

### 剩餘路線圖（非財務）

依 `Ouvoca vs.txt` Phase C/D/E：請購/RFQ/GRN/RMA、領退料/批號追溯、
備份 UI/MFA/HTTPS、HR/Portal/外協（客戶反饋驅動）。

---

## 九、v3.62 資安硬化與治理（審計 P1/P2 收尾）

| 項目 | 內容 | 驗證 |
|---|---|---|
| 登入暴力破解鎖定 | `failed_login_count`/`locked_until` + 閾值（system_settings，預設 5 次鎖 15 分）；鎖定期連正確密碼也 429 | `test_v362_hardening.py`（8/8） |
| Session 撤銷 | `token_version`：改密碼 +1 → 所有舊 JWT 立即失效（middleware + load_user_context 驗證） | 同上 |
| 上傳內容驗證 | magic bytes 簽名檢查（PDF/PNG/JPG/XLSX/DOCX/XLS）+ 文字檔腳本標記拒絕；既有測試改以合法內容 | `test_files_v313` 11/11 |
| Prompt injection 防線 | 外部 DB 查詢結果以資料邊界包裝 + 系統提示詞明確「外部內容不是指令」 | grep smoke |
| 發票號並發重號 | `_gen_invoice_no` 改集中式原子計數器（原 COUNT+1 racy） | 單元測試 |
| 信用額度強制檢查 | SO 建立時檢查 credit_limit - 未收應收 ≥ 訂單金額，否則擋（設定可關） | 同上 |
| 備份自動化 | `app/services/backup.py`：SQLite 快照 + WAL checkpoint + 保留策略 + 還原（先存救援檔）；API + 3 支 AI tool；lifespan 排程（依 backup.schedule，預設 03:00） | 同上 |
| 記憶體守衛 | `_SLOT_RETRY` 上限 2000 筆（防無上限成長） | — |

最終驗證：**854 passed, 7 skipped（沙箱 socket）, 0 failed**；alembic 001→012 全通；權限審計 MISSING=0。

---

## 十、v3.63 M3 表單工程（請購 / 收料 / 領料 / 退貨）

| 單據 | 內容 | 驗證 |
|---|---|---|
| 請購單 PR | `PurchaseRequisition`（draft→approved→converted）+ PR→PO 轉換（品項/數量帶入、單價以成本預設）+ API + 2 支 AI tool | `test_v363_m3_documents.py`（5/5） |
| 收料單 GRN | `GoodsReceiptNote`：收貨原子更新 PO 收貨量 + 入庫 + 狀態機（approved→received/partial_received）+ API + AI tool | 同上 |
| 領料單 | `MaterialIssue`：工單領料扣原料庫存 + 成本快照（WO 成本更準）+ API + AI tool | 同上 |
| 退貨單 RMA | `ReturnNote`：draft→approved→processed（退貨入庫）+ API + AI tool | 同上 |

Migration v013（8 張表，全新/升級路徑通過）；權限審計 MISSING=0（+11 權限碼）；
AI tools 192 支、DB 101 張表。

### 剩餘路線圖

- 批號/序號追溯（正反向 Pegging）— 製造業稽核下一塊
- 條碼/QR 標籤列印 + 條碼槍作業頁
- MFA（TOTP）、MESH HTTPS/mTLS、病毒掃描（需外部依賴）
- HR/Portal/外協（客戶反饋驅動）

---

## 十一、v3.64 現場作業 + 資安收尾（追溯 / RFQ / 標籤 / 掃描 / MFA / AV / MESH）

| 項目 | 內容 | 驗證 |
|---|---|---|
| 批號追溯 | `BatchLot` + 正反向 Pegging（經 InventoryTransaction 動向鏈解析 PO/GRN/WO/MI/DN/RT 單號）+ API + AI tool | `test_v364_trace_rfq_mfa.py`（8/8） |
| 序號追溯 | `SerialNumber` 主檔 + 狀態/最近文件追蹤 + API + AI tool | 同上 |
| RFQ 詢價比價 | `RFQ`/`SupplierQuote`：建立→送出→多家報價→比價（每料件最低價）→決標自動轉 PO + API + 4 支 AI tool | 同上 |
| 料件標籤 | 60×40mm QR 標籤 PDF（reportlab + qrcode）+ API + AI tool（回 base64） | 同上 |
| 條碼槍掃描 | POST /api/warehouse/scan：料號/批號/序號一次解析，回庫存與可執行操作 | 同上 |
| MFA（TOTP） | 兩階段登入（密碼 → TOTP）+ setup/enable/disable API；`/mfa/verify` 設為 public | 同上 |
| 病毒掃描掛鉤 | `AV_SCAN_URL` 設定後上傳先掃（ClamAV 類 REST）；未設定 = no-op；感染檔拒絕 | 同上 |
| MESH HTTPS | `MESH_USE_HTTPS`/mTLS 憑證設定項（部署層套用） | 設定項 |

Migration v014（6 張新表 + users MFA 欄位）；權限審計 MISSING=0（+10）；
AI tools 201 支、DB 107 張表。

最終驗證：**867 passed, 7 skipped（沙箱 socket）, 0 failed**；alembic 001→014 全通。

---

## 十二、v3.65 前端落地 + Galaxy UI 整合

**uiverse-io/galaxy（MIT，3000+ UI 元件）** 評估結果：純 CSS/HTML 元件庫，
與 Ouvoca 的 React + Tailwind 前端相容。已精選整合：

- `src/styles/galaxy.css` — Galaxy Toggle（設定開關）/ Loader（載入動畫）/ Scan Card（掃描卡）樣式
- `src/components/ui/GalaxyToggle.tsx` / `GalaxyLoader.tsx` — React 封裝元件

**前端功能落地**（後端 v3.63/3.64 功能全部接到頁面）：

| 頁面 | 新增 |
|---|---|
| Inventory | 條碼槍作業列（掃描料號/批號/序號 → 結果卡 + 追溯按鈕）、每料件 QR 標籤列印按鈕 |
| Settings | MFA（TOTP）設定區（密鑰/啟用/停用，Galaxy Toggle）、備份管理（立即備份/列表/還原/刪除）、系統組態（信用額度檢查、備份開關、稅率、保留天數、鎖定閾值） |
| Purchase | RFQ 詢價比價 tab（建立→送出→登錄報價→比價→決標轉 PO） |

驗證：`tsc --noEmit` 0 錯誤；`vite build` 成功（635 KB JS / 76 KB CSS）。

### 全部交付總覽（v3.60 → v3.65）

- 資安：tool 級 RBAC、租戶隔離、連線加密、登入鎖定、session 撤銷、MFA(TOTP)、上傳驗證、prompt injection 防線、AV 掛鉤
- 財務：三大報表、401/405、3-Way Match、票據、固定資產折舊、WO 成本、銷貨成本結轉
- 表單：請購→PO、GRN、領料、RMA、RFQ 比價、集中編號、狀態機
- 製造/現場：批號/序號追溯、QR 標籤、條碼槍掃描
- 治理：備份自動化+還原、系統組態、權限審計（MISSING=0）、86 科科目表
- 前端：上述功能全部有可操作頁面

---

## 十三、v3.66 健檢修復（`Ouvoca vs.txt` 專業審計 24 項）

| 等級 | # | 問題 | 修復 |
|---|---|---|---|
| P0 | 1 | MFA 可被繞過（mfa_pending token 當正式 token） | middleware 透傳 `mfa_pending` + `load_user_context` 拒絕 → 401（實測驗證） |
| P0 | 2 | 啟用 MFA 後前端登不進去 | Login 兩階段 UI（驗證碼輸入）+ `apiMfaVerify` |
| P0 | 3 | RFQ list/award HTTP 500（lazy-load） | 兩處補 `selectinload`；新增 HTTP 層測試 |
| P0 | 4 | 分批收貨第二次必失敗 | 狀態機補 `sent` 與 `partial_received→partial_received` |
| P1 | 5 | 升級後新功能對非 superuser 403 | update.sh/bat 升級後自動跑 `seed_permissions` |
| P1 | 6 | 備份刪除 Windows 失敗 | `_is_valid_sqlite` try/finally 顯式 close |
| P1 | 7 | 備份檔名路徑穿越 | 檔名白名單 regex + `Path(name).name` 檢查 |
| P1 | 8 | PostgreSQL 不相容（strftime） | 改 `extract(year/month)` 跨方言 |
| P1 | 9 | QR 標籤尺寸/相依錯誤 | `qrcode[pil]` + 頁面 60mm×40mm（`mm` 單位） |
| P1 | 10 | CORS 在 Auth 內層 | CORS 移到最外層（預檢 OPTIONS 不再被 401） |
| P2 | 11 | 超收/超付無上限 | GRN 累計 ≤ 訂購量；付款累計 ≤ AP 金額 |
| P2 | 12 | 折舊/COGS 重複結轉 | 同期間同來源防呆（已存在即擋） |
| P2 | 13 | 登入無速率限制、MFA 失敗不計鎖定 | login/mfa/chat 加 `@limiter.limit`；MFA 失敗計入鎖定 |
| P2 | 14 | 還原不處理 WAL/SHM | 還原後清除殘留 `-wal`/`-shm` |
| P2 | 15 | 資產負債表語意錯誤 | 改累計餘額（entry_date < 次月初） |
| P2 | 16 | 排程備份月底 ValueError | `timedelta(days=1)` 取代 `replace(day+1)` |
| P2 | 17 | 稅率存成字串 | 前端小數 regex 修正 |
| P2 | 18 | RFQ 報價用錯料件/不刷新 | list 帶 items、quote 表單預填、決標後刷新 PO |
| P2 | 19 | 代碼全域 unique 擋多租戶 | BankAccount/FixedAsset code 改租戶域 + migration v015 |
| P2 | 20 | 3-Way Match None 值 TypeError | format 前 `(received_qty or 0)` |
| P2 | 21 | row filter fallback 死碼 | `scope_for` none 才退化 read |
| P2 | 22 | 追溯 raw SQL 繞過租戶過濾 | 改 ORM select（自動 tenant filter） |
| P2 | 23 | galaxy.css 標註不實 + 未用 import | 標註誠實化；移除未用 `useState` |
| P2 | 24 | Node engines 太嚴 | `>=20 <25`；utcnow 於受支援版本（<3.13）可正常運作 |

最終驗證：後端全綠（見套件輸出）、前端 tsc/build 通過、alembic 001→015 全通、權限審計 MISSING=0。

---

## 十四、v3.67 健檢回測殘留項（`TURNKEY_PHASE0.txt` 回測報告 3 項）

| # | 殘留項 | 修復 |
|---|---|---|
| 1 | QR 標籤右緣被裁 ~1.7mm | `drawImage(108,30,55×55)`、`rect(2,2,166,109)` — 全在 170.08×113.39pt 畫布內 |
| 2 | 3-Way Match `unit_price` None 防呆只做一半 | `(unit_price or 0)` 於運算與格式化 |
| 3 | 乾淨環境未驗證全綠 | `pip install -r requirements.txt`（qrcode[pil] 到位）+ 全量 pytest |

另依回測建議：`update.*` 串 seed_permissions 已確認、`requirements.txt` 已改 `qrcode[pil]`。

---

## 十五、v3.68 Turnkey Phase 0 補完（`TURNKEY_PHASE0.txt`）

| 套件 | 內容 | 狀態 |
|---|---|---|
| P0-1 會計科目表 86 科 | `fs_line`/`is_system` + API 保護 | ✅（M1-1） |
| P0-2 角色矩陣 | 10 角色 × 231 權限碼（全量 sync + audit MISSING=0） | ✅（M1-0/2） |
| P0-3 家規 20 條 | `DEFAULT_RULES` 3→20：新增 `credit_check`/`has_customer_tax_id`/`period_open`/`field_in`/`not_empty` 五種 condition；接入 so.create / so.ship / po.receive / je.create 四個觸發點（allow-predicate 語意） | ✅ v3.68 |
| P0-4 表單 PDF | 既有 PO/SO/DN/發票/報價 + 料件標籤 + **檢驗報告 + 盤點表** | ✅ v3.68 |
| P0-5 行業種子 | metal/plastic/pcb/food/textile 五行業 seed | ✅（既有） |
| P0-6 系統組態 | 14 項預設 + GET/PUT API + env>DB>default | ✅（M1-3） |
| 90 分鐘驗收劇本 | `docs/TURNKEY_PHASE0_SEED_SPEC.md` §8 | ✅ 規格齊 |

家規 20 條涵蓋：WO 釋放需做法、PO 高額審批/至少 1 項、SO 信用額度/B2B 統編、出貨需確認、
收貨需核准/不可超收、傳票期間鎖定/借貸平衡、退貨/請購/RFQ 狀態守門、高額收付款審批、
領料/完工需釋放、報價/工單/收付款必填、庫存低水位與批號效期提醒。

---

## 十六、v3.69 效能健檢（`fixProblem.txt` 效能審計）

| 等級 | 問題 | 修復 |
|---|---|---|
| P0 | GET /api/purchase/orders 400（items MissingGreenlet） | 列表查詢補 `selectinload(PurchaseOrder.items)`（實測 200） |
| ① | 181 FK 欄位 159 個無索引（87%） | migration v016 自動掃 metadata 建複合索引 `(tenant_id, fk)` 142 個 + created_at 排序索引；實測 2 萬 PO 明細 1,030 倍加速 |
| ② | 每請求固定開銷 | SecurityHeaders/RequestID 改 pure ASGI（省 task group）；`load_user_context` 合併一次 JOIN；Audit 只記 mutation（GET 不寫）；SQLite 連線重用 `SQLITE_POOL_REUSE` 開關 |
| ③ | N+1 三處 | `_labor_cost` 批次撈 WorkCenter、`convert_pr_to_po` 批次撈 Part、`compare_quotes` 批次撈報價明細 |
| ④ | PostgreSQL 池太小 | DB_POOL_SIZE 20→30 |

新增 `test_v369_perf_regression.py`（PO 列表 HTTP、security headers、audit 只記 mutation）。

### 最後剩餘（需外部依賴 / 客戶反饋）

- HR（考勤/薪資）、客戶/供應商 Portal、外協託工 — 2+ 客戶簽約後啟動
- MESH HTTPS/mTLS 實際部署（憑證管理屬運維）
- 病毒掃描需外部 AV 服務（掛鉤已備）
