
import re, json, unicodedata
from typing import Dict, Any, List, Tuple

def norm(s: str) -> str:
    if s is None:
        return ""
    s = str(s).lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9\s\-_/]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def load_keyword_map(path: str) -> Dict[str, Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
def check_condition(user_value, cond):
    """
    Valida o valor do perfil do usuário (user_value) contra a regra cond.
    cond deve ter: type, op (quando aplicável) e value.
    """
    # Tipo de dado da regra
    t = (cond.get("type") or "").lower()
    # Operador (<=, >=, ==, in etc.)
    op = cond.get("op")
    # Valor esperado (com padrão sensato)
    expected = cond.get("value", True)

    # BOOL
    if t == "bool":
        return bool(user_value) == bool(expected)

    # NUMBER
    if t == "number":
        try:
            user_v = float(user_value)
        except Exception:
            return False
        try:
            exp_v = float(expected)
        except Exception:
            return False

        if op == "<=":
            return user_v <= exp_v
        if op == ">=":
            return user_v >= exp_v
        if op == "==":
            return user_v == exp_v
        return False

    # SELECT_IN (listas de opções)
    if t == "select_in":
        exp_list = expected if isinstance(expected, (list, tuple, set)) else [expected]
        return str(user_value) in set(map(str, exp_list))

    # TEXT (comparação normalizada)
    if t == "text":
        return norm(user_value) == norm(expected)

    # Se o tipo não for reconhecido, falha com segurança
    return False

def evaluate_requirements(requirement_text: str, profile: Dict[str, Any], kw_map: Dict[str, Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    req = norm(requirement_text)
    met, missing = [], []
    for key, cond in kw_map.items():
        if key in req:
            ok = check_condition(profile.get(cond["field"]), cond)
            label = cond.get("label", key)
            if ok:
                met.append(label)
            else:
                missing.append(label)
    return met, missing
