from __future__ import annotations
from functools import lru_cache, wraps
from typing import Callable, TypeVar, Any

T = TypeVar("T")

# Detecta Streamlit (opcional)
try:
    import streamlit as st  # type: ignore
    _HAS_ST = True
except Exception:
    _HAS_ST = False

def cached_data(func: Callable[..., T] | None = None, **st_kwargs: Any):
    """
    Decorator de cache para dados (preferindo st.cache_data quando disponível).
    Fallback para lru_cache quando Streamlit não está presente.
    """
    if _HAS_ST:
        return st.cache_data(**st_kwargs)(func) if func else (lambda f: st.cache_data(**st_kwargs)(f))

    # Fallback: lru_cache (ignora ttl/show_spinner/etc.)
    def _wrap(f: Callable[..., T]):
        maxsize = st_kwargs.get("maxsize", 1024)
        return lru_cache(maxsize=maxsize)(f)
    return _wrap if func is None else _wrap(func)

def cached_resource(func: Callable[..., T] | None = None, **st_kwargs: Any):
    """
    Cache para recursos pesados (modelos, conexões).
    """
    if _HAS_ST:
        return st.cache_resource(**st_kwargs)(func) if func else (lambda f: st.cache_resource(**st_kwargs)(f))

    def _wrap(f: Callable[..., T]):
        # um recurso único por assinatura; maxsize=1 costuma bastar
        return lru_cache(maxsize=1)(f)
    return _wrap if func is None else _wrap(func)
