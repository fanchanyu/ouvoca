# How to Get an LLM API Key and Use It with Ouvoca (Complete Guide)

> Applies to Ouvoca v3.14+
> Target audience: non-technical users
> Estimated time: 5–10 minutes

---

## 1. Why Do I Need an API Key?

Ouvoca's "AI Conversational CRUD" feature (query/add/edit/delete by talking) is powered by a **Large Language Model (LLM)**. LLMs run in the cloud — to call one, you must first **sign up for an account and apply for an API Key** (like a key).

### What If I Don't Have an API Key?

Ouvoca is **designed to work without one**:

| Feature | API Key Required? |
|---|---|
| Login / account management | ❌ No |
| Inventory / Purchase / Sales / Production (mouse-click ops) | ❌ No |
| File upload / report download | ❌ No |
| Load demo data | ❌ No |
| War-room real-time dashboard | ❌ No |
| **AI Assistant chat (CRUD)** | ✅ **Yes** |

In other words: **You can use Ouvoca as a traditional ERP without applying**, but you lose the "talk to it" headline feature.

---

## 2. 3 LLM Providers Compared (Pick One)

| Provider | Price | Free Tier | Chinese Quality | Recommended For |
|---|---|---|---|---|
| 🇨🇳 **DeepSeek (recommended)** | $0.14 / 1M input tokens (dirt cheap) | Small credit on signup | ⭐⭐⭐⭐⭐ | **Most users**: best value |
| 🇺🇸 **OpenAI (GPT-4o-mini)** | $0.15 / 1M | $5 trial (90 days) | ⭐⭐⭐⭐ | Already have OpenAI account |
| 🇺🇸 **Anthropic Claude** | $0.25 / 1M (haiku) | $5 on signup | ⭐⭐⭐⭐⭐ | Better reasoning, long-form |
| 🏠 **Ollama (offline)** | $0 (runs locally) | Unlimited | ⭐⭐⭐ | Have GPU + want fully offline |

### Our Recommendation → DeepSeek

Reasons:
1. **100× cheaper** than OpenAI
2. Best Chinese understanding (especially Traditional Chinese)
3. OpenAI-compatible API format — easy to switch providers later
4. A typical small factory's monthly bill is **NT$10–100** (essentially free)

If you're worried about a Chinese company storing your data → pick OpenAI or Claude (data stays in the US).

---

## 3. Apply for a DeepSeek API Key (Recommended, 5 min)

### Step 1️⃣ · Sign Up

1. Open https://platform.deepseek.com/sign_up
2. Register with **email** or **phone number** (Gmail works best)
3. Verify email, set password, land on home page

### Step 2️⃣ · Get API Key

1. After login, click **"API Keys"** in left sidebar
2. Click blue **"Create new API Key"** button (top right)
3. Name the key (e.g., `ouvoca-2026`), click Create
4. **Copy the `sk-xxxxxxxxxxxxxxxxxxxxxxxx` shown immediately** (shown only once!)

> ⚠️ Forgot to copy → delete and create a new one. **Don't try to find it in the page.**

### Step 3️⃣ · Top Up (Optional)

The free signup credit is limited (about NT$15 / ~200 chats).

To continue using:
1. Click **"Top Up"** in left sidebar
2. Minimum top-up is USD$2 (~300 chats)
3. Credit card / PayPal / Alipay / WeChat Pay all accepted

> 💡 **Saving tip**: NT$30/month is plenty for a small factory's ERP chat volume. **Try the free tier first** to see how quickly you burn through it.

---

## 4. Give the Key to Ouvoca (3 Methods)

### Method A: Settings Page (recommended, easiest)

1. Login to Ouvoca (http://localhost:5173)
2. Click **"⚙️ Settings"** in left sidebar
3. In the top "🤖 AI Assistant Settings" section:
   - **Provider** → pick "DeepSeek" from dropdown
   - **API Key** field → paste your `sk-xxxxx...`
   - Click **"🧪 Test Connection (no save)"** → see "✅ DeepSeek connection successful"
   - Click **"💾 Save (effective immediately)"**
4. Done! No restart, no re-login. Go to AI Assistant page and start talking.

#### Screenshot Mockup (ASCII art)

```
┌────────────────────────────────────────────┐
│  🤖 AI Assistant Settings    ⚠️ Not Set Up  │
│  Apply for LLM API Key to enable...        │
│                                            │
│  Provider:  [DeepSeek (recommended)   ▼]   │
│             No account? Sign up → (5 min)  │
│                                            │
│  API Key:   [sk-•••••••••••••••••] [👁]   │
│             Effective immediately, no restart│
│                                            │
│  ☑ Verify SSL certificate                  │
│             (Disable for Windows + DeepSeek)│
│                                            │
│  [🧪 Test (no save)]  [💾 Save (live)]    │
└────────────────────────────────────────────┘
```

### Method B: Edit backend/.env (for developers)

```bash
# Open with Notepad / VS Code:
backend/.env

# Edit these 3 lines:
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-paste-your-key-here
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

Save, then:
- **Docker mode**: `docker compose restart backend`
- **Dev mode**: run `stop_dev.bat` → `start_dev.bat`

### Method C: Environment Variables (advanced / production)

```bash
# Linux / Mac
export LLM_API_KEY="sk-your-key"
docker compose up -d

# Windows PowerShell
$env:LLM_API_KEY = "sk-your-key"
```

---

## 5. Windows + DeepSeek Common Issue: SSL Certificate Error

### Symptom

Click "Test Connection" and see:
```
❌ Connection failed: SSLCertVerificationError
```

### Cause

Windows' CA cert store hasn't updated with DeepSeek's root certificate. Common issue with Windows + DeepSeek combo — not an Ouvoca bug.

### Fix (fastest)

In Ouvoca Settings, **uncheck "Verify SSL certificate"** → retry test.
This just makes Python skip SSL verification — doesn't affect your security (key is still sent over TLS-encrypted connection).

Cleaner fix: upgrade Python `certifi` package — not necessary for non-developers.

---

## 6. Other Provider Steps

### OpenAI (GPT-4o-mini)

1. Sign up: https://platform.openai.com/signup (credit card required)
2. Get Key: left **API Keys** → **Create new secret key** (shown once)
3. In Ouvoca Settings: pick OpenAI, paste key, save

### Anthropic Claude

1. Sign up: https://console.anthropic.com/
2. Go to **Workbench → Settings → API Keys → Create Key**
3. In Ouvoca Settings: pick Anthropic, paste key, save

### Ollama (local offline)

1. Download: https://ollama.com/download → install
2. Terminal: `ollama pull llama3.2` (~2GB model)
3. In Ouvoca Settings: pick Ollama, leave key empty, save
4. Confirm `ollama serve` is running locally

---

## 7. Security Reminders

### ✅ Things You Should Do

- **API Key = password**; leaks let others use your quota
- Don't paste keys into chat / Slack / GitHub commits
- Rotate keys regularly (every 3-6 months)
- If you suspect a leak → revoke at provider + create new

### ✅ How Ouvoca Handles Your Key

- Stored in `backend/.env` on your local machine (plaintext file)
- **Never** uploaded to any server
- **Never** git-committed (`.gitignore` excludes `.env`)
- Pre-commit hook auto-scans `sk-` patterns and blocks accidents

### ✅ Where Conversation Data Goes

When you chat with the AI Assistant:
- Your **typed text** is sent to the LLM provider (DeepSeek/OpenAI/Anthropic)
- **Business DB data is not sent** (unless the AI calls a tool that queries DB and includes results in subsequent context)
- Provider retention policies differ — check their privacy terms

To keep data fully on-premise → **use Ollama offline mode** (Method D).

---

## 8. Cost Estimates (Small Factory Reality)

| Scenario | Usage | DeepSeek/mo | OpenAI/mo |
|---|---|---|---|
| Boss asks 5× daily | 150/month | NT$3 | NT$45 |
| Sales rep uses 10× daily | 1500/month | NT$30 | NT$450 |
| Whole 20-person company heavy use | 20000/month | NT$400 | NT$6,000 |

> 💡 **Ouvoca is token-efficient**: each chat usually < 2000 tokens.

---

## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| "Connection refused" | Check network / proxy settings |
| "Invalid API key" | Re-confirm key has no missing chars / extra spaces |
| "Rate limit" | Too many requests, wait minutes or upgrade plan |
| "Insufficient balance" | DeepSeek balance empty, go Top Up |
| "Model not found" | Provider changed model name; update in Settings |
| Windows SSL error | Uncheck "Verify SSL certificate" |
| Settings won't save | Confirm you're admin (need `system.config.update`) |
| Key change has no effect | Save is instant; if not, hard refresh (Ctrl+F5) |

---

## 10. Related Documentation

- [USER_MANUAL_EN.md](./USER_MANUAL_EN.md) — Full user manual
- [PRODUCT_OVERVIEW_EN.md](./PRODUCT_OVERVIEW_EN.md) — Product overview for buyers
- [INSTALLATION_EN.md](./INSTALLATION_EN.md) — Installation guide
- [LICENSE-SMALL-BUSINESS.md](../LICENSE-SMALL-BUSINESS.md) — Free tier (≤20 users)

Chinese version: [HOW_TO_GET_LLM_API_KEY_ZH.md](./HOW_TO_GET_LLM_API_KEY_ZH.md)
