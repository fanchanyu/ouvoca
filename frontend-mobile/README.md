# LLM-ERP Mobile App

> **AI-Native ERP for SMB Manufacturers — Mobile Edition**
> 中文 | [English](#english)

---

## 中文版

### 📱 這是什麼？

**LLM-ERP** 的原生手機 App（基於 Expo + React Native），補足桌機網頁版的「行動優先」承諾：

- 📊 老闆/廠長隨身儀表板（含 AI 智能摘要）
- 📦 庫存隨手查（業務站在客戶面前 3 秒答題）
- 📷 QR 掃碼盤點 / 報工
- 💬 AI 自然語言問答（手機原生對話介面）
- 👤 個人帳號管理

### 🎯 為何要有原生 App？

| 場景 | 響應式網頁 | 原生 App |
|---|---|---|
| 客戶面前查庫存 | 需要連網、開瀏覽器 | 一鍵開 App |
| QR 掃碼盤點 | 不支援 | ✅ 原生相機 |
| 推播通知 | ❌ | ✅ FCM/APNs |
| 離線快取 | 有限 | ✅ AsyncStorage |
| LINE 分享 | 一般 | ✅ 深層整合 |

### 🚀 快速開始

#### 1. 安裝 Node.js + Expo CLI

```bash
# 安裝 Node.js 20 LTS（先確認 node --version）
# Windows: https://nodejs.org/
# Mac: brew install node@20
# Linux: 用 nvm

# 安裝 Expo CLI（全域）
npm install -g expo-cli eas-cli
```

#### 2. 安裝專案依賴

```bash
cd frontend-mobile
npm install
```

#### 3. 設定後端 API 位址

編輯 `app.json` 中的 `extra.apiBaseUrl`：

```json
{
  "expo": {
    "extra": {
      "apiBaseUrl": "http://192.168.1.X:8000"
    }
  }
}
```

**重點**：
- 開發時不能用 `localhost`（手機看不到電腦的 localhost）
- 必須用**電腦在區網的 IP**
- 查 IP：Windows `ipconfig` / Mac `ifconfig | grep inet`
- 手機要連同一個 Wi-Fi

#### 4. 啟動開發伺服器

```bash
npm start
# 或
npx expo start
```

#### 5. 在手機上預覽

**選項 A：Expo Go App（最快、零設定）**

1. 從 App Store / Google Play 安裝 **Expo Go**
2. 用手機相機掃 terminal 顯示的 QR Code
3. App 自動開啟

**選項 B：iOS 模擬器（僅 Mac）**

```bash
npm run ios
```

**選項 C：Android 模擬器**

```bash
npm run android
```

### 🔧 設定後端讓手機看得到

預設後端只 listen `127.0.0.1`，手機需要連到您電腦的內網 IP，請改：

```bash
# 在後端執行
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

或在 `docker-compose.yml` 中已預設 `0.0.0.0`，可直接用：

```bash
docker compose up -d
```

並確認 Windows 防火牆允許 port 8000。

### 📦 打包 APK / IPA（正式發佈）

```bash
# 安裝 EAS CLI
npm install -g eas-cli
eas login

# 建立 Android APK（測試用）
eas build --platform android --profile preview

# 建立 Android AAB（Google Play）
eas build --platform android --profile production

# 建立 iOS IPA（需 Apple Developer 帳號 $99/年）
eas build --platform ios --profile production
```

詳見 [Expo EAS Build 文件](https://docs.expo.dev/build/introduction/)。

### 🗺️ 目錄結構

```
frontend-mobile/
├── app/                    # Expo Router 檔案式路由
│   ├── _layout.tsx        # 根 layout
│   ├── index.tsx          # 啟動路由（自動跳轉）
│   ├── login.tsx          # 登入頁
│   └── (tabs)/            # 底部 Tab 區
│       ├── _layout.tsx    # Tab 設定
│       ├── dashboard.tsx  # 儀表板（AI 摘要 + 統計卡）
│       ├── inventory.tsx  # 庫存（可搜尋列表）
│       ├── scan.tsx       # QR/條碼掃描
│       ├── chat.tsx       # AI 對話助手
│       └── me.tsx         # 個人/設定/登出
├── src/
│   ├── lib/api.ts         # 共用 API client
│   └── store/auth.ts      # Zustand+AsyncStorage 持久化
├── app.json               # Expo 設定
├── package.json
└── tsconfig.json
```

### 🎨 設計準則

| 原則 | 落地 |
|---|---|
| **行動優先** | 5 tab + 大按鈕、最少打字 |
| **3 步操作** | 任何功能 ≤ 3 tap 完成 |
| **離線降級** | AsyncStorage 快取 token + 基本資料 |
| **大字體** | 老闆/廠長戶外可讀 |
| **單手操作** | 重要按鈕在拇指自然範圍 |

### 🔐 安全注意

- ✅ Token 存於 AsyncStorage（不加密），生產建議改 SecureStore
- ✅ 401 自動 logout
- ❌ Demo 模式僅供測試，正式環境後端會關閉
- ❌ 不在前端儲存任何敏感商業資料

### 🛣️ Roadmap

- [x] Phase 1 骨架（Login + 5 tabs）✅ 完成
- [ ] Phase 1.5 推播通知（Expo Notifications + FCM）
- [ ] Phase 2 報工流程（拍照 + 簽名）
- [ ] Phase 2 離線同步（SQLite + 上傳佇列）
- [ ] Phase 3 語音輸入（expo-speech）

### ❓ 常見問題

**Q: 為何手機跑不起來？**
A: 99% 是 `apiBaseUrl` 設錯。檢查：①是否用了內網 IP（不是 localhost）②手機是否在同一個 Wi-Fi ③防火牆是否擋 8000。

**Q: Expo Go 顯示空白？**
A: 看 terminal log，多半是 typo。重啟：`npm start --clear`。

**Q: QR 掃描不能用？**
A: 需要授權相機權限，第一次會跳出系統提示，按「允許」。已拒絕的話到手機「設定 → Expo Go → 相機」開啟。

**Q: 上架 App Store / Google Play 要錢嗎？**
A: Google Play 開發者帳號 $25 一次性，Apple Developer $99/年。Expo EAS Build 本身免費額度夠用。

---

## English

### 📱 What is this?

**Native mobile app** for LLM-ERP, built with Expo + React Native, delivering on the "mobile-first" promise alongside the web app:

- 📊 Owner/foreman dashboard with AI summary
- 📦 Instant inventory lookup (3-second customer-facing answers)
- 📷 QR/barcode scan for stock-take or work-order reporting
- 💬 Natural language Q&A
- 👤 Personal account management

### 🎯 Why native?

| Scenario | Responsive web | Native |
|---|---|---|
| Inventory in front of customer | Browser required | One-tap |
| QR scan | Not supported | ✅ Native camera |
| Push notifications | ❌ | ✅ FCM/APNs |
| Offline cache | Limited | ✅ AsyncStorage |
| LINE share | Generic | ✅ Deep integration |

### 🚀 Quick Start

#### 1. Install Node.js + Expo CLI

```bash
# Install Node.js 20 LTS
# Windows: https://nodejs.org/
# Mac: brew install node@20

# Global tools
npm install -g expo-cli eas-cli
```

#### 2. Install dependencies

```bash
cd frontend-mobile
npm install
```

#### 3. Configure backend API URL

Edit `app.json`:

```json
{
  "expo": {
    "extra": {
      "apiBaseUrl": "http://192.168.1.X:8000"
    }
  }
}
```

**Important**:
- Do NOT use `localhost` (your phone can't see your computer's localhost)
- Use your computer's **LAN IP**
- Windows: `ipconfig` / Mac: `ifconfig | grep inet`
- Both devices must be on the same Wi-Fi

#### 4. Start dev server

```bash
npm start
```

#### 5. Preview on device

**Option A: Expo Go (easiest)**

1. Install **Expo Go** from App Store / Google Play
2. Scan the QR shown in the terminal
3. App loads automatically

**Option B: iOS Simulator (Mac only)**

```bash
npm run ios
```

**Option C: Android Emulator**

```bash
npm run android
```

### 🔧 Make backend reachable from phone

```bash
# Bind to all interfaces
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Or via docker compose (already 0.0.0.0)
docker compose up -d
```

Make sure Windows Firewall allows port 8000.

### 📦 Build APK / IPA (Production)

```bash
npm install -g eas-cli
eas login

# Android APK (testing)
eas build --platform android --profile preview

# Android AAB (Google Play)
eas build --platform android --profile production

# iOS IPA (requires Apple Developer $99/year)
eas build --platform ios --profile production
```

See [Expo EAS Build docs](https://docs.expo.dev/build/introduction/).

### 🗺️ Directory layout

```
frontend-mobile/
├── app/                    # Expo Router (file-based routing)
│   ├── _layout.tsx
│   ├── index.tsx          # Boot redirect
│   ├── login.tsx
│   └── (tabs)/
│       ├── _layout.tsx
│       ├── dashboard.tsx  # AI summary + stat cards
│       ├── inventory.tsx  # Searchable list
│       ├── scan.tsx       # QR / barcode
│       ├── chat.tsx       # AI assistant
│       └── me.tsx         # Profile / settings / logout
├── src/
│   ├── lib/api.ts
│   └── store/auth.ts      # Zustand + AsyncStorage
├── app.json
├── package.json
└── tsconfig.json
```

### 🎨 Design principles

| Principle | Concrete |
|---|---|
| **Mobile-first** | 5 tabs, big buttons, minimal typing |
| **3-tap rule** | Any function ≤ 3 taps |
| **Offline degrade** | Token + basic data cached |
| **Large fonts** | Readable outdoor |
| **One-hand reach** | Key actions in thumb zone |

### 🔐 Security notes

- ✅ Token in AsyncStorage (not encrypted); switch to SecureStore for production
- ✅ Auto-logout on 401
- ❌ Demo mode is dev-only; backend disables it when JWT_SECRET is set
- ❌ Do not cache sensitive business data on-device

### 🛣️ Roadmap

- [x] Phase 1 skeleton (Login + 5 tabs) ✅ Done
- [ ] Phase 1.5 Push notifications
- [ ] Phase 2 Work-order reporting (photo + signature)
- [ ] Phase 2 Offline sync (SQLite + upload queue)
- [ ] Phase 3 Voice input

### ❓ FAQ

**Q: App won't load on phone**
A: 99% chance `apiBaseUrl` is wrong. Check: ① LAN IP not localhost ② Same Wi-Fi ③ Firewall allows 8000.

**Q: Expo Go shows blank screen**
A: Check terminal log, usually a typo. Try `npm start --clear`.

**Q: QR scanner doesn't work**
A: Needs camera permission. Allow on first prompt, or go to Settings → Expo Go → Camera.

**Q: Does publishing cost money?**
A: Google Play: $25 one-time. Apple Developer: $99/year. Expo EAS Build free tier is enough for SMB use.

---

**License**: MIT
**Part of**: [LLM-ERP main repo](../README.md)
