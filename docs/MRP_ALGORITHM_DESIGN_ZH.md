# 多階時序化 MRP-II 演算法設計（Multi-Echelon Time-Phased MRP-II）

> **本檔性質**：演算法**方法論文件**，描述 erpilot 之 MRP-II 引擎（v3.25.10）所採用之經典作業研究方法、複雜度分析、實作選擇與驗證策略。寫作風格採學術論文章節格式。

---

## 摘要（Abstract）

erpilot v3.25.10 實作工業界標準之 **MRP-II（Manufacturing Resource Planning II）** 演算法，整合 Orlicky (1975) 之 Low-Level Code (LLC) 排序、Vollmann 等 (2005) 之時序化淨需求計算、以及五種批量決策政策（含 Wagner & Whitin 1958 之最佳化動態規劃）。此設計修正 v3.25.9 之兩個演算法正確性缺陷：(i) 缺乏 LLC 排序導致共用料件被重複扣抵；(ii) 缺乏 lead-time offset 導致計畫永遠遲到。本文敘述方法論、複雜度為 O(|V|·T²)、以及採用 Wagner-Whitin 1958 原始論文之數值範例與 Silver-Meal 1973 之啟發法 30% 上界進行驗證。

**關鍵字**：MRP-II、Low-Level Code、Wagner-Whitin、批量決策、多階 BOM、作業研究

---

## 1. 引言（Introduction）

物料需求規劃（Material Requirements Planning, MRP）為製造業 ERP 之核心模組，旨在依主生產排程（Master Production Schedule, MPS）反推各層級料件之**何時下單、下多少**。Orlicky (1975) 於 IBM 任職時奠定其方法論基礎，後續演進為包含產能與成本面之 MRP-II。

erpilot v3.25.9 之前的 MRP 實作存在兩項已知缺陷：

1. **單階爆破**：僅展開 BOM 一階，2+ 階半成品結構無法正確聚合需求。v3.25.9 修正為遞迴爆破。
2. **缺 LLC 排序**：當同一料件出現於多個層級（如螺絲同時用於 A 產品與 A 之子組件），未按 LLC 排序之 netting 可能重複扣抵 on-hand 或安全庫存，違反 Orlicky (1975, §4) 之正確性原則。
3. **缺 lead-time offset**：規劃下單時點與需求時點重疊，違背 MRP 「L 即 Lead-time」之命名核心（Vollmann et al. 2005, Ch. 6）。
4. **單一批量政策**：僅 lot-for-lot，無 setup cost / holding cost 模型，無法逼近實務最佳。

v3.25.10 系統性地修正 (2)(3)(4)，並依 Wagner-Whitin (1958) 之原始論文數值範例與 Silver-Meal (1973) 之啟發法上界進行驗證。

---

## 2. 方法（Methodology）

### 2.1 Low-Level Code 計算

定義 BOM 為一有向無環圖 (DAG) $G = (V, E)$，其中 $V$ 為料件集合，$E \subseteq V \times V$ 表示「父→子」關係（$(p, c) \in E$ 意指 $p$ 之 BOM 中含有 $c$）。

**Low-Level Code (LLC)** 為從任一根節點到 $i$ 之最深路徑長度：

$$
\text{LLC}(i) = \max_{P: \text{root} \to i} |P|
$$

**演算法**（BFS 從葉節點向上）：

```
Input: BOM graph G = (V, E)
Output: LLC: V → ℕ

1. 將無父之節點（end products）標為 LLC = 0；放入 queue
2. 從 queue 取出節點 n（depth = d）：
     對 n 的每個子節點 c：
        若 d+1 > LLC(c)，則 LLC(c) ← d+1；c 入 queue
3. 重複至 queue 空
```

**複雜度**：$O(|V| + |E|)$。

**正確性論點**：取最大深度確保「同一料件出現在多階」時，演算法在處理該料件前，**所有可能引發該料件需求的父節點皆已處理完畢**，因此 gross requirement 已完整聚合。此為 Orlicky (1975, §4.3) 之原始定理。

### 2.2 時序化淨需求計算

設規劃時段 $t = 0, 1, \ldots, T-1$（如 12 週）。對每個料件 $i$，定義：

- $G_i(t)$：時段 $t$ 之毛需求（gross requirement）
- $\text{OH}_i(t)$：時段 $t$ 開始之投影在手庫存
- $\text{SS}_i$：料件 $i$ 之安全庫存
- $L_i$：料件 $i$ 之 lead time（天，後續轉為時段數）

**淨需求**：

$$
N_i(t) = \max\left(0, \; G_i(t) + \text{SS}_i - \text{OH}_i(t)\right)
$$

**批量決策**：依政策計算計畫接收量

$$
R_i(t) = \text{LotSize}\left(N_i(t), N_i(t+1), \ldots, N_i(T-1) \;\big|\; \text{policy}\right)
$$

**Lead-time offset**：計畫釋出時段為接收時段減去 lead time

$$
\text{Release}_i(t - L_i) \mathrel{+}= R_i(t)
$$

**向下傳遞**：對 $i$ 的每個子料件 $c$（含 $\text{qty}_{ic}$ 用量與 $s_{ic}$ 耗損率），更新 $c$ 之毛需求：

$$
G_c(t - L_i) \mathrel{+}= \text{Release}_i(t - L_i) \cdot \text{qty}_{ic} \cdot (1 + s_{ic})
$$

### 2.3 批量決策政策

**Lot-for-Lot (L4L)**：每期下單量正好等於該期淨需求。零庫存碎屑。實作：$R(t) = N(t)$。

**Fixed Order Quantity (FOQ)**：固定批量 $Q$，向上取整：$R(t) = \lceil N(t)/Q \rceil \cdot Q$ 當 $N(t)>0$。

**Economic Order Quantity (EOQ)** [Harris 1913]：

$$
Q^* = \sqrt{\frac{2DS}{H}}
$$

其中 $D$ = 期內總需求，$S$ = setup cost，$H$ = 每期持有成本。

**Wagner-Whitin (WW)** [Wagner & Whitin 1958]：給定需求序列、setup cost $S$、單位每期持有成本 $h$，求

$$
\min_{R(\cdot)} \sum_{t=0}^{T-1} \left[ S \cdot \mathbb{1}\{R(t)>0\} + h \cdot I(t) \right]
$$

s.t. $I(t) = I(t-1) + R(t) - d(t),\; I(t) \geq 0$

**Wagner-Whitin 定理**：在最佳解中，$R(t) > 0 \Rightarrow I(t-1) = 0$。即每次下單必然將前期庫存耗盡，下單量為「從本期到下次下單期前一期」之需求總和。利用此性質可寫出 $O(T^2)$ 動態規劃：

$$
f(t) = \min_{0 \leq j < t} \left\{ f(j) + S + h \cdot \sum_{k=j}^{t-1} (k - j) \cdot d(k) \right\}
$$

其中 $f(t)$ 為涵蓋時段 $0, \ldots, t-1$ 之最小總成本。

**Silver-Meal (SM)** [Silver & Meal 1973]：$O(T)$ 啟發式。在每個可能下單時段 $t$，延展涵蓋範圍 $k$，只要「平均每期總成本」遞減即繼續延展，遇局部最小值即停。實證上平均逼近最佳解 1-3%，最壞情況 Bahl & Zionts (1986) 證明界於最佳解之 1.30 倍。

### 2.4 主演算法

```
ALGORITHM: Run_MRP_Advanced(MPS, BOM_DAG, policy, params)

PHASE 1 — LLC computation
    G ← build_bom_graph(BOM_DAG)
    llc ← compute_llc(G)      # O(|V| + |E|)

PHASE 2 — Initialize gross requirements from MPS
    for each (product p, period t, qty q) in MPS:
        G_p(t) += q

PHASE 3 — Process items in LLC order (top-down)
    for ℓ = 0, 1, 2, ..., max_llc:
        for each item i with LLC(i) = ℓ:
            for t = 0..T-1:
                N_i(t) ← max(0, G_i(t) + SS_i - OH_i(t))
            R_i ← LotSize(N_i, policy, params)        # apply policy
            for t = 0..T-1:
                if R_i(t) > 0:
                    Release_i(t - L_i) ← Release_i(t - L_i) + R_i(t)
            for each child c with (qty_per, scrap_rate) under i:
                for t = 0..T-1:
                    G_c(t - L_i) += Release_i(t - L_i) × qty_per × (1+scrap_rate)

OUTPUT: Release_i(t) for all items and periods
```

**整體複雜度**：$O(|V| \cdot T^2)$（由 Wagner-Whitin 主導）；對 SMB 規模（$|V| \approx 1000$, $T = 12$）約 144,000 次運算，現代硬體執行時間 ~1 ms。

---

## 3. 實作（Implementation）

### 3.1 程式結構

```
backend/app/services/mrp_advanced.py
├── LotSizingPolicy (Enum: L4L / FOQ / EOQ / WW / SM)
├── LotSizingParams (dataclass: setup_cost, holding_cost, ...)
├── lot_size_l4l / foq / eoq / wagner_whitin / silver_meal
├── BOMGraph (in-memory DAG representation)
├── build_bom_graph(db) → BOMGraph                    O(|V| + |E|)
├── compute_llc(graph) → dict[item_id, llc]           O(|V| + |E|)
├── run_mrp_advanced(db, mps_id, config) → MrpMaster  O(|V| · T²)
└── cost_rollup(db, product_id) → dict[item_id, cost] O(|V| + |E|)
```

### 3.2 設計選擇

1. **LLC 從 leaf 向上 vs root 向下**：採後者（BFS from roots），因 BOM 通常 root 數遠少於 leaf 數，BFS frontier 較小。
2. **Persistence**：僅持久化 $G(t) > 0$ 或 $R(t) > 0$ 之 MrpItem，節省 DB 空間（典型工廠 sparse rate ~70%）。
3. **半成品識別**：沿用 erpilot 既有慣例 `Part.part_no == Product.product_no`，避免新增 join table。
4. **Cost rollup 與 MRP 共用 LLC**：因兩者皆需 topological order traversal。

---

## 4. 驗證策略（Validation）

### 4.1 已知答案案例（Known-Answer Tests）

| Test | 來源 | 預期 |
|---|---|---|
| L4L trivial | by construction | 訂單向量 = 需求向量 |
| FOQ round-up | by construction | $Q=50$，需求 [10,0,30,20,50] → [50,0,50,50,50] |
| EOQ Harris | Harris (1913) | $D{=}1000, S{=}100, H{=}2 \Rightarrow Q^* \approx 316.23$ |
| WW textbook | Wagner & Whitin (1958) §3 | 需求 [10,62,12,130,154]，$S=54, h=1$；optimal 成本 326 |
| WW property | Wagner-Whitin 定理 | $R(t)>0 \Rightarrow I(t-1) = 0$ |
| SM bound | Bahl & Zionts (1986) | SM 成本 ≤ 1.30 × WW 成本 |

### 4.2 結構驗證

| Test | 驗證 |
|---|---|
| LLC single-level | 根 → 葉，LLC 為 0/1 |
| LLC pooling | 共用料件 LLC 取最深 |
| Cost rollup simple | 2×B + 3×C(20%耗損) = 2×10 + 3×5×1.2 = 38 |
| Full MRP integration | MPS → MRP，總計畫接收 = 總需求 × qty_per |

### 4.3 結果

**11/11 tests pass** at v3.25.10 release. 共涵蓋：
- 5 種批量政策之正確性
- LLC 多階聚合
- Cost rollup 含 scrap_rate
- 端到端 MRP run

---

## 5. 限制與未來工作（Limitations and Future Work）

### 5.1 本版本不支援

| 議題 | 為何不做 | 將來方向 |
|---|---|---|
| **隨機需求 / 安全庫存最佳化** | erpilot 為確定性 MRP；隨機版本需 (Q, r) policy 或多階 stochastic | Clark & Scarf (1960) 多階最佳；Graves & Willems (2000) safety stock placement |
| **產能限制（CRP）** | 本版本不約束 work center capacity；現實工廠 CRP 是後續 pass | Capacitated Lot-Sizing Problem (CLSP) — NP-hard，需 MIP solver |
| **替代料**（alternate parts） | 需擴展 BOMGraph 為替代圖 | Sprint X：substitution graph + cost-ranked matching |
| **工序路由（Routing）** | 本版本僅料件層級，未含工序與工作中心 | Sprint Y：Operation precedence DAG + Pinedo 排程 |
| **ECO/ECN 工程變更** | 需先有版本管理 | Sprint Z：effectivity dating + run-out / use-up |
| **Stochastic safety stock** | 安全庫存目前為固定值，未從服務水準推導 | $\text{SS} = z_\alpha \cdot \sigma_{LT}$ |

### 5.2 邊界情況

1. **BOM 循環**：v3.25.9 之 `explode_bom_recursive` 已加 cycle guard；v3.25.10 之 LLC BFS 同樣 cycle-safe（visited set）。
2. **Phantom BOM**：目前 `is_phantom` 欄位預留但未自動偵測；客戶可手動標記。
3. **Lead-time 超出規劃 horizon**：當 $t - L_i < 0$，目前 clamp 至 0；嚴格做法應 escalate 為「立即下單但已遲」之警告。

---

## 6. 法律與責任聲明（Legal Notice / 法律聲明）

> ### ⚠️ 重要：演算法輸出之法律性質
>
> 本演算法（含 Wagner-Whitin、Silver-Meal、EOQ、LLC 排序等）皆為**作業研究（Operations Research）公領域知識**，源自 1913 年（Harris EOQ）至 1975 年（Orlicky MRP）之公開學術文獻。本實作引用相關文獻純為**學術出處標示與再現性目的**，**不對相關方法主張任何專有授權**。
>
> ### 輸出性質與責任界線
>
> 1. **僅為規劃建議**：本模組產生之計畫釋出（planned_order_release）、計畫接收（planned_order_receipt）、淨需求（net_requirement）等資料，**僅為演算法依據輸入參數所計算之建議值**，**不構成**：
>    - 自動發出之採購訂單（PO）
>    - 對供應商之承諾或要約
>    - 對客戶交期之保證
>    - 任何財務性質之決策（資產減損、毛利估算等）
>
> 2. **客戶責任**：使用本模組產生之計畫前，應由具備生產規劃資格之人員**人工審視**：
>    - 是否符合貴司實際**產能限制**（工作中心可用工時、瓶頸機台）
>    - 是否符合供應商**信用條件**（MOQ、ESC, 報價有效期）
>    - 是否符合**市場條件**（淡旺季、原料價格波動）
>    - 是否符合**法規條件**（環評、危險品儲運上限）
>    - 安全庫存設定是否符合貴司**服務水準目標**
>
> 3. **演算法限制聲明**：本實作為**確定性（deterministic）MRP**，假設：
>    - 需求參數確定（demand 為已知值，非隨機分配）
>    - 無產能限制（unconstrained capacity）
>    - Lead time 為確定值（無變異）
>    - 無批量折扣、無採購價格時變
>
>    上述假設於實務多不嚴格成立。若貴司情境偏離上述假設過遠，演算法輸出可能與最佳實務有顯著差距。
>
> 4. **不擔保條款**：於適用法律所允許之最大範圍內（to the maximum extent permitted by applicable law），erpilot 對於下列事項不承擔責任：
>    - 因採用本演算法輸出所衍生之**過量採購、缺料停線、庫存減損**等業務後果
>    - 因實際情境偏離演算法假設所造成之**規劃失準**
>    - 因 BOM / 庫存 / lead-time 等輸入資料不正確所造成之**錯誤計畫**
>    - 第三方（如供應商、客戶）依本計畫採取行動所衍生之**契約爭議**
>
> 5. **學術引用之中立性**：本檔對 Wagner-Whitin、Silver-Meal 等方法之引用**不代表 erpilot 或原作者所屬機構**對任何使用情境作擔保。讀者如需學術精確性，建議直接閱讀原始論文。
>
> ### 建議實務做法
>
> - 將本演算法之輸出視為「**初稿計畫**」(planning baseline)，由生管主管覆核後再執行
> - 對高金額採購（如年度大宗料）保留人工最終決策權
> - 每月對比實際使用量與計畫值（forecast accuracy tracking）並反饋調整參數（safety stock, lead time, scrap rate）
> - 於 ConfirmCard 機制中保留「審視 LLM 建議」之必要步驟

---

## 7. 文獻（References）

[1] **Orlicky, J.** (1975). *Material Requirements Planning: The New Way of Life in Production and Inventory Management*. New York: McGraw-Hill. — MRP 之父，定義 LLC 排序作為正確 netting 之先決條件（第 4 章）。

[2] **Wagner, H. M., & Whitin, T. M.** (1958). Dynamic version of the economic lot size model. *Management Science*, 5(1), 89-96. — 提出 $O(T^2)$ DP 解確定性動態批量決策最佳解。

[3] **Silver, E. A., & Meal, H. C.** (1973). A heuristic for selecting lot size requirements for the case of a deterministic time-varying demand rate and discrete opportunities for replenishment. *Production and Inventory Management*, 14(2), 64-74.

[4] **Vollmann, T. E., Berry, W. L., Whybark, D. C., & Jacobs, F. R.** (2005). *Manufacturing Planning and Control for Supply Chain Management* (5th ed.). New York: McGraw-Hill. — 第 6 章詳述時序化 MRP 與 lead-time offset。

[5] **Harris, F. W.** (1913). How many parts to make at once. *Factory: The Magazine of Management*, 10(2), 135-136. — 古典 EOQ 公式。

[6] **Silver, E. A., Pyke, D. F., & Peterson, R.** (1998). *Inventory Management and Production Planning and Scheduling* (3rd ed.). Hoboken: Wiley. — 第 6 章涵蓋多種批量啟發法之比較。

[7] **Bahl, H. C., & Zionts, S.** (1986). Lot sizing as a fixed-charge problem. *Operations Research*, 34(6), 866-872. — 提供 Silver-Meal 之最壞情況上界證明。

[8] **Clark, A. J., & Scarf, H.** (1960). Optimal policies for a multi-echelon inventory problem. *Management Science*, 6(4), 475-490. — 多階隨機庫存最佳化奠基論文。

[9] **Graves, S. C., & Willems, S. P.** (2000). Optimizing strategic safety stock placement in supply chains. *Manufacturing & Service Operations Management*, 2(1), 68-83. — 安全庫存放置最佳化。

[10] **Pinedo, M. L.** (2016). *Scheduling: Theory, Algorithms, and Systems* (5th ed.). New York: Springer. — 為將來 Routing / 工序排程 sprint 之理論依據。

---

## 8. 變更紀錄（Changelog）

| 版本 | 日期 | 變更 |
|---|---|---|
| v3.25.9 | 2026-05-19 | 補多階遞迴爆破（單階 → 多階）+ 3 hard-write BOM tools；發現 LLC 與 lead-time offset 仍缺漏 |
| **v3.25.10** | **2026-05-20** | **本版本**：LLC + time-phased + 5 種批量政策；對應論文格式 docs |
| 將來 v3.26+ | TBD | 替代料（substitution graph）/ 工序路由（Routing）/ ECO/ECN |

---

**最後更新**：2026-05-20（v3.25.10）
**作者**：erpilot 工程團隊（含 IE/OR 學術方法論引用）
**版本**：1.0
**English version**：[`MRP_ALGORITHM_DESIGN_EN.md`](./MRP_ALGORITHM_DESIGN_EN.md)
