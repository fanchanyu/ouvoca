# LLM-ERP Backup & Restore SOP (English)

> **Losing customer data is unrecoverable. This SOP is mission-critical.**
> Mandatory reading for customer IT, our support staff, and all implementation consultants.

---

## 📑 Contents

1. [3-2-1 Backup Strategy](#1-3-2-1-backup-strategy)
2. [Daily Backup (Automated)](#2-daily-backup-automated)
3. [Weekly Backup (Off-site)](#3-weekly-backup-off-site)
4. [Monthly Archive (Cold Storage)](#4-monthly-archive-cold-storage)
5. [Backup Verification SOP](#5-backup-verification-sop)
6. [Restore SOP](#6-restore-sop)
7. [Disaster Recovery Plan (DRP)](#7-disaster-recovery-plan-drp)
8. [Cross-Machine Migration](#8-cross-machine-migration)
9. [Backup Checklist](#9-backup-checklist)

---

## 1. 3-2-1 Backup Strategy

**3 copies · 2 media · 1 off-site**

```
Original DB (production server)
   ↓ Daily 02:00 (auto)
Daily backup (local disk, /opt/backup/) — retain 7 days
   ↓ Sunday 03:00
Weekly backup (NAS or cloud S3/GCS) — retain 4 weeks
   ↓ 1st of month 04:00
Monthly archive (offline / glacier) — retain 7 years (tax requirement)
```

---

## 2. Daily Backup (Automated)

### 2.1 SQLite Mode

`scripts/backup_daily.sh`:

```bash
#!/bin/bash
set -e
BACKUP_DIR=/opt/backup/daily
DATE=$(date +%Y%m%d_%H%M)
mkdir -p $BACKUP_DIR

# Copy DB from container (no downtime)
docker compose exec -T backend cat /app/erp.db > $BACKUP_DIR/erp-$DATE.db

# Compress
gzip $BACKUP_DIR/erp-$DATE.db

# Retain 7 days
find $BACKUP_DIR -name "erp-*.db.gz" -mtime +7 -delete

# Checksum
md5sum $BACKUP_DIR/erp-$DATE.db.gz > $BACKUP_DIR/erp-$DATE.md5
```

crontab:

```cron
0 2 * * * /opt/llm-erp/scripts/backup_daily.sh >> /var/log/llm-erp-backup.log 2>&1
```

### 2.2 PostgreSQL Mode

```bash
docker compose exec -T db pg_dump -U erp erp | gzip > $BACKUP_DIR/erp-$DATE.sql.gz
```

### 2.3 Also Back Up .env + Config

```bash
# Include .env and docker-compose.yml (back up when secrets rotate)
tar czf $BACKUP_DIR/config-$DATE.tar.gz backend/.env docker-compose.yml
```

---

## 3. Weekly Backup (Off-site)

`scripts/backup_weekly.sh`:

```bash
#!/bin/bash
set -e
LOCAL=/opt/backup/daily
REMOTE=s3://your-bucket/llm-erp-backup/$(date +%Y/%m)/

# Sync daily folder to S3 (or GCS / B2)
aws s3 sync $LOCAL $REMOTE --storage-class STANDARD_IA

# Notify
curl -X POST https://notify-api.line.me/api/notify \
     -H "Authorization: Bearer $LINE_TOKEN" \
     -d "message=✓ Weekly backup completed $(date +%F)"
```

crontab:

```cron
0 3 * * 0 /opt/llm-erp/scripts/backup_weekly.sh
```

### 3.1 NAS Alternative

If not using cloud, sync to internal NAS:

```bash
rsync -av --delete $LOCAL/ user@nas.local:/volume1/backup/llm-erp/
```

---

## 4. Monthly Archive (Cold Storage)

On the 1st of each month, move the last complete backup of the previous month to **offline** storage (7-year tax retention):

```bash
# AWS Glacier Deep Archive cheapest ($1/TB/month)
aws s3 cp $LOCAL/erp-$(date -d "last day of last month" +%Y%m%d)*.db.gz \
    s3://your-glacier-bucket/$(date +%Y)/ \
    --storage-class DEEP_ARCHIVE
```

Or burn to disc (ultra-long-term):

```bash
mkisofs -o erp-2026-04.iso $LOCAL/erp-202604*
# Then burn to archival-grade DVD-R / Blu-ray Disc
```

---

## 5. Backup Verification SOP

**An unverified backup is not a backup.**

### 5.1 Verify Weekly

`scripts/verify_backup.sh`:

```bash
#!/bin/bash
set -e
LATEST=$(ls -t /opt/backup/daily/erp-*.db.gz | head -1)
TEMP=/tmp/verify-$$.db

# Decompress
gunzip -c $LATEST > $TEMP

# Open with sqlite and query
RESULT=$(sqlite3 $TEMP "
SELECT 
  (SELECT COUNT(*) FROM users),
  (SELECT COUNT(*) FROM parts),
  (SELECT COUNT(*) FROM sales_orders),
  (SELECT COUNT(*) FROM purchase_orders);
")

# Cleanup
rm $TEMP

# Notify
echo "[$(date)] Backup $LATEST verified: $RESULT"
if echo "$RESULT" | grep -q "0|0|0|0"; then
    curl -X POST https://notify-api.line.me/api/notify \
         -H "Authorization: Bearer $LINE_TOKEN" \
         -d "message=⚠️ Backup verification FAILED: empty DB"
fi
```

crontab:

```cron
0 6 * * 1 /opt/llm-erp/scripts/verify_backup.sh
```

### 5.2 Quarterly Full Restore Drill

Every 3 months, **actually restore** to a test environment:

```bash
# On staging server
docker compose -f docker-compose.staging.yml down
cp /opt/backup/daily/erp-LATEST.db.gz erp-restored.db.gz
gunzip erp-restored.db.gz
docker compose -f docker-compose.staging.yml up -d
# Run full smoke test
bash scripts/run_gates.sh
```

Passing this = proof that backups actually restore.

---

## 6. Restore SOP

### 6.1 Standard Restore

```bash
cd /opt/llm-erp

# 1. Stop services
docker compose down

# 2. Restore DB (specify which backup)
LATEST=/opt/backup/daily/erp-20260514_0200.db.gz
gunzip -c $LATEST > erp.db

# 3. Restore config (if needed)
tar xzf /opt/backup/daily/config-20260514_0200.tar.gz

# 4. Start services
docker compose up -d --build

# 5. Verify
curl http://localhost:8000/api/health
bash scripts/run_gates.sh
```

### 6.2 Partial Restore (specific table)

```bash
# Export a table from backup
sqlite3 erp-backup.db ".dump customers" > customers.sql
# Import into current DB (backup current first!)
sqlite3 erp.db < customers.sql
```

---

## 7. Disaster Recovery Plan (DRP)

### 7.1 RPO / RTO

| Metric | Target |
|---|---|
| **RPO** (Recovery Point Objective, data loss tolerance) | ≤ 24 hours (daily backup) |
| **RTO** (Recovery Time Objective, time to recover) | ≤ 2 hours |
| Full-factory offline continuity | MESH mode operates independently |

### 7.2 Disaster Scenarios

#### Scenario A: Disk Failure

```
Event: production server disk fails
Loss: today's transactions (up to 24h)
RTO: 2 hours
Actions:
  1. Replace disk
  2. Restore from latest daily backup
  3. Inform customer which data may need re-entry
  4. Run run_gates.sh
```

#### Scenario B: Data Center Fire / Total Destruction

```
Event: entire DC gone
Loss: this week's transactions (use weekly backup)
RTO: 8 hours
Actions:
  1. Find a machine at customer office / spin up GCP VM
  2. Pull weekly backup from S3
  3. Deploy + restore
  4. Switch DNS / Cloudflare Tunnel
```

#### Scenario C: Ransomware

```
Event: production DB encrypted
Loss: today's transactions
RTO: 1 hour (fastest)
Actions:
  1. Immediately disconnect from network
  2. **DO NOT PAY ransom**
  3. Use clean environment (fresh VM) + yesterday's backup
  4. Engage security expert to investigate vector
  5. Notify customer + initiate personal data breach process (within 72h)
```

#### Scenario D: Accidental Deletion

```
Event: admin accidentally ran DROP TABLE
Loss: depends on scope
RTO: 30 minutes
Actions:
  1. Immediately stop writes
  2. Restore from latest backup (partial or full)
  3. Strengthen RBAC + two-person review SOP
```

---

## 8. Cross-Machine Migration

When customer changes servers / data centers:

```bash
# Old server (A)
cd /opt/llm-erp
docker compose down
tar czf llm-erp-full.tar.gz \
    erp.db \
    backend/.env \
    docker-compose.yml \
    /opt/backup/daily/
scp llm-erp-full.tar.gz user@new-server:/tmp/

# New server (B)
cd /opt
tar xzf /tmp/llm-erp-full.tar.gz
cd llm-erp
docker compose up -d --build
bash scripts/run_gates.sh
```

---

## 9. Backup Checklist

Required before Day 14 go-live:

- [ ] `scripts/backup_daily.sh` deployed + in crontab
- [ ] `scripts/backup_weekly.sh` deployed + in crontab
- [ ] `scripts/verify_backup.sh` deployed + in crontab
- [ ] S3 / NAS bucket configured (write tested)
- [ ] LINE Notify token configured (notification tested)
- [ ] Customer IT knows backup location + restore SOP
- [ ] Practiced one full restore (on staging)
- [ ] Customer signed off on backup strategy document

---

## 📞 Backup SOS

| Issue | Contact |
|---|---|
| Backup suddenly failing | LINE @llmerp (P1) |
| Need to restore but stuck | 24/7 phone (Pro+ customers) |
| Planning / upgrade | support@llm-erp.example |

---

**Chinese version**: [`BACKUP_RESTORE_SOP_ZH.md`](./BACKUP_RESTORE_SOP_ZH.md)
**Last updated**: 2026-05-14 · v2.5
