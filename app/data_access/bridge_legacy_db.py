# app/data_access/bridge_legacy_db.py
# Bridge robusto para acessar o db.py legado, com múltiplos fallbacks e erro detalhado.

# app/data_access/bridge_legacy_db.py
# Carrega SEMPRE o db.py pelo caminho absoluto (sem depender do nome "db")

from __future__ import annotations
from pathlib import Path
import importlib.util
import traceback

ROOT = Path(__file__).resolve().parents[2]           # .../Matupiri_v1
DB_FILE = ROOT / "db.py"

def _load_db_module():
    if not DB_FILE.exists():
        raise RuntimeError(f"db.py não encontrado em {DB_FILE}")
    try:
        spec = importlib.util.spec_from_file_location("db_legacy", DB_FILE)
        mod = importlib.util.module_from_spec(spec)  # type: ignore
        assert spec and spec.loader
        spec.loader.exec_module(mod)                 # type: ignore
        return mod
    except Exception:
        raise RuntimeError(
            "Falha ao carregar o db.py por caminho absoluto:\n" +
            traceback.format_exc()
        )

_legacy = _load_db_module()

# Exponha as funções esperadas pelo restante do app:
def _missing(*_a, **_k):
    raise RuntimeError("Função ausente no db.py legado.")

init_db                   = getattr(_legacy, "init_db", _missing)
migrate_db                = getattr(_legacy, "migrate_db", _missing)
migrate_accounts          = getattr(_legacy, "migrate_accounts", _missing)
migrate_analytics         = getattr(_legacy, "migrate_analytics", _missing)

log_event                 = getattr(_legacy, "log_event", _missing)
get_analytics             = getattr(_legacy, "get_analytics", _missing)

create_person_account     = getattr(_legacy, "create_person_account", _missing)
create_collective_account = getattr(_legacy, "create_collective_account", _missing)
authenticate_person       = getattr(_legacy, "authenticate_person", _missing)
authenticate_collective   = getattr(_legacy, "authenticate_collective", _missing)

save_profile_for_account   = getattr(_legacy, "save_profile_for_account", _missing)
update_profile_for_account = getattr(_legacy, "update_profile_for_account", _missing)
get_profiles_by_account    = getattr(_legacy, "get_profiles_by_account", _missing)
load_profile               = getattr(_legacy, "load_profile", _missing)
