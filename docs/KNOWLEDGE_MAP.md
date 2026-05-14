# 知識地圖：PDF 章節 ↔ 程式模組對映

> **本檔目的**：建立《生產排程系統完整參考資料》PDF 14 章與本系統程式碼之間的精準對映，讓任何人都能：
> - 從理論章節 → 找到對應程式
> - 從程式 → 回溯到理論依據
> - 知道每個概念目前實作到哪個層次（schema / service / API / agent）
>
> **狀態符號**：🟢 完整實作　🟡 部分實作　⏳ 規劃中　❌ 未開始

---

## 第 1 章：生產排程概論

| PDF 概念 | 程式對映 | 狀態 |
|---|---|---|
| §1.1 排程定義（What/When/Who） | （系統理念，散見於 API 設計） | 🟢 |
| §1.2 排程三基本問題 | API 操作對映：What=`products`/`parts`、When=`scheduled_start/end`、Who=`work_centers`/`operators` | 🟡 |
| §1.4 演進歷史（1950s→2020s AI） | 本專案定位為 2020s AI-Native 階段 | 🟢（定位） |

---

## 第 2 章：生產規劃層級架構

### §2.1 五層規劃模型（→ 系統採七層展開）

| 層級 | PDF 名稱 | 系統實作位置 | 狀態 |
|---|---|---|---|
| **L0** | 策略規劃 Business Planning | （未實作，Phase 5） | ❌ |
| **L1** | S&OP | （未實作，Phase 5） | ❌ |
| **L2** | MPS | `app/models/mps_mrp.py:MpsMaster, MpsEntry`<br>`app/services/mps_mrp.py:create_mps, add_mps_entry`<br>`app/api/mps_mrp.py` | 🟡 |
| **L3** | MRP | `app/models/mps_mrp.py:MrpMaster, MrpItem`<br>`app/services/mps_mrp.py:run_mrp`（單階展開） | 🟡 |
| **L4** | RCCP/CRP | （未實作，Phase 1） | ❌ |
| **L5** | APS/FCS | （未實作，Phase 2） | ❌ |
| **L6** | MES/SFC | `app/models/production.py:ProductionOrder, Operation, DispatchLog` | 🟡 |

### §2.3 時間柵欄（Time Fence）

| 概念 | 程式對映 | 狀態 |
|---|---|---|
| DTF（Demand Time Fence） | `app/models/mps_mrp.py:TimeFence.dtf_days` | 🟡 schema 有，無強制邏輯 |
| PTF（Planning Time Fence） | `app/models/mps_mrp.py:TimeFence.ptf_days` | 🟡 schema 有，無強制邏輯 |
| 凍結/穩定/彈性區判斷 | （待實作） | ❌ |

### §2.4 閉環回饋機制

| 環節 | 程式對映 | 狀態 |
|---|---|---|
| MPS → MRP | `run_mrp(mps_id)` 已串通 | 🟢 |
| MRP → RCCP/CRP | （待實作） | ❌ |
| RCCP → 回饋調整 MPS | （待實作） | ❌ |
| 工單發放 → MES | `release_production_order` → `wo.released` event | 🟡 |
| MES → 完工入庫 | （`complete_production_order` 有，但未自動入庫成品） | 🟡 |
| 成本結算 → 績效分析 | （未實作） | ❌ |

---

## 第 3 章：S&OP 銷售與作業規劃

| §3.X 主題 | 程式對映 | 狀態 |
|---|---|---|
| §3.2 五步驟流程 | （未實作，Phase 5） | ❌ |
| §3.3 關鍵產出（生產率/庫存目標/交期承諾/採購前置） | （未實作） | ❌ |
| §3.4 S&OP 與 MPS 關係（aggregate→disaggregate） | （未實作） | ❌ |

---

## 第 4 章：MPS 主生產排程

| §4.X 主題 | PDF 要求 | 程式對映 | 狀態 |
|---|---|---|---|
| §4.2 MPS 輸入 | 客戶訂單、銷售預測、預計庫存、安全庫存、已發放工單、時間柵欄 | `MpsEntry`：forecast_demand / actual_demand / planned_production | 🟡 缺：預測比對、已發放工單合併 |
| §4.3 時段化展算 4 步驟 | 毛需求→PAB→新 MPS 計畫→ATP | `MpsEntry.projected_on_hand = planned - actual_demand`（過於簡化） | 🟡 待補完整公式 |
| §4.3 PAB 公式 | PABt = PAB(t-1) + 計畫接收 - 毛需求 + MPS 計畫 | 需重寫 | ❌ |
| §4.3 ATP 計算 | 銷售人員承諾用 | `MpsEntry.available_to_promise = max(0, planned - actual)`（簡化） | 🟡 |
| §4.5 KPI（MPS 達成率/訂單滿足率/庫存周轉/MPS 變更次數） | （未實作） | ❌ |

**Phase 1 任務**：在 `app/services/mps_mrp.py` 重寫完整 PAB/ATP 時段化公式。

---

## 第 5 章：MRP 物料需求規劃

| §5.X 主題 | PDF 要求 | 程式對映 | 狀態 |
|---|---|---|---|
| §5.2 MRP 輸入輸出 | MPS+BOM+庫存+物料主檔 → 計畫訂單/採購建議/行動訊息/Pegging | `run_mrp(mps_id)` 已串接前 3 個輸入 | 🟡 |
| §5.3 BOM 多階展開 | Level 0 → Level N 遞迴 | 目前只展 Level 1（直接子件） | 🟡 |
| §5.4 淨需求計算 | = 毛需求 - 現有庫存 - 在途 + 已分配 + 安全庫存 | 簡化為 `max(0, gross - on_hand)` | 🟡 |
| §5.5 時段化與提前期偏移 | 物料下單時間 = 需要時間 - 前置期 | 未實作 | ❌ |
| §5.6 批量規則 | Lot-for-Lot / FOQ / POQ / EOQ | 全部未實作 | ❌ |
| §5.7 行動訊息 | Release/Reschedule In/Reschedule Out/Cancel/Firm | 未實作 | ❌ |
| §5.8 常見陷阱 | BOM/前置期/庫存不準、不跑產能、頻率太低、無 Pegging | 系統設計上避免了一部分（async + audit），其餘待 Phase 1 補 | 🟡 |

**Phase 1 任務**：MRP 改寫為遞迴多階展開 + 淨需求完整公式 + Action Message 產出。

---

## 第 6 章：產能規劃（RCCP/CRP/FCS）

| §6.X 主題 | PDF 要求 | 程式對映 | 狀態 |
|---|---|---|---|
| §6.1 產能規劃四層級（RRP/RCCP/CRP/FCS） | 應有四個獨立計算層 | 未實作 | ❌ |
| §6.2 RCCP 產能清單法 | 每產品需要多少關鍵工作中心工時 | 未實作 | ❌ |
| §6.3 CRP 細產能規劃 | 依途程做時段負載 | 未實作 | ❌ |
| §6.4 FCS 三種方式 | Forward / Backward / Bottleneck-based | 未實作 | ❌ |
| §6.5 產能策略 | Overtime/Outsource/Add Shift/TOC/Leveling | 未實作 | ❌ |

**Phase 1 任務**：新增 `app/services/capacity.py` + `app/models/capacity.py`（BillOfCapacity, CapacityLoad）。

---

## 第 7 章：APS 高級規劃與排程

| §7.X 主題 | PDF 要求 | 程式對映 | 狀態 |
|---|---|---|---|
| §7.2 APS vs MRP 6 大差異 | 有限產能/雙向/最佳化/多資源/局部重排/what-if | 未實作 | ❌ |
| §7.3 APS 6 大核心功能 | ATP/CTP、多廠 MRP、FCS、最佳化、What-if、執行追蹤 | 未實作 | ❌ |
| §7.4 排程策略 | Due Date/SPT/CR/Drum-Buffer-Rope/多目標 | 未實作 | ❌ |
| §7.5 What-if 模擬 | 多情境比較交期/成本/利用率 | 未實作 | ❌ |

**Phase 2 任務**：建立 `app/scheduling/` 模組，內含 algorithms / what_if / multi_objective。

---

## 第 8 章：MES 製造執行系統

| §8.X 主題 | PDF 要求 | 程式對映 | 狀態 |
|---|---|---|---|
| §8.3 MES 8 大模組 | 工單管理/排程派工/站點報工/物料追蹤/品質管控/設備監控/人員管理/異常管理/追溯管理 | 工單管理 🟢、品質 🟡、其他 ❌ | 🟡 |
| §8.4 資料收集點 | 開工掃描+物料投入+完工報工 | `DispatchLog` 有 schema、缺實際掃描入口 | 🟡 |
| §8.5 OEE | 可用率 × 性能率 × 良品率 | 未實作 | ❌ |
| §8.6 MES → 排程回饋 | 完工時間/工時/良率回饋更新計畫 | 未實作 | ❌ |

**Phase 3 任務**：新增 `app/services/mes.py` 實作 OEE 計算 + 報工 API。

---

## 第 9 章：Shop Floor Control 現場派工

| §9.X 主題 | PDF 要求 | 程式對映 | 狀態 |
|---|---|---|---|
| §9.2 SFC 6 大功能 | Order Release/Dispatching/Data Collection/Order Tracking/Exception Handling/Performance Analysis | 部分（release 有、dispatch schema 有） | 🟡 |
| §9.3 派工規則 | FIFO/EDD/SPT/LPT/CR/MROP/LWKR/SLACK（8 種） | 全部未實作 | ❌ |
| §9.4 派工清單 Dispatch List | 工作中心級的優先序清單 | 未實作 | ❌ |
| §9.5 看板與拉式生產 | Push / Pull / Hybrid | 未實作 | ❌ |

**Phase 3 任務**：實作 8 種派工規則 → `app/scheduling/dispatch_rules.py`，並提供 dispatch list API。

---

## 第 10 章：排程演算法分類與比較

| §10.X 主題 | PDF 要求 | 程式對映 | 狀態 |
|---|---|---|---|
| §10.1 演算法分類樹 | Exact / Heuristic / Metaheuristic / AI / Hybrid | 未實作 | ❌ |
| §10.2 演算法比較表（13 種） | MIP/DP/Rules/Johnson/NEH/GA/SA/TS/ACO/PSO/RL/Hybrid | 未實作 | ❌ |
| §10.3 GA 詳解 | 編碼/適應度/選擇交配變異/收斂 | 未實作 | ❌ |
| §10.4 SA 詳解 | 溫度/降溫/接受機率 | 未實作 | ❌ |
| §10.5 演算法對照總結 | 各問題類型建議演算法 | 未實作 | ❌ |

**Phase 4 任務**：建立 `app/scheduling/algorithms/`，至少實作 GA + SA + TS + RL 4 種。

---

## 第 11 章：三元排程（人-機-料）

| §11.X 主題 | PDF 要求 | 程式對映 | 狀態 |
|---|---|---|---|
| §11.1 三元定義 | Man（技能/工時/班次）× Machine（設備/速度/換線）× Material（庫存/前置/BOM） | Material 🟢、Machine 🟡、Man ❌ | 🟡 |
| §11.2 vs 傳統排程 | 三維 NP-hard，業界 APS 核心 | 未實作 | ❌ |
| §11.3 數學建模 | 6 大約束（人/機/料/技能/順序/工時） | 部分模型在 ConstraintChecker | 🟡 |
| §11.4 三實務場景 | 半導體晶圓廠/汽車組裝/模具製造 | 文件，無對應實作 | ⏳ |
| §11.5 求解策略 | Decomposition / Integration / Bottleneck-based | 未實作 | ❌ |

**Phase 2 任務**：新增 `app/models/workforce.py`（Skill, ShiftCalendar, EmployeeAvailability）+ Machine 換線矩陣。

---

## 第 12 章：ERP 系統中的生產模塊整合

| §12.X 主題 | PDF 要求 | 程式對映 | 狀態 |
|---|---|---|---|
| §12.1 ERP 8 大模組 | 銷售/生產/採購/庫存/財會/品管/人力/倉儲 | 全部已有 model + API | 🟢 |
| §12.2 SAP PP 核心資料表 | MARA/MAST/STPO/PLAS/CRHD/PLAF/AUFK/AFPO/AFKO/AFVC/MSEG | 概念對映齊全（命名不同） | 🟢 |
| §12.3 跨模組整合（10 對映） | MM↔PP↔SD↔QM↔WM↔FI/CO↔HR | 大部分已串通（透過 EventBus） | 🟢 |
| §12.4 資訊流 vs 物料流 | 12 個流程環節對照 | 大部分已串通 | 🟢 |
| §12.5 訂單到收款完整鏈 | SO→MPS→MRP→PO→入庫→工單→MES→完工→出貨→開票→結算 | 8/10 環節已通（缺 MES 細節 + 結算） | 🟡 |

---

## 第 13 章：常見排程問題與解題方法

| §13.X 主題 | PDF 要求 | 程式對映 | 狀態 |
|---|---|---|---|
| §13.1 排程問題 10 大分類 | 1/Pm/Qm/Fm/FFm/Jm/FJm/Om/RCPSP | 系統需支援 Job Shop (Jm) 與 Flexible Job Shop (FJm) | ❌ |
| §13.2 績效指標 | Cmax/ΣCj/Lmax/ΣTj/U/Fmax/ΣwjCj/ΣwjTj（8 種） | 未實作 | ❌ |
| §13.3 經典解題思路 | 1‖ΣwjTj=WSPT、F2‖Cmax=Johnson、Jm‖Cmax=GA/TS | 未實作 | ❌ |
| §13.4 實務挑戰 9 大 | 交期延遲/庫存高/插單頻繁/異常停線等 | 部分有 Constraint 防範 | 🟡 |

**Phase 4 任務**：演算法引擎中加入 KPI 計算器與問題分類器。

---

## 第 14 章：參考文獻

| 文獻 | 用途 |
|---|---|
| Pinedo (2016) Scheduling: Theory, Algorithms, and Systems | 排程理論主參考 |
| Goldratt (1984) The Goal | TOC 瓶頸理論 |
| Hopp & Spearman (2011) Factory Physics | 製造系統理論 |
| Goldberg (1989) GA in Search... | GA 演算法 |
| Kirkpatrick et al. (1983) Simulated Annealing | SA 演算法 |
| 潘昭賢、賴士葆《作業管理》 | 中文教科書 |
| 劉冰深《生產管理》 | 中文教科書 |
| MESA International White Papers | MES 標準 |
| ISA-95 | 製造系統整合標準 |

---

## 對映完整度總結

| 章節 | PDF 內容點數 | 已實作 | 完成度 |
|---|---|---|---|
| §1 概論 | 4 | 3 | 75% |
| §2 層級架構 | 12 | 4 | 33% |
| §3 S&OP | 6 | 0 | 0% |
| §4 MPS | 10 | 4 | 40% |
| §5 MRP | 12 | 4 | 33% |
| §6 產能規劃 | 8 | 0 | 0% |
| §7 APS | 10 | 0 | 0% |
| §8 MES | 12 | 4 | 33% |
| §9 SFC | 10 | 3 | 30% |
| §10 演算法 | 13 | 0 | 0% |
| §11 三元排程 | 8 | 3 | 38% |
| §12 ERP 整合 | 10 | 8 | 80% |
| §13 排程問題 | 12 | 1 | 8% |
| **合計** | **127** | **34** | **27%** |

> **解讀**：目前完成了大約 27% 的理論覆蓋，且集中在 §12 ERP 整合（80%）與基礎概念（§1, §11 中的料維度）。
> **Phase 1 後預期**：完成 §4/§5/§6 三章 → 整體完成度 → 約 45%
> **Phase 2 後預期**：完成 §7/§11 → 約 60%
> **Phase 3 後預期**：完成 §8/§9 → 約 75%
> **Phase 4 後預期**：完成 §10/§13 → 約 90%
> **Phase 5-7 後**：100%（含 §2 完整閉環 + §3 S&OP + MESH 真實落地）
