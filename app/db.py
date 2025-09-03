# app/db.py — shim para expor o db.py da raiz ao import "db"
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .../Matupiri_v1
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Reexporta tudo do db.py da raiz
from db import *  # noqa: F401,F403