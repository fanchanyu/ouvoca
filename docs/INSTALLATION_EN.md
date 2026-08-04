# Ouvoca Installation Guide

> Written for factory owners, plant staff, and whoever is doing the install.
> **繁體中文版**: [`INSTALLATION_ZH.md`](./INSTALLATION_ZH.md)
> Stuck mid-install? See [`INSTALL_TROUBLESHOOTING_EN.md`](./INSTALL_TROUBLESHOOTING_EN.md)

---

## 🚨 Read This First: Three Known Installer Defects

The installer scripts currently have three reproducible defects. **Every route below tells you the one
thing to do up front** to work around them. These are bugs in the scripts, not problems with your machine.

| # | Symptom | Affects | Do this first |
|---|---|---|---|
| 1 | Double-clicking `install_easy.bat` flashes a black window and closes; nothing is installed | Route A (Windows) | Fix one line → [steps](#a0-fix-one-line-first-required) |
| 2 | `install.bat` spins for 60 seconds at "Waiting for backend" and fails | Routes B, C | Create a `.env` by hand → [steps](#b1-create-two-env-files-by-hand-required) |
| 3 | You put `LLM_API_KEY` in `backend/.env` as documented, and the AI assistant still does nothing | Routes B, C | Use the in-app settings page, or the root `.env` → [details](#2-llm_api_key-for-the-ai-assistant) |

> 💡 **Want the fastest path?** Single machine, trying it out → **Route A**.
> Already have Docker, or need the War Room / multi-plant nodes → **Route B**.

---

## 🧭 Pick a Route

| | 🅰️ Easy Install | 🅱️ Docker One-Click | 🅲 Docker Manual |
|---|---|---|---|
| **Script** | `install_easy.bat` / `install_easy.sh` | `install.bat` / `install.sh` | `docker compose` commands |
| **For whom** | Non-technical users, single-machine trial | Someone assisting, multi-plant / War Room | IT / implementation engineers |
| **Prerequisites** | Windows: **none** (Win10 1803+)<br>Mac/Linux: Python 3.11/3.12 + Node 20–24 installed yourself | Docker Desktop | Docker Desktop / Docker Engine |
| **Downloads** | ~500 MB (Python, Node, packages) | Docker images (first build is slow) | Same |
| **Disk after install** | ~750 MB (all inside the project folder) | Depends on Docker | Depends on Docker |
| **Time** | 10–20 min (per the script's own banner) | ~2–5 min first build, plus wait | Same |
| **Services started** | backend 8000, frontend 5173 | backend 8000, frontend 5173, war-room 8080, factories 8001/8002 | Same (your choice) |
| **Where data lives** | `backend\erp.db` | Docker volume `backend-data` (`/app/data/erp.db` in container) | Same |
| **How to remove** | `uninstall_easy.bat` / `.sh` | `docker compose down -v` | Same |

> ⚠️ **Common misconception**: `install.bat` / `install.sh` are **not** "native Python/Node installers" —
> they are **Docker scripts** — `install.bat` Step 1 (lines 27–40) checks for Docker and aborts if it is absent.
> The Docker-free path is `install_easy.*`.
>
> ⚠️ The banners printed by those two scripts (`install.bat` line 17, `install.sh` line 42) still show the
> **product's pre-rename name**. You did not download the wrong build, and functionality is unaffected.
> See [`RENAME_NOTICE_EN.md`](./RENAME_NOTICE_EN.md).

---

# 🅰️ Route A — Easy Install (Zero Prerequisites)

Best for: one Windows PC at home or in the office, just trying the system out, no Docker.

## A0. Fix One Line First (required)

Lines 146–147 of `install_easy.bat` contain a cmd parsing error that aborts the entire batch file at Step 3.
Because there is no `pause` before it, double-clicking makes the window vanish instantly with no message —
no virtual environment, no packages, no database.

**The fix**: open `install_easy.bat` in **Notepad**, find the line starting with `for /f "delims=" %%k in`,
and delete **that line and the one below it** (2 lines total):

```bat
        for /f "delims=" %%k in ('""%PYEXE%" -c "import secrets; print(secrets.token_hex(32))""') do set "NEWJWT=%%k"
        "%PYEXE%" -c "import pathlib; p=pathlib.Path('backend/.env'); s=p.read_text(encoding='utf-8'); s=s.replace('change-me-in-production-please-use-openssl-rand-hex-32', '%NEWJWT%'); p.write_text(s, encoding='utf-8')"
```

Replace them with **this single line** (leading whitespace does not matter):

```bat
        "%PYEXE%" -c "import secrets,pathlib; p=pathlib.Path('backend/.env'); s=p.read_text(encoding='utf-8'); p.write_text(s.replace('change-me-in-production-please-use-openssl-rand-hex-32', secrets.token_hex(32)), encoding='utf-8')"
```

Save the file. This line generates a 64-character secret key and writes it into your configuration.

> Don't want to edit a file? Use **Route B** instead, or ask your vendor / IT to apply this one-line change.
> The Mac/Linux `install_easy.sh` does **not** have this defect and can be run as-is.

## A1. Run the Installer

### Windows

1. Extract the Ouvoca folder anywhere (e.g. `C:\ouvoca`); a path without spaces or non-ASCII characters is safest
2. Open that folder in File Explorer
3. **Double-click `install_easy.bat`**

**What you should see**: a console window stepping through five stages.

```text
============================================================
  Ouvoca AI ERP - Easy Installer
  About to download (~500 MB total)
============================================================

[Step 1/5] Python 3.11                       -> downloads + installs into tools\python (no admin rights)
[Step 2/5] Node.js 20                        -> downloads + extracts into tools\node
[Step 3/5] 後端套件 / Backend dependencies   -> creates backend\venv, runs pip (2-5 min)
[Step 4/5] 前端套件 / Frontend dependencies  -> runs npm install (3-8 min)
[Step 5/5] 資料庫初始化 / Database seeding   -> creates tables + admin account

  Installation complete!
  Login: admin / admin123

Launch now [Y,N]?
```

Press `Y` and the services start, opening http://localhost:5173 in your browser.

> The script downloads Python 3.11.9 (python.org) and Node.js 20.11.1 (nodejs.org) **directly from the
> vendors** to your machine — nothing is redistributed by this project.
> Licensing details: [`THIRD_PARTY_DOWNLOADS_EN.md`](./THIRD_PARTY_DOWNLOADS_EN.md)

<details>
<summary>⚠️ Two Windows caveats worth knowing</summary>

- **It does not detect an existing Python / Node.** The script only checks for `tools\python\python.exe`
  and `tools\node\node.exe`. Even if your system already has Python 3.11 or Node 20, it downloads its own
  copy into `tools\`.
- **A failed Step 5 only prints a WARN, yet the script still declares success.**
  If `[Step 5/5]` prints `WARN seed failed`, the admin account may not exist and `admin / admin123` will
  not log in. See [Verifying the Install](#-verifying-the-install).

</details>

### Mac / Linux

```bash
cd ~/ouvoca
bash install_easy.sh
```

`install_easy.sh` does **not** download Python or Node. It only *detects* them and, if missing, prints
install commands and exits.

| Requirement | Version | If missing |
|---|---|---|
| Python | 3.11 or 3.12 (`>=3.11,<3.13`) | macOS: `brew install python@3.11`<br>Ubuntu: `sudo apt install -y python3.11 python3.11-venv python3-pip` |
| Node.js | **20 – 24** | macOS: `brew install node@20`<br>Ubuntu: `curl -fsSL https://deb.nodesource.com/setup_20.x \| sudo -E bash - && sudo apt install -y nodejs` |

> ⚠️ **The script's Node check is too permissive.** `install_easy.sh` accepts Node ≥ 18 and prints OK,
> but `frontend-desktop/.npmrc` sets `engine-strict=true` while `package.json` requires `>=20.0.0 <25.0.0`.
> **Node 18, 19, or 25+ will therefore fail hard at `npm install`** with an `EBADENGINE` error — immediately
> after the script told you it was fine. Confirm `node --version` reports v20–v24 before running.

## A2. Daily Start / Stop

| Action | Windows | Mac / Linux |
|---|---|---|
| Start | double-click `start.bat` | `bash start.sh` |
| Stop | double-click `stop_dev.bat` | `bash stop.sh` |
| Backend errors | the console window titled `ouvoca-backend` | `logs-backend.txt` |
| Frontend errors | the console window titled `ouvoca-frontend` | `logs-frontend.txt` |

> ⚠️ `start.bat` tells you to use `stop_dev.bat` while `start.sh` tells you to use `stop.sh`. The asymmetry
> is expected — **there is no `stop.bat` on Windows**; use `stop_dev.bat`.
>
> ⚠️ `start.bat` / `start.sh` **force-kill whatever occupies ports 8000 and 5173 without asking first.**
> If you run other dev servers on those ports, shut them down yourself before starting.

---

# 🅱️ Route B — Docker One-Click

Best for: machines that already run Docker Desktop, or deployments that need the War Room dashboard and
the multi-plant MESH nodes.

## B0. Install Docker Desktop (one-time)

<details>
<summary>Windows / Mac / Linux steps</summary>

**Windows**
1. Go to https://www.docker.com/products/docker-desktop/ and click "Download for Windows"
2. Run the downloaded `.exe`, accept the defaults
3. **Reboot** after installation
4. Launch 🐳 Docker Desktop and wait for **Engine running** in the lower-left corner

**Mac**
1. Same URL, click "Download for Mac" (pick Intel or Apple Silicon)
2. Open the `.dmg` and drag Docker into Applications
3. Launch Docker via Spotlight; approve the permission prompt on first run

**Linux**
```bash
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl start docker
sudo usermod -aG docker $USER && newgrp docker
```

</details>

## B1. Create Two .env Files by Hand (required)

This is the landmine that Routes B and C **always** hit, with an error message that reveals nothing.
There are two compounding causes:

1. `install.bat` line 71 uses `[RandomNumberGenerator]::GetBytes(48)`, a static method that **does not exist**
   in Windows PowerShell 5.1 — the only PowerShell shipped with Windows
   (verified locally: `does not contain a method named 'GetBytes'`).
   The substitution still runs, so `JWT_SECRET=` ends up **empty**, and because the script's only check is
   "did the string `change-me` disappear", it happily reports "OK, JWT_SECRET auto-generated".
2. More fundamentally, `docker-compose.yml` **never reads `backend/.env`**. Compose resolves
   `${JWT_SECRET:-...}` from shell environment variables or from a `.env` file **in the same directory as
   `docker-compose.yml`** (the repository root). With no root `.env`, the container receives the literal
   `change-me-in-production-...`, and `backend/app/main.py` (lines 32–37) calls `SystemExit(1)` on a default
   JWT secret.

**Net effect**: `install.bat` stalls at `[Step 4/5] Waiting for backend`, times out after 60 seconds, and
prints "Backend timeout".

### The fix: create two files

**① Root `.env`** — read by docker compose, supplies the variables compose injects

Windows (Shift + right-click in the project folder → "Open PowerShell window here"):

```powershell
$b = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
$jwt = ($b | ForEach-Object { $_.ToString('x2') }) -join ''
Set-Content -Path .env -Value "JWT_SECRET=$jwt" -Encoding ascii
Get-Content .env
```

Mac / Linux:

```bash
echo "JWT_SECRET=$(openssl rand -hex 32)" > .env
cat .env
```

**What you should see**: `JWT_SECRET=` followed by exactly **64** hexadecimal characters. Any other length
means generation failed.

**② `backend/.env`** — baked into the image at build time; supplies everything compose does *not* pass
(most importantly `DEBUG`)

```powershell
copy backend\.env.example backend\.env
```
```bash
cp backend/.env.example backend/.env
```

> Why both? `docker-compose.yml` lines 22–34 hard-inject only these variables:
> `DATABASE_DRIVER`, `DATABASE_URL`, `DATABASE_URL_PROD`, `JWT_SECRET`, `LLM_PROVIDER`, `LLM_API_KEY`,
> `LLM_MODEL`, `LOG_LEVEL`, `ALLOW_DEMO_BYPASS`, `CORS_ORIGINS`.
> Everything else (`DEBUG`, `CONNECTION_ENCRYPTION_KEY`, `SEED_ADMIN_*`, …) comes from the `backend/.env`
> that `COPY . .` bakes into the image. Without it, `DEBUG` falls back to `false`, and production mode
> forbids SQLite — so the backend refuses to start for a *different* reason.

## B2. Run the Installer

**Windows**: double-click `install.bat`
**Mac / Linux**: `chmod +x install.sh && ./install.sh`

**What you should see**:

```text
[Step 1/5] Checking Docker...              -> OK Docker installed and running
[Step 2/5] Configuring environment...      -> .env exists, skipping (you created it in B1)
[Step 2.5] Checking port conflicts...      -> OK all ports available
[Step 3/5] Starting services (2-5 min)...  -> docker compose up -d --build
[Step 4/5] Waiting for backend...          -> OK Backend ready (12s)
[Step 4.5] Verifying dual endpoints...     -> OK both localhost and 127.0.0.1 reachable
[Step 5/5] Loading demo data...            -> OK Demo data loaded

               Installation Done
  Desktop UI:   http://localhost:5173
  War Room:     http://localhost:8080
  API Docs:     http://localhost:8000/docs
  Login: admin / admin123
```

The browser opens automatically when it finishes.

<details>
<summary>😱 Still stuck at "[Step 4/5] Waiting for backend"</summary>

The script only says "Backend timeout" and never shows the real cause. Pull the container logs yourself:

```bash
docker compose logs --tail=50 backend
```

| Log message | Meaning | Fix |
|---|---|---|
| `JWT_SECRET 是預設值或太短` (default or too short) | No root `.env`, or the value is under 32 chars | Redo [B1](#b1-create-two-env-files-by-hand-required) |
| `DATABASE_DRIVER=sqlite 不能用於 production` | `DEBUG` resolved to false | Ensure `backend/.env` exists (it contains `DEBUG=true`), then `docker compose up -d --build` |
| `DB 無法連線` (cannot connect) | Volume permission or path issue | `docker compose down -v`, then retry |

Inspect what the container actually received:
```bash
docker compose exec backend env | findstr JWT      # Windows
docker compose exec backend env | grep JWT         # Mac/Linux
```

</details>

<details>
<summary>⚠️ Two traps specific to install.sh (Mac/Linux)</summary>

- The wait loop has **no failure branch** after 60 attempts. Even when the backend never comes up, the script
  still prints "🎉 Installation Done". Judge success by "the browser opens http://localhost:5173 and you can
  log in", not by that banner.
- The script runs under `set -e`, so if `docker compose exec -T backend python -m scripts.seed` fails,
  the script **aborts silently** — the "Seed failed" message it was designed to print can never be reached.
  A sudden stop with no output is exactly this case.

</details>

## B3. Daily Operations

| Action | Command |
|---|---|
| Start | `docker compose up -d` |
| Stop | `docker compose down` |
| Restart backend | `docker compose restart backend` |
| Tail logs | `docker compose logs -f backend` |
| Apply changes to root `.env` | `docker compose up -d` (recreates containers) |
| Apply changes to `backend/.env` | `docker compose up -d --build` (**rebuild required** — it is baked into the image) |

> All services declare `restart: unless-stopped`, so the stack comes back up whenever Docker starts.
> For auto-start on login: Docker Desktop → Settings → General → check
> "Start Docker Desktop when you log in".

---

# 🅲 Route C — Docker Manual (for IT)

Use this when you want explicit control over which services run.

```bash
# 1. Both .env files (as in B1: root for compose interpolation, backend/ gets baked into the image)
cp backend/.env.example backend/.env
echo "JWT_SECRET=$(openssl rand -hex 32)" >> .env
# In a .env file the LAST definition of a key wins, so appending overrides the blank in .env.example
echo "CONNECTION_ENCRYPTION_KEY=$(openssl rand -hex 32)" >> backend/.env   # see section 3 below

# 2. Minimal stack (skip War Room and MESH factory nodes)
docker compose up -d --build backend frontend

# 3. Wait for health checks
docker compose ps

# 4. Initialise the database
#    (tables + 231 permission codes + 10 roles + 86-account CoA + 14 system settings + demo data)
docker compose exec -T backend python -m scripts.seed

# 5. Stamp the schema version (see section 4 below)
docker compose exec -T backend python -m alembic stamp head
```

Services and ports defined in `docker-compose.yml` (**all bound to 127.0.0.1 — deliberately not exposed
to the LAN**):

| Service | URL | Notes |
|---|---|---|
| `backend` | http://localhost:8000 | API; `/docs` is the interactive reference |
| `frontend` | http://localhost:5173 | Main UI (served by nginx) |
| `war-room` | http://localhost:8080 | Big-screen operations dashboard |
| `factory-a` | http://localhost:8001 | MESH plant node A |
| `factory-b` | http://localhost:8002 | MESH plant node B |

> To expose the system on a LAN or in production, switch to `docker-compose.prod.yml` and read
> [`NETWORK_DEPLOYMENT_EN.md`](./NETWORK_DEPLOYMENT_EN.md) first (CORS, reverse proxy, certificates).

---

# 🔑 Required Post-Install Configuration

## 1. Change the Default Password Immediately

| Username | Password |
|---|---|
| `admin` | `admin123` |

The login screen itself reminds you of this in an amber notice.

**How to change it**: after logging in, type in the **AI assistant chat**:
`改密碼 我的新密碼是 XXXXXX` ("change password, my new password is …"). A confirmation card appears — click
confirm. Saying "undo" within 90 seconds reverts it. Changing the password bumps the token version, so every
existing session is invalidated and other devices must sign in again.

> ⚠️ This flow runs through the AI assistant, so it requires `LLM_API_KEY` to be configured (next section).
> Until the password has been changed, do not expose the system to any untrusted network.

## 2. LLM_API_KEY (for the AI assistant)

The system works without a key — inventory, purchasing, sales, production and reporting are all unaffected.
Only the conversational "just say it" interface needs one.

### Easiest method: configure it in the UI (works on all three routes, no restart)

1. After logging in, click **⚙️ Settings** in the left-hand navigation (URL ends in `/settings`)
2. Find the **🤖 AI 助手設定 (AI Assistant)** section — these Settings section headings are currently
   rendered in Chinese regardless of the interface language
3. Choose a provider (DeepSeek / OpenAI / Anthropic / Ollama) and paste your API key
4. Click **Test** first; once it succeeds, click **Save**
5. The badge in the corner flips from "not configured" to "enabled (deepseek)"

This writes to `backend/.env` **and updates the running process in memory**, so no restart is needed.

### Where to get a key

| Provider | URL | Notes |
|---|---|---|
| **DeepSeek** (recommended) | https://platform.deepseek.com | Cheapest; strong Chinese-language performance |
| OpenAI | https://platform.openai.com/api-keys | Established, most stable, most expensive |
| Anthropic Claude | https://console.anthropic.com | Strong reasoning and writing |
| **Ollama** (local, zero cost) | https://ollama.com | No key, no data leaves your machine, needs a GPU |

📖 **Step-by-step signup walkthrough** (payment, quotas, cost estimates):
[`HOW_TO_GET_LLM_API_KEY_EN.md`](./HOW_TO_GET_LLM_API_KEY_EN.md)

### ⚠️ Docker users: important

`docker-compose.yml` line 28 reads `LLM_API_KEY: ${LLM_API_KEY:-}`. When that variable is undefined in the
root `.env`, compose injects an **empty string** into the container — and an empty string still counts as
"set", which **takes precedence over the `backend/.env` baked into the image**.

Therefore: **editing `backend/.env` and running `docker compose restart backend` has no effect** on the AI
assistant, and produces no error message either.

Correct approaches for Docker (pick one):
- Use the **UI settings page** above — effective immediately (but a container rebuild reinstates compose's
  empty value, so you would set it again).
- **Or** put the key in the **root** `.env` and run `docker compose up -d`:
  ```dotenv
  JWT_SECRET=<your 64-character secret>
  LLM_API_KEY=sk-xxxxxxxxxxxx
  LLM_PROVIDER=deepseek
  LLM_MODEL=deepseek-chat
  ```

Self-check:
```bash
docker compose exec backend env | grep LLM     # what the container actually received
curl http://localhost:8000/api/health          # look at the llm_provider field
```

## 3. CONNECTION_ENCRYPTION_KEY (only if you connect external databases)

Purpose: since v3.60 the system can connect to your legacy databases. Those connection strings — including
credentials — are stored **encrypted with AES-256-GCM**, and this is the key used to encrypt and decrypt them.

**No installer script generates it.** `backend/.env.example` line 52 leaves it blank. When blank, the key is
derived from `SHA-256(JWT_SECRET)` (`backend/app/core/crypto.py`, line 36).

| Your situation | What to do |
|---|---|
| No external database integration | Safe to ignore |
| You connect external databases | **Set a dedicated key** |

```bash
# Generate, then paste into CONNECTION_ENCRYPTION_KEY= in backend/.env
openssl rand -hex 32
```

> 🚨 **Critical warning**: [`SECRETS_ROTATION_SOP_EN.md`](./SECRETS_ROTATION_SOP_EN.md) requires rotating
> `JWT_SECRET` every 90 days. If you have **not** set a dedicated `CONNECTION_ENCRYPTION_KEY`, the encryption
> key is derived from `JWT_SECRET` — **the moment you rotate it, every stored external connection becomes
> permanently undecryptable**, with no warning. Either set a dedicated key now, or plan to re-enter every
> external connection after each rotation.

## 4. Stamp the Schema Version (`alembic stamp head`)

**No installer ever runs Alembic.** `scripts.seed` builds the schema through `init_db()` in
`backend/app/database.py`, which calls `Base.metadata.create_all`. As a result, the `alembic_version` table
never exists.

Consequence: when you later run `update.bat` / `update.sh`, `alembic upgrade head` assumes a brand-new
database and tries to replay migrations from the first revision. It fails — and the script discards the error
(`2>nul`), reporting only "WARN: upgrade failed or not needed". If a release adds a column to an existing
table, that change is silently skipped.

**Run this once after installation**:

```powershell
:: Route A (Windows) - from the project folder
cd backend
venv\Scripts\python.exe -m alembic stamp head
```
```bash
# Route A (Mac/Linux)
cd backend && venv/bin/python -m alembic stamp head

# Routes B / C (Docker)
docker compose exec -T backend python -m alembic stamp head
```

**What you should see**:

```text
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running stamp_revision  -> 016_fk_indexes
```

`016_fk_indexes` is the current head revision (`backend/alembic/versions/`, v001 → v016).

---

# 📦 Load Industry Sample Data (optional)

Five industry packs are bundled, each with representative parts, finished goods with BOMs, suppliers and
customers.

| Industry | Code |
|---|---|
| Metal machining (CNC fasteners) | `metal` |
| Plastic injection moulding | `plastic` |
| PCB electronics assembly | `pcb` |
| Food processing / bakery | `food` |
| Textile dyeing | `textile` |
| Load all five | `all` |

**The command differs by route**:

```powershell
:: Route A (Windows)
cd backend
venv\Scripts\python.exe -m scripts.seed_industries metal
```
```bash
# Route A (Mac/Linux)
cd backend && venv/bin/python -m scripts.seed_industries metal

# Routes B / C (Docker)
docker compose exec -T backend python -m scripts.seed_industries metal
#   or the bundled wrapper (Docker only):
./load_industry.sh metal
```

> ⚠️ `load_industry.sh` is a one-line wrapper around `docker compose exec -T backend ...`, so it works
> **only on the Docker routes**, and **there is no `.bat` equivalent**. On Route A, call
> `python -m scripts.seed_industries` directly as shown above.

> Separately, **Settings → 📦 示範資料 (Demo Data)** manages a *different* dataset: 5 customers / 3 suppliers / 10 parts,
> all prefixed `DEMO-`, with one-click load and one-click purge. The industry packs above are **not**
> `DEMO-` prefixed, so that purge button will not remove them.

---

# ⬆️ Upgrading

## Use `update.bat` / `update.sh` (recommended)

| Action | Windows | Mac / Linux |
|---|---|---|
| Upgrade | double-click `update.bat` | `bash update.sh` |

It performs six steps:

| Step | What it does |
|---|---|
| 1 | Stops whatever is listening on 8000 / 5173 |
| 2 | **Backs up** `backend\erp.db`, `backend\.env`, `backend\uploads\` into `backups\` |
| 3 | Pulls new code (`git pull` if a git checkout, otherwise downloads the GitHub zip and overlays it, skipping your data files) |
| 4 | `pip install -r requirements.txt` + `npm install` |
| 5 | `alembic upgrade head` **plus `python -m scripts.seed_permissions`** |
| 6 | Offers to restart the services |

### Why step 5's `seed_permissions` is not optional

Every new feature (RFQ, goods receipt, lot traceability, backup management, financial statements, …) ships
new **permission codes**. Those codes must be expanded onto the roles by `seed_permissions`. Skip it and
**every non-superuser gets 403 Forbidden on all new features** — which, from the shop floor, looks exactly
like the features are broken.

`seed_permissions` currently provisions **231 permission codes** (182 primary + 49 aliases) and
**10 system roles**.

<details>
<summary>⚠️ Three known defects in the update scripts</summary>

1. **`update.bat` names every backup folder `backups\_`.**
   It derives the timestamp from `wmic` (line 92), but **WMIC was removed from Windows starting with 11 24H2**
   (verified locally: `wmic` NOT FOUND). The timestamp comes back empty, so every upgrade writes into the same
   `backups\_` folder and **overwrites the previous backup**.
   👉 **Recommendation: copy `backend\erp.db` somewhere safe yourself before upgrading.**

2. **Alembic failures are invisible.**
   Line 222 is `alembic upgrade head 2>nul` — stderr is discarded and any failure degrades to
   "WARN: upgrade failed or not needed". To see the real error, run it manually (without `2>nul`):
   ```powershell
   cd backend
   venv\Scripts\python.exe -m alembic upgrade head
   ```

3. **Chart of accounts and system settings are not re-seeded.**
   Upgrades re-run `seed_permissions` only — **not** `seed_accounts` (the 86-account CoA) and not the system
   settings defaults. New accounts or settings added in a release will not appear on existing installs.
   Apply them manually when needed:
   ```powershell
   cd backend
   venv\Scripts\python.exe -m scripts.seed_accounts
   ```

</details>

## Upgrading with plain Docker commands

```bash
docker compose down
git pull                       # or overlay a freshly downloaded zip
docker compose up -d --build
docker compose exec -T backend python -m alembic upgrade head
docker compose exec -T backend python -m scripts.seed_permissions   # <- never skip this
```

> ⚠️ This path performs **no automatic backup**. Take one yourself first (next section).

---

# 💾 Backup and Restore

## Where your data lives

| Route | Database | Uploaded files |
|---|---|---|
| A (native) | `backend\erp.db` | `backend\uploads\` |
| B / C (Docker) | volume `backend-data` → `/app/data/erp.db` in container | `/app/uploads/` in container |

> 🚨 **Docker users, note**: only `/app/data` is backed by a volume.
> **Uploaded files (`/app/uploads`) and in-app backups (`/app/backups`) live inside the container and are
> lost on rebuild.** If you upload important documents, copy them out regularly with `docker compose cp`.

## Manual backup

```powershell
:: Route A (Windows) - stop the services first, then copy
copy backend\erp.db  D:\backups\erp-20260804.db
```
```bash
# Route A (Mac/Linux)
cp backend/erp.db ~/backup/erp-$(date +%Y%m%d).db

# Routes B / C (Docker)
docker compose cp backend:/app/data/erp.db ./erp-backup-20260804.db
docker compose cp backend:/app/uploads ./uploads-backup
```

## Built-in backup management (v3.62)

**Settings → 💾 備份管理 (Backup Management)** lets you create, list, restore and delete backups, and
configure a schedule.
Backup files are written to `backend/backups/backup-*.db`. Before any restore the system automatically saves
a `pre-restore-*.db` safety copy.

📖 Full strategy (3-2-1 rule, offsite, verification, disaster recovery):
[`BACKUP_RESTORE_SOP_EN.md`](./BACKUP_RESTORE_SOP_EN.md)

---

# 🗑 Reset and Uninstall

## Reset (wipe data and start over)

| Route | How |
|---|---|
| B / C (Docker) | Double-click `reset.bat` (Windows) or run `bash reset.sh`; type `YES` to confirm |
| A (native) | ⚠️ **Do not use `reset.bat` / `reset.sh`** |

> 🚨 **`reset.bat` / `reset.sh` only support Docker.** They run `docker compose down -v` and delete
> `backend\.seeded` and `backend\.env`.
> On Route A the effect is backwards: **your actual data in `backend\erp.db` is untouched, while
> `backend\.env` — which holds your JWT secret and API key — is deleted**, so the backend will refuse to
> start next time. (`reset.sh` also runs under `set -e`, so without Docker it aborts on line one and does
> nothing at all.)

Route A reset, done manually:

```powershell
:: 1) Back up first!
copy backend\erp.db D:\backups\erp-before-reset.db
:: 2) Delete the database and the seed marker
del backend\erp.db backend\erp.db-wal backend\erp.db-shm backend\.seeded
:: 3) Rebuild (leave .env alone)
cd backend
venv\Scripts\python.exe -m scripts.seed
```

## Full uninstall

| Route | How |
|---|---|
| A (Windows) | Double-click **`uninstall_easy.bat`** |
| A (Mac/Linux) | `bash uninstall_easy.sh` |
| B / C | `docker compose down -v`, then delete the folder |

`uninstall_easy.bat` does the following:

1. Stops whatever listens on 8000 / 5173
2. Removes `tools\python` **including its Windows registry entries** — nothing left behind in
   "Add or remove programs"
3. Deletes `tools\`, `backend\venv`, `frontend-desktop\node_modules`
4. **Asks** (twice, defaulting to no) whether to also delete `backend\erp.db`, `uploads\` and `.env`
5. **Asks** whether to purge the global npm / pip caches — decline if you have other Node/Python projects

Afterwards the whole folder can simply be deleted.

> The Mac/Linux `uninstall_easy.sh` deliberately **does not touch** your Python or Node — those are managed
> by brew/apt and belong to your system.

---

# ✅ Verifying the Install

Work down the list; anything that does not match has a fix below it.

| # | Check | Expected | If not |
|---|---|---|---|
| 1 | Open http://localhost:8000/api/health | JSON containing `"status":"ok"` and `"db":"ok"` | Backend is down → read the logs |
| 2 | Open http://localhost:5173 | Dark animated gradient background with a white login card | Frontend is down |
| 3 | Top-right of the login screen | 🇹🇼 繁中 / 🇺🇸 EN language toggle | — |
| 4 | With both fields empty | Amber hint box naming `admin` / `admin123` (this notice is hardcoded in Chinese: 「第一次安裝？…」) | — |
| 5 | Bottom of the login card | Green pulsing dot with the LLM provider name | May be hidden when no key is set |
| 6 | Sign in as `admin` / `admin123` | Main dashboard loads | **Cannot log in = seeding failed**, see below |
| 7 | Dashboard | 4 stat cards, AI summary, red stock alert (M6 bolt below safety stock — seeded on purpose) | — |

> ❗ **Not seeing a yellow "Demo Mode" button is correct.**
> That button only renders when `ALLOW_DEMO_BYPASS=true`, and all three sources (`.env.example`,
> `docker-compose.yml`, the application default) ship it as `false` — because it lets anyone obtain
> super-admin access with `Bearer demo`. **A correctly installed system does not show that button.**

**If check 6 fails (seeding did not complete)**:

```powershell
:: Route A (Windows)
cd backend
venv\Scripts\python.exe -m scripts.seed
```
```bash
# Route A (Mac/Linux)
cd backend && venv/bin/python -m scripts.seed

# Routes B / C (Docker)
docker compose exec -T backend python -m scripts.seed
```

**What success looks like** (these lines appear among a lot of SQL output, which is normal):

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

That single command covers everything: schema creation → **231 permission codes and 10 roles** →
the **86-account Taiwan chart of accounts** → **14 default system settings** → demo parts, products, BOMs,
suppliers, customers and work centres.

---

# ❓ FAQ

<details>
<summary><strong>Q1. What does it cost?</strong></summary>

| Item | Cost |
|---|---|
| The software itself | Free (open source; separate commercial terms apply) |
| Docker | Free for small businesses — check Docker's current licence terms |
| Running on your own machine | Electricity only |
| LLM API (optional) | Usage-based; DeepSeek runs roughly NT$300–1,000 / month |

Without an LLM API key the total is **NT$0** — you simply lose the conversational interface.

</details>

<details>
<summary><strong>Q2. Can I use it on a phone?</strong></summary>

**Not by default, and that is a deliberate security decision.**

- Docker route: `docker-compose.yml` binds every port to `127.0.0.1` (lines 21, 56, 74, 90, 108) and the
  file header states explicitly that nothing is exposed to the LAN.
- Native route: the Vite dev server has no `host` setting, so it listens on localhost only.

Making it reachable from a phone requires changing the port binding, `CORS_ORIGINS`, **and** the firewall
together. Follow [`NETWORK_DEPLOYMENT_EN.md`](./NETWORK_DEPLOYMENT_EN.md) rather than changing one of them.

</details>

<details>
<summary><strong>Q3. "Port 8000 already in use"</strong></summary>

`install.bat` / `install.sh` pre-check ports 8000, 5173, 8080, 8001 and 8002 and abort if any is taken.

Usual culprits: a previous instance that was not shut down (`docker compose down` first), another project's
dev server, or Skype.

To genuinely change a port, edit the matching line in `docker-compose.yml` — e.g. `"127.0.0.1:8000:8000"`
becomes `"127.0.0.1:8888:8000"` — then update `CORS_ORIGINS` and the frontend's API target to match.

</details>

<details>
<summary><strong>Q4. Which version am I on? Why does it say 2.0.0?</strong></summary>

The version comes from the `version` field of `/api/health` and is also printed under the login card.

The application default is **3.69.0** (`backend/app/config.py`), but `backend/.env.example` line 10 still
carries a stale `APP_VERSION=2.0.0`, and `.env` values outrank application defaults. So **any install copied
from `.env.example` reports 2.0.0**.

To report the real version, delete the `APP_VERSION=2.0.0` line from `backend/.env` (on Docker, rebuild with
`--build` afterwards).

</details>

<details>
<summary><strong>Q5. Moving to a new computer?</strong></summary>

1. Old machine: stop the services and back up `backend/erp.db`, `backend/.env`, `backend/uploads/`
2. New machine: install from scratch using any route in this guide
3. Stop the services again, then copy those three items over the fresh install
4. Start up

> Always carry `.env` across — it holds `JWT_SECRET`, and changing it forces everyone to sign in again.
> If you use external database connections without a dedicated `CONNECTION_ENCRYPTION_KEY`, a changed
> `JWT_SECRET` makes those stored connections undecryptable.

</details>

<details>
<summary><strong>Q6. Our corporate network blocks the downloads</strong></summary>

`install_easy.bat` needs `python.org`, `nodejs.org`, `pypi.org` and `registry.npmjs.org`. Ask IT to
allowlist those four domains.

⚠️ [`INSTALL_TROUBLESHOOTING_EN.md`](./INSTALL_TROUBLESHOOTING_EN.md) claims that installing Node yourself
makes the script detect it and skip the download. **That is currently false** — `install_easy.bat` only
checks whether `tools\node\node.exe` exists and never calls `where node`, so it downloads anyway.
A workaround that does work: download `node-v20.11.1-win-x64.zip` yourself, save it as
`tools\downloads\node.zip`, then run the script.

Also note the script's `curl` calls omit `-f`, so a corporate interception page gets saved as if it were the
installer and only explodes later, in a confusing way. After downloading, sanity-check that
`tools\downloads\python-installer.exe` is larger than 20 MB.

</details>

---

# 📚 Further Reading

| Topic | Document |
|---|---|
| Install failed — look it up by symptom | [`INSTALL_TROUBLESHOOTING_EN.md`](./INSTALL_TROUBLESHOOTING_EN.md) |
| Getting an LLM API key | [`HOW_TO_GET_LLM_API_KEY_EN.md`](./HOW_TO_GET_LLM_API_KEY_EN.md) |
| Day-to-day operation | [`USER_MANUAL_EN.md`](./USER_MANUAL_EN.md) |
| LAN exposure / production deployment | [`NETWORK_DEPLOYMENT_EN.md`](./NETWORK_DEPLOYMENT_EN.md) |
| Backup and disaster recovery | [`BACKUP_RESTORE_SOP_EN.md`](./BACKUP_RESTORE_SOP_EN.md) |
| Secret rotation | [`SECRETS_ROTATION_SOP_EN.md`](./SECRETS_ROTATION_SOP_EN.md) |
| Administration and advanced deployment | [`ADMIN_GUIDE.md`](./ADMIN_GUIDE.md) |
| Licences of the third-party software downloaded during install | [`THIRD_PARTY_DOWNLOADS_EN.md`](./THIRD_PARTY_DOWNLOADS_EN.md) |

**PDF manuals**: double-click `build_pdfs.bat` (Windows) or run `./build_pdfs.sh` (Mac/Linux) — Node.js
required. Output lands in `docs/pdf/`. See [`scripts/build-pdfs/README.md`](../scripts/build-pdfs/README.md).

---

# 📞 Getting Help

When reporting an installation problem, include:

1. Which route you used (A / B / C)
2. Your operating system and version
3. Which step it stopped at (a screenshot is ideal)
4. The backend error output
   - Route A: `logs-backend.txt`, or the contents of the `ouvoca-backend` console window
   - Routes B / C: `docker compose logs --tail=50 backend`
