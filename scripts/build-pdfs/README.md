# LLM-ERP PDF Builder

> **把所有客戶面向手冊轉成精美 PDF / Convert all customer-facing manuals to beautiful PDFs**
> 中文 | [English](#english)

---

## 中文版

### 🎯 為什麼需要 PDF？

| 場景 | 為什麼用 PDF | 為什麼不用 Markdown |
|---|---|---|
| 寄給客戶 | 排版固定、不會跑版 | 客戶不會 render markdown |
| 列印手冊 | A4 分頁、頁碼齊全 | 純文字列印醜 |
| 簽呈附件 | 正式公文格式 | 不接受 .md |
| 老闆 iPad 看 | iOS 原生 PDF | 要裝 app |
| 客戶 LINE 傳 | 直接預覽 | 看不懂 |

### 📦 包含哪些 PDF？

執行後在 `docs/pdf/` 產生 **12 份 PDF**（雙語對稱）：

| # | 檔名 | 對象 | 雙語 |
|---|---|---|---|
| 01 | 安裝指南_中文.pdf / Installation_Guide_EN.pdf | 老闆/秘書 | ✅ |
| 02 | 快速入門_Quick_Start.pdf | 所有使用者 | ✅（單檔） |
| 03 | 使用者操作手冊_中文.pdf / User_Manual_EN.pdf | 業務/廠長/採購 | ✅ |
| 04 | Mobile_App_使用指南_Guide.pdf | 手機使用者 | ✅（單檔） |
| 05 | 網路部署規劃_中文.pdf / Network_Deployment_EN.pdf | IT/導入工程師 | ✅ |
| 06 | 系統架構流程拓樸_中文.pdf / System_Architecture_Topology_EN.pdf | IT/架構師 | ✅ |
| 07 | LLM評比報告_中文.pdf / LLM_Benchmark_Report_EN.pdf | 採購決策者 | ✅ |

> ⚠️ **不轉 PDF 的文件**：CLAUDE.md / WORKLOG.md / GAP_ANALYSIS.md / CUSTOMER_POSITIONING.md / ROADMAP.md / DEVELOPMENT_SOP.md / CODE_REVIEW_REPORT.md / ARCHITECTURE_DECISIONS.md / PERMISSION_MODEL.md … 都是**內部開發文件**，客戶不需要看。

### 🚀 快速開始

#### 前置（一次性）

需要 **Node.js 18 或 20 LTS**：
- Windows: 去 https://nodejs.org/ 下載 `.msi`，一路 Next
- Mac: `brew install node@20`
- Linux: `curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash - && sudo apt-get install -y nodejs`

#### 執行

**Windows**：直接雙擊專案根目錄的 `build_pdfs.bat`

**Mac / Linux**：
```bash
cd opnetest
chmod +x build_pdfs.sh
./build_pdfs.sh
```

#### 流程

```
[1] 檢查 Node.js  ✓
[2] 安裝依賴（首次 ~150 MB，含 Chromium）
[3] 跑 12 份 PDF 轉換
[4] 自動開啟 docs/pdf 資料夾
```

**首次執行**：約 3-5 分鐘（下載 Puppeteer Chromium）
**之後執行**：約 30 秒-1 分鐘

### 🎨 PDF 樣式特色

- **眼睛舒服**：白底深字，A4 排版
- **中英文字型**：自動 fallback 到系統可用字型（微軟正黑體 / PingFang TC / Noto Sans CJK）
- **代碼區塊**：深色背景、單行不會被切斷分頁
- **表格美化**：藍色表頭、斑馬線、邊框
- **頁首頁尾**：自動加上文件標題 + 頁碼
- **Mermaid 圖**：透過 Puppeteer 自動渲染為向量圖

詳細樣式設定見 `style.css`。

### 🔧 進階：自訂

#### 加入新文件

編輯 `build.mjs` 的 `DOCS_TO_BUILD`：

```javascript
{ src: 'YOUR_NEW_DOC_ZH.md', out: 'YOUR_NEW_DOC.pdf', title: '你的標題' },
```

#### 改樣式

編輯 `style.css`：
- 字型：改 `body { font-family: ... }`
- 主色：搜尋 `#2563eb`（藍色品牌色）
- 字級：改 `body { font-size: 10.5pt; }`

#### 改頁面大小

編輯 `build.mjs` 中 `pdf_options.format`：
- `'A4'`（預設）
- `'Letter'`（美規）
- `'A3'`（大張）

### ❓ 常見問題

**Q: 第一次跑很慢？**
A: 對。要下載 Chromium（~150 MB），之後就快了。

**Q: PDF 中文顯示成豆腐？**
A: 系統沒裝中文字型。Windows/Mac 預設都有，Linux 跑：
```bash
sudo apt-get install fonts-noto-cjk fonts-wqy-zenhei
```

**Q: 怎麼只轉某一份？**
A: 編輯 `build.mjs`，把不要的條目註解掉。

**Q: 可以加封面頁嗎？**
A: 可以。在每份 MD 第一行加 `# 標題`，建議再加一頁引用區塊作為摘要。

**Q: SVG 圖會嵌進 PDF 嗎？**
A: 會。`style.css` 有 `img, svg { max-width: 100%; }`，相對路徑 SVG 也會抓進去（基於 `docs/` 為 basedir）。

**Q: PDF 太大？**
A: 由 Chromium 產生，含字型嵌入，正常每份 0.3-2 MB。要壓縮可用 `gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/ebook -o out.pdf in.pdf`。

### 🛠️ 故障排除

| 錯誤 | 解法 |
|---|---|
| `npm install` 失敗 | 設定 npm registry：`npm config set registry https://registry.npmmirror.com/`（中國）或 `https://registry.npmjs.org/`（國際） |
| `Cannot find module 'md-to-pdf'` | 重跑 `npm install` |
| `Failed to launch browser` | Linux 需裝 Chromium 依賴：`sudo apt-get install libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2` |
| Windows 防毒擋 puppeteer | 把 `scripts/build-pdfs/node_modules/puppeteer/.local-chromium/` 加白名單 |
| PDF 空白 | 檢查 MD 是否有語法錯誤（破損的 markdown table） |

---

## English

### 🎯 Why PDF?

| Scenario | Why PDF | Why not MD |
|---|---|---|
| Email to client | Fixed layout | Client can't render markdown |
| Print manual | A4 pagination + page numbers | Plain text prints ugly |
| Official attachment | Formal format | .md not accepted |
| Boss on iPad | Native PDF viewer | Needs an app |
| LINE share | Inline preview | Unreadable |

### 📦 What gets built?

Run produces **12 PDFs** in `docs/pdf/`:

| # | Filename | Audience |
|---|---|---|
| 01 | Installation Guide (ZH + EN) | Owner/secretary |
| 02 | Quick Start (bilingual single) | All |
| 03 | User Manual (ZH + EN) | Sales/foreman/buyer |
| 04 | Mobile App Guide (bilingual single) | Mobile users |
| 05 | Network Deployment (ZH + EN) | IT/integrator |
| 06 | System Architecture & Topology (ZH + EN) | IT/architect |
| 07 | LLM Benchmark Report (ZH + EN) | Decision maker |

### 🚀 Quick Start

#### Prerequisites

Install **Node.js 18 or 20 LTS** from https://nodejs.org/

#### Run

**Windows**: double-click `build_pdfs.bat`
**Mac/Linux**:
```bash
chmod +x build_pdfs.sh
./build_pdfs.sh
```

**First run**: ~3-5 min (Puppeteer Chromium download)
**Later runs**: ~30s-1 min

### 🎨 Style features

- Light theme, A4 layout
- Auto-fallback Chinese fonts
- Syntax-highlighted code blocks
- Beautiful tables (zebra rows, blue headers)
- Header/footer with title + page numbers
- Mermaid diagrams rendered as vectors

### ❓ FAQ

**Q: First run is slow.**
A: Downloading Chromium (~150 MB). Subsequent runs are fast.

**Q: Chinese shows as boxes.**
A: System missing CJK font. On Linux:
```bash
sudo apt-get install fonts-noto-cjk
```

**Q: Build only one PDF?**
A: Edit `build.mjs`, comment out other entries.

**Q: PDF too large?**
A: ~0.3-2 MB each is normal. Compress with `gs -sDEVICE=pdfwrite -dPDFSETTINGS=/ebook`.

### 🛠️ Troubleshooting

| Error | Fix |
|---|---|
| `npm install` fails | Try a different registry |
| `Failed to launch browser` | Linux: install Chromium runtime deps |
| Blank PDF | Check MD for broken syntax |

---

**Maintainer**: LLM-ERP Project
**Last updated**: 2026-05-14
