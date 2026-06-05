"""Module 11 — Alternative-Data Research.

Pulls recent monsoon/weather headlines (Google News RSS — free, no key),
AI-summarizes them, and extracts bullish / bearish / risk factors for the
RAINMUMBAI rainfall outlook. Stored as a digest in alt_documents.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingest.base import http_get_text
from app.models.orm import AltDocument
from app.services import llm

QUERIES = [
    "India monsoon rainfall forecast",
    "Mumbai rainfall IMD",
    "El Nino La Nina Indian monsoon",
    "Indian Ocean Dipole monsoon",
]
RSS = "https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
MAX_PER_QUERY = 5

SYSTEM = (
    "You are a weather-derivatives analyst. From the rainfall/monsoon news headlines provided, "
    "judge the implication for Mumbai monsoon RAINFALL (more rain = bullish, less = bearish). "
    "Respond with STRICT JSON only, no prose, in this exact shape: "
    '{"summary": "2-3 sentence overview", '
    '"bullish": ["short factor", ...], "bearish": ["short factor", ...], '
    '"risks": ["short risk", ...], "sentiment": <number -1..1>}'
)


def fetch_headlines() -> list[dict]:
    items: list[dict] = []
    seen = set()
    for q in QUERIES:
        try:
            xml = http_get_text(RSS.format(q=q.replace(" ", "+")), timeout=20)
            root = ET.fromstring(xml)
        except Exception as exc:  # noqa: BLE001
            print(f"[news] feed '{q}' skipped: {exc}")
            continue
        for it in root.iter("item"):
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            pub = (it.findtext("pubDate") or "").strip()
            if not title or title in seen:
                continue
            seen.add(title)
            items.append({"title": title, "url": link, "published": pub, "query": q})
            if len([x for x in items if x["query"] == q]) >= MAX_PER_QUERY:
                break
    return items


def _extract_json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:  # noqa: BLE001
        return None


def refresh(db: Session) -> dict:
    headlines = fetch_headlines()
    if not headlines:
        return {"available": False, "reason": "no headlines fetched"}

    listing = "\n".join(f"- {h['title']}" for h in headlines)
    try:
        raw = llm.generate(f"Headlines:\n{listing}", system=SYSTEM, temperature=0.2, max_tokens=600)
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "reason": f"LLM unreachable: {exc}"}

    parsed = _extract_json(raw) or {}
    factors = {
        "bullish": parsed.get("bullish", [])[:6],
        "bearish": parsed.get("bearish", [])[:6],
        "risks": parsed.get("risks", [])[:6],
        "headlines": headlines,
    }
    doc = AltDocument(
        source="google_news",
        title="Monsoon news digest",
        url=None,
        published_at=None,
        raw_text=listing,
        summary=parsed.get("summary") or raw[:500],
        sentiment=float(parsed.get("sentiment", 0)) if isinstance(parsed.get("sentiment", 0), (int, float)) else 0.0,
        factors=factors,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"available": True, "id": doc.id, "n_headlines": len(headlines)}


def latest(db: Session) -> dict:
    doc = db.execute(select(AltDocument).order_by(AltDocument.ingested_at.desc()).limit(1)).scalar_one_or_none()
    if not doc:
        return {"available": False}
    f = doc.factors or {}
    return {
        "available": True,
        "as_of": doc.ingested_at.isoformat() if doc.ingested_at else None,
        "summary": doc.summary,
        "sentiment": doc.sentiment,
        "bullish": f.get("bullish", []),
        "bearish": f.get("bearish", []),
        "risks": f.get("risks", []),
        "headlines": f.get("headlines", []),
    }
