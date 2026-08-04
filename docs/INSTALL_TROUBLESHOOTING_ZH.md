# 安裝排錯指南（電腦小白版）/ Install Troubleshooting Guide

> **裝失敗了？別慌**，本文按「症狀」分類，最常見的問題排在最前面。
> 90% 的安裝問題能用前 3 條解決。
>
> **English version**: [INSTALL_TROUBLESHOOTING_EN.md](./INSTALL_TROUBLESHOOTING_EN.md)

---

## 🆘 緊急自救：先試這 3 件事

不論什麼錯誤訊息，先做這 3 件事，能解決 80% 問題：

1. **以系統管理員身分執行**
   右鍵 `install_easy.bat` → 「以系統管理員身分執行」
2. **暫時關閉防毒軟體**
   Windows Defender / Norton / Kaspersky / 趨勢科技都可能誤判 silent Python installer
   裝完後再開回去
3. **檢查網路**
   `install_easy.bat` 需要連 `python.org`、`nodejs.org`、`pypi.org`、`registry.npmjs.org`
   公司網路常擋這幾個域名，請聯絡 IT 加白名單

---

## 📋 按錯誤訊息查表

### `curl: command not found` 或 `tar: command not found`

**原因**：你的 Windows 太舊（10 build 1803 以前）。
**解法**：
- 升級到 Windows 10 1903+ 或 Windows 11，或
- 改用 Docker 路徑（`install.bat`）

### `Python install failed` / Python 安裝失敗

**最可能原因**：防毒軟體擋了 silent installer。
**解法**：
1. 暫時關閉防毒軟體 30 分鐘
2. 重跑 `install_easy.bat`
3. 裝完後重開防毒軟體
4. 把專案資料夾加入防毒**白名單**（避免運行時被擋）

**次要原因**：磁碟空間不足。Python 安裝需要 ~300 MB。

### `Node download failed`

**原因**：網路不穩，或 nodejs.org 連不上。
**解法**：
```
1. 在瀏覽器手動測試 https://nodejs.org/dist/v20.11.1/
   能不能打開？打不開 → 公司網路擋了
2. 若公司擋 nodejs.org，請聯絡 IT 開放，或
3. 改用手動安裝：
   - 從 https://nodejs.org/zh-tw/ 下載 LTS 版（Windows Installer .msi）
   - 安裝完後再跑 install_easy.bat
   - 腳本會偵測到系統已有 node 並跳過下載
```

### `pip install failed` / 後端套件安裝失敗

**最可能原因 1**：網路問題（PyPI 連不上）。
```cmd
ping pypi.org
```
若 unreachable → 公司網路擋了，請開放 `pypi.org` + `*.pythonhosted.org`。

**最可能原因 2**：某個套件需要 Visual C++ Build Tools。
**解法**：安裝免費的 [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) → 重跑。

**最可能原因 3**：用了公司 Proxy。
**解法**：先設環境變數，再跑腳本：
```cmd
set HTTPS_PROXY=http://your-proxy:port
set HTTP_PROXY=http://your-proxy:port
install_easy.bat
```

### `npm install failed` / 前端套件安裝失敗

**原因 1**：網路不穩，npm registry 連不上。
**解法**：用淘寶鏡像（台灣可用）：
```cmd
cd frontend-desktop
npm config set registry https://registry.npmmirror.com
npm install
```

**原因 2**：node_modules 已部分損壞。
**解法**：
```cmd
rmdir /s /q frontend-desktop\node_modules
del frontend-desktop\package-lock.json
install_easy.bat
```

### `Backend failed to start in 30s`

**原因 1**：8000 埠被占用（其他程式在用）。
**解法**：
```cmd
netstat -ano | findstr :8000
```
看到 PID，例如 12345 → `taskkill /F /PID 12345`。

**原因 2**：backend\\.env 缺欄位或格式錯誤。
**解法**：
```cmd
del backend\.env
install_easy.bat
```
讓腳本重新建立 `.env`。

### 瀏覽器打開 http://localhost:5173 顯示「無法連線」

**原因**：前端沒啟動，或防火牆擋了 5173。
**解法**：
1. 看 `ouvoca-frontend` 那個小視窗有沒有錯誤訊息
2. Windows 防火牆 → 允許 `node.exe` 連線
3. 重跑 `start.bat`

### 「忘記密碼」/「登入失敗」

預設帳密：`admin` / `admin123`
若改過密碼忘記，重新初始化 DB：
```cmd
del backend\erp.db
del backend\.seeded
install_easy.bat
```
⚠️ 注意：會清掉所有資料。

---

## 🔥 完全裝不起來怎麼辦？

如果上面試了都不行，**最後的求救手段**：

### 求救選項 A：用 Docker 路徑

Docker 路徑相對「容錯」，但需要先裝 Docker Desktop：
1. <https://www.docker.com/products/docker-desktop/> 下載安裝
2. 雙擊 `install.bat`（不是 install_easy.bat）

### 求救選項 B：找在地 IT

Taiwan SMB 常見方案：請在地 IT 廠商代裝（500-2000 NT$/次）。
請他們看本份排錯指南 + 把錯誤訊息給他們，通常 1 小時內解決。

### 求救選項 C：開 GitHub Issue

到 <https://github.com/fanchanyu/ouvoca/issues> 開 issue，附上：
1. Windows 版本（`winver` 看一下）
2. 完整錯誤訊息（截圖）
3. 卡在哪一步（`[Step X/5]`）

我們會在 48 小時內回覆。

---

## 💡 預防建議（裝完之後）

1. **把 Ouvoca 資料夾加入防毒白名單** — 避免每次啟動被掃描拖慢
2. **定期備份 `backend/erp.db`** — 這檔就是你所有的 ERP 資料
3. **首次登入後立刻改密碼** — 不要繼續用 `admin123`
4. **記得開瀏覽器 bookmark** http://localhost:5173

---

## 🆙 我昨天裝的，今天有新版怎麼辦？/ Upgrade

> **不要重裝**！重裝會把你的 ERP 資料清掉。**用 `update.bat`** 才能保留資料。

### 正常情境（90% 適用）

1. **關閉 Ouvoca**（關掉那兩個 cmd 視窗）
2. **雙擊 `update.bat`** — 會自動跑 6 步：
   - Step 1: 停止服務（埠口 8000 / 5173）
   - Step 2: **備份你的資料** 到 `backups\YYYYMMDD_HHMMSS\`（erp.db / .env / uploads）
   - Step 3: 從 GitHub 下載新版（自動偵測 git pull 或下載 zip）
   - Step 4: 更新 pip + npm 套件（如果有新依賴）
   - Step 5: 跑 `alembic upgrade head`（如果有資料庫結構變動）
   - Step 6: 重啟服務，自動開瀏覽器
3. **完成！** 你的所有 ERP 資料完全保留

### 萬一新版有 bug 想還原昨天版本

1. 關閉 Ouvoca
2. 開 `backups\YYYYMMDD_HHMMSS\` 找最新的備份
3. 把備份內的 `erp.db` 複製回 `backend\`
4. 把備份內的 `.env` 複製回 `backend\`
5. 把備份內的 `uploads\` 複製回 `backend\uploads\`
6. 雙擊 `start.bat`

> 💡 每個備份資料夾內都有 `README.txt` 寫具體還原步驟。

### update 失敗的常見原因

| 錯誤 | 解法 |
|------|------|
| `git pull 失敗 — 有衝突` | 你改過 code，建議：建新資料夾重裝 + 從備份還原資料 |
| `下載失敗` | 網路問題 — 用瀏覽器測 https://github.com/fanchanyu/ouvoca/archive/refs/heads/main.zip 能不能下 |
| `pip install 失敗` | 防火牆擋 pypi.org — 同 [pip install failed](#pip-install-failed--後端套件安裝失敗) |
| `alembic upgrade 失敗` | 通常無害（SQLite 會自動建表）— 重新跑 `start.bat` 看能不能進系統 |

### 我不想自動更新，想自己控制

不跑 `update.bat` 即可。Ouvoca 永遠不會自動更新自己。

要手動檢查有沒有新版：
- 進 https://github.com/fanchanyu/ouvoca/releases
- 看最新版本號 vs 你的版本（畫面右下角 / 後端 `/api/health` 都有）

---

## 🗑 完全移除 Ouvoca / Uninstall

> ⚠️ **不要只刪資料夾**！`install_easy.bat` 跑的 Python silent installer 會在
> **Windows 註冊表**留下「Python 3.11 (64-bit)」項，出現在「新增/移除程式」清單。
> 直接刪資料夾不會清掉這個。

### 正確移除步驟（Windows）

**雙擊 `uninstall_easy.bat`** — 會自動執行：

| 步驟 | 動作 |
|------|------|
| 1️⃣ | 停止執行中的 backend (8000) + frontend (5173) |
| 2️⃣ | 用 Python 原 installer 跑 `/uninstall` 模式 → **清乾淨註冊表** |
| 3️⃣ | 刪 `tools\python` + `tools\node` + 下載暫存 |
| 4️⃣ | 刪 `backend\venv` + `frontend-desktop\node_modules` |
| 5️⃣ | **問你**：要刪你的 ERP 資料嗎？（`erp.db` / `uploads/` / `.env`）|
| 進階 | **問你**：要清全域 npm/pip cache 嗎？（釋放 ~500MB，但會影響其他專案）|

完成後，可放心刪除整個 Ouvoca 資料夾，**Windows 系統零殘留**。

### Mac / Linux

```bash
bash uninstall_easy.sh
```

注意：Mac/Linux 路徑下 Python / Node 是你自己用 `brew` / `apt` 裝的，
解除安裝腳本**不會動到它們**（因為其他專案可能在用）。
只會清這個專案的 `venv` + `node_modules` + 問你要不要清資料。

### 我手動刪了資料夾才發現有 Python 殘留怎麼辦？

開 PowerShell（系統管理員）執行：
```powershell
# 移除 Python 註冊表項
reg delete "HKCU\Software\Python\PythonCore\3.11" /f
# 從「新增/移除程式」清單拿掉
Get-ChildItem "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall" |
  Where-Object { $_.GetValue("DisplayName") -like "Python 3.11*" } |
  Remove-Item -Recurse -Force
```

### 我想保留資料但只移除程式怎麼辦？

跑 `uninstall_easy.bat` → 在「也刪除你的 ERP 資料嗎」**選 N** → 程式部分清乾淨，
`backend\erp.db` + `backend\uploads\` + `backend\.env` 全保留。
之後想重裝，重新跑 `install_easy.bat` 會自動沿用你的資料。

---

# ❓ 安裝常見問題 FAQ（Q1–Q14）

> 🇹🇼 這 14 題自 `README.md` 搬移過來（原第 462–663 行），安裝前先看能省 90% 麻煩。
> 🇺🇸 These 14 questions moved here from `README.md`. Reading them first saves 90% of headaches.
>
> ⚠️ 搬移時修正了兩處**照抄會執行失敗**的指令（Q7 的 `scripts.create_admin` 不存在；
> Q11 的三個 Python 符號名稱與程式碼不符），並移除了兩個已過期的「下個 sprint 補」承諾。

<details>
<summary><strong>Q1. 我的電腦跑得動嗎？/ Will my computer run this?</strong></summary>

| 項目 | 最低 / Min | 建議 / Recommended |
|---|---|---|
| 作業系統 | Win 10 / macOS 11 / Ubuntu 20 | Win 11 / macOS 13 |
| RAM | 4 GB | 8 GB+ |
| 硬碟空間 | 5 GB | 20 GB+（含 Docker images）|
| CPU | 任何 x86_64 / ARM64 | 4 核以上 |
| GPU | ❌ 不需要 | ❌ 不需要（LLM 用雲端 API）|
| 網路 | 安裝時需要 | 日常使用**不需要**（除非開 AI 對話）|

</details>

<details>
<summary><strong>Q2. install.bat 提示「找不到 Docker」/ "Docker not found"</strong></summary>

你還沒裝 Docker Desktop。回 Step 2️⃣ 完成安裝、**重開機**、桌面看到 🐳 圖示再來。

如果裝了 Docker 但還是這個錯：開 Docker Desktop（雙擊桌面 🐳）→ 等左下角出現 `Engine running` 綠燈 → 再跑 install.bat。

</details>

<details>
<summary><strong>Q3. install.bat 卡在「啟動服務」很久 / Stuck at "Starting services"</strong></summary>

首次下載 Docker images（~2 GB）需要 2-5 分鐘，**請耐心等**。
網速慢可能要 10-20 分鐘。

確認方法：另開一個 terminal/cmd 跑 `docker ps`，看到 ouvoca-backend / ouvoca-frontend 在 Up 狀態 = 進度正常。

</details>

<details>
<summary><strong>Q4. 瀏覽器打開只看到「Cannot connect / 無法連線」</strong></summary>

最常見：等服務完全啟動需要 1-2 分鐘，**等一下再重新整理 (F5)**。

還不行的話：
1. 確認 install.bat 沒報錯（看到「安裝完成」）
2. `docker compose ps` 看服務狀態都是 `Up`
3. `docker compose logs backend` 看後端錯誤訊息
4. 試試 http://127.0.0.1:5173（換 localhost）

</details>

<details>
<summary><strong>Q5. 提示「Port 5173 / 8000 被占用」/ "Port in use"</strong></summary>

你的電腦已經有其他程式用了同樣的 port（最常見是 Vite dev server 或別的 web 服務）。

**最簡單**：重開機，再跑 install.bat。

**進階**：
- Windows: `netstat -ano | findstr :5173` 找到 PID → 用工作管理員關掉
- Mac/Linux: `lsof -i :5173` 找到 PID → `kill -9 <PID>`

</details>

<details>
<summary><strong>Q6. Windows Defender / 防毒軟體擋住了 install.bat</strong></summary>

第一次跑批次檔常見現象。Ouvoca 是開源 (AGPL-3.0)，可以在 GitHub 完整檢視程式碼。

按「**更多資訊 → 仍要執行 (Run anyway)**」就好。

不放心可以先閱讀 `install.bat` 的內容（用記事本打開）— 只做 5 件事：檢查 Docker、設定 .env、跑 docker compose、等就緒、執行 seed。

</details>

<details>
<summary><strong>Q7. 預設帳號 admin / admin123 安全嗎？要改嗎？</strong></summary>

**內部使用**（公司內網、沒對外開放）：可以不改，方便試用。

**對外發行**（連得到網際網路或多人共用）：**一定要改！**

**改密碼最快的方法 —— 在 AI 助手（Chat）打字：**

```
改密碼，我的新密碼是 MyN3wP@ss
```

→ AI 會出 ConfirmCard 確認卡 → 點「確認」→ 下次用新密碼登入。
（改完密碼會自動撤銷其他裝置上的舊登入，這是 v3.62 的行為。）

對外發行時也要把 `backend/.env` 的 `JWT_SECRET` 換成 64 字元亂數
（`install.bat` / `install_easy.bat` 已經自動產生過了）。

</details>

<details>
<summary><strong>Q8. 我可以匯入舊的 Excel / 報價單 / 鼎新 DB 嗎？</strong></summary>

**3 種匯入方式**：

| 方式 | 場景 | 怎麼做 |
|---|---|---|
| 📁 直接上傳 | 報價單 / 發票 / 合約 / 規格書 PDF | 登入 → ⚙️ 設定 → 上傳業務文件 → 拖檔案 → 選分類 |
| 📊 Excel CSV 匯入 | 你的料件清單、客戶清單 | 用 Schema Mapping AI 接 connector（自動對欄位）|
| 🔗 直連現有 ERP | 鼎新 / 正航 / SAP 主檔 | 設定 connector，AI 自動 mapping 欄位（見 [外部 DB 串接指南](./EXTERNAL_DB_INTEGRATION_DESIGN_ZH.md)）|

**🌱 小小企業軌（≤20 人）免費含閉源 connector！**

> ⚠️ **直連現有商用 ERP 前的合規提醒**：商用 ERP（例如 Workflow / ChengHang / SAP B1 / Vitals 等）之授權合約對「以共用 / 服務帳號連線」之規定可能不同；具體請依貴司與該廠商之合約為準。建議客戶於啟用前先和原 ERP 廠商書面確認授權範圍，必要時購買相應之整合授權。Ouvoca **不參與、不代理**與第三方 ERP 廠商之合約 / 授權事務；於適用法律所允許之最大範圍內不承擔相關責任。完整提醒：[`EXTERNAL_DB_LICENSING_NOTICE_ZH.md`](./EXTERNAL_DB_LICENSING_NOTICE_ZH.md) / [EN](./EXTERNAL_DB_LICENSING_NOTICE_EN.md)。

</details>

<details>
<summary><strong>Q9. 我的資料安全嗎？會不會傳到雲端？</strong></summary>

**完全本地**，除非你自己開啟 AI 對話：

| 項目 | 在哪 | 會傳出去嗎？ |
|---|---|---|
| 業務資料（料件、訂單、庫存）| 你的電腦 `backend/erp.db`（SQLite）或你設的 PostgreSQL | ❌ 永不離開你的電腦 |
| 上傳的檔案（報價單、發票）| 你的電腦 `backend/uploads/` | ❌ 永不離開 |
| **AI 對話**（如果你開啟） | 只有「**你打的問題文字**」會傳給 LLM 供應商（DeepSeek / OpenAI 等）| ⚠️ **問題文字**會出去，但 DB 資料不會 |

如果連 LLM 都不想連網 → 用本地 Ollama（離線模式，見 [`HOW_TO_GET_LLM_API_KEY_ZH.md`](./HOW_TO_GET_LLM_API_KEY_ZH.md)）。

</details>

<details>
<summary><strong>Q10. 一定要連網嗎？/ Do I need internet?</strong></summary>

| 階段 | 需要網路嗎？ |
|---|---|
| 第一次安裝（下載 Docker images） | ✅ 需要 |
| 日常使用（CRUD、查報表） | ❌ 不需要 |
| AI 對話（如果有開啟）| ⚠️ 需要（除非用 Ollama 離線 LLM） |
| 更新到新版 | ✅ 需要 |

</details>

<details>
<summary><strong>Q11. 我忘了密碼怎麼辦？/ Forgot password?</strong></summary>

**先試最簡單的**：如果你**還登得進去**（只是想換密碼），在 AI 助手講
「改密碼，我的新密碼是 XXX」即可，不需要碰指令列。

**真的完全登不進去**時，才用下面這段重設 admin 密碼：

```bash
docker compose exec backend python -c "
import asyncio
from app.database import AsyncSessionLocal
from app.models.organization import User
from app.services.auth import hash_password
from sqlalchemy import select

async def reset():
    async with AsyncSessionLocal() as db:
        u = (await db.execute(select(User).where(User.username=='admin'))).scalar_one()
        u.hashed_password = hash_password('newpass123')
        await db.commit()
        print('OK admin 密碼已重設為 newpass123')

asyncio.run(reset())
"
```

> 非 Docker 安裝（`install_easy.bat`）請在 `backend\` 目錄下改用
> `..\tools\python\python.exe -c "..."`（同一段程式碼）。
> 重設完請立刻登入改成你自己的密碼。
>
> 仍然卡住？開 [GitHub Issue](https://github.com/fanchanyu/ouvoca/issues/new)。

</details>

<details>
<summary><strong>Q12. 小小企業免費門檻怎麼算？/ How is the ≤20 free tier counted?</strong></summary>

看 **同時在線使用者數**（24 小時內任一時刻的峰值，15 分鐘 idle 算下線）。

舉例：
- 公司 50 人有 Ouvoca 帳號，但同時在線最多 18 人 → ✅ 適格（白用）
- 公司 25 人，同時在線常 22 人 → ❌ 不適格（需商業授權）
- 公司 100 人但只 5 個業務在用 → ✅ 適格

完整條款：[`LICENSE-SMALL-BUSINESS.md`](../LICENSE-SMALL-BUSINESS.md)

</details>

<details>
<summary><strong>Q13. 升級到新版怎麼弄？/ How to upgrade?</strong></summary>

**最簡單（推薦）**：雙擊專案根目錄的 `update.bat`（Mac / Linux 跑 `bash update.sh`）。
它會自動備份你的資料 → 拉新版 → 跑資料庫升級 → 補權限碼 → 重啟。

**Docker 使用者手動升級**：

```bash
cd Ouvoca
git pull origin main          # 或重下載 ZIP 覆蓋
docker compose down
docker compose up -d --build  # 重 build 新版
docker compose exec backend alembic upgrade head   # 跑 DB migration
docker compose exec backend python -m scripts.seed_permissions  # 補新版權限碼
```

你的資料（DB + uploads/）會**完整保留**。

> 💡 最後那行別漏掉：新版新增的功能會帶新的權限碼，沒補會出現「明明是管理員卻 403」。

</details>

<details>
<summary><strong>Q14. 我電腦已有其他版本的 Python（3.12 / 3.13）/ 沒裝 Python，會衝突嗎？</strong></summary>

**完全不會。** `install_easy.bat` 會把 Python 3.11.9 安裝到專案內的 `tools\python\` 資料夾，**不修改你系統的 PATH、不污染你現有的 Python**。

- 如果你系統有 Python 3.12 / 3.13 → 它們繼續存在，`install_easy` 用自己的 3.11
- 如果你系統沒 Python → `install_easy` 直接下載 3.11.9 silent install 進 `tools\python\`
- 卸載：跑 `uninstall_easy.bat`（會一併清 Windows 註冊表殘留）

`start.bat` 啟動時會**優先**使用 `tools\python\` 的 Python，而不是系統的。

</details>

⚠️ **還沒解的問題？** 開 [GitHub Issue](https://github.com/fanchanyu/ouvoca/issues/new) 我們處理。

---

**最後更新**：v3.70（2026-08-04）· FAQ Q1–Q14 自 README 搬入

