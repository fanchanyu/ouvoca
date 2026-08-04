# Ouvoca 安裝指南

> 給工廠老闆、廠務、以及幫忙裝機的 IT 看的一份文件。
> **English version**: [`INSTALLATION_EN.md`](./INSTALLATION_EN.md)
> 裝到一半卡住？請看 [`INSTALL_TROUBLESHOOTING_ZH.md`](./INSTALL_TROUBLESHOOTING_ZH.md)

---

## 🚨 開始之前：這一版有 3 個已知的安裝地雷

安裝腳本目前有三個確定會踩到的問題。**每一條安裝路線下面都寫了要先做的動作**，照著做就能裝起來。
（這些是腳本的問題，不是你的電腦有問題。）

| # | 症狀 | 影響哪條路線 | 先做什麼 |
|---|---|---|---|
| 1 | 雙擊 `install_easy.bat`，黑視窗閃一下就不見，什麼都沒裝 | 路線 A（Windows） | 先改一行字 → [看步驟](#a0-先修掉那一行必做) |
| 2 | 跑 `install.bat` 到「等待後端就緒」空轉 60 秒後失敗 | 路線 B、C | 先手動建一個 `.env` → [看步驟](#b1-先自己建兩個-env-檔必做) |
| 3 | 照文件把 `LLM_API_KEY` 填進 `backend/.env`，AI 助手還是沒反應 | 路線 B、C | 改用畫面上的設定頁，或填在根目錄 `.env` → [看說明](#2-llmapikeyai-助手要用) |

> 💡 **只想最快裝好？** 家裡/辦公室一台電腦自己用 → 走 **路線 A**。
> 已經有 Docker、或要用多廠與戰情室 → 走 **路線 B**。

---

## 🧭 先選一條路線

| | 🅰️ 一鍵安裝 | 🅱️ Docker 一鍵安裝 | 🅲 Docker 手動 |
|---|---|---|---|
| **腳本** | `install_easy.bat` / `install_easy.sh` | `install.bat` / `install.sh` | `docker compose` 指令 |
| **給誰** | 完全不懂電腦的人、單機試用 | 有人幫忙裝、要多廠/戰情室 | IT / 導入工程師 |
| **前置需求** | Windows：**什麼都不用**（Win10 1803 以上）<br>Mac/Linux：要先自己裝 Python 3.11/3.12 + Node 20~24 | Docker Desktop | Docker Desktop / Docker Engine |
| **會下載** | 約 500 MB（Python、Node、套件） | Docker 映像檔（首次 build 較久） | 同左 |
| **裝完佔用** | 約 750 MB（都在資料夾內） | 依 Docker 而定 | 依 Docker 而定 |
| **耗時** | 10–20 分鐘（腳本自述） | 首次 build 約 2–5 分鐘＋等待 | 同左 |
| **啟動什麼** | 後端 8000、前端 5173 | 後端 8000、前端 5173、戰情室 8080、分廠 8001/8002 | 同左（可自選） |
| **資料放哪** | `backend\erp.db` | Docker volume `backend-data`（容器內 `/app/data/erp.db`） | 同左 |
| **怎麼移除** | `uninstall_easy.bat` / `.sh` | `docker compose down -v` | 同左 |

> ⚠️ **常見誤解**：`install.bat` / `install.sh` **不是**「本機 Python/Node 安裝腳本」，它們是 **Docker 腳本**
> （`install.bat` 的 Step 1／第 27–40 行第一件事就是檢查 Docker，找不到就中止）。真正不需要 Docker 的是 `install_easy.*`。
>
> ⚠️ 這兩支腳本（`install.bat` 第 17 行、`install.sh` 第 42 行）的開場橫幅印的仍是**更名前的舊產品名**，
> 不是你下載錯版本，也不影響功能。更名說明見 [`RENAME_NOTICE_ZH.md`](./RENAME_NOTICE_ZH.md)。

---

# 🅰️ 路線 A｜一鍵安裝（零前置）

適合：家裡或辦公室一台 Windows 電腦，想先試用看看，不想碰 Docker。

## A0. 先修掉那一行（必做）

`install_easy.bat` 第 146–147 行有個 cmd 語法錯誤，會讓整個批次檔在第 3 步當場中止
（而且它前面沒有 `pause`，所以雙擊時視窗會直接消失，你什麼訊息都看不到）。

**修法**：用**記事本**打開 `install_easy.bat`，找到開頭是 `for /f "delims=" %%k in` 的那一行，
把**那一行和它下面那一行**（共 2 行）整段刪掉：

```bat
        for /f "delims=" %%k in ('""%PYEXE%" -c "import secrets; print(secrets.token_hex(32))""') do set "NEWJWT=%%k"
        "%PYEXE%" -c "import pathlib; p=pathlib.Path('backend/.env'); s=p.read_text(encoding='utf-8'); s=s.replace('change-me-in-production-please-use-openssl-rand-hex-32', '%NEWJWT%'); p.write_text(s, encoding='utf-8')"
```

換成**這一行**（開頭的空白留著沒關係）：

```bat
        "%PYEXE%" -c "import secrets,pathlib; p=pathlib.Path('backend/.env'); s=p.read_text(encoding='utf-8'); p.write_text(s.replace('change-me-in-production-please-use-openssl-rand-hex-32', secrets.token_hex(32)), encoding='utf-8')"
```

存檔（記事本 → 檔案 → 儲存）。這一行的作用是幫你產生一組 64 位數的密鑰寫進設定檔。

> 不想改檔案？請改走 **路線 B**，或請廠商 / 公司 IT 幫忙改這一行。
> Mac / Linux 的 `install_easy.sh` **沒有**這個問題，可以直接跑。

## A1. 執行安裝

### Windows

1. 把 Ouvoca 資料夾解壓到任何位置（例如 `C:\ouvoca`），路徑**不要有中文或空白**比較保險
2. 用檔案總管打開該資料夾
3. **雙擊 `install_easy.bat`**

**你會看到什麼**：一個黑色視窗，依序跑完 5 個步驟。

```text
============================================================
  Ouvoca AI ERP - Easy Installer
  即將下載 / About to download (~500 MB total)
============================================================

[Step 1/5] Python 3.11                       ← 下載並安裝到 tools\python（不需管理員權限）
[Step 2/5] Node.js 20                        ← 下載並解壓到 tools\node
[Step 3/5] 後端套件 / Backend dependencies   ← 建 backend\venv，跑 pip（2–5 分鐘）
[Step 4/5] 前端套件 / Frontend dependencies  ← 跑 npm install（3–8 分鐘）
[Step 5/5] 資料庫初始化 / Database seeding   ← 建表 + 建管理員帳號

  安裝完成！Installation complete!
  登入帳密 / Login: admin / admin123

現在啟動嗎 / Launch now [Y,N]?
```

按 `Y` → 自動叫起服務並開瀏覽器到 http://localhost:5173

> **腳本會自動下載** Python 3.11.9（python.org）與 Node.js 20.11.1（nodejs.org），
> 這些軟體由原廠直接下載到你電腦，Ouvoca 沒有重新散布。
> 授權說明見 [`THIRD_PARTY_DOWNLOADS_ZH.md`](./THIRD_PARTY_DOWNLOADS_ZH.md)。

<details>
<summary>⚠️ 兩個要注意的地方（Windows）</summary>

- **不會偵測你已經裝好的 Python / Node**：腳本只看資料夾裡有沒有 `tools\python\python.exe`、`tools\node\node.exe`。
  就算你系統已經有 Python 3.11 或 Node 20，它還是會重新下載一份到 `tools\`。
- **第 5 步失敗只會印 WARN，但結尾仍然說「安裝完成」**：
  如果 `[Step 5/5]` 印出 `WARN seed failed`，代表**管理員帳號可能沒有建出來**，
  這時 `admin / admin123` 會登不進去。請往下看 [安裝成功怎麼確認](#-安裝成功怎麼確認)。

</details>

### Mac / Linux

```bash
cd ~/ouvoca
bash install_easy.sh
```

`install_easy.sh` **不會**幫你下載 Python / Node，它只做「偵測」，缺了就印出安裝指令然後停下來。

| 需求 | 版本 | 沒有的話 |
|---|---|---|
| Python | 3.11 或 3.12（`>=3.11,<3.13`） | Mac：`brew install python@3.11`<br>Ubuntu：`sudo apt install -y python3.11 python3.11-venv python3-pip` |
| Node.js | **20 ~ 24** | Mac：`brew install node@20`<br>Ubuntu：`curl -fsSL https://deb.nodesource.com/setup_20.x \| sudo -E bash - && sudo apt install -y nodejs` |

> ⚠️ **腳本的 Node 檢查太寬鬆**：`install_easy.sh` 只要求 Node ≥ 18 就說 OK，
> 但 `frontend-desktop/.npmrc` 設了 `engine-strict=true`，而 `package.json` 要求 `>=20.0.0 <25.0.0`。
> 所以 **Node 18、19 或 25 以上會在 npm install 那一步失敗**（錯誤訊息含 `EBADENGINE`），
> 即使前一步腳本才剛跟你說 OK。請先確認 `node --version` 是 v20 ~ v24。

## A2. 之後每天怎麼開

| 動作 | Windows | Mac / Linux |
|---|---|---|
| 啟動 | 雙擊 `start.bat` | `bash start.sh` |
| 關閉 | 雙擊 `stop_dev.bat` | `bash stop.sh` |
| 看後端錯誤 | 看標題為 `ouvoca-backend` 的視窗 | `logs-backend.txt` |
| 看前端錯誤 | 看標題為 `ouvoca-frontend` 的視窗 | `logs-frontend.txt` |

> ⚠️ `start.bat` 的畫面會叫你用 `stop_dev.bat`，`start.sh` 的畫面會叫你用 `stop.sh` —— 兩邊名字不一樣是正常的，
> **Windows 沒有 `stop.bat`**，請用 `stop_dev.bat`。
>
> ⚠️ `start.bat` / `start.sh` 開始前會**直接強制關掉**佔用 8000 與 5173 的任何程式，不會先問你。
> 如果你同一台電腦上有別的開發伺服器在用這兩個 port，請先自己關掉再啟動。

---

# 🅱️ 路線 B｜Docker 一鍵安裝

適合：已經有 Docker Desktop、或需要「戰情室（War Room）＋多廠節點」的環境。

## B0. 先裝 Docker Desktop（一次性）

<details>
<summary>Windows / Mac / Linux 安裝步驟</summary>

**Windows**
1. 打開 https://www.docker.com/products/docker-desktop/ → 點「Download for Windows」
2. 雙擊下載的 `.exe`，一路 Next
3. 安裝完**重開機**
4. 桌面雙擊 🐳 Docker Desktop，等視窗左下角出現 **Engine running**

**Mac**
1. 同一個網址 → 點「Download for Mac」（選 Intel 或 Apple Silicon）
2. 雙擊 `.dmg`，把 Docker 拖到 Applications
3. Spotlight 搜尋 "Docker" 啟動，第一次會要求權限，按「允許」

**Linux**
```bash
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl start docker
sudo usermod -aG docker $USER && newgrp docker
```

</details>

## B1. 先自己建兩個 .env 檔（必做）

這是路線 B / C **一定會踩、而且錯誤訊息完全看不出原因**的那顆地雷。原因有兩層：

1. `install.bat` 第 71 行用的 `[RandomNumberGenerator]::GetBytes(48)` 這個寫法，
   在 Windows 內建的 PowerShell 5.1 **不存在**（實測會回 `does not contain a method named 'GetBytes'`）。
   結果是 `JWT_SECRET=` 被寫成**空的**，但腳本的檢查只看「change-me 有沒有消失」，所以還是印出「OK 已自動產生」。
2. 更關鍵的是：`docker-compose.yml` **從來不讀 `backend/.env`**。
   compose 的 `${JWT_SECRET:-...}` 只會讀「**docker-compose.yml 同一層目錄**（也就是專案根目錄）的 `.env`」。
   根目錄沒有 `.env` 時，容器就會拿到字面值 `change-me-in-production-...`，
   而 `backend/app/main.py` 第 32–37 行看到預設密鑰會**直接結束程式**。

**結果**：`install.bat` 會停在 `[Step 4/5] 等待後端就緒`，空轉 60 秒後印「X 後端超時」。

### 解法：手動建立兩個檔案

**① 根目錄的 `.env`** —— 給 docker compose 讀（供應 compose 會覆寫的那幾個變數）

Windows（在專案資料夾按住 Shift + 右鍵 →「在這裡開啟 PowerShell 視窗」）：

```powershell
$b = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
$jwt = ($b | ForEach-Object { $_.ToString('x2') }) -join ''
Set-Content -Path .env -Value "JWT_SECRET=$jwt" -Encoding ascii
Get-Content .env
```

Mac / Linux：

```bash
echo "JWT_SECRET=$(openssl rand -hex 32)" > .env
cat .env
```

**你會看到什麼**：`JWT_SECRET=` 後面接一長串 **64 個字元**的英數字。長度不是 64 就是失敗了。

**② `backend/.env`** —— 會被打包進映像檔，供應 compose **沒有**傳的那些變數（例如 `DEBUG`）

```powershell
copy backend\.env.example backend\.env
```
```bash
cp backend/.env.example backend/.env
```

> 為什麼兩個都要？`docker-compose.yml` 第 22–34 行只「硬塞」這幾個變數給容器：
> `DATABASE_DRIVER`、`DATABASE_URL`、`DATABASE_URL_PROD`、`JWT_SECRET`、`LLM_PROVIDER`、`LLM_API_KEY`、
> `LLM_MODEL`、`LOG_LEVEL`、`ALLOW_DEMO_BYPASS`、`CORS_ORIGINS`。
> 其餘設定（`DEBUG`、`CONNECTION_ENCRYPTION_KEY`、`SEED_ADMIN_*`…）是靠 build 時被 `COPY` 進映像檔的
> `backend/.env` 提供的。少了它，`DEBUG` 會變成 `false`，而正式模式禁止用 SQLite，後端一樣會拒絕啟動。

## B2. 執行安裝

**Windows**：雙擊 `install.bat`
**Mac / Linux**：`chmod +x install.sh && ./install.sh`

**你會看到什麼**：

```text
[Step 1/5] 檢查 Docker / Checking Docker...        → OK Docker installed and running
[Step 2/5] 設定環境變數 / Configuring environment  → i .env 已存在，跳過（因為 B1 已經建好了）
[Step 2.5] 檢查 port 衝突                          → OK 所有 port 都可用
[Step 3/5] 啟動服務 (首次需 2-5 分鐘)              → docker compose up -d --build
[Step 4/5] 等待後端就緒                            → OK 後端就緒 (12 秒)
[Step 4.5] 驗證 localhost + 127.0.0.1 雙路徑       → OK 兩個都通
[Step 5/5] 載入示範資料                            → OK 示範資料已載入

               安裝完成 / Installation Done
  Desktop UI:   http://localhost:5173
  War Room:     http://localhost:8080
  API Docs:     http://localhost:8000/docs
  帳號 admin / 密碼 admin123
```

跑完會自動開瀏覽器。

<details>
<summary>😱 還是停在「[Step 4/5] 等待後端就緒」怎麼辦</summary>

腳本只會說「後端超時」，不會告訴你真正的原因。自己撈容器的錯誤訊息：

```bash
docker compose logs --tail=50 backend
```

| log 裡出現 | 意思 | 解法 |
|---|---|---|
| `JWT_SECRET 是預設值或太短` | 根目錄 `.env` 沒建、或值長度不到 32 | 回到 [B1](#b1-先自己建兩個-env-檔必做) |
| `DATABASE_DRIVER=sqlite 不能用於 production` | `DEBUG` 變成 false | 確認 `backend/.env` 存在（裡面有 `DEBUG=true`），然後 `docker compose up -d --build` 重建 |
| `DB 無法連線` | volume 權限或路徑問題 | `docker compose down -v` 後重跑 |

檢查容器實際收到的值：
```bash
docker compose exec backend env | findstr JWT      # Windows
docker compose exec backend env | grep JWT         # Mac/Linux
```

</details>

<details>
<summary>⚠️ install.sh（Mac/Linux）的兩個小陷阱</summary>

- 等待後端的迴圈跑完 60 次**沒有失敗處理**，就算後端沒起來，腳本最後還是會印「🎉 安裝完成」。
  請以「瀏覽器打得開 http://localhost:5173 且登得進去」為準，不要以那行字為準。
- 腳本開頭是 `set -e`，所以 `docker compose exec -T backend python -m scripts.seed` 一旦失敗，
  腳本會**無聲中斷**（原本設計要印的「Seed 失敗」訊息永遠不會出現）。畫面突然停住就是這個。

</details>

## B3. 之後每天怎麼開

| 動作 | 指令 |
|---|---|
| 啟動 | `docker compose up -d` |
| 停止 | `docker compose down` |
| 重啟後端 | `docker compose restart backend` |
| 看 log | `docker compose logs -f backend` |
| 改了根目錄 `.env` 後生效 | `docker compose up -d`（重新建立容器） |
| 改了 `backend/.env` 後生效 | `docker compose up -d --build`（要**重新 build**，因為 .env 是打包進映像檔的） |

> 容器都設了 `restart: unless-stopped`，所以 Docker Desktop 一開機啟動，Ouvoca 就會自己跟著起來。
> 想要開機自動啟動：Docker Desktop → Settings → General → 勾「Start Docker Desktop when you log in」。

---

# 🅲 路線 C｜Docker 手動（給 IT）

不想跑腳本、要自己控制起哪些服務時用。

```bash
# 1. 兩個 .env（同 B1；根目錄的給 compose 內插，backend 的會被 COPY 進映像檔）
cp backend/.env.example backend/.env
echo "JWT_SECRET=$(openssl rand -hex 32)" >> .env
# .env 檔內同名的變數以「最後一筆」為準，所以直接附加在檔尾即可覆蓋 .env.example 的空值
echo "CONNECTION_ENCRYPTION_KEY=$(openssl rand -hex 32)" >> backend/.env   # 見「必要設定」第 3 節

# 2. 只起最小組合（不要戰情室與分廠節點時）
docker compose up -d --build backend frontend

# 3. 等健康檢查通過
docker compose ps

# 4. 初始化資料庫（建表 + 231 個權限碼 + 10 個角色 + 86 科科目表 + 14 項系統組態 + 示範資料）
docker compose exec -T backend python -m scripts.seed

# 5. 標記資料庫版本（見「必要設定」第 4 節）
docker compose exec -T backend python -m alembic stamp head
```

`docker-compose.yml` 定義的服務與 port（**全部都綁 127.0.0.1，區網其他人連不到，這是刻意的**）：

| 服務 | 網址 | 說明 |
|---|---|---|
| `backend` | http://localhost:8000 | API，`/docs` 是互動式文件 |
| `frontend` | http://localhost:5173 | 主畫面（nginx 提供靜態檔） |
| `war-room` | http://localhost:8080 | 戰情室大螢幕儀表板 |
| `factory-a` | http://localhost:8001 | MESH 分廠節點 A |
| `factory-b` | http://localhost:8002 | MESH 分廠節點 B |

> 要開放給區網或正式上線，請改用 `docker-compose.prod.yml`，並先讀
> [`NETWORK_DEPLOYMENT_ZH.md`](./NETWORK_DEPLOYMENT_ZH.md)（含 CORS、反向代理、憑證）。

---

# 🔑 安裝完成後：一定要做的設定

## 1. 立刻改掉預設密碼

| 帳號 | 密碼 |
|---|---|
| `admin` | `admin123` |

登入畫面自己也會提醒你這件事（黃色小字）。

**怎麼改**：登入後在 **AI 助手對話框**打「改密碼 我的新密碼是 XXXXXX」→ 系統會出一張確認卡 → 點確認。
（90 秒內講「撤銷」可以還原。改完之後所有舊的登入 token 會立刻失效，其他裝置要重新登入。）

> ⚠️ 這個功能走的是 AI 助手，所以**要先設好 LLM_API_KEY**（下一節）。
> 在還沒設 Key 之前，請務必不要把系統開放給不信任的網路。

## 2. LLM_API_KEY（AI 助手要用）

沒有 Key 也能用 Ouvoca —— 庫存、採購、銷售、生產、報表全部照常，只有「用講的」那個 AI 對話不能用。

### 最簡單的做法：用畫面設定（三條路線都適用，不用重開）

1. 登入後點左側選單的 **⚙️ 設定**（網址結尾 `/settings`）
2. 找到 **🤖 AI 助手設定** 這一區
3. 選供應商（DeepSeek / OpenAI / Anthropic / Ollama）→ 貼上 API Key
4. 先按 **測試**，看到成功訊息後再按 **儲存**
5. 右上角的標籤會從 `⚠️ 未設定` 變成 `✓ 已啟用（deepseek）`

這個做法會同時寫進 `backend/.env` **並立即在記憶體生效**，不需要重啟後端。

### 申請 Key 去哪裡

| 供應商 | 網址 | 說明 |
|---|---|---|
| **DeepSeek**（推薦） | https://platform.deepseek.com | 最便宜，中文能力好 |
| OpenAI | https://platform.openai.com/api-keys | 老牌、最穩、最貴 |
| Anthropic Claude | https://console.anthropic.com | 推理與寫作能力強 |
| **Ollama**（本機、零成本） | https://ollama.com | 不用 Key、資料不出門，需自備 GPU |

📖 **一步一步的申請教學**（含付款、額度、費用估算）：
[`HOW_TO_GET_LLM_API_KEY_ZH.md`](./HOW_TO_GET_LLM_API_KEY_ZH.md)

### ⚠️ Docker 使用者請特別注意

`docker-compose.yml` 第 28 行是 `LLM_API_KEY: ${LLM_API_KEY:-}`。
根目錄 `.env` 沒設這個變數時，容器會拿到一個**空字串**，而「空字串」在設定系統裡算「已設定」，
**優先權高於映像檔裡的 `backend/.env`**。

所以：**只改 `backend/.env` 再 `docker compose restart backend`，AI 助手不會有反應**（也不會報錯）。

Docker 路線正確做法（擇一）：
- 用上面的「畫面設定」→ 立刻生效（但容器一旦重建就會被 compose 的空值蓋掉，重建後要再設一次）
- **或**把 Key 寫進**根目錄** `.env`，然後 `docker compose up -d`：
  ```dotenv
  JWT_SECRET=（你的 64 位密鑰）
  LLM_API_KEY=sk-xxxxxxxxxxxx
  LLM_PROVIDER=deepseek
  LLM_MODEL=deepseek-chat
  ```

自我檢查：
```bash
docker compose exec backend env | grep LLM     # 看容器實際拿到什麼
curl http://localhost:8000/api/health          # llm_provider 欄位
```

## 3. CONNECTION_ENCRYPTION_KEY（有接外部資料庫才要）

用途：v3.60 起可以連你原本的舊系統資料庫，那些**連線字串（含帳號密碼）會用 AES-256-GCM 加密後存起來**，
這把金鑰就是用來加解密的。

**沒有任何安裝腳本會產生它**，`backend/.env.example` 第 52 行是留空的。
留空時，系統會改用「`JWT_SECRET` 的 SHA-256」當金鑰（`backend/app/core/crypto.py` 第 36 行）。

| 你的情況 | 要做什麼 |
|---|---|
| 沒有要接外部資料庫 | 可以不管它 |
| 有接外部資料庫 | **一定要**設一把獨立的金鑰 |

```bash
# 產生後填進 backend/.env 的 CONNECTION_ENCRYPTION_KEY=
openssl rand -hex 32
```

> 🚨 **重要警告**：[`SECRETS_ROTATION_SOP_ZH.md`](./SECRETS_ROTATION_SOP_ZH.md) 要求 `JWT_SECRET` 每 90 天輪換一次。
> 如果你**沒有**單獨設 `CONNECTION_ENCRYPTION_KEY`，那金鑰是從 `JWT_SECRET` 衍生的 ——
> **換掉 `JWT_SECRET` 的那一刻，所有已存的外部資料庫連線設定就永遠解不開了**（沒有任何警告）。
> 要嘛先設一把獨立金鑰，要嘛輪換後準備重新輸入所有外部連線設定。

## 4. 標記資料庫版本（`alembic stamp head`）

**安裝腳本從來沒有跑過 alembic。** `scripts.seed` 是靠 `backend/app/database.py` 的 `init_db()`
用 `Base.metadata.create_all` 直接把表建出來的，所以資料庫裡**不會有 `alembic_version` 這張表**。

後果：以後跑 `update.bat` / `update.sh` 升級時，`alembic upgrade head` 會以為你的資料庫是全新的，
想從第一版開始建表 → 失敗 → 而腳本把錯誤訊息丟掉了（`2>nul`），只印一句「WARN 或無需升級」。
新版如果替既有的表加了欄位，這個升級就默默沒做到。

**安裝完成後執行一次**（只要做一次）：

```powershell
:: 路線 A（Windows）— 在專案資料夾開 cmd
cd backend
venv\Scripts\python.exe -m alembic stamp head
```
```bash
# 路線 A（Mac/Linux）
cd backend && venv/bin/python -m alembic stamp head

# 路線 B / C（Docker）
docker compose exec -T backend python -m alembic stamp head
```

**你會看到什麼**：

```text
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running stamp_revision  -> 016_fk_indexes
```

`016_fk_indexes` 是目前的最新資料庫版本編號（`backend/alembic/versions/` 底下 v001 → v016）。

---

# 📦 載入你這一行的範例資料（選用）

內建 5 個行業的範例，每個包含典型料件、成品與 BOM、供應商、客戶。

| 行業 | 代號 |
|---|---|
| 金屬加工（CNC 螺絲） | `metal` |
| 塑膠射出 | `plastic` |
| PCB 電子組裝 | `pcb` |
| 食品加工烘焙 | `food` |
| 紡織印染 | `textile` |
| 全部載入 | `all` |

**指令依路線不同**：

```powershell
:: 路線 A（Windows）
cd backend
venv\Scripts\python.exe -m scripts.seed_industries metal
```
```bash
# 路線 A（Mac/Linux）
cd backend && venv/bin/python -m scripts.seed_industries metal

# 路線 B / C（Docker）
docker compose exec -T backend python -m scripts.seed_industries metal
#   或用包好的腳本（僅限 Docker）：
./load_industry.sh metal
```

> ⚠️ `load_industry.sh` 內容是 `docker compose exec -T backend ...`，**只能在 Docker 路線用**，
> 而且**沒有 Windows 的 .bat 版本**。路線 A 請用上面的 `python -m scripts.seed_industries`。

> 另外，**設定 → 📦 示範資料** 頁面有一組不一樣的東西：
> 5 客戶 / 3 供應商 / 10 料件，全部帶 `DEMO-` 前綴，可以一鍵載入、也可以一鍵清除。
> 上面的行業資料**不帶 `DEMO-` 前綴**，那顆「清除示範資料」按鈕清不掉。

---

# ⬆️ 升級到新版

## 用 `update.bat` / `update.sh`（推薦）

| 動作 | Windows | Mac / Linux |
|---|---|---|
| 升級 | 雙擊 `update.bat` | `bash update.sh` |

它會依序做 6 件事：

| 步驟 | 內容 |
|---|---|
| 1 | 停掉 8000 / 5173 上的服務 |
| 2 | **備份** `backend\erp.db`、`backend\.env`、`backend\uploads\` 到 `backups\` 底下 |
| 3 | 下載新程式碼（有 git 就 `git pull`，沒有就抓 GitHub zip 解壓覆蓋，會跳過你的資料檔） |
| 4 | `pip install -r requirements.txt` + `npm install`（補新套件） |
| 5 | `alembic upgrade head` **＋ `python -m scripts.seed_permissions`** |
| 6 | 問你要不要重新啟動 |

### 為什麼第 5 步的 `seed_permissions` 不能跳過

新版加的功能（詢價比價、收料單、批號追溯、備份管理、三大財報…）都會帶新的**權限碼**。
權限碼要靠 `seed_permissions` 展開到各個角色上。**沒跑的話，除了超級管理員以外，
所有人點新功能一律拿到 403「沒有權限」** —— 而且畫面上看起來就像功能壞了。

目前 `seed_permissions` 會建立 **231 個權限碼**（182 主表 + 49 別名）與 **10 個系統角色**。

<details>
<summary>⚠️ update 腳本的 3 個已知問題</summary>

1. **`update.bat` 的備份資料夾名稱會變成 `backups\_`**
   它用 `wmic` 取時間（第 92 行），但 **Windows 11 24H2 起 wmic 已經被移除**（本機實測 `wmic` NOT FOUND）。
   結果每次升級都寫進同一個 `backups\_` 資料夾，**上一次的備份會被蓋掉**。
   👉 **建議：升級前自己先手動複製一份** `backend\erp.db` 到別的地方（例如隨身碟）。

2. **alembic 失敗看不到原因**
   第 222 行是 `alembic upgrade head 2>nul`，錯誤訊息被丟掉，一律降級成「WARN 或無需升級」。
   要看真正發生什麼事，自己手動跑一次（不要加 `2>nul`）：
   ```powershell
   cd backend
   venv\Scripts\python.exe -m alembic upgrade head
   ```

3. **不會補跑科目表與系統組態**
   升級只重跑 `seed_permissions`，**不會**重跑 `seed_accounts`（86 科會計科目）與系統組態。
   新版如果加了科目或組態項目，既有的安裝不會自動出現。需要時手動補：
   ```powershell
   cd backend
   venv\Scripts\python.exe -m scripts.seed_accounts
   ```

</details>

## 只想用 Docker 指令升級

```bash
docker compose down
git pull                       # 或下載新的 zip 覆蓋
docker compose up -d --build
docker compose exec -T backend python -m alembic upgrade head
docker compose exec -T backend python -m scripts.seed_permissions   # ← 千萬別漏
```

> ⚠️ 這條路**沒有自動備份**。請先自己備份（見下一節）再開始。

---

# 💾 備份與還原

## 你的資料在哪裡

| 路線 | 資料庫 | 上傳的檔案 |
|---|---|---|
| A（本機） | `backend\erp.db` | `backend\uploads\` |
| B / C（Docker） | volume `backend-data` → 容器內 `/app/data/erp.db` | 容器內 `/app/uploads/` |

> 🚨 **Docker 使用者注意**：只有 `/app/data` 掛了 volume。
> **上傳的檔案（`/app/uploads`）與系統內建備份（`/app/backups`）都在容器裡，容器一重建就沒了。**
> 有上傳重要檔案的話，請定期用 `docker compose cp` 撈出來。

## 手動備份

```powershell
:: 路線 A（Windows）— 先關掉服務再複製
copy backend\erp.db  D:\備份\erp-20260804.db
```
```bash
# 路線 A（Mac/Linux）
cp backend/erp.db ~/backup/erp-$(date +%Y%m%d).db

# 路線 B / C（Docker）
docker compose cp backend:/app/data/erp.db ./erp-backup-20260804.db
docker compose cp backend:/app/uploads ./uploads-backup
```

## 系統內建的備份管理（v3.62）

登入後到 **設定 → 💾 備份管理**，可以建立、列出、還原、刪除備份，也能設定排程。
備份檔存在 `backend/backups/backup-*.db`。還原前系統會自動先存一份 `pre-restore-*.db` 保命。

📖 完整的備份策略（3-2-1 原則、異地、驗證、災難復原）：[`BACKUP_RESTORE_SOP_ZH.md`](./BACKUP_RESTORE_SOP_ZH.md)

---

# 🗑 重置與解除安裝

## 重置（清空資料重來）

| 路線 | 怎麼做 |
|---|---|
| B / C（Docker） | 雙擊 `reset.bat`（Windows）或 `bash reset.sh`，輸入 `YES` 確認 |
| A（本機） | ⚠️ **不要用 `reset.bat` / `reset.sh`** |

> 🚨 **`reset.bat` / `reset.sh` 只支援 Docker**。它做的三件事是
> `docker compose down -v`、刪 `backend\.seeded`、刪 `backend\.env`。
> 對路線 A 的人來說：**真正的資料 `backend\erp.db` 一個字都沒被刪掉，
> 反而是含 JWT 密鑰與 API Key 的 `backend\.env` 被刪了** —— 下次啟動後端會直接掛掉。
> （`reset.sh` 還有 `set -e`，沒裝 Docker 時第一行就中止，等於什麼都沒做。）

路線 A 要重置，請自己手動來：

```powershell
:: 1) 先備份！
copy backend\erp.db D:\備份\erp-重置前.db
:: 2) 刪資料庫與標記
del backend\erp.db backend\erp.db-wal backend\erp.db-shm backend\.seeded
:: 3) 重建（.env 保留不要動）
cd backend
venv\Scripts\python.exe -m scripts.seed
```

## 完全移除

| 路線 | 怎麼做 |
|---|---|
| A（Windows） | 雙擊 **`uninstall_easy.bat`** |
| A（Mac/Linux） | `bash uninstall_easy.sh` |
| B / C | `docker compose down -v`，再刪掉整個資料夾 |

`uninstall_easy.bat` 會做的事：

1. 停掉 8000 / 5173 上的服務
2. 移除 `tools\python`（**含 Windows 註冊表項**，不會在「新增/移除程式」留下殘骸）
3. 刪 `tools\`、`backend\venv`、`frontend-desktop\node_modules`
4. **會問你**要不要一併刪掉 `backend\erp.db`、`uploads\`、`.env`（問兩次，預設不刪）
5. **會問你**要不要清 npm / pip 的全域 cache（有別的 Node/Python 專案的話建議選不要）

跑完之後整個 Ouvoca 資料夾就可以直接刪掉了。

> Mac / Linux 的 `uninstall_easy.sh` **不會**動到你的 Python / Node（那是 brew / apt 裝的，是系統的東西）。

---

# ✅ 安裝成功怎麼確認

一步一步自己檢查，任何一項不對就往下看對應的解法。

| # | 檢查 | 應該看到 | 不對的話 |
|---|---|---|---|
| 1 | 瀏覽器打開 http://localhost:8000/api/health | 一段 JSON，`"status":"ok"`、`"db":"ok"` | 後端沒起來 → 看 log |
| 2 | 瀏覽器打開 http://localhost:5173 | 深色動態漸層背景 + 白色登入卡 | 前端沒起來 |
| 3 | 登入卡右上角 | 🇹🇼 繁中 / 🇺🇸 EN 切換鈕 | — |
| 4 | 帳號密碼欄都空著時 | 黃色提示框：「💡 第一次安裝？預設帳號 admin，密碼 admin123。⚠️ 登入後請立即改密碼」 | — |
| 5 | 卡片最下方 | 綠色小圓點 + LLM 供應商名稱 | 沒設 Key 時可能不顯示 |
| 6 | 用 `admin` / `admin123` 登入 | 進到主畫面 | **登不進去 = seed 沒跑成功**，見下方 |
| 7 | 主畫面 | 4 張統計卡 + AI 摘要 + 紅色庫存警示（M6 螺絲低於安全庫存，這是刻意種的示範資料） | — |

> ❗ **看不到黃色「Demo Mode」按鈕是正常的。**
> 那顆按鈕只有在 `ALLOW_DEMO_BYPASS=true` 時才出現，而三個地方（`.env.example`、`docker-compose.yml`、程式預設）
> 全都預設 `false` —— 因為它會讓任何人用 `Bearer demo` 取得超級管理員權限。
> **正確安裝的系統看不到這顆按鈕才對。**

**第 6 項登不進去（seed 沒跑成功）的補救**：

```powershell
:: 路線 A（Windows）
cd backend
venv\Scripts\python.exe -m scripts.seed
```
```bash
# 路線 A（Mac/Linux）
cd backend && venv/bin/python -m scripts.seed

# 路線 B / C（Docker）
docker compose exec -T backend python -m scripts.seed
```

**你會看到什麼**（這幾行代表成功，中間會夾雜大量 SQL 訊息，那是正常的）：

```text
✓ Permission seed completed.
  Tenants: HQ
  Permissions: 231 (182 main + 49 extras)
  Roles: 10
  Row Filters: 6
✓ seed_accounts: 86 defined (86 created / 0 updated)
✓ Seed completed.
  Admin login: username='admin' password='admin123'
  Parts: 10  Products: 2  Suppliers: 4  Customers: 4
```

`scripts.seed` 一支就包辦了：建表 → **231 個權限碼 + 10 個角色** → **86 科台灣會計科目表** →
**14 項系統組態預設值** → 示範用的料件 / 成品 / BOM / 供應商 / 客戶 / 工作中心。

---

# ❓ 常見問題

<details>
<summary><strong>Q1. 要花錢嗎？</strong></summary>

| 項目 | 費用 |
|---|---|
| Ouvoca 軟體 | 免費（開源授權，商用另有條款） |
| Docker | 免費（小企業免授權費，詳見 Docker 官網條款） |
| 跑在自己電腦 | 只有電費 |
| LLM API（選用） | 看用量；DeepSeek 大約 NT$300–1,000／月 |

不設 LLM API Key 的話，總花費是 **NT$0**（少了「用講的」那個功能而已）。

</details>

<details>
<summary><strong>Q2. 手機可以看嗎？</strong></summary>

**預設不行，而且這是刻意的安全設計。**

- Docker 路線：`docker-compose.yml` 把所有 port 都綁在 `127.0.0.1`（第 21、56、74、90、108 行），
  檔頭也寫明「不暴露到 LAN」。
- 本機路線：前端的 vite 沒有設 `host`，預設只聽 localhost。

要讓區網或手機連得到，需要同時處理 port 綁定、`CORS_ORIGINS`、防火牆三件事。
請照 [`NETWORK_DEPLOYMENT_ZH.md`](./NETWORK_DEPLOYMENT_ZH.md) 做，別只改一個地方。

</details>

<details>
<summary><strong>Q3. 「Port 8000 已被佔用」怎麼辦？</strong></summary>

`install.bat` / `install.sh` 會先檢查 8000、5173、8080、8001、8002 這五個 port，有人佔用就中止。

常見佔用者：之前沒關乾淨的 Ouvoca（先跑 `docker compose down`）、其他專案的開發伺服器、Skype。

真的需要換 port：改 `docker-compose.yml` 裡的對應那行，例如
`"127.0.0.1:8000:8000"` 改成 `"127.0.0.1:8888:8000"`，
然後 `CORS_ORIGINS` 與前端的 API 位址也要一起調整。

</details>

<details>
<summary><strong>Q4. 版本號怎麼看？畫面顯示 2.0.0 是不是裝錯了？</strong></summary>

版本號來自 `/api/health` 的 `version` 欄位，登入卡下面也會顯示。

程式內建的版本是 **3.69.0**（`backend/app/config.py`），
但 `backend/.env.example` 第 10 行還留著一行舊的 `APP_VERSION=2.0.0`，
而 `.env` 的值優先權比程式內建高。所以**如果你是從 `.env.example` 複製出來的，畫面就會顯示 2.0.0**。

要顯示正確版本：把 `backend/.env` 裡的 `APP_VERSION=2.0.0` 那一行刪掉（Docker 路線刪完要 `--build` 重建）。

</details>

<details>
<summary><strong>Q5. 想換一台電腦用？</strong></summary>

1. 舊電腦：停掉服務，備份 `backend/erp.db`、`backend/.env`、`backend/uploads/`
2. 新電腦：照本文重新安裝一次（路線隨你）
3. 安裝完先停掉服務，把備份的三樣蓋回去
4. 重新啟動

> `.env` 一定要一起搬 —— 裡面有 `JWT_SECRET`，換了之後所有人都要重新登入；
> 如果有接外部資料庫而又沒設 `CONNECTION_ENCRYPTION_KEY`，那些連線設定會直接解不開。

</details>

<details>
<summary><strong>Q6. 公司網路擋住下載怎麼辦？</strong></summary>

`install_easy.bat` 需要連 `python.org`、`nodejs.org`、`pypi.org`、`registry.npmjs.org`，
請 IT 把這四個網域加白名單。

⚠️ [`INSTALL_TROUBLESHOOTING_ZH.md`](./INSTALL_TROUBLESHOOTING_ZH.md) 裡寫「自己先裝好 Node，腳本會偵測到就跳過下載」
—— **這句話目前是錯的**。`install_easy.bat` 只檢查 `tools\node\node.exe` 存不存在，
從頭到尾沒有 `where node`，所以還是會重新下載。
可行的替代作法：自己把 `node-v20.11.1-win-x64.zip` 下載好放到 `tools\downloads\node.zip`，再跑腳本。

另外，腳本裡的 `curl` **沒有加 `-f` 參數**，所以公司網路的攔截頁面會被當成正常檔案存下來，
要到執行安裝檔或解壓的時候才會爆出看不懂的錯誤。下載完覺得怪怪的，先確認
`tools\downloads\python-installer.exe` 有沒有 20 MB 以上。

</details>

---

# 📚 延伸閱讀

| 想知道什麼 | 看這份 |
|---|---|
| 裝失敗了，按症狀查 | [`INSTALL_TROUBLESHOOTING_ZH.md`](./INSTALL_TROUBLESHOOTING_ZH.md) |
| 怎麼申請 LLM API Key | [`HOW_TO_GET_LLM_API_KEY_ZH.md`](./HOW_TO_GET_LLM_API_KEY_ZH.md) |
| 每天怎麼操作 | [`USER_MANUAL_ZH.md`](./USER_MANUAL_ZH.md) |
| 開放給區網 / 正式上線 | [`NETWORK_DEPLOYMENT_ZH.md`](./NETWORK_DEPLOYMENT_ZH.md) |
| 備份與災難復原 | [`BACKUP_RESTORE_SOP_ZH.md`](./BACKUP_RESTORE_SOP_ZH.md) |
| 密鑰輪換 | [`SECRETS_ROTATION_SOP_ZH.md`](./SECRETS_ROTATION_SOP_ZH.md) |
| 系統管理、進階部署 | [`ADMIN_GUIDE.md`](./ADMIN_GUIDE.md) |
| 安裝時下載的第三方軟體授權 | [`THIRD_PARTY_DOWNLOADS_ZH.md`](./THIRD_PARTY_DOWNLOADS_ZH.md) |

**PDF 版手冊**：Windows 雙擊 `build_pdfs.bat`、Mac/Linux 跑 `./build_pdfs.sh`（需 Node.js），
產出在 `docs/pdf/`。詳見 [`scripts/build-pdfs/README.md`](../scripts/build-pdfs/README.md)。

---

# 📞 需要協助

回報安裝問題時，附上這些會快很多：

1. 你走的是哪一條路線（A / B / C）
2. 作業系統版本
3. 卡在哪一個 Step（截圖最好）
4. 後端的錯誤訊息
   - 路線 A：`logs-backend.txt`，或標題 `ouvoca-backend` 那個視窗的內容
   - 路線 B / C：`docker compose logs --tail=50 backend`
