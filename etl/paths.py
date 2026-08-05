# -*- coding: utf-8 -*-
"""Caminhos do pipeline ETL — Painel de Dados Abertos de Sergipe."""
from __future__ import annotations

import os
from pathlib import Path

ETL_DIR = Path(__file__).resolve().parent
REPO_ROOT = ETL_DIR.parent
PAINEL_DIR = str(REPO_ROOT / "painel" / "dados")
BASE = str(REPO_ROOT)
BASES_DIR = str(REPO_ROOT / "00. Bases de Dados")

# Fallback: reutilizar planilhas IDEB já baixadas no projeto Joinville
_DEFAULT_IDEB = (
    Path(r"C:\Users\mathe\OneDrive\Desktop\Trabalhos\02. Joinville")
    / "25. Painel de Indicadores Abertos Joinville"
    / "04. Produto 4_Indicadores Educacionais"
    / "00. Bases de Dados"
    / "02. Fluxo e Rendimento (Inep_2010_2024_Rendimento_TDI)"
    / "02. IDEB"
)
IDEB_DIR = os.environ.get(
    "SE_IDEB_DIR",
    str(REPO_ROOT / "00. Bases de Dados" / "02. IDEB")
    if (REPO_ROOT / "00. Bases de Dados" / "02. IDEB").exists()
    and any((REPO_ROOT / "00. Bases de Dados" / "02. IDEB").rglob("*.xlsx"))
    else str(_DEFAULT_IDEB),
)

os.makedirs(PAINEL_DIR, exist_ok=True)
