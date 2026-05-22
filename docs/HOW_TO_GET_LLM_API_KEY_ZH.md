# 如何申請 LLM API Key 並讓 Ouvoca 用上（完整教學）

> 適用 Ouvoca v3.14+
> 目標讀者：電腦小白也能照著做
> 預計時間：5-10 分鐘

---

## 一、為什麼需要 API Key？

Ouvoca 的「AI 對話式 CRUD」功能（查/增/改/刪都用講的）背後是 **大型語言模型（LLM）**。
LLM 跑在雲端，要呼叫它必須先**註冊一個帳號、申請一把 API Key**（像鑰匙）。

### 沒有 API Key 怎麼辦？

Ouvoca **設計上沒有 Key 也能用**：

| 功能 | 需要 API Key 嗎？ |
|---|---|
| 登入 / 帳號管理 | ❌ 不需要 |
| 庫存 / 採購 / 銷售 / 生產的滑鼠操作 | ❌ 不需要 |
| 上傳檔案 / 下載報表 | ❌ 不需要 |
| 載入示範資料 | ❌ 不需要 |
| War-room 即時儀表板 | ❌ 不需要 |
| **AI 助手對話（CRUD）** | ✅ **需要** |

換句話說：**沒申請也能用 Ouvoca 當傳統 ERP**，只是少了「用講的」這個賣點。

---

## 二、3 家 LLM Provider 比較（你選一家就好）

| Provider | 價格 | 免費額度 | 中文能力 | 推薦給... |
|---|---|---|---|---|
| 🇨🇳 **DeepSeek（推薦）** | $0.14 / 百萬 input tokens（超便宜）| 註冊送少量 | ⭐⭐⭐⭐⭐ | **大多數人**：CP 值最高 |
| 🇺🇸 **OpenAI (GPT-4o-mini)** | $0.15 / 百萬 | $5 試用（90 天）| ⭐⭐⭐⭐ | 已有 OpenAI 帳號 |
| 🇺🇸 **Anthropic Claude** | $0.25 / 百萬（haiku）| 註冊送 $5 | ⭐⭐⭐⭐⭐ | 重視推理品質、寫長文 |
| 🏠 **Ollama（離線）** | $0（本機跑）| 無限 | ⭐⭐⭐ | 有 GPU + 想完全離線 |

### 我們的推薦 → DeepSeek

理由：
1. 價格比 OpenAI 便宜 **百倍**
2. 中文理解最強（同樣的台灣中文，DeepSeek 比 GPT 答得好）
3. 用 OpenAI 相容 API 格式，將來換 provider 一行字搞定
4. 一般小工廠跑一個月 Ouvoca 對話費 **NT$10-100**，幾乎免費

如果你怕中國公司收你資料 → 選 OpenAI 或 Claude（資料留美國）。

---

## 三、申請 DeepSeek API Key（推薦路徑，5 分鐘）

### Step 1️⃣ · 註冊帳號

1. 打開瀏覽器，連到 https://platform.deepseek.com/sign_up
2. 用 **email** 或 **手機號碼**註冊（建議用 Gmail 比較順）
3. 收驗證信、設密碼、進首頁

### Step 2️⃣ · 拿 API Key

1. 登入後，左側選單點 **「API Keys」**
2. 右上角點藍色按鈕 **「Create new API Key」**
3. 給這把 key 一個名字（例：`ouvoca-2026`），按 Create
4. **跳出來的 `sk-xxxxxxxxxxxxxxxxxxxxxxxx` 立刻複製**（這串只會顯示一次！）

> ⚠️ 沒複製到 → 點刪掉重新建一把，**不要嘗試在頁面找回**。

### Step 3️⃣ · 充值（選做）

DeepSeek 註冊送的免費額度有限（約 NT$15 可打 200 次對話）。

要持續用：
1. 左側選單點 **「Top Up」**
2. 最少儲值 USD$2（約 NT$60，可打 300+ 次對話）
3. 信用卡 / PayPal / 支付寶 / WeChat Pay 都接受

> 💡 **省錢提醒**：DeepSeek 一個月 NT$30 對小工廠的 ERP 對話量已經很夠。**先不儲值跑跑看免費額度用多快**再決定。

---

## 四、把 Key 餵給 Ouvoca（3 種方法）

### 方法 A：用 Settings 頁設定（推薦，最簡單）

1. 登入 Ouvoca（http://localhost:5173）
2. 左側 sidebar 點 **「⚙️ 設定」**
3. 在最上面「🤖 AI 助手設定」區塊：
   - **選 Provider** → 下拉選「DeepSeek」
   - **API Key** 欄位 → 貼入剛才複製的 `sk-xxxxx...`
   - 點 **「🧪 測試連線（不儲存）」** → 看到「✅ DeepSeek 連線成功」就 OK
   - 點 **「💾 儲存（即時生效）」**
4. 完成！不需重啟、不需重新登入。回 AI 助手頁就能對它講話了。

#### 截圖示意（ASCII art）

```
┌────────────────────────────────────────────┐
│  🤖 AI 助手設定                  ⚠️ 未設定  │
│  申請 LLM API Key 啟用對話式 CRUD...        │
│                                            │
│  Provider:  [DeepSeek（推薦）        ▼]    │
│             還沒帳號？去申請 → (5 分鐘)     │
│                                            │
│  API Key:   [sk-•••••••••••••••••] [👁]   │
│             貼入後即時生效（不需重啟）       │
│                                            │
│  ☑ 驗證 SSL 證書                          │
│             （Windows 連 DeepSeek 失敗時可關）│
│                                            │
│  [🧪 測試連線（不儲存）]  [💾 儲存（即時生效）]│
└────────────────────────────────────────────┘
```

### 方法 B：直接編輯 backend/.env 檔（給工程師）

```bash
# 用記事本 / VS Code 打開
backend/.env

# 改這 3 行：
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-貼你的key在這
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

存檔後：
- **Docker 模式**：`docker compose restart backend`
- **dev 模式**：跑 `stop_dev.bat` → `start_dev.bat`

### 方法 C：環境變數（給進階使用者 / production）

```bash
# Linux / Mac
export LLM_API_KEY="sk-你的key"
docker compose up -d

# Windows PowerShell
$env:LLM_API_KEY = "sk-你的key"
```

---

## 五、Windows 用 DeepSeek 常見問題：SSL 證書錯誤

### 症狀

按「測試連線」看到：
```
❌ 連線失敗：SSLCertVerificationError
```

### 原因

Windows 的 CA 證書庫沒更新到 DeepSeek 的根憑證。這是 Windows + DeepSeek 的常見組合問題，不是 Ouvoca 的 bug。

### 解法（最快）

在 Ouvoca Settings 頁，**取消勾選「驗證 SSL 證書」** → 重試測試。
這只是讓 Python 跳過 SSL 驗證、不影響你的安全性（key 還是 TLS 加密傳輸）。

更乾淨的解法：升級 Python `certifi` 套件 — 但對電腦小白不必要。

---

## 六、其他 Provider 申請步驟

### OpenAI (GPT-4o-mini)

1. 註冊：https://platform.openai.com/signup（需信用卡）
2. 拿 Key：左側 **API Keys** → **Create new secret key**（一樣只顯示一次）
3. 在 Ouvoca 設定頁：Provider 選 OpenAI、貼 key、儲存

### Anthropic Claude

1. 註冊：https://console.anthropic.com/
2. 進 **Workbench → Settings → API Keys → Create Key**
3. 在 Ouvoca 設定頁：Provider 選 Anthropic、貼 key、儲存

### Ollama（本機離線）

1. 下載：https://ollama.com/download → 雙擊安裝
2. 終端機跑：`ollama pull llama3.2`（下載 model ~2GB）
3. 在 Ouvoca 設定頁：Provider 選 Ollama、key 留空、儲存
4. 確認本機 `ollama serve` 在跑

---

## 七、安全性提醒

### ✅ 你應該做的

- **API Key 等同密碼**，洩漏會被別人用你的額度
- 不要把 key 貼到聊天室 / Slack / GitHub commit
- 定期到 provider 後台**輪換 key**（每 3-6 個月）
- 萬一懷疑外洩 → 立刻去 provider 後台**撤銷** + **建新的**

### ✅ Ouvoca 對你的 key 怎麼處理

- 存在你電腦本機 `backend/.env`（明文，但是本機檔案）
- **永遠不會**上傳到任何 server
- **永遠不會**被 git commit（`.gitignore` 已排除 `.env`）
- pre-commit hook 自動掃 `sk-` 模式，誤推會被擋下

### ✅ 對話資料的去向

當你用 AI 助手對話時：
- 你打的**問題文字**會傳給 LLM provider（DeepSeek/OpenAI/Anthropic）
- DB 裡的**業務資料不會傳**（除非 AI 主動呼叫 tool 查 DB，那 tool 回的結果會包含在後續 context）
- LLM provider 的 retention policy 各家不同，看他們的 privacy 條款

要完全資料不出公司 → **用 Ollama 離線**（方法 D）。

---

## 八、費用試算（小工廠實況）

| 場景 | 用量 | DeepSeek 月費 | OpenAI 月費 |
|---|---|---|---|
| 老闆每天問 5 次 | 150 次/月 | NT$3 | NT$45 |
| 業務每天用 10 次 | 1500 次/月 | NT$30 | NT$450 |
| 全公司 20 人重度使用 | 20000 次/月 | NT$400 | NT$6,000 |

> 💡 **Ouvoca 設計很省 token**：每次對話多半 < 2000 token，大量短對話。

---

## 九、疑難排解

| 症狀 | 解法 |
|---|---|
| 「Connection refused」 | 檢查網路、proxy 設定 |
| 「Invalid API key」 | 重新確認 key 沒少字、沒多空白 |
| 「Rate limit」 | 額度用太快，等幾分鐘或升級方案 |
| 「Insufficient balance」 | DeepSeek 額度用完，去 Top Up |
| 「Model not found」 | provider 改版了，到設定頁更新 model 名 |
| Windows SSL 錯 | 取消勾「驗證 SSL 證書」 |
| Settings 頁存不下 | 確認你是 admin（有 `system.config.update` 權限）|
| 改完 key 沒效果 | Settings 頁儲存是即時生效，不行的話 hard refresh（Ctrl+F5）|

---

## 十、相關文件

- [USER_MANUAL_ZH.md](./USER_MANUAL_ZH.md) — 完整使用者操作手冊
- [PRODUCT_OVERVIEW_ZH.md](./PRODUCT_OVERVIEW_ZH.md) — 給採購決策者的產品說明書
- [INSTALLATION_ZH.md](./INSTALLATION_ZH.md) — 安裝指南
- [LICENSE-SMALL-BUSINESS.md](../LICENSE-SMALL-BUSINESS.md) — ≤20 人完全免費條款

英文版：[HOW_TO_GET_LLM_API_KEY_EN.md](./HOW_TO_GET_LLM_API_KEY_EN.md)
