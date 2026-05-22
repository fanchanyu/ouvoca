# Project Rename Notice — erpilot → Ouvoca

> **Effective Date**: 2026-05-22
> **Old Name**: erpilot
> **New Name**: Ouvoca
> **New Repository**: https://github.com/fanchanyu/ouvoca
>
> **中文版本**: [`RENAME_NOTICE_ZH.md`](./RENAME_NOTICE_ZH.md)

---

## To Past Readers, Contributors, and Prospective Customers

This project was originally published on GitHub under the name "**erpilot**". After due diligence, we have discovered that the name "**erpilot / ERPilot**" has been **previously registered or used by multiple organizations** in the ERP / SaaS / consulting service industry, including but not limited to:

- **ERPilot LLC** (USA) — business entity / trademark application records
- **ERPilot.in** (India) — ERP consulting service
- Other ERP / consulting service organizations with similar spelling (ER Pilot / e-RPilot etc.)

To **respect the rights of existing trademark holders** and avoid market confusion, trademark disputes, or legal entanglements, this project has been officially renamed to "**Ouvoca**" effective **2026-05-22**.

---

## Our Position and Commitments

1. ❌ We **do not assert** any trademark rights over the wording "erpilot / ERPilot"
2. ❌ We **do not imply** any commercial, technical, or legal affiliation with the aforementioned organizations
3. ✅ We acknowledge our **failure in thorough trademark search** of prior users, and hereby apologize
4. ✅ Before the rename, we verified the originality of "Ouvoca" through **4 channels**:
   - USPTO / TIPO trademark database search (no conflicts found)
   - Domain WHOIS lookup (ouvoca.com / ouvoca.ai both unregistered)
   - GitHub handle search (no user squatting)
   - Google / company database comprehensive search (no significant competing brand)

### 📌 Proactive Clarification on Similarly-Spelled Brands

| Similar Brand | Domain | Differentiation from Ouvoca |
|---|---|---|
| **Avoca AI** (avoca.ai, 2026) | NYC AI voice agent for trades (plumbers, electricians) | **Different domain** (voice booking system) + **different ICP** (blue-collar trades vs SMB manufacturing ERP) + **different initial letter** (A vs O) |
| **Ouva** (SF, healthcare AI) | Healthcare AI | Different domain + different spelling |
| **Ouvéa** (French Pacific island) | Geographic name | Not a commercial brand |

Ouvoca's **core positioning**: "**Conversational AI-Native ERP for SMB Manufacturers**" / "Desktop conversational ERP for 50-100 person factories" — **zero overlap** in domain or ICP with any of the above.

---

## Specific Impact on Existing Users

### 🧑‍💻 For Developers Who Previously Cloned / Starred / Forked

- **Repository URL changed**: `github.com/fanchanyu/erpilot` → `github.com/fanchanyu/ouvoca`
- **GitHub auto-redirect**: Old URL still works in the short term, but we **strongly recommend** updating your local git remote:
  ```bash
  git remote set-url origin https://github.com/fanchanyu/ouvoca.git
  ```
- **Issue / PR links**: GitHub automatically migrates existing IDs (recommend updating bookmarks)
- **Docker image tags**: Will change to `ouvoca/backend` / `ouvoca/frontend` in next release

### 📚 Regarding Existing Commit History

- Git history **retains** the "erpilot" string in commit messages / file contents from before 2026-05-22
  - **Reason**: Force-rewriting history (git filter-branch / BFG) would break all existing commit hashes, affecting any forks / clones / mirrors
  - **Policy**: Use the rename commit as the **dividing line in time**; all forward content is Ouvoca
- For clean history needs, you can squash / branch off after the rename commit

### 🏢 For Prospective Customers / Procurement Evaluators

- ✅ **PDF customer documents** (72 bilingual) have all been rebuilt with Ouvoca branding
- ✅ **API descriptions / UI strings / Tagline**: "**Ouvoca — Conversational AI-Native ERP for SMB Manufacturers**"
- ✅ **Legal documents**: CLA / LICENSE-COMMERCIAL / LICENSE-SMALL-BUSINESS all synchronized
- ✅ **Existing business contact channels**: Unchanged, still via GitHub Issue (label `legal/cla`)

### 🔧 For Existing Deployments

| Impact Item | Description |
|---|---|
| Docker container names | `erpilot-*` still works (backward compatible); new deployments should use `ouvoca-*` |
| Environment variables | All retain original names (no `ERPILOT_*` prefixed vars), zero migration cost |
| Database schema | Completely unchanged |
| API endpoint paths | Completely unchanged (no `/api/erpilot/*` paths) |
| Configuration file locations | Unchanged |

---

## ⚠️ Apology Statement

We **sincerely apologize** for the following inconveniences caused by this rename:

> 1. Any **name confusion concerns** caused for existing "**erpilot / ERPilot**" trademark holders
>    — Our oversight in not completing trademark due diligence at project inception.
>
> 2. **URL changes / bookmark invalidation / documentation updates** required of readers / contributors / customers
>    — We will maintain the rename notice prominently in README and complete all external reference update requests by end of 2026.
>
> 3. **Inability to notify** community references in blog posts / tutorial videos / third-party documentation in a timely manner
>    — We cannot individually notify all, but welcome citers to obtain this official statement via GitHub Issue
>    for use in correcting articles.

---

## Our Commitments

| Commitment | Action |
|---|---|
| Future naming | Any new branch / derivative product will undergo **prior multi-channel trademark search** (USPTO / TIPO / WIPO / domain / GitHub) |
| Transparency | If existing erpilot / ERPilot rights holders wish to communicate, please contact via GitHub Issue; **reply within 7 business days** |
| Legal compliance | Complete USPTO trademark application for Ouvoca in Q3 2026 (class 9 + 42) |
| Existing documents | All historical legal notices from v3.37-v3.43 (72 bilingual PDFs) have been fully rebuilt as Ouvoca versions |

---

## Public Apology to Existing ERPilot Rights Holders

If this notice is the first you've heard of this project — being "**ERPilot LLC**", "**ERPilot.in**", or another existing erpilot / ERPilot trademark / company name rights holder — we hereby **formally apologize**:

> We deeply regret that this project, prior to 2026-05-22, was publicly distributed on GitHub under the name "erpilot",
> which may have caused **brand confusion, market confusion, or goodwill impact** for your company.
>
> As of **2026-05-22**, this project has **completely ceased** using the name "erpilot" and completed
> project-wide renaming to "**Ouvoca**". If you believe there are still matters requiring negotiation
> or remediation (such as requesting git history cleanup, specific commit removal, or other remedial measures),
> please contact the maintainer directly via **GitHub Issue or the contact methods in this project's README**.
> We commit to **responding within 7 business days** and entering good-faith negotiation.

---

## Legal Statement

1. This notice does **not constitute** any waiver, assignment, or admission of trademark infringement
2. The project maintainer **acknowledges past use** of the wording "erpilot" and **immediately ceased** such use upon discovering the conflict, completing this rename
3. As of the rename effective date (2026-05-22), this project seeks trademark protection **under the name "Ouvoca"** under applicable law
4. To the maximum extent permitted by applicable law, the maintainer will negotiate any **third-party disputes** arising from "erpilot" name usage prior to 2026-05-22 in good faith, not actively assuming compensation obligations beyond legally mandatory liability

---

**Rename Effective Date**: 2026-05-22
**Corresponding Commit**: (rename commit hash — to be recorded in this commit's message)
**New Repository**: https://github.com/fanchanyu/ouvoca
**New Primary Brand**: Ouvoca
**New Tagline**: "**Ouvoca — Conversational AI-Native ERP for SMB Manufacturers**" / 「對話式 AI-Native ERP，給 50-100 人小型製造業」

**Maintainer**: Ouvoca Project Team
