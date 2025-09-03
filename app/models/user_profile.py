from __future__ import annotations
from typing import Any

from pydantic import BaseModel, Field, ConfigDict, field_validator


class UserProfile(BaseModel):
    """
    Perfil do usuário para avaliação de elegibilidade.
    - Aceita campos extras (schema dinâmico).
    - Mantém campos básicos de localização.
    """
    model_config = ConfigDict(extra="allow", validate_assignment=True)

    estado: str | None = Field(default=None, description="UF do usuário (ex.: PA)")
    municipio: str | None = Field(default=None, description="Município do usuário")
    ibge_mun: str | None = Field(default=None)
    genero: str | None = Field(default=None)

    @field_validator("estado", mode="before")
    @classmethod
    def _norm_uf(cls, v: Any):
        if v is None:
            return v
        s = str(v).strip().upper()
        return s[:2] if s else s

    @field_validator("municipio", "genero", mode="before")
    @classmethod
    def _strip(cls, v: Any):
        if v is None:
            return v
        s = str(v).strip()
        return s or None

    # ---------------- Conveniências ----------------

    def as_dict(self) -> dict[str, Any]:
        """Dicionário incluindo extras, pronto para o motor de regras."""
        return self.model_dump()

    def get_bool(self, key: str) -> bool | None:
        v = self.model_extra.get(key) if key not in self.model_fields_set else getattr(self, key, None)
        if v is None:
            return None
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        if s in {"true", "t", "1", "sim", "yes", "y"}:
            return True
        if s in {"false", "f", "0", "nao", "não", "no", "n"}:
            return False
        return None

    def get_number(self, key: str) -> float | None:
        v = self.model_extra.get(key) if key not in self.model_fields_set else getattr(self, key, None)
        if v is None or v == "":
            return None
        try:
            return float(v)
        except Exception:
            return None

    def get_text(self, key: str) -> str | None:
        v = self.model_extra.get(key) if key not in self.model_fields_set else getattr(self, key, None)
        if v is None:
            return None
        s = str(v).strip()
        return s or None
