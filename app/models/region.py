from __future__ import annotations
from typing import Any

from pydantic import BaseModel, Field, ConfigDict, field_validator


class Region(BaseModel):
    """
    Representa uma localização (UF/município) com possíveis metadados IBGE e coordenadas.
    Pode ser construída a partir de tabelas do IBGE geradas no seu ETL.
    """
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    uf: str = Field(..., min_length=2, max_length=2, description="Sigla da UF (ex.: PA)")
    municipio: str | None = Field(default=None, description="Nome do município")
    ibge_uf: str | None = Field(default=None)
    ibge_mun: str | None = Field(default=None)
    lat: float | None = Field(default=None)
    lon: float | None = Field(default=None)

    @field_validator("uf", mode="before")
    @classmethod
    def _norm_uf(cls, v: Any):
        if v is None:
            return v
        s = str(v).strip().upper()
        return s[:2] if s else s

    @field_validator("municipio", mode="before")
    @classmethod
    def _norm_mun(cls, v: Any):
        if v is None:
            return v
        s = str(v).strip()
        return s or None
