from __future__ import annotations
from datetime import datetime, timezone
from app.utils.validators_br import is_valid_cpf, format_cpf, is_valid_cnpj, format_cnpj
from app.utils.text import normalize, to_bool, safe_int, safe_float
from app.utils.dates import period_label_to_range_iso

def test_cpf_validation_and_format():
    assert is_valid_cpf("529.982.247-25") is True  # CPF de teste amplamente usado
    assert is_valid_cpf("000.000.000-00") is False
    assert format_cpf("52998224725") == "529.982.247-25"

def test_cnpj_format_and_invalid():
    assert format_cnpj("04252011000110") == "04.252.011/0001-10"
    assert is_valid_cnpj("11.111.111/1111-11") is False  # repetido inválido

def test_text_utils_and_numbers():
    assert normalize("CAd-ÚNICO!!") == "cad unico"
    assert to_bool("sim") is True and to_bool("não") is False
    assert safe_int("12.0") == 12
    assert safe_float("3,14") == 3.14

def test_period_label_to_range_iso_fixed_now():
    now = datetime(2025, 8, 29, 12, 0, tzinfo=timezone.utc)
    s7, e7 = period_label_to_range_iso("Últimos 7 dias", now=now)
    assert s7[:10] == "2025-08-22" and e7[:10] == "2025-08-29"
    all_s, all_e = period_label_to_range_iso("Tudo", now=now)
    assert all_s is None and all_e is None
