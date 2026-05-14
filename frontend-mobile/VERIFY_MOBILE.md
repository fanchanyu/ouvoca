# Mobile 實機驗收 SOP / Mobile Real-Device Verification

> 此文件是 **Mobile 驗收最後一哩** — Claude 不能代您做的部分。
> 跑完這 5 步、截 5 張圖存到 `docs/mobile-evidence/`，才能說 Mobile「真實可用」。

---

## 🎯 為什麼非要您親自跑？

Mobile App 要實機驗證的關鍵點，**沒有手機/模擬器我們無法測**：
- 觸控手勢
- 相機/QR 掃描
- 真實網路延遲
- 字型/排版在不同裝置渲染
- AsyncStorage 持久化

CI 能保證的：✅ TypeScript 編譯、✅ npm install 成功
CI 保證不了的：❌ 上述 5 個

---

## ✅ 開始之前的必備檢查（30 秒）

```bash
# 1. Node.js 已裝（v18+）
node --version

# 2. Mobile deps 已裝
cd frontend-mobile && ls node_modules/expo > /dev/null && echo "OK"

# 3. 後端跑得起來
cd ../backend && python -c "from app.main import app; print('OK', len(app.routes), 'routes')"

# 4. 找到您電腦的內網 IP
# Windows:
ipconfig | grep -i "ipv4"
# Mac/Linux:
ifconfig | grep "inet " | grep -v 127.0.0.1
```

把那個 IP 記下來（如 `192.168.1.100`）。

---

## 步驟 1：設定 Mobile 連到您的後端

編輯 `frontend-mobile/app.json`，找 `extra.apiBaseUrl`，改成：

```json
{
  "expo": {
    "extra": {
      "apiBaseUrl": "http://192.168.1.100:8000"
    }
  }
}
```

⚠️ 重點：
- **不能用** `localhost` — 手機看不到您電腦的 localhost
- 手機必須與電腦**在同一個 Wi-Fi**
- 防火牆要放行 port 8000

---

## 步驟 2：啟動後端（兩個視窗）

**視窗 1 — HQ 後端**：
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
看到 `Application startup complete` = OK。

**視窗 2 — Factory node A（可選，驗 MESH）**：
```bash
cd backend
FACTORY_ID=demo-a FACTORY_NAME='示範主廠' PORT=8001 HQ_URL=http://127.0.0.1:8000 python factory_node.py
```

驗證 factory 註冊到 HQ：
```bash
curl http://127.0.0.1:8000/api/factory/list
# 應該看到 demo-a
```

---

## 步驟 3：啟動 Expo Dev Server

**視窗 3 — Expo**：
```bash
cd frontend-mobile
npm start
```

Terminal 會印出大 QR Code。

---

## 步驟 4：手機 App 開起來

1. 手機從 App Store / Google Play 裝 **Expo Go**
2. 用手機相機（iOS）或 Expo Go 內建掃描（Android）掃 QR
3. App 自動載入

---

## 步驟 5：跑 5 個關鍵流程 + 截圖

**每步截一張圖，存到 `docs/mobile-evidence/`**：

### Evidence 1：開 App + 看到 Login 頁
- 漸層藍色背景
- LLM-ERP 標題
- 帳密欄位（預填 admin/admin123）
- 「Demo 模式」黃色按鈕
- 底部顯示版本號

📸 存檔名：`01_login_screen.png`

### Evidence 2：Demo 模式進首頁
- 按「Demo 模式」按鈕
- 看到 Dashboard：
  - AI 智能摘要卡片
  - 4 個統計卡（營收/工單/採購/警示）
  - 紅色「低於安全庫存」清單
  - 工單進度區

📸 存檔名：`02_dashboard.png`

### Evidence 3：庫存頁可搜尋
- 點底部「庫存」tab
- 看到零件清單
- 在搜尋框打 `M6`，清單即時過濾

📸 存檔名：`03_inventory_search.png`

### Evidence 4：AI 對話
- 點底部「AI 助手」tab
- 點建議：「列出庫存最低 5 個零件」
- 看到對話氣泡 + AI 回應（demo 模式會說「demo」標籤）

📸 存檔名：`04_ai_chat.png`

### Evidence 5：個人/設定/登出
- 點底部「我的」tab
- 看到頭像、帳號資訊、系統資訊（API base、版本、LLM provider、DB status）
- 按「登出」→ 回到 Login 頁

📸 存檔名：`05_me_logout.png`

---

## 📝 驗收完成後

把截圖存到 `docs/mobile-evidence/`，跑一次 `bash scripts/run_gates.sh` 確認所有 gate 全綠，然後就可以說 **Mobile 真實可用**。

---

## 🚨 常見問題

### Q1：手機上 App 顯示「Network Error」
- ① 確認 `app.json` 的 `apiBaseUrl` 不是 localhost
- ② 在電腦的瀏覽器測 `http://<那個IP>:8000/api/health` 能不能通
- ③ Windows 防火牆放行 port 8000
- ④ 手機跟電腦同一個 Wi-Fi

### Q2：Expo Go 顯示「Something went wrong」
- 看 Terminal 視窗 3 的 log，多半是 TypeScript / import 錯誤
- 重啟：`npm start --clear`

### Q3：QR 掃描 tab 不能用
- 第一次會問相機權限，按「允許」
- 已拒絕：手機設定 → Expo Go → 相機 → 開啟

### Q4：Demo 模式進去看不到資料
- 確認後端有跑 seed：`docker compose exec backend python -m scripts.seed`
- 或：`cd backend && python -m scripts.seed`

### Q5：AI 對話只回「demo 模式」訊息
- 那是正確的 — 沒設 `LLM_API_KEY` 預設走 demo 模式
- 要真實 AI：編輯 `backend/.env` 設 `LLM_API_KEY=sk-...`，然後重啟後端

---

## 📅 一頁紙驗收清單（列印出來簽名用）

```
日期：____________  驗收人：____________

□ Step 1 設定 apiBaseUrl 為內網 IP        [____]
□ Step 2 後端 uvicorn 起來 + /api/health  [____]
□ Step 3 Expo dev server 顯示 QR          [____]
□ Step 4 Expo Go 掃 QR、App 載入成功      [____]
□ Step 5-1 看到 Login 頁                  [____]
□ Step 5-2 Demo 進 Dashboard 有資料       [____]
□ Step 5-3 庫存搜尋過濾正常               [____]
□ Step 5-4 AI 對話有回應                  [____]
□ Step 5-5 個人頁 + 登出正常              [____]

5 張截圖已存 docs/mobile-evidence/   [____]
run_gates.sh 全綠                    [____]
```
