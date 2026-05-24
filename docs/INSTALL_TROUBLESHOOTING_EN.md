# Install Troubleshooting Guide

> **Install failed? Don't panic.** This doc lists problems by symptom, with the
> most common ones first. 90% of issues resolve with the top 3 fixes.
>
> **中文版**: [INSTALL_TROUBLESHOOTING_ZH.md](./INSTALL_TROUBLESHOOTING_ZH.md)

---

## 🆘 Emergency Self-Rescue: Try These 3 First

Regardless of the error, try these — they fix 80% of issues:

1. **Run as Administrator**
   Right-click `install_easy.bat` → "Run as administrator"
2. **Temporarily disable antivirus**
   Windows Defender / Norton / Kaspersky / Trend Micro may flag the silent Python installer.
   Re-enable after install completes.
3. **Check network**
   `install_easy.bat` needs to reach `python.org`, `nodejs.org`, `pypi.org`, `registry.npmjs.org`.
   Corporate firewalls often block these — ask IT to whitelist them.

---

## 📋 Symptom → Fix

### `curl: command not found` or `tar: command not found`

**Cause**: Windows too old (pre-build 1803).
**Fix**: Upgrade to Windows 10 1903+ or Windows 11, or use the Docker path (`install.bat`).

### `Python install failed`

**Most likely**: Antivirus blocked the silent installer.
**Fix**:
1. Temporarily disable antivirus for 30 minutes
2. Re-run `install_easy.bat`
3. After install completes, re-enable antivirus
4. Add the project folder to antivirus **whitelist** (prevents runtime blocking)

**Secondary**: Insufficient disk space. Python install needs ~300 MB.

### `Node download failed`

**Cause**: Unstable network, or nodejs.org unreachable.
**Fix**:
```
1. In a browser, test https://nodejs.org/dist/v20.11.1/
   Loads? Good. Doesn't load? Corporate firewall blocking.
2. If blocked, ask IT to allow nodejs.org, or
3. Manual install:
   - Download LTS from https://nodejs.org/ (Windows Installer .msi)
   - Install it, then re-run install_easy.bat
   - The script detects system Node and skips its own download
```

### `pip install failed` (backend dependencies)

**Most likely 1**: Network problem (PyPI unreachable).
```cmd
ping pypi.org
```
Unreachable → corporate firewall. Ask IT to allow `pypi.org` + `*.pythonhosted.org`.

**Most likely 2**: A package needs Visual C++ Build Tools.
**Fix**: Install free [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) → re-run.

**Most likely 3**: Using a corporate proxy.
**Fix**: Set proxy env vars before running:
```cmd
set HTTPS_PROXY=http://your-proxy:port
set HTTP_PROXY=http://your-proxy:port
install_easy.bat
```

### `npm install failed`

**Cause 1**: Unstable network / npm registry unreachable.
**Fix**: Use a mirror (e.g., for users in Asia):
```cmd
cd frontend-desktop
npm config set registry https://registry.npmmirror.com
npm install
```

**Cause 2**: node_modules partially corrupted.
**Fix**:
```cmd
rmdir /s /q frontend-desktop\node_modules
del frontend-desktop\package-lock.json
install_easy.bat
```

### `Backend failed to start in 30s`

**Cause 1**: Port 8000 is occupied by another process.
**Fix**:
```cmd
netstat -ano | findstr :8000
```
Note the PID (e.g., 12345) → `taskkill /F /PID 12345`.

**Cause 2**: `backend\.env` missing fields or has format errors.
**Fix**:
```cmd
del backend\.env
install_easy.bat
```
Lets the script regenerate `.env`.

### Browser shows "Cannot connect" at http://localhost:5173

**Cause**: Frontend didn't start, or firewall blocked port 5173.
**Fix**:
1. Check the `ouvoca-frontend` window for error messages
2. Windows Firewall → Allow `node.exe`
3. Re-run `start.bat`

### "Login failed" / Forgot password

Default credentials: `admin` / `admin123`.
If you changed the password and forgot, re-initialize the DB:
```cmd
del backend\erp.db
del backend\.seeded
install_easy.bat
```
⚠️ Warning: This wipes ALL data.

---

## 🔥 Cannot Install At All?

If none of the above works, final escalation:

### Option A: Use the Docker path

The Docker path is more "fault-tolerant" but requires Docker Desktop first:
1. Download from <https://www.docker.com/products/docker-desktop/>
2. Double-click `install.bat` (not install_easy.bat)

### Option B: Hire local IT

A common SMB pattern: hire a local IT contractor to install (~USD 20-70 / install).
Share this troubleshooting guide and the error messages — usually solved within an hour.

### Option C: File a GitHub Issue

Open an issue at <https://github.com/fanchanyu/ouvoca/issues> with:
1. Windows version (run `winver` and screenshot)
2. Full error message (screenshot)
3. Which step (`[Step X/5]`) failed

We respond within 48 hours.

---

## 💡 Post-Install Tips

1. **Add Ouvoca folder to antivirus whitelist** — prevents slow startup scans
2. **Regularly back up `backend/erp.db`** — this file contains ALL your ERP data
3. **Change the admin password on first login** — don't keep using `admin123`
4. **Bookmark http://localhost:5173** in your browser

---

## 🗑 Complete Uninstall

> ⚠️ **Don't just delete the folder!** The silent Python installer run by
> `install_easy.bat` leaves "Python 3.11 (64-bit)" in **Windows registry**,
> visible in "Add/Remove Programs". Deleting the folder won't clean this up.

### Correct uninstall (Windows)

**Double-click `uninstall_easy.bat`** — it will:

| Step | Action |
|------|--------|
| 1 | Stop running backend (8000) + frontend (5173) |
| 2 | Run Python installer in `/uninstall` mode → **cleans registry** |
| 3 | Delete `tools\python` + `tools\node` + download cache |
| 4 | Delete `backend\venv` + `frontend-desktop\node_modules` |
| 5 | **ASK YOU**: delete your ERP data? (`erp.db` / `uploads/` / `.env`) |
| Adv | **ASK YOU**: clear global npm/pip cache? (frees ~500MB, affects other projects) |

After completion, you can safely delete the entire Ouvoca folder — **zero residue in Windows**.

### Mac / Linux

```bash
bash uninstall_easy.sh
```

Note: On Mac/Linux, Python/Node were installed by you via `brew`/`apt`. The uninstall
script **does NOT touch them** (other projects may use them). It only removes this
project's `venv` + `node_modules`, then asks about your data.

### I already deleted the folder and found Python residue

Open PowerShell (admin) and run:
```powershell
reg delete "HKCU\Software\Python\PythonCore\3.11" /f
Get-ChildItem "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall" |
  Where-Object { $_.GetValue("DisplayName") -like "Python 3.11*" } |
  Remove-Item -Recurse -Force
```

### I want to keep my data, just remove the software

Run `uninstall_easy.bat` → answer **N** to "Delete your ERP data?" → all program
files cleaned, `backend\erp.db` + `backend\uploads\` + `backend\.env` preserved.
Re-running `install_easy.bat` later will automatically reuse your data.

---

**Last updated**: v3.51 (2026-05-24)
