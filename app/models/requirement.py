from __future__ import annotations
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ConfigDict, field_validator


class RequirementType(str, Enum):
    """Tipos de requisitos previstos no motor (ex.: utils.evaluate_requirements)."""
    BOOL = "bool"          # campo booleano (True/False)
    NUMBER = "number"      # campo numérico (>=, <=, ==, etc.)
    SELECT = "select"      # valor contido em opções
    TEXT = "text"          # presença de texto/palavra-chave
    DOC = "doc"            # documento (ex.: CPF, RG, RGP)
    OTHER = "other"


class Requirement(BaseModel):
    """
    Representa uma regra/condição mapeável ao perfil do usuário.
    Serve como estrutura para construir/validar seu `keyword_map.json`.
    """
    model_config = ConfigDict(extra="allow", validate_assignment=True)

    code: str = Field(..., description="Identificador do requisito (ex.: 'cpf', 'rgp')")
    label: str = Field(..., description="Nome legível (ex.: 'CPF válido')")
    profile_field: str = Field(..., description="Campo do perfil associado (ex.: 'cpf', 'rgp')")
    type: RequirementType = Field(default=RequirementType.DOC)
    any_of: list[str] = Field(default_factory=list, description="Tokens/chaves gatilho encontrados no texto de acesso")
    negate: bool = Field(default=False, description="Se True, inverte a avaliação (raro)")
    notes: str | None = None

    @field_validator("code", "label", "profile_field", mode="before")
    @classmethod
    def _strip(cls, v: Any):
        if v is None:
            return v
        s = str(v).strip()
        return s or None

    @field_validator("any_of", mode="before")
    @classmethod
    def _listify(cls, v: Any):
        if v is None:
            return []
        if isinstance(v, (list, tuple)):
            return [str(x).strip() for x in v if str(x).strip()]
        s = str(v).strip()
        if not s:
            return []
        for sep in [";", "|", ",", "\n"]:
            s = s.replace(sep, "|")
        return [p.strip() for p in s.split("|") if p.strip()]
