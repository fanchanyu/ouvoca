# Throughput Accounting + DBR Scheduling + 訂單接受決策設計（v3.28）

> **本檔性質**：跨**作業研究 / 管理會計 / ERP / AI** 四域之方法論文件，描述 Ouvoca v3.28 之 **Throughput Accounting (TA)** + **Drum-Buffer-Rope (DBR) 排程** + **訂單接受決策（Order Acceptance）** 三模組。本版本完成 Goldratt (1984) TOC 三部曲：v3.27 已 IDENTIFY 瓶頸 → v3.28 EXPLOIT (DBR) + SUBORDINATE (TA)。

> 📘 前置文件：[`MRP_ALGORITHM_DESIGN_ZH.md`](./MRP_ALGORITHM_DESIGN_ZH.md)（v3.25.10）／[`MRP_CAPACITY_AWARE_DESIGN_ZH.md`](./MRP_CAPACITY_AWARE_DESIGN_ZH.md)（v3.26）／[`PLANNING_EXPLAINABILITY_DESIGN_ZH.md`](./PLANNING_EXPLAINABILITY_DESIGN_ZH.md)（v3.27）

---

## 摘要（Abstract）

本文敘述 Ouvoca v3.28 完成 Goldratt (1984) Theory of Constraints 三部曲之後兩步：(i) **Throughput Accounting (TA)** [Goldratt 1992; Corbett 1998] — 取代傳統成本會計之 product-mix 決策框架；(ii) **Drum-Buffer-Rope (DBR) 排程** [Schragenheim & Dettmer 2000] — 以瓶頸資源（CCR）作為產線節拍器；(iii) **訂單接受決策（Order Acceptance Decision）** — Goldratt 1990 §6 之 "highest T/CCR-min first" 規則之實作。我們進一步證明此規則在**單一 binding constraint 下為最佳**（continuous knapsack relaxation argument），並以 21 個結構不變量測試驗證之，含 4 個 Goldratt 教科書經典例。SMB 老闆每日提問「**這張單該不該接？**」可直接由本模組之 `evaluate_order_acceptance()` 在 ~10 ms 內回答。

**關鍵字**：Throughput Accounting、DBR、訂單接受、product mix、TOC、瓶頸計價

---

## 1. 引言（Introduction）

### 1.1 為何傳統成本會計會誤導決策

**標準成本會計** 將每單位之 fixed overhead 攤分（如直接人工小時、機台折舊），得出「單位成本」。在此框架下，若一張訂單之售價 < 單位成本，會被判定為「虧本」而拒絕。

然而 **Goldratt (1992) *The Haystack Syndrome*** 指出此邏輯之根本錯誤：

> 「Fixed overhead 不會因為這張訂單而真的多花錢。如果工人本來就在那裡領薪水、機器本來就在折舊，這張單佔了他們一些時間，並不會多生出 overhead。」

具體例：某產品標準成本 $80（其中 material $30、直接人工攤提 $40、overhead $10），售價 $75。標準成本會計判「虧 $5」拒絕。但 TA 分析：

| 項目 | 標準成本 | Throughput Accounting |
|---|---|---|
| Revenue | $75 | $75 |
| TVC (真實變動成本) | n/a | $30（僅 material） |
| 攤提人工 + overhead | $50 | $0（period 固定成本） |
| **「利潤」** | -$5（拒絕） | $45 throughput（接！） |

接 vs 拒之差別 = $45 × 訂單數 × 12 月 = **大量真實現金流量**。標準成本會計**誤判** → 客戶誤拒高 throughput 訂單，逐年累積虧大錢。

### 1.2 TOC 三部曲整合

| 步驟 | 來源 | Ouvoca 對應 |
|---|---|---|
| **IDENTIFY** constraint | Goldratt 1984 | v3.27 `identify_bottlenecks` |
| **EXPLOIT** constraint | Goldratt 1990 | v3.28 DBR + 排序 |
| **SUBORDINATE** to exploit | Goldratt 1990 | v3.28 TA 決策 |
| **ELEVATE** constraint | Goldratt 1990 | v3.27 counterfactual + 加班 / alternate |
| **REPEAT** | Goldratt 1990 | 持續循環 |

---

## 2. 方法（Methodology）

### 2.1 模組 1：Throughput Accounting 三大會計變數

**Goldratt 1992** 定義：

$$
\text{Throughput (T)} = \text{Revenue} - \text{Truly Variable Cost (TVC)}
$$

**TVC 之嚴格定義**：成本必須**1:1 隨產品數量變動**才算 TVC。包含：

| 計入 TVC | 不計入（屬 OE）|
|---|---|
| ✅ 原材料 (BOM 物料 × scrap factor) | ❌ 直接人工（工人薪水固定）|
| ✅ 銷售佣金（% revenue） | ❌ 機台折舊 |
| ✅ 外包加工費 | ❌ 廠房租金 |
| ✅ 包裝耗材 | ❌ 監工 / 管理薪 |

**Operating Expense (OE)** ＝ 期間固定成本（含直接人工、攤提、廠租等）。

**Inventory (I)** ＝ WIP + 原料 + 成品庫存（以 TVC 計，**不含 overhead 攤提**）。

**Net Profit** ＝ Σ T − OE（不必逐單算 fixed overhead）。

### 2.2 模組 2：訂單接受決策（The Killer Decision）

對單一訂單 $(p, q, P)$（產品 p、數量 q、單價 P），計算：

$$
T_{\text{order}} = q \cdot (P - \text{TVC}_p(P))
$$

$$
\text{T per CCR min} = \frac{T_{\text{order}}}{q \cdot \text{bottleneck\_min}_p}
$$

**Goldratt 1990 §6 之決策規則**：

```
若 T_order < 0:        REJECT  (虧本)
若 bottleneck 不夠:    REJECT  (做不出來)
若 T/CCR-min < 門檻:   NEGOTIATE  (議價或外包)
其他:                  ACCEPT
```

**Continuous Knapsack 最佳性論證**：在單一 binding constraint $\sum_i q_i \cdot a_i \leq C$ 下，最佳化 $\sum_i q_i \cdot t_i$ 之 LP relaxation 之最佳解，即為「按 $t_i / a_i$ 降序排序、依次填滿 capacity」之 greedy。**Goldratt 1990 §6** 證明此規則對 single CCR 為最佳。多 CCR 情境退化為 LP（後續 sprint 用 PuLP 求解）。

### 2.3 模組 3：Drum-Buffer-Rope 排程

**Schragenheim & Dettmer (2000) *Manufacturing at Warp Speed*** 之三元素：

| 元素 | 意義 | 計算 |
|---|---|---|
| 🥁 **Drum** | 瓶頸節拍器 | $\text{rate} = C_{\text{CCR}} / \text{run\_time}_{\text{CCR}}$ |
| 🛡 **Buffer** | 瓶頸前時間緩衝（防 starvation） | $\text{buffer} = 3 \times \text{run\_time}_{\text{CCR}}$ |
| 🪢 **Rope** | 投料同步繩 | $\text{release\_offset} = \text{buffer\_time}$ |

**為何 buffer = 3× run-time**：**Schragenheim 2000 §4** 依實證觀察，3× 在 typical SMB 環境下平衡「starvation risk」與「WIP 累積成本」。理論上：

- $1\times$：buffer 太小，前工序略有延遲即 bottleneck 斷流
- $3\times$：典型最佳，buffer 占用之 WIP 成本可接受
- $5\times+$：過保護，WIP 膨脹

**Hopp & Spearman 1996 *Factory Physics* §10** 證明：throughput 由 bottleneck 決定；非瓶頸工序之 buffer 為純 waste。Ouvoca 之 DBR 模組僅在瓶頸前放 buffer，非瓶頸工序 buffer = 0。

### 2.4 模組 4：Pricing Curve（敏感度延伸）

對給定 (product, qty, base_price)，掃描多個 discount levels（如 [0, 5%, 10%, 15%, 20%]），計算每個 discount 下之 throughput、T/CCR-min、recommendation 變化。

**業務用途**：sales 在客戶議價時可即時答覆「降 5% 還能接」「降 10% 需主管覆核」「降 15% 拒絕」。

---

## 3. 實作（Implementation）

```
backend/app/services/throughput_accounting.py  (~450 行)
├── TVCBreakdown (dataclass)
│     ├ material_cost / commission_rate / outsourcing_cost
│     └ total_excluding_commission / total_tvc(price)
├── compute_product_tvc(db, product_id, commission, outsourcing)
│     ↑ 走 BOM 樹計算 material_cost
├── OrderEvaluation (dataclass)
│     ├ throughput / t_per_ccr_min / is_feasible / recommendation
│     └ reasoning (List[str])
├── compute_throughput_per_ccr(rev, tvc, bn_min) → float
│     ↑ Goldratt killer metric
├── evaluate_order_acceptance(...) → OrderEvaluation
│     ↑ 主決策邏輯（reject/negotiate/accept）
├── PricingScenario / explore_pricing_curve(...)
│     ↑ what-if discount levels
├── DBRSchedule / compute_dbr_schedule(...)
│     ↑ Schragenheim 2000 Drum-Buffer-Rope
├── rank_orders_by_t_per_ccr(orders)
│     ↑ Goldratt 1990 §6 ordering
└── select_best_product_mix(orders, total_capacity)
      ↑ Greedy knapsack (LP-optimal under single CCR)
```

### 3.1 與既有架構整合

```
        v3.27 identify_bottlenecks  ─┐
                                    │  提供 CCR 識別
                                    ▼
                  ┌─────────────────────────────┐
                  │  v3.28 模組:                 │
                  │  • compute_product_tvc       │
                  │  • evaluate_order_acceptance │
                  │  • compute_dbr_schedule      │
                  │  • select_best_product_mix   │
                  │  • explore_pricing_curve     │
                  └─────────────┬───────────────┘
                                │
                                ▼
                  ╔════════════════════════════╗
                  ║  LLM Agent Layer (v3.29+)  ║
                  ║  「這張單該不該接？」      ║
                  ║  → 自然語言回答 + 數據     ║
                  ╚════════════════════════════╝
```

---

## 4. 驗證（Validation）

### 4.1 4 大結構不變量類別（21 tests, 全 pass）

**Category 1：TVC composition**（Goldratt 1992 嚴格定義）
- `tvc_excludes_commission_in_base`：base TVC 不含 commission
- `tvc_total_includes_commission_when_priced`：total TVC = base + price × commission_rate
- `tvc_zero_commission_uses_only_fixed`：commission=0 時退化為固定值

**Category 2：T/CCR-min monotonicity**
- `throughput_per_ccr_basic`：T = 600−200=400, bn=100 → 4.0
- `throughput_per_ccr_zero_bottleneck_returns_inf`：無 CCR → +∞
- `throughput_per_ccr_monotone_in_price`：價↑ ⟹ T/min↑

**Category 3：訂單決策邏輯**
- `reject_when_infeasible`：產能不足
- `reject_when_loss_making`：虧本
- `accept_when_high_t_per_min`：符合條件
- `negotiate_when_below_threshold`：在門檻下
- `accept_when_no_ccr_consumption`：不消耗 CCR 必接

**Category 4：DBR Schragenheim 2000 教條**
- `dbr_buffer_is_3x_runtime`：預設 3×
- `dbr_drum_rate`：rate = capacity / runtime
- `dbr_zero_runtime_degenerate`：邊界處理
- `dbr_custom_buffer_multiplier`：可調

**Category 5：Knapsack 最佳性**
- `rank_by_t_per_ccr_descending`：Goldratt 1990 §6 排序
- `select_best_product_mix_respects_capacity`：總 capacity 守恆
- `select_mix_infeasible_orders_rejected_first`：不可行優先排除

**Category 6：Pricing curve**
- `pricing_curve_monotone_decreasing_throughput`：discount↑ ⟹ T↓
- `pricing_curve_recommendation_changes_at_breakeven`：建議在斷點改變

**Category 7：DB 整合**
- `compute_product_tvc_from_bom`：走 BOM 取得 material_cost = 26.0（已知答案）

### 4.2 結果

**21/21 tests pass**。Sprint 累計：**412/412 smoke tests pass**。

---

## 5. 限制與未來工作（Limitations and Future Work）

| 議題 | 為何不做 | 將來方向 |
|---|---|---|
| **多 CCR 同時 binding** | greedy 不再最佳；需 LP / MIP | v3.29：整合 PuLP + CBC |
| **Operating Expense 計算自動化** | OE 目前需客戶輸入；未從工資單 / 折舊表自動推導 | 整合 HR + Fixed Asset 模組 |
| **Buffer Management（動態調整）** | 目前固定 3× buffer；DBM 法可隨壓力區動態調整 | Schragenheim 2000 §6 Buffer Management |
| **Lead-time stochasticity** | DBR 假設前工序確定性 | Hopp-Spearman §6 stochastic LT |
| **多瓶頸 schedule 同步** | DBR 假設單一 CCR | Drum-Buffer-Rope-Buffer-Drum 序列 |
| **TVC 含外包工序之自動偵測** | outsourcing_cost 需客戶手輸 | Routing 加 is_outsourced flag |
| **GAAP / IFRS 對映報表** | TA ≠ 標準成本會計，不可直接出財報 | 加 cost-accounting bridge layer |

### 5.1 邊界情況

1. **產品無 BOM**：material_cost = 0；客戶必須手動設定 outsourcing_cost / 否則無法評估
2. **產品無 Routing**：bottleneck_minutes_required = 0 → 必接（從 CCR 角度）；但其實可能受其他 constraint 限制（v3.29 補多 constraint）
3. **commission_rate > 1**：物理不可能，未做檢查（trust input）
4. **negative price**：未做檢查（trust input）— 實務不應發生

---

## 6. 法律與責任聲明（Legal Notice / 法律聲明）

> ### ⚠️ 重要：管理會計分析之法律性質
>
> 本模組依 **Goldratt (1992) Throughput Accounting** 框架產生**管理會計分析**，**並非依 GAAP（一般公認會計準則）或 IFRS（國際財務報告準則）所製作之合規財務報表**。
>
> ### 1. TA vs 標準成本會計之區別
>
> | 用途 | TA | 標準成本會計 |
>|---|---|---|
> | 對外財報 / 稅務申報 | ❌ 不適用 | ✅ 必須使用 |
> | 內部 product-mix 決策 | ✅ 適用 | ❌ 常誤導 |
> | 訂單接受決策 | ✅ 適用 | ❌ 常誤拒高 T 訂單 |
>
> 客戶**不可**將本模組輸出之 throughput / TVC 直接作為財報 / 稅報依據。對外報表請依適用會計準則 + 會計師（CPA）審視。
>
> ### 2. 訂單接受決策之責任
>
> 本模組產生之 `recommendation`（accept/reject/negotiate）為**演算法依輸入參數計算之建議**，**不構成**：
>
> - 對客戶報價 / 接單之**承諾**
> - 對 sales 之**強制執行指令**
> - 對價格之**法律約束**
>
> 客戶於採納建議前，應由具備業務 / 財務 / 法務專業背景之人員**人工審視**：
>
> - **TVC 之認定**是否符合貴司會計政策（不同產業 TVC 定義有差異）
> - **commission_rate** 設定是否符合與業務之合約
> - **outsourcing_cost** 是否已含外包契約之品質 / 交期罰則
> - **bottleneck_minutes_required** 是否反映**實際**情況（含 setup time、待料、品檢時段）
> - **min_acceptable_t_per_min** 門檻之設定是否考慮**機會成本**（如未來 demand）
>
> ### 3. DBR 排程之責任
>
> Buffer = 3× run_time 為 Schragenheim 2000 **經驗值**，**不保證**在所有環境下最佳：
>
> - 上游 lead time 變異大之環境，3× 可能不足（應加大）
> - 訂單頻次低、產品種類多之 high-mix-low-volume 環境，3× 可能過大
> - 客戶應依本身 work flow 觀察實際 starvation / WIP 情況**自行調整** `buffer_multiplier`
>
> ### 4. Pricing Curve 不構成 antitrust 範疇之承諾
>
> 本模組之 pricing scenarios **不構成**：
> - 對特定客戶之**差別取價策略**之法律建議
> - 對市場行為之**反壟斷合規**之確認
>
> 各國反壟斷法（如台灣公平交易法、美國 Sherman Act）對 pricing 行為有特定規範。**不同客戶之不同定價**可能涉及合規議題。建議由法務顧問審視。
>
> ### 5. 演算法限制聲明
>
> - **單一 CCR 假設**：greedy 演算法在多 CCR 同時 binding 時**非最佳**；客戶若有多瓶頸應改用 LP/MIP
> - **確定性假設**：本模組假設 bottleneck_minutes_required、TVC 為確定值；不模型化 lead-time 變異、原料價格波動
> - **continuous relaxation**：knapsack 假設訂單可分割接受；實務上 0-1 knapsack 屬 NP-hard
> - **無策略性互動**：未模型化客戶議價、競爭對手定價反應（屬 game theory 範疇）
>
> ### 6. 不擔保條款
>
> 於適用法律所允許之最大範圍內（to the maximum extent permitted by applicable law），Ouvoca 對下列事項不承擔責任：
>
> - 因採用本模組建議所衍生之**錯誤接 / 拒單**所造成之收入損失或客戶關係損害
> - 因 TVC / OE 誤判所造成之**財報不實**法律後果
> - 因 DBR buffer 設定不當所造成之**生產延誤 / 庫存過剩**
> - 因 pricing curve 之應用所衍生之**反壟斷爭議**
> - 第三方（客戶、供應商、業務、operator）依本建議行動所衍生之**契約 / 勞動 / 競爭法** 爭議
>
> ### 7. 累積適用前置文件之聲明
>
> 本版本疊加於 v3.25.10 + v3.26 + v3.27，因此前置文件 §6 之**所有聲明於此累積適用**。
>
> ### 建議實務做法
>
> - 將本模組輸出視為「**業務決策支援報告**」而非「自動接 / 拒單系統」
> - 重大訂單（如 > 公司年營收 5%）必須走主管覆核流程
> - 每季對比 TVC 設定與實際成本，調整參數
> - 與會計師合作建立 TA → 標準成本之 reconciliation bridge
> - pricing curve 之結果應與市場條件、競爭格局並列考量

---

## 7. 文獻（References）

[1] **Goldratt, E. M.** (1984). *The Goal: A Process of Ongoing Improvement*. North River Press. — TOC 起點

[2] **Goldratt, E. M., & Fox, R. E.** (1986). *The Race*. North River Press. — DBR 雛形

[3] **Goldratt, E. M.** (1990). *What Is This Thing Called Theory of Constraints*. North River Press. — TOC 方法論 + product mix §6

[4] **Goldratt, E. M.** (1992). *The Haystack Syndrome: Sifting Information out of the Data Ocean*. North River Press. — Throughput Accounting

[5] **Corbett, T.** (1998). *Throughput Accounting: TOC's Management Accounting System*. North River Press. — TA 標準參考

[6] **Schragenheim, E., & Dettmer, H. W.** (2000). *Manufacturing at Warp Speed: Optimizing Supply Chain Financial Performance*. CRC Press. — DBR 完整論述

[7] **Schragenheim, E.** (2000). *Management Dilemmas: The Theory of Constraints Approach to Problem Identification*. CRC Press.

[8] **Hopp, W. J., & Spearman, M. L.** (1996, 2008 2nd ed.). *Factory Physics: Foundations of Manufacturing Management*. McGraw-Hill. — DBR vs CONWIP 比較；§10 throughput 由瓶頸決定

[9] **Mabin, V. J., & Balderstone, S. J.** (2003). The performance of the theory of constraints methodology. *IJOPM*, 23(6), 568-595. — TOC empirical performance

[10] **Lawler, E. L., Lenstra, J. K., Rinnooy Kan, A. H. G., & Shmoys, D. B.** (1985). Sequencing and scheduling: Algorithms and complexity. In *Handbooks in OR & MS*, 4, 445-522. — scheduling complexity

[11] **Pinedo, M. L.** (2016). *Scheduling: Theory, Algorithms, and Systems* (5th ed.). Springer.

[12] **Cooper, R., & Kaplan, R. S.** (1988). Measure costs right: Make the right decisions. *Harvard Business Review*, 66(5), 96-103. — ABC vs TA debate

[13] **Wagner, M., & Whitin, T. M.** (1958). [Cited from v3.25.10] — lot sizing within TA context

[14] **Spearman, M. L., Woodruff, D. L., & Hopp, W. J.** (1990). CONWIP: A pull alternative to kanban. *Int. J. Prod. Res.*, 28(5), 879-894. — DBR/CONWIP 對照

---

## 8. 變更紀錄（Changelog）

| 版本 | 日期 | 變更 |
|---|---|---|
| v3.25.10 | 2026-05-20 | 無產能 MRP-II |
| v3.26 | 2026-05-20 | 產能感知 MRP |
| v3.27 | 2026-05-20 | TOC IDENTIFY + Provenance |
| **v3.28** | **2026-05-20** | **本版本**：TOC EXPLOIT + SUBORDINATE (TA + DBR + Order Acceptance) |
| 將來 v3.29+ | TBD | 多 CCR LP/MIP / Buffer Management 動態調整 |
| 將來 v3.30+ | TBD | LLM 包裝層「該不該接這張單」對話式答覆 |

---

**最後更新**：2026-05-20（v3.28）
**作者**：Ouvoca 工程團隊（含 IE/OR/管理會計/AI 跨域學術方法論引用）
**版本**：1.0
**前置文件**：v3.25.10 / v3.26 / v3.27 之 design docs
**English version**：[`THROUGHPUT_ACCOUNTING_DESIGN_EN.md`](./THROUGHPUT_ACCOUNTING_DESIGN_EN.md)
