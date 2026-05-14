# Installation Guide (Owner Version)

> **Done in 3 minutes, no IT background required**

---

## 📦 You Only Do 3 Things

```
   1️⃣ Install Docker      2️⃣ Run installer      3️⃣ Open browser
   ┌──────────┐           ┌──────────┐         ┌──────────┐
   │          │           │          │         │  http:// │
   │  🐳      │   →       │  install │   →    │ local:5173│
   │ Docker   │           │   .bat   │         │          │
   │          │           │          │         │  Login ✓ │
   └──────────┘           └──────────┘         └──────────┘
   Download/Install      Double-click          admin/admin123
```

**No typing, no configuration, no tech knowledge.**

---

## ⏱ Time Estimate

| Step | Time |
|---|---|
| Download/install Docker | 5-10 min (first time) |
| Run installer script | 3-5 min (automated) |
| Open browser & login | 30 seconds |
| **Total** | **~10 minutes** |

---

## 1️⃣ Install Docker (One-time)

Docker is like a "protective box" that contains LLM-ERP without affecting your other software.

### Windows Users

1. Visit https://www.docker.com/products/docker-desktop/
2. Click **"Download for Windows"**
3. Double-click the downloaded `.exe`
4. Click Next through the installer
5. **Restart your computer** after install
6. Desktop will show a 🐳 Docker Desktop icon — double-click to open
7. When Docker Desktop window shows **"Engine running"** = ✓ Done

### Mac Users

1. Visit https://www.docker.com/products/docker-desktop/
2. Click **"Download for Mac"** (choose Intel or Apple Silicon)
3. Double-click `.dmg`, drag Docker to Applications
4. Launch Docker (Spotlight search "Docker")
5. First run will ask permissions, click "Allow"

### Linux Users

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl start docker
sudo usermod -aG docker $USER && newgrp docker
```

> **💡 Why Docker?** It lets LLM-ERP run inside a "virtual protective box" on your computer without messing with your Windows / Mac.

---

## 2️⃣ Run One-Click Installer

### Windows

1. Extract the `opnetest` folder anywhere (e.g., `C:\LLM-ERP`)
2. Open the folder in File Explorer
3. **Double-click `install.bat`**
4. Window auto-runs:
   ```
   [Step 1/5] Checking Docker ✓
   [Step 2/5] Configuring environment ✓ (auto-generate JWT_SECRET)
   [Step 3/5] Starting services (first run 2-5min)...
   [Step 4/5] Waiting for backend ✓
   [Step 5/5] Loading demo data ✓
   ```
5. After done, **browser auto-opens** to http://localhost:5173

### Mac / Linux

```bash
cd LLM-ERP/opnetest
chmod +x install.sh
./install.sh
```

→ Same 5 steps, browser auto-opens.

---

## 3️⃣ Login

When the browser opens, you'll see a gradient blue login screen:

| Username | Password |
|---|---|
| `admin` | `admin123` |

Top-right 🌐 **switches between English / 繁體中文 anytime**.

First login shows immediately:
- ✅ 4 key metrics (Revenue / WOs / POs / Stock Alerts)
- ✅ AI Summary (one sentence telling you today's highlight)
- ✅ Red alert: "M6 Bolt below safety stock" (this is demo data)

---

## 4️⃣ Load Your Industry's Demo Data (Optional)

We prepared 5 typical industry samples:

| Your Industry | Command |
|---|---|
| Metal Machining (CNC bolts) | `./load_industry.sh metal` |
| Plastic Injection | `./load_industry.sh plastic` |
| PCB Electronics Assembly | `./load_industry.sh pcb` |
| Food Processing/Bakery | `./load_industry.sh food` |
| Textile Dyeing | `./load_industry.sh textile` |
| Load all | `./load_industry.sh all` |

Each industry includes:
- 8-12 typical parts (with EN/ZH names)
- 2-3 finished products + BOM
- 4-5 industry-standard suppliers
- 4-5 typical customers

**Windows users** run in cmd:
```cmd
docker compose exec backend python -m scripts.seed_industries metal
```

---

## 5️⃣ Set Up AI Assistant (Optional)

If you want the AI to actually answer questions (not just show "demo mode"), set an LLM API Key.

### Steps

1. Open `backend\.env` (Windows) or `backend/.env` (Mac/Linux) in any text editor
2. Find:
   ```
   LLM_PROVIDER=deepseek
   LLM_MODEL=deepseek-chat
   LLM_API_KEY=
   ```
3. Fill your key after `LLM_API_KEY=`
4. Save
5. Restart: `docker compose restart backend`

### Get an API Key (5 minutes)

| Recommended | URL | Notes |
|---|---|---|
| **DeepSeek** (cheapest) | https://platform.deepseek.com | Best for Chinese, $5 free credit |
| OpenAI | https://platform.openai.com/api-keys | Industry standard |
| Anthropic Claude | https://console.anthropic.com | Highest quality |
| **Ollama** (zero cost, local) | https://ollama.com | No API key, no data leak |

> **💡 Skip this entirely is OK!** All 11 other pages work fine. Only the AI chat shows a "demo mode" message.

---

## ❓ FAQ

### Q1: Can a non-technical person really install it?

**Yes.** The whole process:
1. Download Docker (just click Next)
2. Double-click one file
3. Browser opens, login

**No command typing required.**

### Q2: Cost?

| Item | Cost |
|---|---|
| LLM-ERP software | Free (open-source) |
| Docker | Free |
| Running on your computer | Free (just electricity) |
| LLM API (optional) | DeepSeek ~NT$ 300-1000/month |
| **Total (without LLM API)** | **NT$ 0** |
| **Total (with LLM API)** | **NT$ 300-1000/month** |

### Q3: Can I skip Docker?

You can but it's harder. Docker is the key to "install without tech knowledge".
If you're technical, see [`ADMIN_GUIDE.md`](./ADMIN_GUIDE.md) for native Python + Node setup.

### Q4: Can I view on mobile?

Yes! Open your phone browser to `http://YOUR-COMPUTER-IP:5173`:

- Find your computer's IP:
  - Windows: `ipconfig` → IPv4 Address
  - Mac/Linux: `ifconfig | grep inet`
- Then on phone browser: `http://192.168.1.X:5173` (replace with your IP)

**Mobile layout is optimized, fully responsive**.

> 📱 **Native Mobile App in Phase 1 roadmap** (Expo). Currently use responsive browser version.

### Q5: How do I stop / restart?

| Action | Command |
|---|---|
| Stop | `docker compose down` |
| Restart | `docker compose restart` |
| Full reset | `docker compose down -v && ./install.sh` |
| View logs | `docker compose logs -f backend` |

### Q6: How to upgrade?

```bash
git pull          # Get latest (or download new zip)
docker compose up -d --build
```

Your existing data is preserved.

### Q7: Installation failed, what to do?

**Case 1: "Docker not found"**
→ Docker not installed, back to Step 1️⃣

**Case 2: "Backend timeout"**
→ First build is slower, may take 5+ minutes. Be patient.
→ Detail: `docker compose logs backend`

**Case 3: "Port 8000 already in use"**
→ Another program uses the port. Edit `docker-compose.yml`, change `8000:8000` to `8888:8000`.

**Case 4: Other**
→ Screenshot `docker compose logs backend` and contact support.

---

## 🆘 Emergency

| Problem | Solution |
|---|---|
| Won't run at all | Contact LINE support |
| Want to fully remove | `docker compose down -v && rm -rf opnetest` |
| Move to new computer | Copy entire `opnetest` folder, run `install.sh` |
| Backup data | `docker compose exec backend cp /app/erp.db /tmp/backup.db` |

---

## ✅ Signs of Successful Install

Open http://localhost:5173, you should see:

1. ✅ Gradient blue login screen
2. ✅ Top-right 🌐 EN/ZH language toggle
3. ✅ Demo Mode entry (yellow button)
4. ✅ System version v2.0.0
5. ✅ Bottom green LLM provider indicator

After login:

1. ✅ AI Summary showing "⚠️ 1 item below safety stock" (demo)
2. ✅ 4 beautiful stat cards
3. ✅ WO progress bar animations
4. ✅ Red stock alert list

**See these → Congrats, system 100% running! 🎉**

---

## 📄 Want PDF Manuals?

We package **all customer-facing manuals** as polished PDFs (bilingual ZH+EN, A4-formatted, print/email ready):

| # | Content | Audience |
|---|---|---|
| 01 | Installation Guide (this doc) ZH + EN | Owner/secretary |
| 02 | Quick Start (single bilingual) | Everyone |
| 03 | User Manual ZH + EN | Sales/foreman/buyer |
| 04 | Mobile App Guide (single bilingual) | Mobile users |
| 05 | Network Deployment ZH + EN | IT/integrator |
| 06 | System Architecture & Topology ZH + EN | IT/architect |
| 07 | LLM Benchmark Report ZH + EN | Decision maker |

**Build it** (requires Node.js 18+):

- Windows: double-click `build_pdfs.bat`
- Mac/Linux: `./build_pdfs.sh`

**Output**: `docs/pdf/` (12 PDFs; first run ~3 min to download deps, later ~1 min)

See: [`scripts/build-pdfs/README.md`](../scripts/build-pdfs/README.md)

---

## 📞 Need Help?

| Need | Contact |
|---|---|
| Technical issues | Internal IT / Our support |
| Training | Monthly online sessions |
| Customization | Quote on request |

**Chinese version**: [`INSTALLATION_ZH.md`](./INSTALLATION_ZH.md)
