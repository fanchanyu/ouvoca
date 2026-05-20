# AI-Augmented Demand Forecasting 引擎設計（v3.29）

> **本檔性質**：跨**時間序列分析 / 機器學習 / ERP / AI** 四域之方法論文件，描述 erpilot v3.29 需求預測引擎之設計、實作與驗證。本版本接通 v3.25.10 → v3.28 規劃鏈之上游缺口：把「客戶手動輸入 MPS」改為「**由歷史銷售自動預測 + LLM 增強**」。

> 📘 前置文件：[`MRP_ALGORITHM_DESIGN_ZH.md`](./MRP_ALGORITHM_DESIGN_ZH.md)（v3.25.10）／[`THROUGHPUT_ACCOUNTING_DESIGN_ZH.md`](./THROUGHPUT_ACCOUNTING_DESIGN_ZH.md)（v3.28）

---

## 摘要（Abstract）

erpilot 之前的 v3.25.10 → v3.28 規劃鏈，建立在 **MPS 由客戶手動輸入** 之假設上 —— 此假設使整條 IE/OR 鏈失去客觀性。本文敘述 v3.29 之**需求預測引擎**，整合 **Croston (1972)** 之 intermittent demand 經典演算法、**Brown (1959) SES / Holt (1957) / Winters (1960)** 之 exponential smoothing 家族、與 **Hyndman & Koehler (2006)** 之 MASE 指標自動選擇最佳方法。同步引入 **Chatfield (1989)** 之 regime change detection 作為 LLM 增強之觸發鉤子，當近期殘差超出 ±2σ 即提示客戶以業務知識覆核。**Makridakis et al. (2018, 2020)** M4 / M5 大型實證競賽證明 classical 方法在多數時序仍勝過 deep learning，故本版本不引入 scipy / statsmodels / torch 相依，**純 Python 實作 5 種方法**保持輕量。30 個結構不變量測試全 pass，含 Hyndman-Koehler 2006 之 MASE < 1 ⟺ 勝過 naive baseline 之經典性質。

**關鍵字**：需求預測、Croston、Holt-Winters、MASE、intermittent demand、regime change、LLM augmentation

---

## 1. 引言（Introduction）

### 1.1 MPS 手動輸入之根本問題

v3.25.10 → v3.28 之 4 個 sprint 完成了 MRP-II、CLSP、TOC 三部曲。但所有計畫之**起點 MPS** 皆假設客戶能填出「W22 要生產 100 個 A 產品」這種數字。實務上：

- SMB 老闆**沒有資料分析能力**
- 銷售歷史**有，但客戶不知道怎麼用**
- 大部分零件是 **intermittent demand**（連續多週為 0，偶爾爆量）—— 直觀填數通常失準
- v3.27 之 explainability：「為什麼下週要這麼多 M6 螺絲？」最終總是回到 MPS，**而 MPS 是客戶自己填的，erpilot 沒能力反問「你這個數字準嗎？」**

### 1.2 為何不直接套 deep learning

**Makridakis (2018) M4 競賽** 結論驚人：在 100,000 個時序之大規模盲測中：

| 方法類別 | 平均 sMAPE | 名次 |
|---|---|---|
| Combine（多 classical 加權平均）| 11.4% | 第 1 |
| Exponential smoothing + ARIMA | 11.9% | 第 2 |
| **deep learning (LSTM, MLP)** | **13.7%** | **倒數** |
| Naive | 14.3% | baseline |

**Makridakis (2020) M5** 用 Walmart 銷售資料：classical 與 ML 表現接近，但 **classical 更穩、更可解釋、訓練成本低**。

對 SMB（短歷史、intermittent 為主），classical **勝率更高**。本版本因此選擇：

- ✅ Naive / Seasonal Naive baseline
- ✅ SES / Holt / Holt-Winters
- ✅ Croston（intermittent specialist）
- ❌ 暫不採 Prophet / N-BEATS / TFT（後續 sprint 評估）

### 1.3 為何 Croston 不可替代

**Croston (1972, *J Op Res Soc* 23)** 為「intermittent demand forecasting」奠定方法論。在 ERP 場景中：

- 工業螺絲：每週 0-0-0-50-0-0-30-0
- 機台零備件：3 個月一次
- 季節性禮品：1 年只在 11 月有訂單

SES 對此類資料**永遠過度預測**（low-bias error 假設不成立）。Croston 拆解為：

```
forecast = (smoothed_demand_when_nonzero) / (smoothed_interval_between_demands)
```

並由 **Syntetos & Boylan (2005)** 證明 Croston 原始版本有正偏（positive bias），需 $(1 - \alpha/2)$ 修正。我們預設採用此修正。

---

## 2. 方法（Methodology）

### 2.1 五種方法之數學形式

**Naive**：
$$
\hat{y}_{t+k|t} = y_t \quad \forall k
$$

**Seasonal Naive**（season length $L$）：
$$
\hat{y}_{t+k|t} = y_{t+k-L\lceil k/L\rceil}
$$

**SES (Brown 1959)**：
$$
\begin{aligned}
\ell_t &= \alpha \cdot y_t + (1-\alpha) \cdot \ell_{t-1} \\
\hat{y}_{t+k|t} &= \ell_t
\end{aligned}
$$

**Holt (1957)** linear trend：
$$
\begin{aligned}
\ell_t &= \alpha y_t + (1-\alpha)(\ell_{t-1} + b_{t-1}) \\
b_t &= \beta (\ell_t - \ell_{t-1}) + (1-\beta) b_{t-1} \\
\hat{y}_{t+k|t} &= \ell_t + k \cdot b_t
\end{aligned}
$$

**Holt-Winters (Winters 1960) additive**：
$$
\begin{aligned}
\ell_t &= \alpha(y_t - s_{t-L}) + (1-\alpha)(\ell_{t-1} + b_{t-1}) \\
b_t &= \beta(\ell_t - \ell_{t-1}) + (1-\beta) b_{t-1} \\
s_t &= \gamma(y_t - \ell_t) + (1-\gamma) s_{t-L} \\
\hat{y}_{t+k|t} &= \ell_t + k \cdot b_t + s_{t-L+1+((k-1) \mod L)}
\end{aligned}
$$

**Croston (1972) + Syntetos-Boylan (2005)** correction：
$$
\hat{y}_{t+k|t} = \left(1 - \frac{\alpha}{2}\right) \cdot \frac{\tilde{Z}_t}{\tilde{X}_t}
$$
其中 $\tilde{Z}_t$ 為非零需求量之 SES，$\tilde{X}_t$ 為非零需求間隔之 SES。

### 2.2 精準度指標（Hyndman & Koehler 2006）

**MAPE**（Mean Absolute Percentage Error）：
$$
\text{MAPE} = \frac{1}{n} \sum_{t=1}^{n} \frac{|y_t - \hat{y}_t|}{|y_t|} \times 100\%
$$
**問題**：$y_t = 0$ 時 undefined；對 over-forecast / under-forecast 不對稱。

**sMAPE**（symmetric）：
$$
\text{sMAPE} = \frac{1}{n} \sum_{t=1}^{n} \frac{2|y_t - \hat{y}_t|}{|y_t| + |\hat{y}_t|} \times 100\%
$$
範圍 [0, 200%]，用於 M4 競賽。

**MASE**（Mean Absolute Scaled Error）—— **本系統之主要指標**：
$$
\text{MASE} = \frac{\text{MAE}_{\text{forecast}}}{\text{MAE}_{\text{naive on training}}}
$$
**性質**（Hyndman-Koehler 2006 證明）：
- Scale-free（跨序列可比）
- $y_t = 0$ 時仍 well-defined
- MASE $< 1 \Leftrightarrow$ 勝過 naive baseline
- M4 競賽用為**主指標**

### 2.3 預測區間（Prediction Interval）

採 **Hyndman & Athanasopoulos (2021) §5.5** 之 residual bootstrap 簡化：
$$
PI_{t+k} = \hat{y}_{t+k} \pm z_{\alpha} \cdot \sigma \cdot \sqrt{k}
$$
其中 $\sigma$ 為 in-sample 殘差之標準差，$\sqrt{k}$ 反映「不確定性隨 horizon 累積」之直覺。

**限制**：假設殘差 iid normal；若殘差有自相關 / heteroscedasticity，區間 mis-calibrated。

### 2.4 自動方法選擇

**演算法**：
```
auto_select(history):
  if zero_fraction(history) > 0.4:           # intermittent 偵測
    candidates = [Naive, Croston]
  else:
    candidates = [Naive, SeasonalNaive, SES, Holt, HoltWinters]
  
  for each method in candidates:
    backtest_result = train_on(history[:-test_size]).forecast(test_size)
    record MASE
  
  return argmin(MASE)  # 最佳方法
```

**為何 intermittent 用更窄候選**：依 **Syntetos & Boylan (2005)** 之結論，SES/Holt 對 intermittent 反應過劇（被零拉低 / 被尖峰拉高），實證上 MASE 較差。

### 2.5 Regime Change Detection（LLM 增強鉤子）

**Chatfield (1989) §13**：連續 $k$ 期殘差超出 $\pm \theta \sigma$ 為「**模型崩壞**」之穩健指標。

erpilot 預設：$k=3, \theta=2.0$（最近 3 期至少 2 期超出 2σ）。

**LLM 整合構想**（v3.30 補）：當 `requires_llm_review = True` 時，prompt LLM 含：
1. 歷史時序
2. 預測值
3. 實際值
4. 業務 context（如客戶清單、季節、近期 SO 變動）

讓 LLM 用業務語言推測原因（如「客戶 X 砍單」「新法規上路」「對手降價」）並建議 qualitative 調整。**所有調整必走 ConfirmCard**（不可直接覆寫）。

---

## 3. 實作（Implementation）

```
backend/app/services/demand_forecasting.py    (~600 行)
├── ForecastMethod (Enum: NAIVE / SEASONAL_NAIVE / SES / HOLT / HOLT_WINTERS / CROSTON / AUTO)
├── ForecastResult (dataclass: point_forecast / lower_95 / upper_95 / MAPE/sMAPE/MASE / diagnostic)
├── BacktestResult (dataclass)
├── RegimeChangeAlert (dataclass)
│
├── forecast_naive / forecast_seasonal_naive
├── forecast_ses + _optimize_alpha_ses (grid search)
├── forecast_holt
├── forecast_holt_winters (additive)
├── forecast_croston (with Syntetos-Boylan correction)
│
├── compute_mape / compute_smape / compute_mase
├── prediction_intervals_residual
├── backtest / run_forecast_method
├── auto_select_method  ← intermittent 偵測 + MASE 競賽
│
├── detect_regime_change  ← LLM 增強鉤子
└── forecast (top-level API)
```

---

## 4. 驗證（Validation）

### 4.1 30 個結構不變量測試（10 categories, 全 pass）

| Category | 測試數 | 涵蓋 |
|---|---|---|
| 1. Naive baseline | 4 | 平直 / 空 / 季節旋轉 / fallback |
| 2. SES (Brown 1959) | 3 | α=1 追蹤 / α≈0 平緩 / constant recovery |
| 3. Holt (1957) | 2 | 線性外推 / horizon 線性 |
| 4. Holt-Winters (1960) | 2 | 完美週期復現 / short history fallback |
| 5. Croston (1972) | 4 | 全零 / rate recovery / 平直 / single event |
| 6. 精準度指標 | 6 | MAPE / sMAPE / MASE 經典性質 |
| 7. Auto-selection | 2 | intermittent 限制 + 選最低 MASE |
| 8. 預測區間 | 2 | 隨 horizon 變寬 / 零殘差零寬 |
| 9. Regime change | 2 | 偵測 / 不誤報 |
| 10. API 整合 | 3 | 完整 ForecastResult / horizon=0 / 顯式方法 |

### 4.2 結果

**30/30 tests pass**。Sprint 累計：**442/442 smoke tests pass**。

---

## 5. 限制與未來工作（Limitations and Future Work）

| 議題 | 為何不做 | 將來方向 |
|---|---|---|
| **Modern ML (Prophet / N-BEATS / TFT)** | M4 顯示 classical 仍具競爭力；ML 引入 torch/scipy 相依太重 | v3.30+：可選相依，僅在 GPU 環境啟用 |
| **Time-series cross-validation** | 用 holdout 而非 rolling forecast origin | Hyndman 2021 §5.4 rolling CV |
| **Hierarchical reconciliation** | product / category / total 三層 forecast 不一致 | Wickramasuriya, Athanasopoulos & Hyndman (2019) MinT |
| **Auto-tuning of (α, β, γ)** | 目前 grid search α；β γ 固定 | Nelder-Mead / scipy.optimize 全參最佳化 |
| **Multiplicative seasonality** | 僅 additive | Holt-Winters multiplicative variant |
| **External regressors** (X-variables) | 純 univariate | ARIMAX / regression with ARMA errors |
| **State-space framework (ETS)** | 未整合 | Hyndman, Koehler, Snyder & Grose (2002) statistical ETS |
| **LLM augmentation 實際整合** | 規範定義完成 / API 未接 | v3.30 補 prompt template + ConfirmCard 流程 |

### 5.1 邊界情況

1. **歷史 < 2 季節**：HW 自動 fallback 到 Holt
2. **歷史全零**：所有方法回傳 0
3. **單一非零事件**：Croston 取均值 / 預期間隔
4. **負值需求**（如退貨）：未特別處理；建議客戶以「銷售淨額」為 input

---

## 6. 法律與責任聲明（Legal Notice / 法律聲明）

> ### ⚠️ 重要：統計預測之法律性質
>
> 本模組產生**統計需求預測**，**所有預測皆具固有不確定性**，**不構成**：
>
> 1. **未來需求之保證**：點預測（point forecast）為演算法依歷史資料所估之**期望值**；實際需求可能與預測有顯著差異。**預測區間**（PI）為機率性近似，95% 區間**不保證** 95% 之事件落入率（特別當資料生成過程改變時）
>
> 2. **採購承諾之依據**：客戶**不可**以本模組預測作為對供應商之採購承諾、對員工之加班排定、對客戶之交期保證之**單一依據**。重大決策應綜合考量市場條件、客戶具名 SO、業務情報等
>
> 3. **供應鏈爭議之證據**：本模組之輸出**不可**作為「該預測值為 X，所以供應商應該…」之爭議證據。預測本質上是**估計**，不是契約承諾
>
> 4. **不可預見事件之預測**：任何統計方法都無法預測：
>    - 自然災害（地震、洪水、颱風）
>    - 政策變動（關稅、法規、貿易戰）
>    - 客戶經營狀況變動（破產、合併、轉廠）
>    - 競爭格局變化（新進業者、技術突破）
>    - Black Swan 事件（Taleb 2007）
>
> ### 1. 演算法限制聲明
>
> - **平穩性假設**：所有方法假設資料生成過程在 forecast horizon 內穩定。**Regime change** 偵測為粗略指標，不能取代業務專業判斷
> - **MASE < 1 並不保證決策正確**：MASE 為「相對於 naive baseline」之表現指標；MASE 0.5 仍可能在絕對精度上不足以支撐重大決策
> - **預測區間之 mis-calibration**：殘差自相關、heteroscedasticity 時 PI 不準
> - **Auto-selection 之過度擬合**：基於 holdout MASE 選方法可能在 holdout 上 lucky，未來不穩
>
> ### 2. LLM 增強層警告（v3.30+ 啟用後適用）
>
> 當 `detect_regime_change` 觸發 LLM 覆核時：
>
> - LLM 可能 **hallucinate** 業務原因（編造客戶 / 競爭情境）
> - LLM 之 qualitative adjustment 應**僅供參考**，不可自動覆寫預測
> - 所有 LLM 建議必走 **ConfirmCard**（人類確認）
> - LLM 提出之原因（如「客戶 X 砍單」）**不構成對客戶 X 之事實陳述**，避免誹謗風險
>
> ### 3. Croston / Intermittent demand 特殊聲明
>
> Croston (1972) 假設**非零需求事件為隨機過程**。實務上：
>
> - 若需求事件有**結構性原因**（如月底盤點補單），統計方法仍可能失準
> - Syntetos-Boylan (2005) 之偏誤修正在 mean 上正確，但在 quantile 估計上仍有 bias
> - 對於**極稀疏資料**（如年度 1 次），任何統計方法都不可靠 — 建議客戶以業務情報為主
>
> ### 4. 與 MPS 整合之責任
>
> 本模組可自動產生 MPS 建議值。但：
>
> - **MPS 之最終決策權應在生管主管**，不可由演算法直接產生 production order
> - 應走 **ConfirmCard 流程**：預測 → MPS 建議 → 主管覆核 → 確認 → 流入 MRP
> - **重大決策**（年度大宗料採購、capacity 投資）必須有額外覆核
>
> ### 5. 不擔保條款
>
> 於適用法律所允許之最大範圍內（to the maximum extent permitted by applicable law），erpilot 對下列事項不承擔責任：
>
> - 因採用本模組預測所衍生之**過量採購 / 缺料停線**所造成之損失
> - 因預測失準所造成之**客戶交期違約 / 違約金**
> - 因 LLM 建議而產生之**錯誤業務判斷**
> - 因 regime change 未及時偵測所造成之**規劃失誤**
> - 因採用本模組之自動 MPS 而未經主管覆核所衍生之**任何後果**
>
> ### 6. 累積適用前置文件之聲明
>
> 本版本為 v3.25.10 → v3.28 規劃鏈之上游補完，因此前置文件 §6 之**所有聲明於此累積適用**。
>
> ### 建議實務做法
>
> - 將預測視為「**起始建議值**」而非「最終 MPS」
> - 每月對比實際 vs 預測，更新 method 選擇與參數
> - 高金額 / 高風險料件（A 類）必須人工複核
> - 在 PI 區間外之大量需求 → 主動聯繫客戶確認原因
> - 保留 forecast accuracy 歷史記錄，作為與客戶 / 供應商議價之參考但**非法律證據**

---

## 7. 文獻（References）

[1] **Brown, R. G.** (1959). *Statistical Forecasting for Inventory Control*. McGraw-Hill. — SES 起源

[2] **Holt, C. C.** (1957/2004 reprint). Forecasting seasonals and trends by exponentially weighted moving averages. *Int. J. Forecast.*, 20(1), 5-10. — 線性趨勢 ES

[3] **Winters, P. R.** (1960). Forecasting sales by exponentially weighted moving averages. *Management Science*, 6(3), 324-342. — Holt-Winters 三變量

[4] **Croston, J. D.** (1972). Forecasting and stock control for intermittent demands. *Operational Research Quarterly*, 23(3), 289-303. — Croston 創始

[5] **Syntetos, A. A., & Boylan, J. E.** (2005). The accuracy of intermittent demand estimates. *Int. J. Forecast.*, 21(2), 303-314. — Croston 偏誤修正

[6] **Hyndman, R. J., & Koehler, A. B.** (2006). Another look at measures of forecast accuracy. *Int. J. Forecast.*, 22(4), 679-688. — MASE 提出

[7] **Hyndman, R. J., Koehler, A. B., Snyder, R. D., & Grose, S.** (2002). A state space framework for automatic forecasting using exponential smoothing methods. *Int. J. Forecast.*, 18(3), 439-454. — ETS 統計框架

[8] **Hyndman, R. J., & Athanasopoulos, G.** (2021). *Forecasting: Principles and Practice* (3rd ed.). OTexts. — 開放教科書（forecasting standard）

[9] **Makridakis, S., Spiliotis, E., & Assimakopoulos, V.** (2018). The M4 Competition: Results, findings, conclusion and way forward. *Int. J. Forecast.*, 34(4), 802-808. — classical vs ML 大型實證

[10] **Makridakis, S., Spiliotis, E., & Assimakopoulos, V.** (2020). The M5 accuracy competition: Results, findings, and conclusions. *Int. J. Forecast.*, 38(4), 1346-1364.

[11] **Chatfield, C.** (1989). *The Analysis of Time Series: An Introduction* (4th ed.). Chapman & Hall. — Regime change indicator

[12] **Wickramasuriya, S. L., Athanasopoulos, G., & Hyndman, R. J.** (2019). Optimal forecast reconciliation for hierarchical and grouped time series through trace minimization. *J. Am. Stat. Assoc.*, 114(526), 804-819. — Hierarchical reconciliation

[13] **Taylor, S. J., & Letham, B.** (2018). Forecasting at scale. *The American Statistician*, 72(1), 37-45. — Prophet（後續 sprint 評估）

[14] **Oreshkin, B. N., Carpov, D., Chapados, N., & Bengio, Y.** (2020). N-BEATS: Neural basis expansion analysis for interpretable time series forecasting. *ICLR*. — N-BEATS

[15] **Lim, B., Arık, S. Ö., Loeff, N., & Pfister, T.** (2021). Temporal fusion transformers for interpretable multi-horizon time series forecasting. *Int. J. Forecast.*, 37(4), 1748-1764. — TFT

[16] **Taleb, N. N.** (2007). *The Black Swan: The Impact of the Highly Improbable*. Random House. — 不可預見事件

---

## 8. 變更紀錄（Changelog）

| 版本 | 日期 | 變更 |
|---|---|---|
| v3.25.10 | 2026-05-20 | MRP-II（基於手動 MPS）|
| v3.26 - v3.28 | 2026-05-20 | CLSP / TOC trilogy（仍基於手動 MPS）|
| **v3.29** | **2026-05-20** | **本版本**：自動需求預測引擎，接通 MPS 上游缺口 |
| 將來 v3.30+ | TBD | LLM 增強層整合 / Prophet 評估 / Hierarchical |
| 將來 v3.31+ | TBD | Rolling CV / ETS state-space / Multiplicative seasonality |

---

**最後更新**：2026-05-20（v3.29）
**作者**：erpilot 工程團隊（含時序分析 / ML / ERP / AI 跨域學術方法論引用）
**版本**：1.0
**English version**：[`DEMAND_FORECASTING_DESIGN_EN.md`](./DEMAND_FORECASTING_DESIGN_EN.md)
