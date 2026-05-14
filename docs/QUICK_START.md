# Quick Start 快速入門

> **5 分鐘從零到看到儀表板** · From zero to dashboard in 5 minutes

---

## 🇹🇼 繁體中文

### 第 1 步：Docker 一鍵啟動

```bash
cd opnetest
cp backend/.env.example backend/.env
docker compose up -d --build
```

等 1-2 分鐘讓所有服務啟動。

### 第 2 步：載入示範資料

選擇您熟悉的行業：

```bash
# 通用示範（10 個零件 + 2 個產品）
docker compose exec backend python -m scripts.seed

# 或載入特定行業：
docker compose exec backend python -m scripts.seed_industries metal     # 金屬加工
docker compose exec backend python -m scripts.seed_industries plastic   # 塑膠射出
docker compose exec backend python -m scripts.seed_industries pcb       # PCB 電子
docker compose exec backend python -m scripts.seed_industries food      # 食品加工
docker compose exec backend python -m scripts.seed_industries textile   # 紡織印染
```

### 第 3 步：開瀏覽器

| 服務 | URL | 說明 |
|---|---|---|
| 桌面 UI | http://localhost:5173 | 主應用 |
| War Room | http://localhost:8080 | 即時看板 |
| API 文件 | http://localhost:8000/docs | OpenAPI / Swagger |
| 健康檢查 | http://localhost:8000/api/health | JSON |

### 第 4 步：登入

| 方式 | 帳密 |
|---|---|
| 正式登入 | `admin` / `admin123` |
| Demo 模式 | 點「以 Demo 模式進入」按鈕 |

### 完成！

進入後您會看到：
- 🌐 右上角可切換中英文
- 📊 儀表板顯示 AI 摘要 + 4 個關鍵數字
- ⚠️ 第一個零件已故意設定為低於安全庫存（紅色警示）

---

## 🇺🇸 English

### Step 1: Docker One-Command Start

```bash
cd opnetest
cp backend/.env.example backend/.env
docker compose up -d --build
```

Wait 1-2 minutes for all services to come up.

### Step 2: Load Demo Data

Pick your industry:

```bash
# Generic demo (10 parts + 2 products)
docker compose exec backend python -m scripts.seed

# Or industry-specific:
docker compose exec backend python -m scripts.seed_industries metal     # Metal Machining
docker compose exec backend python -m scripts.seed_industries plastic   # Plastic Injection
docker compose exec backend python -m scripts.seed_industries pcb       # PCB Assembly
docker compose exec backend python -m scripts.seed_industries food      # Food Processing
docker compose exec backend python -m scripts.seed_industries textile   # Textile Dyeing
```

### Step 3: Open Browser

| Service | URL | Notes |
|---|---|---|
| Desktop UI | http://localhost:5173 | Main app |
| War Room | http://localhost:8080 | Real-time dashboard |
| API Docs | http://localhost:8000/docs | OpenAPI / Swagger |
| Health | http://localhost:8000/api/health | JSON |

### Step 4: Login

| Method | Credentials |
|---|---|
| Regular login | `admin` / `admin123` |
| Demo mode | Click "Continue as Demo" |

### Done!

You'll see:
- 🌐 Top-right: switch ZH/EN
- 📊 Dashboard with AI summary + 4 KPI cards
- ⚠️ First part intentionally below safety stock (red alert)

---

## 🔧 Setting LLM API Key (Optional)

For the AI Assistant to actually answer questions, set one of:

```bash
# Edit backend/.env

# Option A: DeepSeek (cheap, Chinese-friendly)
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.deepseek.com/v1

# Option B: OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-...

# Option C: Anthropic (Claude)
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-latest
LLM_API_KEY=sk-ant-...

# Option D: Ollama (local, free, no key needed)
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://localhost:11434
```

Then restart backend:
```bash
docker compose restart backend
```

Without an API key, the system still runs — only the AI chat shows a friendly fallback message.

---

## 📚 Next Steps · 下一步

- **詳細操作手冊** [USER_MANUAL_ZH.md](./USER_MANUAL_ZH.md) / [USER_MANUAL_EN.md](./USER_MANUAL_EN.md)
- **管理員指南** [ADMIN_GUIDE.md](./ADMIN_GUIDE.md)
- **API 參考** [API_REFERENCE.md](./API_REFERENCE.md)
- **架構圖** [ARCHITECTURE_DIAGRAM.md](./ARCHITECTURE_DIAGRAM.md)
- **部署到生產** [DEPLOYMENT.md](./DEPLOYMENT.md)

---

## ❓ 沒成功 / Not Working?

| 問題 Issue | 解決 Fix |
|---|---|
| Port 5173 / 8000 已被佔用 / In use | Stop the conflicting service or change ports in `docker-compose.yml` |
| Docker 跑不動 / Docker fails | Run `docker compose logs backend` to see errors |
| 沒有 Docker / No Docker | Local dev: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload` |
| 中文亂碼 / Chinese garbled | Browser font must support CJK (Chrome/Edge are fine) |

[完整疑難排解](./USER_MANUAL_ZH.md#9-疑難排解) · [Full Troubleshooting](./USER_MANUAL_EN.md#9-troubleshooting)
