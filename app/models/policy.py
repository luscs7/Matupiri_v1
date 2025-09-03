from __future__ import annotations
from enum import Enum
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, Field, HttpUrl, ConfigDict, field_validator


class PolicyLevel(str, Enum):
    FEDERAL = "Federal"
    ESTADUAL = "Estadual"
    MUNICIPAL = "Municipal"
    OUTRO = "Outro"


def _to_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    s = str(value).strip()
    if not s:
        return []
    # tenta separar por ; | ,  •
    for sep in [";", "|", "•", ",", "\n"]:
        s = s.replace(sep, "|")
    return [p.strip() for p in s.split("|") if p.strip()]


class Policy(BaseModel):
    """
    Representa uma linha da planilha de políticas.
    Campos mapeados para nomes “amigáveis”. Aceita extras e ignora colunas desconhecidas.
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    number: str | None = Field(None, alias="Número")
    title: str = Field(..., alias="Politicas publicas")
    level: PolicyLevel | str | None = Field(None, alias="nivel")
    description: str | None = Field(None, alias="Descrição dos direitos")
    access_text: str | None = Field(None, alias="Acesso")
    operationalization: str | None = Field(None, alias="Operacionalização/Aplicação")
    axes: list[str] = Field(default_factory=list, alias="Organização interna (Subprogramas e/ou Eixos)")
    link: HttpUrl | str | None = Field(None, alias="Link")
    notes: str | None = Field(None, alias="Observações")

    @field_validator("level", mode="before")
    @classmethod
    def _norm_level(cls, v: Any):
        if v is None or v == "":
            return None
        s = str(v).strip().lower()
        if "federal" in s:
            return PolicyLevel.FEDERAL
        if "estadual" in s or "estado" in s:
            return PolicyLevel.ESTADUAL
        if "municip" in s:
            return PolicyLevel.MUNICIPAL
        return PolicyLevel.OUTRO

    @field_validator("axes", mode="before")
    @classmethod
    def _parse_axes(cls, v: Any) -> list[str]:
        return _to_list(v)

    @field_validator("link", mode="before")
    @classmethod
    def _empty_link_as_none(cls, v: Any):
        if v is None:
            return None
        s = str(v).strip()
        return s or None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Policy":
        """
        Constrói a Policy a partir de uma linha de DataFrame/Dict com nomes de coluna originais.
        """
        return cls.model_validate(row)

    def to_display_dict(self) -> dict[str, Any]:
        """Dicionário pronto para UI (útil em tabelas ou exportações)."""
        return {
            "Número": self.number,
            "Política": self.title,
            "Nível": (self.level.value if isinstance(self.level, PolicyLevel) else self.level),
            "Descrição dos direitos": self.description,
            "Acesso (texto)": self.access_text,
            "Organização interna": ", ".join(self.axes),
            "Link": self.link,
            "Observações": self.notes,
        }
