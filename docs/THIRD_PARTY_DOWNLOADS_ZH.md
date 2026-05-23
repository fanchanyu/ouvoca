# 第三方下載揭露 / Third-Party Downloads Disclosure

> 本文件揭露 `install_easy.bat` / `install_easy.sh` 在執行時會從哪些第三方
> 下載什麼軟體、各自授權為何，以及您可以如何手動取得（若您不放心使用自動腳本）。
>
> **Ouvoca 不重新散布（redistribute）這些軟體**——所有檔案都是您的電腦直接從
> 原廠官方網站下載，腳本只是代替您點擊「下載」按鈕。

---

## 1. 自動下載清單

| 名稱 | 版本 | 大小 | 來源 URL | 授權 |
|------|------|------|----------|------|
| **Python** | 3.11.9 | ~26 MB | <https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe> | [PSF License](https://docs.python.org/3/license.html)（類 BSD，可商用、無 copyleft） |
| **Node.js** | 20.11.1 LTS | ~30 MB | <https://nodejs.org/dist/v20.11.1/node-v20.11.1-win-x64.zip> | [MIT License](https://github.com/nodejs/node/blob/main/LICENSE)（可商用、無 copyleft） |
| **pip + setuptools + wheel** | 隨 Python | ~5 MB | 由 Python 3.11.9 內建 | 同 PSF License |
| **npm 套件**（v3.49 約 250 MB） | 隨 `package.json` 變動 | ~250 MB | npm registry <https://registry.npmjs.org/> | 各套件不同，多為 MIT/Apache-2.0/ISC |
| **PyPI 套件**（FastAPI / SQLAlchemy / Pydantic 等） | 隨 `requirements.txt` 變動 | ~200 MB | PyPI <https://pypi.org/> | 各套件不同，多為 MIT/Apache-2.0/BSD |

**總下載量**：約 **500 MB**（首次安裝；後續啟動 0 下載）。

---

## 2. 對「重新散布」的法律立場

`install_easy.bat` **不包含、不打包、不修改**任何上述軟體：

- 腳本內**沒有**夾帶 Python / Node 的二進位
- 腳本**僅執行 `curl` 命令**從原廠下載，等同於使用者親自點瀏覽器
- 腳本將下載檔暫存至 `tools/downloads/`，原檔未經修改
- 安裝後的 `tools/python/`、`tools/node/` 內容**完全等同**於使用者親自安裝

因此就法律上，您執行 `install_easy.bat` ≡ 您親自下載並安裝 Python / Node。
Ouvoca 並未對這些第三方軟體取得任何權利，也未授予任何權利。

各軟體之使用條款請以原廠最新公告為準（連結見上表「授權」欄）。

---

## 3. 隱私與遙測

- **`install_easy.bat` / `start.bat` 不會向 Ouvoca 或任何第三方回傳任何資料。**
- 唯一的網路活動 = 從上表 URL 下載檔案。
- Python 與 Node 安裝後**預設不啟用任何 telemetry**（Node 預設關閉，Python 從未有）。
- 您可以離線安裝（見下方第 4 節）以避免任何外部連線。

Ouvoca 本身**不收集任何安裝統計、使用統計、錯誤回報**。本機運行 = 完全本機資料。

---

## 4. 離線安裝（不想連網下載？）

若您身處離線環境 / 公司禁止外連 / 不信任自動下載，您可以：

### Step 1 — 在有網路的電腦先手動下載

```
1. 從 <https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe>
   下載 python installer，存成 python-installer.exe

2. 從 <https://nodejs.org/dist/v20.11.1/node-v20.11.1-win-x64.zip>
   下載 node zip，存成 node.zip
```

### Step 2 — 把檔案放到對應位置

```
opnetest\
└── tools\
    └── downloads\
        ├── python-installer.exe   (步驟 1 下載的)
        └── node.zip               (步驟 1 下載的)
```

### Step 3 — 雙擊 `install_easy.bat`

腳本偵測到 `tools/downloads/` 已有檔案 → 跳過下載 → 直接使用。

> ⚠️ 注意：PyPI 套件（FastAPI 等）和 npm 套件仍需網路。
> 真正完全離線需另用 `pip download` + `npm pack` 預先打包。

---

## 5. SHA-256 校驗（進階使用者）

若您要確認下載檔未被中間人攻擊（MITM）篡改：

| 檔案 | 預期 SHA-256（請以原廠最新公告為準） |
|------|--------------------------------------|
| `python-3.11.9-amd64.exe` | 見 <https://www.python.org/downloads/release/python-3119/> 頁面下方 "Files" 表 |
| `node-v20.11.1-win-x64.zip` | 見 <https://nodejs.org/dist/v20.11.1/SHASUMS256.txt> |

Windows 校驗指令：
```cmd
certutil -hashfile tools\downloads\python-installer.exe SHA256
certutil -hashfile tools\downloads\node.zip SHA256
```

> 將輸出比對原廠公告的 SHA-256 值。不一致 → 立即刪除 + 重下載 + 報告。

---

## 6. 與 Docker 路徑的對照

| 維度 | `install_easy.bat`（電腦小白）| `install.bat`（Docker） |
|------|------------------------------|-------------------------|
| 下載什麼 | Python 26MB + Node 30MB + 套件 500MB | Docker images（Ouvoca + postgres 等）約 1-2 GB |
| 從哪下載 | python.org / nodejs.org / PyPI / npm | Docker Hub (`docker.io`) |
| 自動執行什麼 | silent install + venv 建立 | `docker compose up -d` |
| 法律性質 | 等同使用者親自下載 | 等同使用者親自執行 docker pull |

兩條路徑在法律性質上**完全相同**——Ouvoca 僅提供腳本協助流程，不重新散布第三方軟體。

---

**最後更新**：v3.49（2026-05-22）
**English version**: [THIRD_PARTY_DOWNLOADS_EN.md](./THIRD_PARTY_DOWNLOADS_EN.md)
