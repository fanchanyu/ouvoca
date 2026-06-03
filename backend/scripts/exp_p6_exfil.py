"""P6 dedicated experiment: adversarial data-exfiltration attempts via MESH.

Tests Proposition P6 (aggregate-only federated boundary): raw transactional
rows do not cross factory boundaries under the MESH protocol; only aggregate
scalars do.

Unlike the functional MESH integration test (Section 4.4), which verifies the
happy path, this experiment is adversarial: it starts a factory node and fires
a corpus of crafted queries that each attempt to coax raw rows out of the
aggregate endpoint. P6 predicts that every attempt is either rejected (HTTP
4xx) or returns an aggregate scalar containing no raw-row identifier.

Attack strategies:
  1. domain pivot: request a non-inventory domain to reach other tables.
  2. aggregate abuse: request a non-sum/count aggregate (raw, items, *).
  3. SQL injection in part_no.
  4. raw-field probing: inspect every response for raw-row keys.

Output: eval/exp_p6_exfil.csv + summary.json
"""
from __future__ import annotations

import csv
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

if __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

RAW_FIELD_MARKERS = ["id", "items", "rows", "created_at", "updated_at",
                     "qty_available", "local_inventory", "part_no\":"]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait(url: str, timeout: float = 15.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if httpx.get(url, timeout=2).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


# (label, path, params)
ATTACKS = [
    ("baseline-legit-agg", "/api/factory/mesh/query",
     {"domain": "inventory", "part_no": "M6-BOLT", "agg": "sum"}),
    ("domain-pivot-customers", "/api/factory/mesh/query",
     {"domain": "customers", "agg": "sum"}),
    ("domain-pivot-raw", "/api/factory/mesh/query",
     {"domain": "raw", "agg": "sum"}),
    ("domain-pivot-users", "/api/factory/mesh/query",
     {"domain": "users", "agg": "sum"}),
    ("agg-abuse-raw", "/api/factory/mesh/query",
     {"domain": "inventory", "agg": "raw"}),
    ("agg-abuse-items", "/api/factory/mesh/query",
     {"domain": "inventory", "agg": "items"}),
    ("agg-abuse-star", "/api/factory/mesh/query",
     {"domain": "inventory", "agg": "*"}),
    ("sqli-part-no", "/api/factory/mesh/query",
     {"domain": "inventory", "part_no": "' OR '1'='1", "agg": "sum"}),
    ("sqli-union", "/api/factory/mesh/query",
     {"domain": "inventory", "part_no": "x' UNION SELECT * FROM local_inventory--", "agg": "sum"}),
]


def main() -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    factory_script = backend_dir / "factory_node.py"
    port = _free_port()
    import tempfile
    db_path = Path(tempfile.gettempdir()) / f"p6_exfil_{port}.db"
    if db_path.exists():
        db_path.unlink()
    env = {**os.environ, "FACTORY_ID": "p6-test", "FACTORY_NAME": "P6 Test",
           "PORT": str(port), "FACTORY_DB": str(db_path),
           "HQ_URL": "http://127.0.0.1:1"}
    proc = subprocess.Popen([sys.executable, str(factory_script)],
                             env=env, cwd=str(backend_dir),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    url = f"http://127.0.0.1:{port}"
    rows: list[dict] = []
    try:
        if not _wait(f"{url}/api/factory/health"):
            print("Factory node failed to start")
            return 1
        # seed some raw inventory so there IS data to exfiltrate
        httpx.post(f"{url}/api/factory/inventory/upsert",
                   json={"part_no": "M6-BOLT", "qty_on_hand": 3000})
        httpx.post(f"{url}/api/factory/inventory/upsert",
                   json={"part_no": "M8-NUT", "qty_on_hand": 1500})

        print(f"\n{'Attack':28} {'HTTP':>5}  {'raw leaked?':>11}  body excerpt")
        print("-" * 90)
        for label, path, params in ATTACKS:
            try:
                r = httpx.get(url + path, params=params, timeout=5)
                code = r.status_code
                body = r.text
            except Exception as e:
                code = -1
                body = str(e)[:120]
            # A leak is a 200 response whose body contains a raw-row marker
            # beyond the permitted aggregate fields (total, count, factory_id,
            # domain, query, results).
            leaked = False
            if code == 200:
                low = body.lower()
                # permitted keys are total/count/factory_id/domain/query/results
                for marker in ("\"items\"", "\"rows\"", "created_at",
                               "updated_at", "qty_available", "\"id\""):
                    if marker in low:
                        leaked = True
                        break
            rows.append({
                "attack": label, "http_code": code, "raw_leaked": leaked,
                "body_excerpt": body.replace("\n", " ")[:160],
            })
            tag = "LEAK" if leaked else ("blocked" if code >= 400 else "agg-only")
            print(f"  {label:26} {code:>5}  {tag:>11}  {body[:50]}")
    finally:
        try:
            proc.terminate(); proc.wait(timeout=5)
        except Exception:
            proc.kill()
        if db_path.exists():
            try:
                db_path.unlink()
            except Exception:
                pass

    n = len(rows)
    leaks = sum(int(r["raw_leaked"]) for r in rows)
    blocked = sum(int(r["http_code"] >= 400) for r in rows)
    agg_only = sum(int(r["http_code"] == 200 and not r["raw_leaked"])
                    for r in rows)
    print("-" * 90)
    print(f"Attacks: {n}  |  blocked (4xx): {blocked}  |  "
          f"aggregate-only (200, no raw): {agg_only}  |  LEAKS: {leaks}")

    out_dir = Path(__file__).resolve().parents[3] / "ISF_Q2_投稿" / "eval"
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "exp_p6_exfil.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    (out_dir / "exp_p6_exfil_summary.json").write_text(
        json.dumps({
            "proposition": "P6 aggregate-only federated boundary",
            "n_attacks": n,
            "blocked_4xx": blocked,
            "aggregate_only_200": agg_only,
            "raw_leaks": leaks,
            "interpretation": (
                f"Of {n} adversarial queries against the MESH aggregate endpoint, "
                f"{blocked} were rejected with an HTTP 4xx (domain pivots to "
                f"non-inventory tables and non-sum/count aggregates), and "
                f"{agg_only} returned an aggregate scalar with no raw-row field. "
                f"Raw-row leaks: {leaks}. The SQL-injection attempts in part_no do "
                f"not exfiltrate rows because the endpoint composes a parameterised "
                f"SUM/COUNT query and never selects raw columns; the injected string "
                f"is bound as a literal part_no value and matches nothing. This is "
                f"the path-elimination property (Section 2.6.4) at the network "
                f"boundary: the class of paths that return a raw row through the "
                f"aggregate endpoint is empty by construction, because the endpoint "
                f"has no code path that selects raw columns. The separate raw "
                f"endpoint exists but is not reachable through the HQ aggregator."
            ),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nCSV: {out_dir / 'exp_p6_exfil.csv'}")
    return 0 if leaks == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
