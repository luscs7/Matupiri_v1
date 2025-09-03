from __future__ import annotations
from typing import Any, Dict, Iterable, Optional
import os
import pandas as pd

from app.data_access.storage import read_excel, read_csv, read_geojson, read_json, resolve, ensure_dirs
from app.utils.config import paths

# Bridge com seu banco legado (db.py na raiz)
from app.data_access import bridge_legacy_db as DB

# ------------- Boot e Migrations -------------

def boot_migrations() -> None:
    """Inicializa e migra o banco (idempotente)."""
    ensure_dirs()  # garante 'data/' etc.
    # Permite trocar o arquivo .db pelo env DB_PATH
    # Seu db.py já lê essa env (mantenha essa convenção no legado):
    if "DB_PATH" not in os.environ:
        # opcional: definir um default aqui se quiser centralizar
        # os.environ["DB_PATH"] = str(resolve("pp_platform.db"))
        pass
    DB.init_db()
    DB.migrate_db()
    DB.migrate_accounts()
    DB.migrate_analytics()

# ------------- Autenticação -------------

def create_person_account(display_name: str, username: str, password: str) -> Dict[str, Any]:
    return DB.create_person_account(display_name, username, password)

def create_collective_account(cnpj: str, contact: str, password: str) -> Dict[str, Any]:
    return DB.create_collective_account(cnpj, contact, password)

def authenticate_person(username: str, password: str) -> Optional[Dict[str, Any]]:
    return DB.authenticate_person(username, password)

def authenticate_collective(cnpj: str, password: str) -> Optional[Dict[str, Any]]:
    return DB.authenticate_collective(cnpj, password)

# ------------- Perfis -------------

def save_profile_for_account(owner_account_id: int, profile: Dict[str, Any]) -> int:
    return DB.save_profile_for_account(owner_account_id, profile)

def update_profile_for_account(profile_id: int, owner_account_id: int, profile: Dict[str, Any]) -> bool:
    return DB.update_profile_for_account(profile_id, owner_account_id, profile)

def get_profiles_by_account(owner_account_id: int) -> Iterable[Iterable[Any]]:
    return DB.get_profiles_by_account(owner_account_id)

def load_profile(profile_id: int) -> Dict[str, Any]:
    return DB.load_profile(profile_id)

# ------------- Analytics / Observatório -------------

def log_event(**kwargs) -> None:
    """
    Exemplos de uso:
      log_event(kind="search", uf="PA", municipio="Bragança", query="pronaf")
      log_event(kind="view", policy="Bolsa Família", uf="PA", municipio="Bragança", gender="feminino")
      log_event(kind="matches", met=["cpf"], missing=["rgp"], uf="PA", municipio="Bragança")
      log_event(kind="eligible", policy="Seguro Defeso", uf="PA")
    """
    DB.log_event(**kwargs)

def get_analytics(start_iso: Optional[str] = None,
                  end_iso: Optional[str] = None,
                  uf: Optional[str] = None,
                  municipio: Optional[str] = None,
                  gender: Optional[str] = None) -> Iterable[Dict[str, Any]]:
    return DB.get_analytics(start_iso=start_iso, end_iso=end_iso, uf=uf, municipio=municipio, gender=gender)

# ------------- Dados de Catálogo (arquivos) -------------

def load_policies_table(xlsx_path: Optional[str] = None) -> pd.DataFrame:
    """
    Lê a planilha de políticas. Por padrão usa paths()["POLICIES_XLSX"].
    Normaliza colunas e mantém apenas as necessárias.
    """
    P = paths()
    path = xlsx_path or P.get("POLICIES_XLSX", "data/processed/politicas_publicas.xlsx")
    cols = [
        "Número",
        "Politicas publicas",
        "nivel",
        "Operacionalização/Aplicação",
        "Descrição dos direitos",
        "Acesso",
        "Organização interna (Subprogramas e/ou Eixos)",
        "Link",
        "Observações",
    ]
    df = read_excel(path, sheet=0, usecols=cols)
    if df.empty:
        return df
    df.columns = [c.strip() for c in df.columns]
    keep = [c for c in cols if c in df.columns]
    return df[keep].copy()

def load_defesos_csv(path: Optional[str] = None) -> pd.DataFrame:
    """
    Esperado: colunas ['especie','nome_popular','arte_pesca','uf','inicio','fim','fundamento_legal','esfera','link_oficial']
    """
    P = paths()
    _path = path or P.get("DEFESOS_CSV", "data/processed/defesos.csv")
    return read_csv(_path, dtype=str)

def load_ucs_csv(path: Optional[str] = None) -> pd.DataFrame:
    """
    Esperado: ['nome','categoria','esfera','uf','area_ha','link']
    """
    P = paths()
    _path = path or P.get("UCS_CSV", "data/processed/ucs.csv")
    return read_csv(_path)

def load_ucs_geojson(path: Optional[str] = None) -> dict:
    P = paths()
    _path = path or P.get("UCS_GEOJSON", "data/processed/ucs.geojson")
    return read_geojson(_path)

def load_profile_schema(path: Optional[str] = None) -> dict:
    P = paths()
    _path = path or P.get("PROFILE_SCHEMA", "data/docs/profile_schema.json")
    return read_json(_path)

def load_keyword_map(path: Optional[str] = None) -> dict:
    P = paths()
    _path = path or P.get("KEYWORD_MAP", "data/docs/keyword_map.json")
    return read_json(_path)