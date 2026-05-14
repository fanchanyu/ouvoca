# 學術與商業頂點思維（STRATEGY LANDSCAPE）

> **本檔目的**：站在「最高點」俯瞰整個專案——這不只是寫 ERP 程式，而是建構**製造業生態平台**。
> 從學術角度看，這專案融合了 DDD / Event-Driven / Multi-Tenant / Game Theory；
> 從商業角度看，這是 Land-Expand + Network Effect + Data Moat 的範例。

---

## Part I：學術頂點（Academic Excellence）

### 1. Domain-Driven Design（DDD）的實踐

#### 1.1 戰略設計（Strategic Design）

我們的系統有 **12 個 Bounded Context**，每個都有清楚邊界：

| Bounded Context | 核心概念 | 關鍵實體 | 關鍵領域事件 |
|---|---|---|---|
| Inventory | 庫存管理 | Part, Inventory, Transaction | `inventory.changed`, `stock.below_safety` |
| Purchase | 採購 | Supplier, PO, POItem | `po.approved`, `po.received` |
| Production | 生產 | WO, Operation, WC | `wo.released`, `wo.completed` |
| Sales | 銷售 | Customer, SO, SOItem | `so.shipped` |
| Quality | 品質 | Inspection, NC, CAPA | `nc.created`, `capa.created` |
| Accounting | 會計 | Account, Journal, AR | `journal.posted`, `month.end_close` |
| Warehouse | 倉儲 | Zone, Bin, Pick | `pick.completed` |
| CRM | 客戶關係 | Lead, Opp, Event | `lead.converted` |
| MPS/MRP | 規劃 | MpsMaster, MrpItem | `mrp.generated` |
| Permission/RBAC | 權限治理 | Role, User, Audit | `permission.role_granted` |
| AI/Agent | LLM 互動 | Conversation, Decision | (內部) |
| MESH | 多廠協同 | Tenant, Factory Node | `mesh.factory_registered` |

→ 完整 Context Map 可繪 Ubiquitous Language 圖（未來文件）。

#### 1.2 戰術設計（Tactical Design）

| DDD Pattern | 我們的實作位置 |
|---|---|
| **Aggregate Root** | `PurchaseOrder` 是聚合根，`PurchaseOrderItem` 是其內部實體 |
| **Entity** | `Part`, `Customer`, `Employee`（有 ID 與生命週期） |
| **Value Object** | `MpsEntry.PAB` 計算結果（無 ID） |
| **Domain Service** | `app/services/mps_mrp.py:run_mrp()`（跨多個聚合的業務邏輯） |
| **Domain Event** | `DomainEvent` dataclass + EventBus |
| **Repository** | SQLAlchemy session（簡化版） |
| **Anti-Corruption Layer** | LLM provider 抽象（OpenAI/Anthropic/DeepSeek 各自 API → 統一介面） |

→ 這不是「教科書級」DDD（小廠不需要完整 CQRS / Event Sourcing），但戰術 pattern 大量採用。

---

### 2. 分散式系統理論（Distributed Systems）

#### 2.1 CAP Theorem 取捨

MESH 多廠是典型分散式場景：

| 屬性 | 我們的選擇 | 原因 |
|---|---|---|
| **Consistency** | **最終一致**（eventual） | 工廠暫時離線 OK，恢復後追平 |
| **Availability** | **高可用** | 即使 HQ 掛了，工廠仍可本地運作 |
| **Partition Tolerance** | **必選** | 分散式系統的必要條件 |

→ 我們選 **AP**（犧牲強一致），符合製造業常見斷網場景。

#### 2.2 共識協議

不需要 Paxos / Raft 等強共識協議，因為：
- 每筆庫存交易**只屬於一個 tenant**（無跨 tenant 寫衝突）
- HQ 與工廠之間只有「查詢聚合」（讀取），無協同寫入
- 結算階段才有跨 tenant 操作（夜間批次，無併發）

#### 2.3 訊息傳遞語義

- HQ → 工廠：**At-most-once**（網路失敗就降級用 fallback，避免重複查詢扣費）
- 工廠 → HQ（事件）：**At-least-once**（事件可能重複，但 idempotent 處理）
- 內部 EventBus：**Best-effort**（in-memory，故障時丟失可接受，因 audit_logs 仍寫了 DB）

---

### 3. 多租戶模式（Multi-Tenancy Patterns）

> 參考 Microsoft Azure SaaS Architecture / AWS Multi-Tenant Patterns。

| 模式 | 隔離強度 | 成本 | 我們的選擇 |
|---|---|---|---|
| Database-per-tenant | 最強 | 最高 | ❌ |
| Schema-per-tenant | 強 | 高 | ❌ |
| **Shared schema + tenant_id** | 中 | 低 | ✅（ADR-002） |
| Hybrid（核心 shared + 敏感分離） | 彈性 | 中 | 🟡 未來（HR/薪資可考慮） |

#### 3.1 Tenant Isolation Patterns

我們實作了以下隔離機制：

1. **資料隔離**：每張業務表的 `tenant_id` + Row-Level Filter（自動 WHERE）
2. **權限隔離**：角色綁定 tenant_id（NULL = 系統共用）
3. **執行隔離**：MESH 各廠獨立 Python process + 本地 DB
4. **AI 隔離**：工廠節點用本地 Ollama（不送 cloud LLM）
5. **稽核隔離**：每廠 audit_logs 本地保留，HQ 看不到 raw

---

### 4. Game Theory（賽局理論）—— 外協生態的設計

> 外協廠不會註冊我們的系統，怎麼讓他們**自願**回報進度？

#### 4.1 激勵相容（Incentive Compatibility）

設計原則：**讓「誠實回報」是外協廠的支配策略**（dominant strategy）。

| 設計 | 賽局意義 |
|---|---|
| LINE Bot 掃 QR 不需註冊 | 降低交易成本接近零 |
| 回報即同步主廠系統 | 外協廠不用再打電話告知，省時間 |
| 主廠依即時數據付款（vs. 月底結算） | 早回報 = 早收錢（金錢激勵） |
| QR 內含 token，主廠驗證真偽 | 防偽造（懲罰機制） |
| 完工率 / 準時率公開 | 聲譽機制（reputation） |

→ 這是**機制設計（Mechanism Design）**的小型應用：透過規則設計，讓所有參與者的最佳策略對齊整體效益。

#### 4.2 對主廠老闆（王董）的應用

王董為何要採用？兩個賽局：
- **競爭賽局**：客戶要的是「準時、便宜、彈性」，導入這套系統能比同業快——成為「正回饋循環」
- **代理問題**：老闆怕業務私下接單、廠長私下換料 → 系統留下完整 audit trail，糾正資訊不對稱

---

### 5. 資訊理論安全（Information-Theoretic Security）

MESH 多廠中，HQ 為什麼**真的看不到**工廠明細？

#### 5.1 設計而非加密

不靠加密保證安全（加密在運算時必須解密），而是**根本不上傳**：

```
HQ 問: "M6 螺絲全廠庫存"
   ↓
HQ Bot 分發查詢到 3 個工廠節點
   ↓
工廠 A 本地查 DB → 回 "3000"  (整數，沒明細)
工廠 B 本地查 DB → 回 "2500"
工廠 C 本地查 DB → 回 "1800"
   ↓
HQ 聚合 → 回王董 "7300"
```

HQ 永遠沒看到「哪批料、誰買的、何時收到、單價多少」。

#### 5.2 與差分隱私（Differential Privacy）的關係

未來可加：聚合查詢加雜訊（如「M6 螺絲庫存約 7000-7500」），讓 HQ 連總量都猜不準確——適合競爭性極強的工會型客戶。

---

## Part II：商業頂點（Business Excellence）

### 6. 商業模式畫布（Business Model Canvas）

| 元件 | 內容 |
|---|---|
| **Customer Segments** | 50-100 人（上限）小型製造業；多數實際 10-20 人 + 外包鏈 |
| **Value Propositions** | LINE 原生 ERP / 自然語言操作 / 行動優先 / MESH 多廠 / 1/10 SAP 價格 |
| **Channels** | 直銷（業務拜訪）/ 工會推廣 / 製造業展覽 / 雲市集 |
| **Customer Relationships** | 訂閱制 + 客戶成功經理（CSM） |
| **Revenue Streams** | 訂閱 30-50 萬/年 + 顧問 / 客製化 / 訓練 |
| **Key Resources** | 程式碼 / Multi-Agent / 客戶數據 / 品牌 |
| **Key Activities** | 開發 / 客戶導入 / 教育訓練 / 客戶成功 |
| **Key Partners** | LINE 雲端 / AWS / Azure / DeepSeek/Anthropic / 工會 / 顧問公司 |
| **Cost Structure** | 開發人員 / Cloud 費 / LLM API 費 / 客戶獲取成本 |

---

### 7. 競爭護城河（Moats）

#### 7.1 五大護城河

```
                  競爭護城河五力
                  ┌─────────────┐
                  │  LLM-ERP    │
                  └──────┬──────┘
                         │
        ┌────────┬───────┼───────┬────────┐
        ▼        ▼       ▼       ▼        ▼
    Network   Switch   Data    Brand    Tech
    Effect    Cost     Moat    Trust    Lead
```

| 護城河 | 強度 | 來源 |
|---|---|---|
| **1. Network Effect** | ⭐⭐⭐ | 外協廠越多，整個生態越值錢（VMI 想接的廠都進來了） |
| **2. Switching Cost** | ⭐⭐⭐⭐ | 客戶把所有 BOM/客戶/供應商搬上來後，難以離開 |
| **3. Data Moat** | ⭐⭐⭐⭐ | 累積各廠工序時間、品質、交期數據 → 訓練更精準的 LLM |
| **4. Brand Trust** | ⭐⭐ | LINE 原生、台灣製造 → 中小企業信任 |
| **5. Tech Lead** | ⭐⭐⭐ | Multi-Agent + MESH 架構，2-3 年領先傳統 ERP |

#### 7.2 為什麼別人複製不了

- **SAP/Oracle**：包袱太重，無法做小廠輕量化（會自我蠶食）
- **Odoo**：開源但中文 / LINE / MESH 都弱
- **新創**：技術可行但需要 1-2 年才能追上我們的累積
- **自建**：客戶沒這預算與技術

---

### 8. Land-and-Expand 策略

#### 8.1 階段性擴張

```
階段 1：Land（單點突破）
  ↓ 一個 15 人工坊
  → 老闆愛上 LINE Bot
  → 全廠開始用
  ↓
階段 2：Deepen（單客戶深化）
  ↓ 加更多模組
  → 工坊長到 30 人
  → 接外包鏈（變成 50 人虛擬團隊）
  ↓
階段 3：Multiply（推薦擴散）
  ↓ 工會老闆社群
  → 一個推 10 個
  → 變成同業標配
  ↓
階段 4：Platform（生態平台）
  ↓ 外協廠也是「客戶」
  → 客戶的客戶也接入
  → 形成製造業 LINE-Native 標準
```

#### 8.2 客戶生命週期價值（CLV）

| 階段 | 年費 | 滯留期 | CLV |
|---|---|---|---|
| Year 1（試用） | 30 萬 | – | 30 萬 |
| Year 2（深化） | 40 萬（加模組） | – | 70 萬 |
| Year 3+（穩定） | 50 萬（含外協加值） | 5+ 年 | **250+ 萬** |

→ 一個 50 人廠客戶，5 年累計 CLV ≈ 250 萬。CAC（獲客成本）若控在 30 萬以下，LTV/CAC > 8x（SaaS 黃金比）。

---

### 9. 訂價策略（Pricing）

#### 9.1 三層訂閱制

| 方案 | 適合 | 年費 | 包含 |
|---|---|---|---|
| **Starter** | 10-30 人單廠 | NT$30 萬 | 12 個 domain + LINE Bot + Mobile + 5 個外協 |
| **Growth** | 30-80 人 + 多廠 | NT$50 萬 | + MESH 多廠（3 廠）+ MRP/MPS + 進階 RBAC |
| **Enterprise** | 80-100 人 + 客製 | NT$80 萬+ | + 客製化 + 顧問 + SLA + 進階 BI |

#### 9.2 附加加值

| 服務 | 計價 |
|---|---|
| 額外外協廠（超過免費額度） | NT$2,000/廠/年 |
| 顧問 / 客製化開發 | NT$15,000/人天 |
| 教育訓練（員工 30 人以下） | 免費 |
| 教育訓練（30 人以上） | NT$10,000/場 |
| 24/7 SLA 支援 | +NT$10 萬/年 |
| 雲端代管 | +NT$5 萬/年 |

#### 9.3 跟競爭定位

```
NT$200 萬 ┤  SAP B1 / Oracle
NT$100 萬 ┤  鼎新 / 正航（含顧問費）
NT$ 50 萬 ┤  ★ 我們 Growth ★
NT$ 30 萬 ┤  ★ 我們 Starter ★
NT$  0 元 ┤  Excel + LINE（現況）/ Odoo 開源（DIY）
```

我們填補了「Excel 太陽春」與「鼎新太貴」之間的空白。

---

### 10. 平台經濟學（Platform Economics）

#### 10.1 兩邊市場（Two-Sided Market）

我們不是只服務客戶（單邊），而是建構**雙邊網絡**：

```
   主廠（付費）          外協廠（不付費）
    ↑                        ↑
    │ 想知道外協進度          │ 想拿到工單與付款
    │                        │
    ↓                        ↓
       LLM-ERP 平台（我們）
              ↑
              │ 提供工單流、QR Bot
              │
        外協生態擴大 → 主廠更有議價力
        主廠更多 → 外協廠更想加入
        → 正向飛輪
```

#### 10.2 何時收外協廠費？

**Phase 1-4：不收**（先擴大網絡）
**Phase 5+**：若同一外協廠服務 3+ 主廠，收 NT$500/月（多廠 dashboard）

---

### 11. 與工業 4.0 / 智慧製造的關係

| 工業 4.0 元素 | 我們的對應 |
|---|---|
| **CPS（Cyber-Physical System）** | MES 接機台（Phase 6+） |
| **IIoT** | 設備感測器（Phase 6+） |
| **AI 預測維護** | LLM + 機台異常數據（Phase 5+） |
| **數位孿生（Digital Twin）** | What-if 模擬（Phase 5+） |
| **預測排程（Predictive Scheduling）** | APS + ML（Phase 5+） |
| **生產線可視化** | 即時 SSE 儀表板 ✅（已有） |

→ 我們從**管理層的數位化**入手（成本低、見效快），而非**設備層的智慧化**（成本高、ROI 慢）。
→ 等管理層成熟後，再向下整合到設備層——**從上到下的工業 4.0**。

---

## Part III：學術 + 商業的交織

### 12. Data Moat 的學術機制

#### 12.1 我們收集什麼數據

| 數據 | 學術價值 | 商業價值 |
|---|---|---|
| 各廠 BOM 結構 | 知識圖譜 | 預測零件需求 |
| 各廠工序時間 | 排程演算法訓練 | OEE 基準對標 |
| 各廠不良率 | 品質統計分布 | 預測 NC 機率 |
| 業務對話 LLM | RLHF 訓練 | 更精準的 agent |
| 各廠交期延遲原因 | 因果分析 | 風險預警 |

#### 12.2 數據網絡效應（Data Network Effect）

```
客戶 1 用 → 累積數據 1
客戶 2 用 → 累積數據 1+2
客戶 N 用 → 累積數據 1+2+...+N → AI 更精準 → 客戶 N+1 更想用
```

→ **越多客戶用，AI 對下個客戶越有用**。這是 SaaS 與 ML 結合的核心優勢。

---

### 13. 為什麼這個專案能改變產業

#### 13.1 三個結構性破壞

1. **ERP 不再是「會用的人才」的特權**
   - 過去：必須會 SAP 才能查報表 → 顧問費吸血
   - 現在：用 LINE 講中文就行 → 老闆親自用

2. **製造業 IT 從「成本中心」變「策略資產」**
   - 過去：ERP 是負擔 → 拿來給會計用
   - 現在：ERP 是競爭優勢 → 業務、廠長、外協廠都受益

3. **MESH 模式讓「家庭工廠」也能企業化**
   - 過去：10 人廠買不起 ERP，永遠是「黑工廠」
   - 現在：10 人廠用 30 萬就有完整系統 → 接得到大客戶訂單

#### 13.2 終極願景

> **「讓台灣每一家中小製造業，都用 LINE-Native ERP 跑得起企業級營運。」**
>
> 過去工業時代的紅利屬於大企業，因為它們買得起 SAP。
> AI 時代的紅利屬於「能用 AI 的人」，無關公司大小。
> 我們把這個紅利打包成 30 萬一年的訂閱，讓台灣 14 萬家中小製造業都能享有。

---

## 14. 結語：學術與商業的閉環

```
         學術（為什麼）                     商業（怎麼賺）
       ┌──────────────┐                ┌──────────────┐
       │  DDD          │                │ 30 萬訂閱     │
       │  Multi-Tenant │                │ Land-Expand   │
       │  Event-Driven │ ←──互相滋養─→  │ Network Effect│
       │  Game Theory  │                │ Data Moat     │
       │  Info Security│                │ Platform Econ │
       └──────────────┘                └──────────────┘
              ↓                                ↓
       做出沒人能複製的東西               做出客戶離不開的東西
```

我們不是寫 ERP——
**我們是用學術武裝商業，用商業驗證學術。**

---

**最後更新**：2026-05-14
**作者**：Claude（依使用者「補強到學術及商業頂點」指示撰寫）
**閱讀對象**：創辦人 / 投資人 / 技術合夥人
