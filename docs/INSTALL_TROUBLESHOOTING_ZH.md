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

**最後更新**：v3.51（2026-05-24）
