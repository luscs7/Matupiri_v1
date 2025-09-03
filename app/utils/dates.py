from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def utcnow_iso() -> str:
    return utcnow().isoformat()

def period_label_to_range_iso(label: str, now: Optional[datetime] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Converte labels como 'Últimos 7 dias' / 'Últimos 30 dias' / 'Últimos 90 dias' / 'Tudo'
    em (start_iso, end_iso). Retorna (None, None) para 'Tudo'.
    """
    _now = now or utcnow()
    l = (label or "").strip().lower()
    if "7" in l:
        return (_now - timedelta(days=7)).isoformat(), _now.isoformat()
    if "30" in l:
        return (_now - timedelta(days=30)).isoformat(), _now.isoformat()
    if "90" in l:
        return (_now - timedelta(days=90)).isoformat(), _now.isoformat()
    return None, None
