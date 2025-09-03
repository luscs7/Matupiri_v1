# db.py — backend SQLite para Matupiri (Cadastro + Observatório)
from __future__ import annotations

import os
import hmac
import json
import binascii
import sqlite3
from threading import Lock
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

# ------------------------------------------------------------
# Config
# ------------------------------------------------------------
DB_PATH = Path(os.environ.get("DB_PATH") or "infra/pp_platform.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
_DB_LOCK = Lock()

# ------------------------------------------------------------
# Conexão
# ------------------------------------------------------------
@contextmanager
def _conn():
    cn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cn.row_factory = sqlite3.Row
    # PRAGMAs para desempenho e integridade
    cn.execute("PRAGMA journal_mode=WAL;")
    cn.execute("PRAGMA synchronous=NORMAL;")
    cn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield cn
        cn.commit()
    finally:
        cn.close()

# ------------------------------------------------------------
# Util: tempo e normalização
# ------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _norm_str(s: Optional[str]) -> Optional[str]:
    return s.strip() if isinstance(s, str) else s

# ------------------------------------------------------------
# Util: senha PBKDF2
# ------------------------------------------------------------
_PBKDF2_ITER = 130_000

def _pbkdf2(password: str, salt: bytes, iters: int = _PBKDF2_ITER) -> bytes:
    from hashlib import pbkdf2_hmac
    return pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters, dklen=32)

def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = _pbkdf2(password, salt)
    return f"pbkdf2${_PBKDF2_ITER}${binascii.hexlify(salt).decode()}${binascii.hexlify(dk).decode()}"

def _verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters_s, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2":
            return False
        iters = int(iters_s)
        salt = binascii.unhexlify(salt_hex)
        expected = binascii.unhexlify(hash_hex)
        dk = _pbkdf2(password, salt, iters)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False

def _is_pbkdf2_hash(s: str) -> bool:
    return isinstance(s, str) and s.startswith("pbkdf2$")

# ------------------------------------------------------------
# Schema & Migrações
# ------------------------------------------------------------
def init_db() -> None:
    """Cria tabelas base (idempotente)."""
    with _conn() as cn:
        cur = cn.cursor()

        # Usuários "legados" (se usados por alguma parte do app)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT,
            created_at TEXT
        )
        """)

        # Contas (pessoa/collectivo) para login
        cur.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT CHECK(kind IN ('person','collective')) NOT NULL,
            username TEXT UNIQUE,        -- login pessoa
            display_name TEXT,           -- nome exibido para pessoa
            cnpj TEXT UNIQUE,            -- login coletivo
            contact TEXT,                -- contato coletivo
            password_hash TEXT NOT NULL,
            created_at TEXT
        )
        """)

        # Perfis salvos (dados de cadastro)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,                -- legado (pode ficar vazio)
            profile_json TEXT,
            version INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT,
            owner_account_id INTEGER     -- vínculo com accounts.id
        )
        """)

        # Resultados de elegibilidade (opcional)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS eligibility_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            profile_id INTEGER,
            desired_policy TEXT,
            matched_policies_json TEXT,
            gaps_json TEXT,
            created_at TEXT
        )
        """)

        # Analytics para Observatório
        cur.execute("""
        CREATE TABLE IF NOT EXISTS analytics_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            kind TEXT NOT NULL,          -- 'search','view','matches','eligible'
            policy TEXT,
            uf TEXT,
            municipio TEXT,
            query TEXT,
            gender TEXT,
            met_json TEXT,               -- requisitos atendidos
            missing_json TEXT,           -- requisitos faltantes
            extras_json TEXT
        )
        """)

def migrate_accounts() -> None:
    """Garante colunas de contas e vínculo com perfis."""
    with _conn() as cn:
        cur = cn.cursor()
        # tabela accounts já criada em init_db; aqui garantimos que existe
        cur.execute("PRAGMA table_info(accounts)")
        # vínculo owner_account_id em profiles
        cols = [r[1] for r in cn.execute("PRAGMA table_info(profiles)").fetchall()]
        if "owner_account_id" not in cols:
            cur.execute("ALTER TABLE profiles ADD COLUMN owner_account_id INTEGER;")

def migrate_analytics() -> None:
    """Garante colunas/estrutura de analytics."""
    with _conn() as cn:
        cur = cn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS analytics_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            kind TEXT NOT NULL,
            policy TEXT,
            uf TEXT,
            municipio TEXT,
            query TEXT,
            gender TEXT,
            met_json TEXT,
            missing_json TEXT,
            extras_json TEXT
        )
        """)
        # Backfills tolerantes (não falham se já existem)
        try: cur.execute("ALTER TABLE analytics_events ADD COLUMN gender TEXT")
        except Exception: pass
        try: cur.execute("ALTER TABLE analytics_events ADD COLUMN met_json TEXT")
        except Exception: pass

def migrate_db() -> None:
    """Pequenas migrações em perfis (created_at/updated_at)."""
    with _conn() as cn:
        cur = cn.cursor()
        cols = [r[1] for r in cur.execute("PRAGMA table_info(profiles)").fetchall()]
        if "updated_at" not in cols:
            cur.execute("ALTER TABLE profiles ADD COLUMN updated_at TEXT;")
        if "created_at" not in cols:
            cur.execute("ALTER TABLE profiles ADD COLUMN created_at TEXT;")
        # Preenche campos vazios
        now = _now_iso()
        cur.execute("""
            UPDATE profiles
               SET updated_at = COALESCE(updated_at, created_at, ?),
                   created_at = COALESCE(created_at, ?)
             WHERE updated_at IS NULL OR updated_at='' OR created_at IS NULL OR created_at='';
        """, (now, now))

# ------------------------------------------------------------
# Accounts (pessoa / coletivo)
# ------------------------------------------------------------
def create_person_account(name: str, username: str, password_or_hash: str) -> int:
    """
    Cria conta de pessoa.
    - Se receber senha em texto, gera PBKDF2.
    - Se receber hash PBKDF2 (pbkdf2$...), salva direto (compat bridge).
    """
    pw_hash = password_or_hash if _is_pbkdf2_hash(password_or_hash) else _hash_password(password_or_hash)
    with _DB_LOCK:
        with _conn() as cn:
            cur = cn.execute("""
                INSERT INTO accounts (kind, username, display_name, password_hash, created_at)
                VALUES ('person', ?, ?, ?, ?)
            """, (username, name, pw_hash, _now_iso()))
            rid = cur.lastrowid or cn.execute("SELECT last_insert_rowid()").fetchone()[0]
            return int(rid)

def create_collective_account(cnpj: str, contact: str, password_or_hash: str) -> int:
    pw_hash = password_or_hash if _is_pbkdf2_hash(password_or_hash) else _hash_password(password_or_hash)
    with _DB_LOCK:
        with _conn() as cn:
            cur = cn.execute("""
                INSERT INTO accounts (kind, cnpj, contact, password_hash, created_at)
                VALUES ('collective', ?, ?, ?, ?)
            """, (cnpj, contact, pw_hash, _now_iso()))
            rid = cur.lastrowid or cn.execute("SELECT last_insert_rowid()").fetchone()[0]
            return int(rid)

def authenticate_person(username: str, password_or_hash: str):
    with _conn() as cn:
        row = cn.execute("""
            SELECT id, kind, username, display_name, password_hash
              FROM accounts WHERE kind='person' AND username=?
        """, (username,)).fetchone()
        if not row:
            return None
        stored = row["password_hash"] or ""
        if _is_pbkdf2_hash(password_or_hash):
            ok = hmac.compare_digest(stored, password_or_hash)
        else:
            ok = _verify_password(password_or_hash, stored)
        if ok:
            return {"id": row["id"], "kind": row["kind"], "username": row["username"], "display_name": row["display_name"]}
        return None

def authenticate_collective(cnpj: str, password_or_hash: str):
    with _conn() as cn:
        row = cn.execute("""
            SELECT id, kind, cnpj, contact, password_hash
              FROM accounts WHERE kind='collective' AND cnpj=?
        """, (cnpj,)).fetchone()
        if not row:
            return None
        stored = row["password_hash"] or ""
        if _is_pbkdf2_hash(password_or_hash):
            ok = hmac.compare_digest(stored, password_or_hash)
        else:
            ok = _verify_password(password_or_hash, stored)
        if ok:
            return {"id": row["id"], "kind": row["kind"], "cnpj": row["cnpj"], "contact": row["contact"]}
        return None

# ------------------------------------------------------------
# Users "legado" (opcional)
# ------------------------------------------------------------
def ensure_user(user_id: str, name: Optional[str] = None):
    with _DB_LOCK:
        with _conn() as cn:
            cur = cn.execute("SELECT id FROM users WHERE id=?", (user_id,))
            if not cur.fetchone():
                cn.execute("INSERT INTO users (id, name, created_at) VALUES (?,?,?)",
                           (user_id, name or "", _now_iso()))

# ------------------------------------------------------------
# Perfis
# ------------------------------------------------------------
def save_profile_for_account(owner_account_id: int, profile: Dict[str, Any]) -> int:
    now = _now_iso()
    with _DB_LOCK:
        with _conn() as cn:
            last = cn.execute("SELECT COALESCE(MAX(version),0) FROM profiles WHERE owner_account_id=?", (owner_account_id,)).fetchone()[0]
            version = int(last or 0) + 1
            cur = cn.execute("""
                INSERT INTO profiles (user_id, profile_json, version, created_at, updated_at, owner_account_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("", json.dumps(profile, ensure_ascii=False), version, now, now, owner_account_id))
            rid = cur.lastrowid or cn.execute("SELECT last_insert_rowid()").fetchone()[0]
            return int(rid)

def update_profile_for_account(profile_id: int, owner_account_id: int, profile: Dict[str, Any]) -> None:
    now = _now_iso()
    with _DB_LOCK:
        with _conn() as cn:
            row = cn.execute("SELECT owner_account_id FROM profiles WHERE id=?", (profile_id,)).fetchone()
            if not row or int(row["owner_account_id"] or 0) != int(owner_account_id):
                raise PermissionError("Este perfil não pertence à sua conta.")
            cn.execute("UPDATE profiles SET profile_json=?, updated_at=? WHERE id=?",
                       (json.dumps(profile, ensure_ascii=False), now, profile_id))

def get_profiles_by_account(owner_account_id: int) -> List[Tuple[int,int,str,str]]:
    with _conn() as cn:
        cur = cn.execute("""
            SELECT id, version, created_at, updated_at
              FROM profiles
             WHERE owner_account_id=?
             ORDER BY version DESC
        """, (owner_account_id,))
        return [(int(r["id"]), int(r["version"] or 1), r["created_at"], r["updated_at"]) for r in cur.fetchall()]

# ---- APIs legado por user_id (se ainda usadas em alguma parte) ----
def save_profile(user_id: str, profile: Dict[str, Any]) -> int:
    now = _now_iso()
    with _DB_LOCK:
        with _conn() as cn:
            last = cn.execute("SELECT COALESCE(MAX(version),0) FROM profiles WHERE user_id=?", (user_id,)).fetchone()[0]
            version = int(last or 0) + 1
            cur = cn.execute("""
                INSERT INTO profiles (user_id, profile_json, version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, json.dumps(profile, ensure_ascii=False), version, now, now))
            rid = cur.lastrowid or cn.execute("SELECT last_insert_rowid()").fetchone()[0]
            return int(rid)

def update_profile(profile_id: int, profile: Dict[str, Any]):
    now = _now_iso()
    with _DB_LOCK:
        with _conn() as cn:
            cn.execute("UPDATE profiles SET profile_json=?, updated_at=? WHERE id=?",
                       (json.dumps(profile, ensure_ascii=False), now, profile_id))

def get_profiles(user_id: str) -> List[Tuple[int,int,str,str]]:
    with _conn() as cn:
        cur = cn.execute("""
            SELECT id, version, created_at, updated_at
              FROM profiles
             WHERE user_id=?
             ORDER BY version DESC
        """, (user_id,))
        return [(int(r["id"]), int(r["version"] or 1), r["created_at"], r["updated_at"]) for r in cur.fetchall()]

def load_profile(profile_id: int) -> Dict[str, Any]:
    with _conn() as cn:
        r = cn.execute("SELECT profile_json FROM profiles WHERE id=?", (profile_id,)).fetchone()
        return json.loads(r["profile_json"]) if r else {}

# ------------------------------------------------------------
# Elegibilidade (opcional)
# ------------------------------------------------------------
def save_eligibility(user_id: str, profile_id: int, desired_policy: Optional[str],
                     matched_policies: List[Dict[str, Any]], gaps: List[Dict[str, Any]]) -> int:
    now = _now_iso()
    with _DB_LOCK:
        with _conn() as cn:
            cur = cn.execute("""
                INSERT INTO eligibility_results
                (user_id, profile_id, desired_policy, matched_policies_json, gaps_json, created_at)
                VALUES (?,?,?,?,?,?)
            """, (user_id, profile_id, desired_policy or "",
                  json.dumps(matched_policies, ensure_ascii=False),
                  json.dumps(gaps, ensure_ascii=False),
                  now))
            rid = cur.lastrowid or cn.execute("SELECT last_insert_rowid()").fetchone()[0]
            return int(rid)

# ------------------------------------------------------------
# Observatório (Analytics)
# ------------------------------------------------------------
def log_event(kind: str,
              policy: Optional[str] = None,
              uf: Optional[str] = None,
              municipio: Optional[str] = None,
              query: Optional[str] = None,
              gender: Optional[str] = None,
              met: Optional[List[str]] = None,
              missing: Optional[List[str]] = None,
              extras: Optional[Dict[str, Any]] = None) -> int:
    """Registra evento para o Observatório."""
    with _DB_LOCK:
        with _conn() as cn:
            cur = cn.execute("""
                INSERT INTO analytics_events
                (ts, kind, policy, uf, municipio, query, gender, met_json, missing_json, extras_json)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (_now_iso(), kind, _norm_str(policy), _norm_str(uf), _norm_str(municipio),
                  _norm_str(query), _norm_str(gender),
                  json.dumps(met or [], ensure_ascii=False),
                  json.dumps(missing or [], ensure_ascii=False),
                  json.dumps(extras or {}, ensure_ascii=False)))
            rid = cur.lastrowid or cn.execute("SELECT last_insert_rowid()").fetchone()[0]
            return int(rid)

def get_analytics(start_iso: Optional[str] = None, end_iso: Optional[str] = None,
                  uf: Optional[str] = None, municipio: Optional[str] = None,
                  gender: Optional[str] = None) -> List[Dict[str, Any]]:
    sql = """
        SELECT ts, kind, policy, uf, municipio, query, gender, met_json, missing_json, extras_json
          FROM analytics_events
         WHERE 1=1
    """
    args: List[Any] = []
    if start_iso:
        sql += " AND ts >= ?"; args.append(start_iso)
    if end_iso:
        sql += " AND ts <= ?"; args.append(end_iso)
    if uf:
        sql += " AND UPPER(COALESCE(uf,'')) = ?"; args.append(uf.strip().upper())
    if municipio:
        sql += " AND LOWER(COALESCE(municipio,'')) = ?"; args.append(municipio.strip().lower())
    if gender:
        sql += " AND LOWER(COALESCE(gender,'')) = ?"; args.append(gender.strip().lower())
    sql += " ORDER BY ts DESC"

    out: List[Dict[str, Any]] = []
    with _conn() as cn:
        for r in cn.execute(sql, tuple(args)):
            d = {
                "ts": r["ts"], "kind": r["kind"], "policy": r["policy"],
                "uf": r["uf"], "municipio": r["municipio"], "query": r["query"],
                "gender": r["gender"],
                "met": json.loads(r["met_json"] or "[]"),
                "missing": json.loads(r["missing_json"] or "[]"),
                "extras": json.loads(r["extras_json"] or "{}"),
            }
            out.append(d)
    return out