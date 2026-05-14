# LLM-ERP 備份還原 SOP（繁體中文）

> **客戶資料毀了賠不起。這支 SOP 是公司命脈。**
> 必讀對象：客戶 IT、我們客服、所有導入顧問。

---

## 📑 目錄

1. [備份策略 3-2-1 原則](#1-備份策略-3-2-1-原則)
2. [日備份（自動）](#2-日備份自動)
3. [週備份（異地）](#3-週備份異地)
4. [月歸檔（冷儲存）](#4-月歸檔冷儲存)
5. [備份驗證 SOP](#5-備份驗證-sop)
6. [還原 SOP](#6-還原-sop)
7. [災難復原計畫（DRP）](#7-災難復原計畫drp)
8. [跨機器移轉](#8-跨機器移轉)
9. [備份檢核清單](#9-備份檢核清單)

---

## 1. 備份策略 3-2-1 原則

**3 份備份 · 2 種媒體 · 1 份異地**

```
原始 DB（在 production server）
   ↓ 每日 02:00 自動
日備份（local disk, /opt/backup/）— 保留 7 天
   ↓ 每週日 03:00
週備份（NAS 或 cloud, S3/GCS）— 保留 4 週
   ↓ 每月 1 日 04:00
月歸檔（離線 / glacier）— 保留 7 年（稅務要求）
```

---

## 2. 日備份（自動）

### 2.1 SQLite 模式

`scripts/backup_daily.sh`:

```bash
#!/bin/bash
set -e
BACKUP_DIR=/opt/backup/daily
DATE=$(date +%Y%m%d_%H%M)
mkdir -p $BACKUP_DIR

# 從 container 拷出 DB（不停服務）
docker compose exec -T backend cat /app/erp.db > $BACKUP_DIR/erp-$DATE.db

# 壓縮
gzip $BACKUP_DIR/erp-$DATE.db

# 保留 7 天
find $BACKUP_DIR -name "erp-*.db.gz" -mtime +7 -delete

# Checksum
md5sum $BACKUP_DIR/erp-$DATE.db.gz > $BACKUP_DIR/erp-$DATE.md5
```

crontab：

```cron
0 2 * * * /opt/llm-erp/scripts/backup_daily.sh >> /var/log/llm-erp-backup.log 2>&1
```

### 2.2 PostgreSQL 模式

```bash
docker compose exec -T db pg_dump -U erp erp | gzip > $BACKUP_DIR/erp-$DATE.sql.gz
```

### 2.3 同時備份 .env 與設定

```bash
# 也包含 .env 跟 docker-compose.yml（密鑰換新就要備）
tar czf $BACKUP_DIR/config-$DATE.tar.gz backend/.env docker-compose.yml
```

---

## 3. 週備份（異地）

`scripts/backup_weekly.sh`:

```bash
#!/bin/bash
set -e
LOCAL=/opt/backup/daily
REMOTE=s3://your-bucket/llm-erp-backup/$(date +%Y/%m)/

# 把整個 daily 同步到 S3（或 GCS / B2）
aws s3 sync $LOCAL $REMOTE --storage-class STANDARD_IA

# Notify
curl -X POST https://notify-api.line.me/api/notify \
     -H "Authorization: Bearer $LINE_TOKEN" \
     -d "message=✓ 週備份完成 $(date +%F)"
```

crontab：

```cron
0 3 * * 0 /opt/llm-erp/scripts/backup_weekly.sh
```

### 3.1 NAS 替代方案

不用雲端的話，可以同步到內網 NAS：

```bash
rsync -av --delete $LOCAL/ user@nas.local:/volume1/backup/llm-erp/
```

---

## 4. 月歸檔（冷儲存）

每月 1 日把上個月最後一份完整備份，搬到「離線」儲存（保 7 年稅務要求）：

```bash
# AWS Glacier Deep Archive 最便宜 ($1/TB/月)
aws s3 cp $LOCAL/erp-$(date -d "last day of last month" +%Y%m%d)*.db.gz \
    s3://your-glacier-bucket/$(date +%Y)/ \
    --storage-class DEEP_ARCHIVE
```

或燒光碟（極長期備份）：

```bash
mkisofs -o erp-2026-04.iso $LOCAL/erp-202604*
# 然後燒入 archival-grade DVD-R / Blu-ray Disc
```

---

## 5. 備份驗證 SOP

**沒驗過的備份不算備份。**

### 5.1 每週驗證一次

`scripts/verify_backup.sh`:

```bash
#!/bin/bash
set -e
LATEST=$(ls -t /opt/backup/daily/erp-*.db.gz | head -1)
TEMP=/tmp/verify-$$.db

# 解壓
gunzip -c $LATEST > $TEMP

# 用 SQLite 開啟做幾個查詢
RESULT=$(sqlite3 $TEMP "
SELECT 
  (SELECT COUNT(*) FROM users),
  (SELECT COUNT(*) FROM parts),
  (SELECT COUNT(*) FROM sales_orders),
  (SELECT COUNT(*) FROM purchase_orders);
")

# Cleanup
rm $TEMP

# 通知
echo "[$(date)] Backup $LATEST verified: $RESULT"
if echo "$RESULT" | grep -q "0|0|0|0"; then
    curl -X POST https://notify-api.line.me/api/notify \
         -H "Authorization: Bearer $LINE_TOKEN" \
         -d "message=⚠️ Backup verification FAILED: empty DB"
fi
```

crontab：

```cron
0 6 * * 1 /opt/llm-erp/scripts/verify_backup.sh
```

### 5.2 每季完整還原演練

每 3 個月**真的還原一次**到測試環境：

```bash
# 在 staging server
docker compose -f docker-compose.staging.yml down
cp /opt/backup/daily/erp-LATEST.db.gz erp-restored.db.gz
gunzip erp-restored.db.gz
docker compose -f docker-compose.staging.yml up -d
# 跑全套 smoke test
bash scripts/run_gates.sh
```

跑過 = 證明備份真的能還原。

---

## 6. 還原 SOP

### 6.1 標準還原

```bash
cd /opt/llm-erp

# 1. 停服務
docker compose down

# 2. 還原 DB（指定要哪份）
LATEST=/opt/backup/daily/erp-20260514_0200.db.gz
gunzip -c $LATEST > erp.db

# 3. 還原設定（若需要）
tar xzf /opt/backup/daily/config-20260514_0200.tar.gz

# 4. 起服務
docker compose up -d --build

# 5. 驗證
curl http://localhost:8000/api/health
bash scripts/run_gates.sh
```

### 6.2 部分還原（只還原某 table）

```bash
# 從備份匯出某表
sqlite3 erp-backup.db ".dump customers" > customers.sql
# 匯回現行 DB（先備份現行）
sqlite3 erp.db < customers.sql
```

---

## 7. 災難復原計畫（DRP）

### 7.1 RPO / RTO

| 項目 | 目標 |
|---|---|
| **RPO**（Recovery Point Objective，可丟失多少資料）| ≤ 24 小時（日備份）|
| **RTO**（Recovery Time Objective，多久要恢復）| ≤ 2 小時 |
| 全廠斷網續用 | MESH 多廠模式可獨立運作 |

### 7.2 災難情境劇本

#### 情境 A：硬碟壞

```
事件：production server 硬碟燒了
損失：當天交易（最多 24h）
RTO：2 小時
動作：
  1. 換新硬碟
  2. 用最近的 daily backup 還原
  3. 告知客戶今天哪些資料可能要重 key
  4. 跑 run_gates.sh
```

#### 情境 B：機房失火 / 完全銷毀

```
事件：整個機房沒了
損失：當週交易（用週備份）
RTO：8 小時
動作：
  1. 在客戶辦公室找一台機器 / 開 GCP VM
  2. 從 S3 拉週備份
  3. 部署 + 還原
  4. 切換 DNS / Cloudflare Tunnel
```

#### 情境 C：勒索病毒

```
事件：production DB 被加密
損失：本日交易
RTO：1 小時（最快）
動作：
  1. 立刻斷網
  2. **不要付贖金**
  3. 用乾淨的環境（新 VM）+ 昨日 backup 還原
  4. 找資安專家檢查感染源
  5. 告警客戶 + 啟動個資外洩通報流程（72h 內）
```

#### 情境 D：人為誤刪

```
事件：管理員誤跑 DROP TABLE
損失：依操作多寡
RTO：30 分鐘
動作：
  1. 立刻 stop 寫入
  2. 從最近 backup 還原（partial 或 full）
  3. 加強 RBAC + 雙人覆核 SOP
```

---

## 8. 跨機器移轉

客戶換伺服器 / 搬機房時：

```bash
# 舊機（A）
cd /opt/llm-erp
docker compose down
tar czf llm-erp-full.tar.gz \
    erp.db \
    backend/.env \
    docker-compose.yml \
    /opt/backup/daily/
scp llm-erp-full.tar.gz user@new-server:/tmp/

# 新機（B）
cd /opt
tar xzf /tmp/llm-erp-full.tar.gz
cd llm-erp
docker compose up -d --build
bash scripts/run_gates.sh
```

---

## 9. 備份檢核清單

導入 Day 14 上線前必須勾完：

- [ ] `scripts/backup_daily.sh` 已部署 + 加入 crontab
- [ ] `scripts/backup_weekly.sh` 已部署 + 加入 crontab
- [ ] `scripts/verify_backup.sh` 已部署 + 加入 crontab
- [ ] S3 / NAS bucket 已開好（測過寫入）
- [ ] LINE Notify token 已設（測過通知）
- [ ] 客戶 IT 知道備份位置 + 還原 SOP
- [ ] 演練過一次完整還原（在 staging）
- [ ] 客戶簽收備份策略文件

---

## 📞 備份問題求救

| 問題 | 聯絡 |
|---|---|
| 備份突然失敗 | LINE @llmerp（P1） |
| 需還原但搞不定 | 24/7 phone（Pro+ 客戶） |
| 規劃 / 升級 | support@llm-erp.example |

---

**對應英文版**：[`BACKUP_RESTORE_SOP_EN.md`](./BACKUP_RESTORE_SOP_EN.md)
**最後更新**：2026-05-14 · v2.5
