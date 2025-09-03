from __future__ import annotations
import pandas as pd
from app.data_access import repositories as repo

def test_boot_migrations_does_not_raise():
    # funções já estão monkeypatched no conftest -> só checa que não explode
    repo.boot_migrations()

def test_load_policies_table_from_tmp(tmp_policies_xlsx):
    df = repo.load_policies_table(tmp_policies_xlsx)
    assert not df.empty
    assert set(["Número","Politicas publicas","Acesso"]).issubset(df.columns)
