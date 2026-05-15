<!--
🛡️  IMPORTANT: 在送出 PR 前，請先在本機跑 `bash scripts/run_gates.sh`
    看到 🟢 ALL GATES PASSED 才送出。CI 也會跑同一支腳本，不過會晚 1-2 分鐘。
    Before submitting, run `bash scripts/run_gates.sh` locally. Only submit
    when you see 🟢 ALL GATES PASSED. CI will run the same script 1-2 min later.
-->

## 📋 Summary / 摘要

<!-- 1-3 句話：本 PR 改了什麼、為什麼。
     1-3 sentences: what this PR changes and why. -->



## 🎯 Type / 類型

<!-- 勾選一個或多個 / Tick one or more -->
- [ ] ✨ Feature 新功能
- [ ] 🐛 Bugfix 修錯
- [ ] ♻️ Refactor 重構（不改行為 / no behavior change）
- [ ] ⚡ Performance 效能
- [ ] 🛡️ Security 安全
- [ ] 📝 Docs 文件
- [ ] 🧪 Test 測試
- [ ] 🏗️ Infra / CI
- [ ] 💥 Breaking change（含 schema migration）

## 🔗 Related / 相關

<!-- 關聯的 issue / discussion / WORKLOG 條目 -->
- Issue: #
- WORKLOG: `docs/WORKLOG.md` § 會話 # __
- Related PRs: #

## 🛡️ Self-Verification Gates / 自證閘

<!-- 必填。在本機跑 `bash scripts/run_gates.sh`，把結果貼過來。
     Required. Run `bash scripts/run_gates.sh` and paste the output. -->

```text
<在這裡貼 run_gates.sh 的最後 12 行輸出 / paste last 12 lines of run_gates output>
```

- [ ] Gate 1 編譯閘：pytest smoke + import + desktop tsc 全綠
- [ ] Gate 2 行為閘：persona「王董一天」+ MESH 整合測試全綠
- [ ] Gate 3 文件閘：PDF builder 跑通、31 份 PDF 全產出

## 🧪 New Tests / 新增測試

<!-- 如果是 feature/bugfix，必須附上新測試證明 -->
- 新增測試檔：`tests/__/test_xxx.py` （N 個 case）
- 涵蓋了：__
- 跑出結果：`X passed, 0 failed in Ys`

## 📸 Evidence / 證據

<!-- 截圖、curl 輸出、log 片段、效能數字 — 任何可重現的證據 -->



## 🚨 Breaking Changes / 破壞性變更

<!-- 若無，寫「無 / None」 -->



## 📦 Migration Required / 是否需要 migration

- [ ] 否 / No
- [ ] 是 / Yes — Alembic revision: `__`
  - Migration name: __
  - Dry-run 跑過：[ ]
  - Rollback 測過：[ ]

## ⚠️ Risk / 風險

<!-- 這個 PR 上線後最可能出包的點是什麼？預備怎麼觀察? -->



## ✅ Reviewer Checklist / 審查者檢核（reviewer 勾）

- [ ] 程式碼可讀、命名清楚
- [ ] 沒有 hardcoded secret / API key
- [ ] 錯誤處理一致（不要吃掉 exception）
- [ ] log 結構化（不是 `print`）
- [ ] 如有新 endpoint：有 RBAC 保護、有 OpenAPI doc
- [ ] 如有新 ORM 關聯：service 有 `selectinload` 預載（避免 async lazy-load 500）
- [ ] 文件同步更新（README / CLAUDE.md / WORKLOG.md）
- [ ] **CI 全綠才合併**

---

<!-- 提交後請耐心等 CI 跑完。任何 reviewer 看到本框消失 = 你忘了填了。 -->
