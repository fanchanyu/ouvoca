# Contributor License Agreement (CLA) — Ouvoca

> **中文 / English bilingual** — both versions are equally authoritative.
> Last updated: 2026-05-16

## Why this CLA exists / 為什麼需要這份 CLA

Ouvoca is released under **AGPL-3.0** for the open-source community.

To keep the project sustainable, the maintainer (currently fanchanyu) also
offers **commercial licenses** to organizations that cannot comply with
AGPL-3.0 (e.g. they need to embed Ouvoca in closed-source products, or
run a SaaS without disclosing their modifications).

For this dual-license model to work, the maintainer needs the right to
**relicense your contribution under terms other than AGPL-3.0**. Without
that right, even one external contribution would block the entire
commercial-licensing track.

This CLA grants exactly — and only — the permissions needed for that.
You keep your copyright. You can still use your own contribution however
you like (including in projects with incompatible licenses).

Ouvoca 採 **AGPL-3.0** 對社群開放。為了讓專案能長期維護，維護者另外提供
**商業授權**給無法遵守 AGPL-3.0 的客戶（例：要把 Ouvoca 嵌入閉源產品、
或不想公開 SaaS 修改的客戶）。

這份 CLA 給維護者一項權利：**把你的 contribution 用 AGPL-3.0 以外的條款再
授權出去**。沒有這項權利，只要有一個外部 PR 進主線，整條商業授權軌就會破口。

你**保留著作權**。你自己仍可用任何方式運用你的 contribution（包含放進其他
和 AGPL-3.0 不相容的專案）。

---

## The Agreement / 協議內容

By submitting a Contribution to this project (whether via Pull Request,
patch, issue attachment, or any other channel), You ("Contributor") agree
to the following with the Project Maintainer ("Maintainer"):

當你（「貢獻者」）以任何方式（PR / patch / issue 附件 / 其他）向本專案提交
貢獻時，即同意以下條款（對方是「專案維護者」）：

### 1. Definitions / 定義

- **"Contribution"** means any original work of authorship — including
  source code, documentation, test cases, configurations, and assets —
  that You intentionally submit to the project.
- **"Submit"** means any form of electronic communication intended to
  result in inclusion in the project.

### 2. Copyright License Grant / 著作權授權

You grant to the Maintainer a **perpetual, worldwide, non-exclusive,
no-charge, royalty-free, irrevocable** license to:

(a) reproduce, modify, prepare derivative works of, publicly display,
    publicly perform, sublicense, and distribute Your Contribution and
    such derivative works under **AGPL-3.0**; AND

(b) **relicense and sublicense** Your Contribution under any other terms
    — including **proprietary, closed-source, and commercial** licenses
    — for the purpose of distributing the project under a dual-license
    or multi-license model.

你授予維護者**永久、全球、非專屬、免費、不可撤回**的著作權授權，可以：

(a) 以 **AGPL-3.0** 條款重製、修改、衍生、公開展示、表演、再授權、散布你的
    貢獻；
(b) 將你的貢獻以**任何其他條款**（包含**專有、閉源、商業**授權）**再授權**，
    以便用 dual-license / multi-license 模式發行整個專案。

### 3. Patent License Grant / 專利授權

You grant to the Maintainer and to recipients of the project a perpetual,
worldwide, non-exclusive, no-charge, royalty-free, irrevocable patent
license to make, use, sell, import, and otherwise transfer Your
Contribution. This patent license extends only to patent claims
licensable by You that are necessarily infringed by Your Contribution
alone or by combination of Your Contribution with the project.

你授予維護者及專案接收者永久、全球、非專屬、免費、不可撤回的專利授權，
涵蓋製造、使用、販售、進口、轉讓你的貢獻。此授權僅限於你的貢獻本身、
或你的貢獻和專案合併後**必然**侵犯的、且**由你可授權**的專利請求項。

### 4. You Retain Your Copyright / 你保留著作權

This Agreement is a **license**, not an assignment. You retain all
right, title, and interest in Your Contributions. You may also license
or distribute Your Contributions to others under any terms You choose.

這份協議是**授權**而非著作權讓與。你保留貢獻的所有權利。你也可以用任何
你選擇的條款把貢獻授權給其他人。

### 5. Representations / 你的聲明

You represent that:

(a) each Contribution is Your original creation, OR You have the right
    to submit it under this CLA;
(b) if Your employer has rights to intellectual property You create,
    You have either (i) received permission to submit Contributions on
    behalf of that employer, OR (ii) the employer has executed a
    separate Corporate CLA with the Maintainer;
(c) You will notify the Maintainer if any of the above changes.

你聲明：

(a) 每項貢獻都是你的原創，或你**有權**依本 CLA 提交；
(b) 如果你的雇主對你創作的智慧財產有權利，你已**取得雇主同意**提交，或
    雇主已和維護者另簽 Corporate CLA；
(c) 上述事項有變動時，你會通知維護者。

### 6. No Support Obligation / 無支援義務

You are not expected to provide support for Your Contributions, except
to the extent You desire to provide support. Your Contributions are
provided "**AS IS**", without warranties of any kind.

你**沒有**支援貢獻的義務（除非你自己想做）。貢獻以「**現狀**」提供，
不附任何擔保。

---

## How to Sign / 如何簽署

We use a **lightweight DCO-style** mechanism. Every commit you contribute
must include a `Signed-off-by:` trailer that matches an email you control:

我們採**輕量級 DCO** 機制。你提交的每個 commit 都要在訊息尾端帶
`Signed-off-by:`，email 必須是你掌控的：

```bash
git commit -s -m "feat: add new feature"
# auto-adds: Signed-off-by: Your Name <you@example.com>
```

Adding `Signed-off-by:` certifies that you have read this CLA and that
your commit is submitted under its terms.

加 `Signed-off-by:` 等同聲明：你已讀過本 CLA，且這個 commit 依本 CLA 提交。

**First-time contributors**: please also open an issue using the
[CLA Acknowledgement template](https://github.com/fanchanyu/ouvoca/issues/new?template=cla-acknowledgement.yml)
so we can record your acceptance.

**第一次貢獻者**：請另用 [CLA 確認 issue 模板](https://github.com/fanchanyu/ouvoca/issues/new?template=cla-acknowledgement.yml)
開一個 issue 留紀錄。

---

## Questions / 問題

For questions about this CLA — or for corporate CLAs that need
negotiated terms — please contact:

關於本 CLA 的問題（含需個別協商條款的公司 CLA）請聯絡：

- GitHub Issue: https://github.com/fanchanyu/ouvoca/issues (label `legal/cla`)
- Email: *(to be filled in by maintainer)*

---

*This CLA is adapted from the [Apache Individual Contributor License Agreement v2.0](https://www.apache.org/licenses/icla.pdf), with an added dual-licensing clause (Section 2(b)) inspired by the Qt and GitLab CLAs.*

*本 CLA 改編自 [Apache 個人 CLA v2.0](https://www.apache.org/licenses/icla.pdf)，
雙授權條款（2(b)）參考 Qt 和 GitLab CLA。*
