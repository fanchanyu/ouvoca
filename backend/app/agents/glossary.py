"""Glossary — 同義詞 / 別名 / 簡稱對映表（v3.3 對話智能；v3.46 Phase 2 G-201 DB 持久化）。

設計目的：
  使用者說「螺絲」、「鋼釘」、「M6」、「長江」、「中華」時，
  AI 能對到 LLM-ERP 內部的標準 part_no / customer_code / supplier_code。

v3.46 升級：
  - GlossaryItem DB table 持久化（重啟不丟失）
  - 啟動時 db_load_glossary() 從 DB 載入到 in-memory dict（熱路徑零 DB 查詢）
  - register_glossary_term tool 同步寫入 DB + 更新 in-memory

設計：see docs/CONVERSATIONAL_ERP_DESIGN_ZH.md §5 原則 #4 + ROADMAP Phase 2 G-201。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class GlossaryEntry:
    """同義詞 → 標準實體的對映。"""
    term: str                       # 使用者說的詞（如「螺絲」）
    canonical_type: str             # "part" | "customer" | "supplier" | "product"
    canonical_id: str               # 對應實體的 UUID 或 code
    canonical_label: str = ""       # 顯示用名稱（如「M6 螺絲」）
    confidence: float = 1.0         # 1.0 = 確定；< 1.0 = 推測
    language: str = "zh-TW"
    aliases: list[str] = field(default_factory=list)  # 其他同義詞
    notes: str = ""


# In-memory store：{term.lower() + ":" + canonical_type → GlossaryEntry}
# 多個 term 可對到同 entity（aliases）
_GLOSSARY: dict[str, GlossaryEntry] = {}


def _key(term: str, canonical_type: str) -> str:
    return f"{term.lower().strip()}:{canonical_type}"


def register_term(entry: GlossaryEntry) -> GlossaryEntry:
    """加入一個 glossary entry。"""
    _GLOSSARY[_key(entry.term, entry.canonical_type)] = entry
    for a in entry.aliases:
        alias_entry = GlossaryEntry(
            term=a, canonical_type=entry.canonical_type,
            canonical_id=entry.canonical_id,
            canonical_label=entry.canonical_label,
            confidence=entry.confidence * 0.9,  # alias 信心稍降
            language=entry.language, notes=f"alias of {entry.term}",
        )
        _GLOSSARY[_key(a, entry.canonical_type)] = alias_entry
    return entry


def resolve_term(term: str, canonical_type: str) -> Optional[GlossaryEntry]:
    """查 glossary。先試精確比對，沒中再試包含比對。"""
    if not term:
        return None
    # exact match
    e = _GLOSSARY.get(_key(term, canonical_type))
    if e is not None:
        return e
    # contains match（粗略：當 term 是 entry.term 的 substring 或反之）
    term_low = term.lower().strip()
    best: Optional[GlossaryEntry] = None
    for k, entry in _GLOSSARY.items():
        if not k.endswith(":" + canonical_type):
            continue
        et = entry.term.lower()
        if term_low in et or et in term_low:
            if best is None or entry.confidence > best.confidence:
                # 包含比對信心打折
                best = GlossaryEntry(**{**entry.__dict__})
                best.confidence = entry.confidence * 0.7
    return best


def list_glossary(
    canonical_type: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 50,
) -> list[GlossaryEntry]:
    items = list(_GLOSSARY.values())
    if canonical_type:
        items = [e for e in items if e.canonical_type == canonical_type]
    if keyword:
        kw = keyword.lower()
        items = [
            e for e in items
            if kw in e.term.lower() or kw in e.canonical_label.lower()
        ]
    return items[:limit]


def clear_glossary() -> None:
    _GLOSSARY.clear()


# ─── DB 持久化函數（v3.46 Phase 2 G-201）────────────────────────────────────

async def db_register_term(
    db: AsyncSession,
    entry: GlossaryEntry,
    created_by: Optional[str] = None,
) -> GlossaryEntry:
    """同時寫入 DB 並更新 in-memory。重啟後 db_load_glossary() 會恢復。"""
    from app.models.glossary import GlossaryItem
    # upsert：term + canonical_type 相同就覆蓋
    existing = (await db.execute(
        select(GlossaryItem).where(
            GlossaryItem.term == entry.term.lower().strip(),
            GlossaryItem.canonical_type == entry.canonical_type,
        )
    )).scalar_one_or_none()

    if existing:
        existing.canonical_id = entry.canonical_id
        existing.canonical_label = entry.canonical_label or entry.canonical_id
        existing.confidence = entry.confidence
        existing.notes = entry.notes
    else:
        db.add(GlossaryItem(
            term=entry.term.lower().strip(),
            canonical_type=entry.canonical_type,
            canonical_id=entry.canonical_id,
            canonical_label=entry.canonical_label or entry.canonical_id,
            confidence=entry.confidence,
            language=entry.language,
            notes=entry.notes,
            created_by=created_by,
        ))
    await db.commit()
    # 同步更新 in-memory
    register_term(entry)
    return entry


async def db_load_glossary(db: AsyncSession) -> int:
    """從 DB 載入所有 glossary 到 in-memory（app 啟動時呼叫）。回傳載入數量。"""
    from app.models.glossary import GlossaryItem
    items = list((await db.execute(select(GlossaryItem))).scalars().all())
    count = 0
    for row in items:
        register_term(GlossaryEntry(
            term=row.term,
            canonical_type=row.canonical_type,
            canonical_id=row.canonical_id,
            canonical_label=row.canonical_label or "",
            confidence=row.confidence or 1.0,
            language=row.language or "zh-TW",
            notes=row.notes or "",
        ))
        count += 1
    return count


def seed_default_glossary() -> None:
    """放幾個常見 demo 用同義詞（給測試 + demo 用，不入 prod seed）。"""
    register_term(GlossaryEntry(
        term="螺絲", canonical_type="part",
        canonical_id="M6-BOLT-20",   # 用 part_no 而非 UUID 方便 demo
        canonical_label="M6 螺絲（M6-BOLT-20）",
        aliases=["鋼釘", "M6", "六角螺絲"],
    ))
    register_term(GlossaryEntry(
        term="螺帽", canonical_type="part",
        canonical_id="M8-NUT", canonical_label="M8 螺帽",
        aliases=["八角螺帽", "M8"],
    ))
    register_term(GlossaryEntry(
        term="長江", canonical_type="supplier",
        canonical_id="SUP-001", canonical_label="長江五金",
        aliases=["長江廠", "長江五金"],
    ))
    register_term(GlossaryEntry(
        term="大華", canonical_type="supplier",
        canonical_id="SUP-002", canonical_label="大華實業",
        aliases=["大華廠", "大華實業"],
    ))
