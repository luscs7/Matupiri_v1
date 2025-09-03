from __future__ import annotations
import re

def _only_digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")

# ---------------- CPF ----------------

def is_valid_cpf(cpf: str) -> bool:
    """
    Valida CPF com cálculo de dígitos verificadores.
    Aceita com/sem máscara.
    """
    n = _only_digits(cpf)
    if len(n) != 11 or n == n[0] * 11:
        return False

    # 1º DV
    s1 = sum(int(n[i]) * (10 - i) for i in range(9))
    d1 = (s1 * 10) % 11
    d1 = 0 if d1 == 10 else d1

    # 2º DV
    s2 = sum(int(n[i]) * (11 - i) for i in range(10))
    d2 = (s2 * 10) % 11
    d2 = 0 if d2 == 10 else d2

    return n[-2:] == f"{d1}{d2}"

def format_cpf(cpf: str) -> str:
    n = _only_digits(cpf)
    if len(n) != 11:
        return cpf
    return f"{n[0:3]}.{n[3:6]}.{n[6:9]}-{n[9:11]}"

# ---------------- CNPJ ----------------

def is_valid_cnpj(cnpj: str) -> bool:
    """
    Valida CNPJ com dígitos verificadores.
    """
    n = _only_digits(cnpj)
    if len(n) != 14 or n == n[0] * 14:
        return False

    def dv(num: str) -> int:
        pesos = [6,5,4,3,2,9,8,7,6,5,4,3,2]
        s = sum(int(num[i]) * pesos[i + (len(pesos)-len(num))] for i in range(len(num)))
        r = s % 11
        return 0 if r < 2 else 11 - r

    d1 = dv(n[:12])
    d2 = dv(n[:12] + str(d1))
    return n[-2:] == f"{d1}{d2}"

def format_cnpj(cnpj: str) -> str:
    n = _only_digits(cnpj)
    if len(n) != 14:
        return cnpj
    return f"{n[0:2]}.{n[2:5]}.{n[5:8]}/{n[8:12]}-{n[12:14]}"
