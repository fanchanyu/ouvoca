# 安裝指南（給老闆看的版本）

> **3 分鐘搞定，不需 IT 背景**

---

## 📦 您要做的只有 3 件事

```
   1️⃣ 裝 Docker          2️⃣ 雙擊安裝           3️⃣ 開瀏覽器
   ┌──────────┐          ┌──────────┐         ┌──────────┐
   │          │          │          │         │  http:// │
   │  🐳      │   →      │  install │   →    │ local:5173│
   │ Docker   │          │   .bat   │         │          │
   │          │          │          │         │  登入✓   │
   └──────────┘          └──────────┘         └──────────┘
   下載安裝             雙擊執行              admin/admin123
```

**不用打字、不用設定、不用懂技術。**

---

## ⏱ 時間預估

| 步驟 | 時間 |
|---|---|
| 下載安裝 Docker | 5-10 分鐘（第一次）|
| 執行安裝腳本 | 3-5 分鐘（自動）|
| 打開瀏覽器登入 | 30 秒 |
| **總計** | **約 10 分鐘** |

---

## 1️⃣ 安裝 Docker（一次性）

Docker 就像「保護箱」，把 LLM-ERP 包起來、不影響您電腦其他軟體。

### Windows 使用者

1. 打開 https://www.docker.com/products/docker-desktop/
2. 點 **「Download for Windows」**
3. 雙擊下載的 `.exe`
4. 一路按 Next 安裝
5. 安裝完**重開機**
6. 桌面會多一個 🐳 Docker Desktop 圖示，雙擊打開
7. 看到 Docker Desktop 視窗顯示 **"Engine running"** = ✓ 完成

### Mac 使用者

1. 打開 https://www.docker.com/products/docker-desktop/
2. 點 **「Download for Mac」**（選 Intel 或 Apple Silicon）
3. 雙擊 `.dmg`，拖 Docker 到 Applications
4. 啟動 Docker（Spotlight 搜尋 "Docker"）
5. 第一次會要求權限，按「允許」

### Linux 使用者

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl start docker
sudo usermod -aG docker $USER && newgrp docker
```

> **💡 為什麼需要 Docker？** 因為它能讓 LLM-ERP 跑在「您電腦的虛擬保護箱」裡，不會弄亂您原本的 Windows / Mac。

---

## 2️⃣ 執行一鍵安裝

### Windows

1. 把 `opnetest` 資料夾解壓到任何位置（如 `C:\LLM-ERP`）
2. 用檔案總管打開該資料夾
3. **雙擊 `install.bat`**
4. 視窗會自動跑：
   ```
   [Step 1/5] 檢查 Docker ✓
   [Step 2/5] 設定環境 ✓ (自動產生 JWT_SECRET)
   [Step 3/5] 啟動服務（首次需 2-5 分鐘）...
   [Step 4/5] 等待後端就緒 ✓
   [Step 5/5] 載入示範資料 ✓
   ```
5. 跑完會**自動開瀏覽器**到 http://localhost:5173

### Mac / Linux

```bash
cd LLM-ERP/opnetest
chmod +x install.sh
./install.sh
```

→ 同樣自動跑完 5 步、自動開瀏覽器。

---

## 3️⃣ 登入

瀏覽器自動打開後，您會看到漸層藍色登入畫面：

| 帳號 | 密碼 |
|---|---|
| `admin` | `admin123` |

按右上角 🌐 **可隨時切換中英文**。

第一次登入後，您會立刻看到：
- ✅ 4 個關鍵數字（今日營收 / 工單 / 採購 / 庫存警示）
- ✅ AI 智能摘要（一句話告訴您今天重點）
- ✅ 紅色警示：「M6 螺絲低於安全庫存」（這是示範資料）

---

## 4️⃣ 載入您行業的範例資料（可選）

我們準備了 5 個典型行業的範例：

| 您的行業 | 指令 |
|---|---|
| 金屬加工（CNC 螺絲）| `./load_industry.sh metal` |
| 塑膠射出 | `./load_industry.sh plastic` |
| PCB 電子組裝 | `./load_industry.sh pcb` |
| 食品加工烘焙 | `./load_industry.sh food` |
| 紡織印染 | `./load_industry.sh textile` |
| 全部都載入 | `./load_industry.sh all` |

每個行業都有：
- 8-12 個典型零件（含中英文名）
- 2-3 個成品 + BOM
- 4-5 家業界供應商（中鋼/台塑/台達等）
- 4-5 家典型客戶（鴻海/三星/全聯等）

**Windows 使用者**：直接在 cmd 跑：
```cmd
docker compose exec backend python -m scripts.seed_industries metal
```

---

## 5️⃣ 設定 AI 助手（可選）

如果您想要 AI 真的回答問題（不是只顯示「demo 模式」），需要設定 LLM API Key。

### 步驟

1. 用記事本打開 `backend\.env`（Windows）或 `backend/.env`（Mac/Linux）
2. 找到這段：
   ```
   LLM_PROVIDER=deepseek
   LLM_MODEL=deepseek-chat
   LLM_API_KEY=
   ```
3. 把 `LLM_API_KEY=` 後面填入您的 key
4. 存檔
5. 重啟：`docker compose restart backend`

### 申請 API Key（5 分鐘）

| 推薦 | 申請網址 | 說明 |
|---|---|---|
| **DeepSeek**（最便宜）| https://platform.deepseek.com | 中文場景 CP 值最高，註冊送 $5 美金 |
| OpenAI | https://platform.openai.com/api-keys | 業界標準 |
| Anthropic Claude | https://console.anthropic.com | 業界品質最高 |
| **Ollama**（零成本，本地）| https://ollama.com | 不用 API Key、資料不外流 |

> **💡 完全不設定也行！** 系統其他 11 個頁面都正常運作，只有 AI 助手對話會顯示 「demo 模式」訊息。

---

## ❓ 常見問題

### Q1：完全不懂技術也能裝嗎？

**可以。** 整個流程：
1. 下載 Docker（按 Next 就好）
2. 雙擊一個檔案
3. 瀏覽器打開、登入

**不需要打任何命令**。

### Q2：要花錢嗎？

| 項目 | 費用 |
|---|---|
| LLM-ERP 軟體 | 免費（開源）|
| Docker | 免費 |
| 跑在自己電腦 | 免費（只算電費）|
| LLM API（可選）| 看用量，DeepSeek 月約 NT$ 300-1000 |
| **總計（不裝 LLM API）** | **NT$ 0** |
| **總計（含 LLM API）** | **NT$ 300-1000/月** |

### Q3：可以不用 Docker 嗎？

可以但比較麻煩。Docker 是讓您「不用懂技術也能裝」的關鍵。
若您是技術人員，可參考 [`ADMIN_GUIDE.md`](./ADMIN_GUIDE.md) 自行 Python + Node 環境部署。

### Q4：手機看得到嗎？

可以！打開手機瀏覽器，輸入 `http://你電腦的IP:5173`：

- 查看您電腦 IP：
  - Windows：`ipconfig` → IPv4 Address
  - Mac/Linux：`ifconfig | grep inet`
- 然後手機瀏覽器輸入 `http://192.168.1.X:5173`（換成您的 IP）

**手機畫面已優化，響應式設計**。

> 📱 **原生 Mobile App 在 Phase 1 規劃中**（Expo 開發），目前先用響應式瀏覽器版本。

### Q5：怎麼停止 / 重啟？

| 動作 | 指令 |
|---|---|
| 停止 | `docker compose down` |
| 重啟 | `docker compose restart` |
| 完全重來 | `docker compose down -v && ./install.sh` |
| 看 log | `docker compose logs -f backend` |

### Q6：升級到新版本？

```bash
git pull          # 抓最新版（或下載新 zip）
docker compose up -d --build
```

舊資料會保留。

### Q7：安裝失敗怎麼辦？

**情況一：「Docker not found」**
→ 沒裝 Docker，回到步驟 1️⃣

**情況二：「Backend timeout」**
→ 第一次 build 較慢，可能 5 分鐘以上。耐心等。
→ 看詳情：`docker compose logs backend`

**情況三：「Port 8000 already in use」**
→ 您有別的程式占用 port。改 `docker-compose.yml` 的 `8000:8000` 為 `8888:8000`。

**情況四：其他**
→ 截圖 `docker compose logs backend` 寄給我們客服。

---

## 🆘 緊急情況

| 問題 | 解法 |
|---|---|
| 完全跑不起來 | LINE 找客服 |
| 想完全移除 | `docker compose down -v && rm -rf opnetest` |
| 想換新電腦 | 把 `opnetest` 整個資料夾複製過去，再跑 `install.sh` |
| 資料備份 | `docker compose exec backend cp /app/erp.db /tmp/backup.db` |

---

## ✅ 安裝成功的標誌

打開 http://localhost:5173，您應該看到：

1. ✅ 漸層藍色登入畫面
2. ✅ 右上角 🌐 中英文切換鈕
3. ✅ Demo Mode 入口（黃色按鈕）
4. ✅ 系統版本 v2.0.0
5. ✅ 底部綠色 LLM provider 指示

登入後：

1. ✅ AI 智能摘要顯示「⚠️ 1 項零件低於安全庫存」（這是 demo）
2. ✅ 4 個漂亮的統計卡片
3. ✅ 工單進度條動畫
4. ✅ 庫存警示紅色清單

**看到這些，恭喜您 — 系統 100% 跑起來了！🎉**

---

## 📄 想要 PDF 版手冊？

我們把**所有給客戶看的手冊**都做了精美 PDF 版（中英雙語、A4 排版、可印可寄）：

| # | 內容 | 對象 |
|---|---|---|
| 01 | 安裝指南（本文件）ZH + EN | 老闆/秘書 |
| 02 | 快速入門（雙語單檔）| 所有使用者 |
| 03 | 使用者操作手冊 ZH + EN | 業務/廠長/採購 |
| 04 | Mobile App 使用指南（雙語單檔）| 手機使用者 |
| 05 | 網路部署規劃 ZH + EN | IT/導入工程師 |
| 06 | 系統架構流程拓樸 ZH + EN | IT/架構師 |
| 07 | LLM 評比報告 ZH + EN | 採購決策者 |

**產生方式**（需 Node.js 18+）：

- Windows：雙擊 `build_pdfs.bat`
- Mac/Linux：`./build_pdfs.sh`

**輸出位置**：`docs/pdf/`（12 份 PDF，首次跑 ~3 分鐘下載依賴，之後 1 分鐘搞定）

詳見：[`scripts/build-pdfs/README.md`](../scripts/build-pdfs/README.md)

---

## 📞 需要協助？

| 需求 | 聯絡 |
|---|---|
| 技術問題 | 內部 IT / 我們客服 |
| 教育訓練 | 每月一次線上課程 |
| 客製化 | 報價討論 |

**對應英文版**：[`INSTALLATION_EN.md`](./INSTALLATION_EN.md)
