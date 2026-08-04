# 安全政策 / Security Policy

## 支援版本 / Supported Versions

| 版本 | 支援 |
|---|---|
| v3.69+ | ✅ 主動維護（security fixes） |
| v3.55–v3.68 | 🟡 重大漏洞修復 |
| < v3.55 | ❌ 不支援 |

## 回報漏洞 / Reporting a Vulnerability

請**不要**在公開 issue 揭露安全漏洞。請 Email 到專案維護者
（GitHub repository 的 maintainer 資訊），並附上：

1. 影響的版本
2. 重現步驟（盡量最小化）
3. 影響評估（可讀取哪些資料 / 可做哪些操作）

我們會在 72 小時內回覆，並在修復後 30 天內發布 advisory。

## 內建安全機制 / Built-in Security

- **RBAC**：95+ → 231 個權限碼、8 張 RBAC 表、tool 級檢查（chat 與 API 共用）
- **多租戶隔離**：自動寫入注入 + 讀取過濾（`with_loader_criteria`），superuser 也不跨租戶
- **認證**：bcrypt、JWT token_version（改密碼即撤銷）、登入失敗鎖定、MFA（TOTP）
- **敏感資料**：外部連線字串 AES-256-GCM 加密儲存
- **上傳**：magic bytes 內容驗證 + 副檔名白名單 + 外部 AV 掛鉤
- **AI 防線**：prompt-injection 資料邊界、工具權限注入 system prompt、LLM 速率限制
- **治理**：audit log（mutation）、備份自動化 + 還原救援檔、權限審計腳本

## 部署建議 / Deployment Checklist

- 更換 `JWT_SECRET`（`openssl rand -hex 32`）並設定 `CONNECTION_ENCRYPTION_KEY`
- 正式環境使用 PostgreSQL（`DATABASE_DRIVER=postgresql`）
- 啟用 HTTPS / 設定 CORS 明確來源（禁用 `*`）
- 定期執行 `python -m scripts.audit_permission_codes` 驗證權限完整性
- 每日備份（預設 03:00，保留 30 天）
