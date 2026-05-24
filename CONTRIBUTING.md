# Contributing to Ouvoca

歡迎貢獻！這份文件幫你快速上手 + 走完 CLA 簽署流程。

> 🌐 **Bilingual notice**: Ouvoca uses 繁體中文 for in-project communication.
> Code comments and docs can be EN or ZH; user-facing strings should be ZH first.

---

## 1. 三步驟貢獻流程

### Step 1 · 開 Issue 討論（重要功能 / 改架構必做）

小修 bug / typo 可以直接送 PR，但**新功能或架構變動**請先開 issue 討論，
避免做完才發現方向不對。Ouvoca 對「加功能 vs 砍功能」的態度是 **砍**
（見 [`docs/ARCHITECTURE_DECISIONS.md`](./docs/ARCHITECTURE_DECISIONS.md)），
所以提案時請順便講「這對 Ouvoca 對話式 ERP 核心承諾有什麼貢獻」（自然語言操作 / ConfirmCard / 90秒 Undo）。

> 🚀 **可上線優先 (Deployability First) — v3.49 凍結原則**
>
> 任何 PR 必須通過「電腦小白裝得起來嗎？」測試：
> - ❌ 不能引入新的「先安裝 X」步驟（除非自動下載 + silent install）
> - ❌ 不能讓 `install_easy.bat` / `install_easy.sh` 失效
> - ❌ 不能讓「雙擊 .bat 就裝完」這個承諾破功
> - ✅ 如果你的功能必須加依賴，請同時更新 `install_easy.bat` 自動處理
>
> **理由**：100 個功能 × 0 客戶上線 = 0 價值。詳見 [README §設計優先順序](./README.md#-設計優先順序--design-priorities)。

### Step 2 · Fork + 開 branch + 寫程式

```bash
gh repo fork fanchanyu/ouvoca --clone
cd Ouvoca
git checkout -b feat/my-thing
# ...寫程式...
```

開發環境一鍵啟動見 [README §一鍵啟動開發環境](./README.md)。

### Step 3 · 跑自證閘 → commit -s → PR

```bash
# 7 道 gate 全綠才能 PR（CI 也會跑一次）
bash scripts/run_gates.sh

# 一定要加 -s（Signed-off-by → CLA 簽署）
git commit -s -m "feat: my thing"

git push origin feat/my-thing
gh pr create --fill
```

PR 模板會帶你貼 `run_gates.sh` 輸出 + 自我檢查清單。

---

## 2. CLA — 第一次貢獻必看

Ouvoca 採 **AGPL-3.0 + 商業授權** 雙軌制（dual-license）。為了讓商業授權
能成立，你貢獻的程式碼需要授權給維護者「可再以商業條款授權」的權利。

**完整條款**：[`CLA.md`](./CLA.md)（雙語）

**簽署方式**（兩個都要做）：

1. **每個 commit 加 `Signed-off-by:` trailer**（用 `git commit -s`）
   - email 要是你自己掌控的
   - CI 會擋掉沒簽的 commit
2. **第一次貢獻**：開一個 [CLA 確認 issue](https://github.com/fanchanyu/ouvoca/issues/new?template=cla-acknowledgement.yml)
   讓我們留紀錄

> ⚠️ 第一次 PR 沒簽？沒關係。CI 會貼留言提醒你 amend commit 重簽，
> 不需要重開 PR。

### 公司員工的情況

如果你在工作時間 / 用公司資源寫的 code，著作權通常**屬於公司**。
請先和公司確認你能不能依個人 CLA 提交，或者公司另簽 Corporate CLA
（見 [`CLA.md` §5(b)](./CLA.md#5-representations--你的聲明)）。

需要 Corporate CLA 模板請開 issue 標 `legal/cla`。

---

## 3. 程式碼風格

### Python（backend）

- Python 3.11（鎖定 >=3.11,<3.13，與 install_easy.bat / Dockerfile 一致）
- async-first（FastAPI / SQLAlchemy 2.0 async）
- 工具註冊用 `@register_tool` decorator + `RiskTier` enum
- 新 service 函式要有 type hint + docstring
- 不寫 `print()`；用 `logger`
- 範例：[`backend/app/services/inventory.py`](./backend/app/services/inventory.py)

### TypeScript（frontend-desktop）

- React 18 + Vite + Tailwind + Zustand
- 共用 component 優先（看 [`EntityRowActions.tsx`](./frontend-desktop/src/components/EntityRowActions.tsx)
  / [`EntityFormModal.tsx`](./frontend-desktop/src/components/EntityFormModal.tsx)）
- API 呼叫一律經 [`lib/api.ts`](./frontend-desktop/src/lib/api.ts)
- 使用者面 strings 用繁體中文

### Commit message

[Conventional Commits](https://www.conventionalcommits.org/) 風格：

```
feat: 新功能
fix: bug 修復
docs: 文件
refactor: 重構（不改行為）
test: 加測試
chore: 雜項（CI / build / deps）
```

技術名詞可保留英文；句子用繁體中文（見 git log 範例）。

---

## 4. 測試

```bash
cd backend
python -m pytest                       # 287 tests
python -m pytest tests/smoke/ -v       # 只跑 smoke
python -m pytest -k test_update_part   # 跑特定 test
```

新功能必加 test。修 bug 必加「**先重現 bug 的 test**」（red→green）。

---

## 5. 你 PR 會被檢查的事

CI（[`.github/workflows/ci.yml`](./.github/workflows/ci.yml)）會跑：

1. ✅ 7 道 self-verification gates
2. ✅ Pytest 全套
3. ✅ Frontend `tsc --noEmit`
4. ✅ CLA / DCO check（Signed-off-by trailer）
5. ✅ Pre-commit secret scan（sk- / ghp_ / xoxb- / JWT_SECRET）

PR 描述記得貼 `run_gates.sh` 輸出（PR 模板會提醒你）。

---

## 6. 重要連結

| 想了解 | 看哪裡 |
|---|---|
| 專案北極星 | [`docs/ARCHITECTURE_DECISIONS.md`](./docs/ARCHITECTURE_DECISIONS.md) + [`docs/CONVERSATIONAL_ERP_DESIGN_ZH.md`](./docs/CONVERSATIONAL_ERP_DESIGN_ZH.md) |
| 對話式 ERP 設計（必讀）| [`docs/CONVERSATIONAL_ERP_DESIGN_ZH.md`](./docs/CONVERSATIONAL_ERP_DESIGN_ZH.md) |
| 開發 SOP | [`docs/DEVELOPMENT_SOP.md`](./docs/DEVELOPMENT_SOP.md) |
| Gap 分析（找事做的好地方）| [`docs/GAP_ANALYSIS.md`](./docs/GAP_ANALYSIS.md) |
| 動態工作日誌 | (內部 AI 工作檔，不公開) — 對外請看 [`docs/ROADMAP.md`](./docs/ROADMAP.md) |
| 雙授權商業面 | [`LICENSE-COMMERCIAL.md`](./LICENSE-COMMERCIAL.md) |

---

謝謝你想貢獻 🙏 — 開 issue / PR 不用客氣，討論型 issue 都歡迎。
