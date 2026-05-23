# Third-Party Downloads Disclosure

> This document discloses what software `install_easy.bat` / `install_easy.sh`
> downloads at runtime, from which third parties, under which licenses, and
> how you can obtain them manually (if you prefer not to use the auto-installer).
>
> **Ouvoca does NOT redistribute these software** — every file is downloaded
> directly by your computer from the original vendor's official site. The
> script merely clicks the "download" button on your behalf.

---

## 1. Auto-downloaded Inventory

| Name | Version | Size | Source URL | License |
|------|---------|------|------------|---------|
| **Python** | 3.11.9 | ~26 MB | <https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe> | [PSF License](https://docs.python.org/3/license.html) (BSD-like, permissive) |
| **Node.js** | 20.11.1 LTS | ~30 MB | <https://nodejs.org/dist/v20.11.1/node-v20.11.1-win-x64.zip> | [MIT License](https://github.com/nodejs/node/blob/main/LICENSE) (permissive) |
| **pip + setuptools + wheel** | bundled with Python | ~5 MB | Bundled in Python 3.11.9 installer | Same as PSF License |
| **npm packages** (v3.49 ≈ 250 MB) | per `package.json` | ~250 MB | npm registry <https://registry.npmjs.org/> | Per-package; mostly MIT / Apache-2.0 / ISC |
| **PyPI packages** (FastAPI / SQLAlchemy / Pydantic etc.) | per `requirements.txt` | ~200 MB | PyPI <https://pypi.org/> | Per-package; mostly MIT / Apache-2.0 / BSD |

**Total download**: ~**500 MB** (first-time install; subsequent launches: 0 downloads).

---

## 2. Legal Position on Redistribution

`install_easy.bat` **does NOT bundle, embed, or modify** any of the above software:

- The script contains **no** Python / Node binaries
- The script **only invokes `curl`** to fetch from official sources, equivalent to a user clicking a download link in a browser
- Downloads are cached in `tools/downloads/`; files are not modified
- Post-install `tools/python/` and `tools/node/` are **bit-for-bit identical** to a manual install

Therefore, legally, running `install_easy.bat` ≡ you downloading and installing
Python / Node yourself. Ouvoca obtains no rights to these third-party software,
and grants no rights to them.

Terms of use for each component are governed by the original vendor (see
the "License" column above).

---

## 3. Privacy & Telemetry

- **`install_easy.bat` / `start.bat` do NOT send any data to Ouvoca or any third party.**
- The only network activity = downloads from the URLs in §1.
- Python and Node **do not enable any telemetry by default** (Node telemetry is off by default; Python has none).
- You can install offline (see §4) to avoid any external connection.

Ouvoca itself **collects no install statistics, no usage statistics, no error reports**.
On-prem deployment = your data stays on your machine.

---

## 4. Offline Installation

If you are in an air-gapped environment, your company blocks outbound traffic,
or you don't trust auto-downloads, you can install offline:

### Step 1 — Manually download on an Internet-connected machine

```
1. From <https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe>,
   download the Python installer; save as python-installer.exe

2. From <https://nodejs.org/dist/v20.11.1/node-v20.11.1-win-x64.zip>,
   download the Node zip; save as node.zip
```

### Step 2 — Place files in the right location

```
opnetest\
└── tools\
    └── downloads\
        ├── python-installer.exe   (from Step 1)
        └── node.zip               (from Step 1)
```

### Step 3 — Double-click `install_easy.bat`

The script detects pre-existing files in `tools/downloads/` → skips download → uses them.

> ⚠️ Note: PyPI packages (FastAPI etc.) and npm packages still need the network.
> A fully offline install requires `pip download` + `npm pack` pre-bundling.

---

## 5. SHA-256 Verification (Advanced Users)

To confirm downloads were not tampered with via MITM:

| File | Expected SHA-256 (cross-check with vendor's current announcement) |
|------|--------------------------------------------------------------------|
| `python-3.11.9-amd64.exe` | See "Files" table at <https://www.python.org/downloads/release/python-3119/> |
| `node-v20.11.1-win-x64.zip` | See <https://nodejs.org/dist/v20.11.1/SHASUMS256.txt> |

Windows verification:
```cmd
certutil -hashfile tools\downloads\python-installer.exe SHA256
certutil -hashfile tools\downloads\node.zip SHA256
```

> Compare output against vendor's published SHA-256. Mismatch → delete + re-download + report.

---

## 6. Comparison with Docker Path

| Aspect | `install_easy.bat` (non-tech) | `install.bat` (Docker) |
|--------|-------------------------------|------------------------|
| What gets downloaded | Python 26MB + Node 30MB + packages 500MB | Docker images (Ouvoca + postgres etc.) ~1–2 GB |
| Source | python.org / nodejs.org / PyPI / npm | Docker Hub (`docker.io`) |
| Auto-executed | silent install + venv creation | `docker compose up -d` |
| Legal nature | Equivalent to user manually downloading | Equivalent to user running `docker pull` manually |

Both paths are **legally identical** — Ouvoca provides scripts to assist the
process, but does not redistribute any third-party software.

---

**Last updated**: v3.49 (2026-05-22)
**Chinese version**: [THIRD_PARTY_DOWNLOADS_ZH.md](./THIRD_PARTY_DOWNLOADS_ZH.md)
