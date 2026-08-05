# -*- coding: utf-8 -*-
"""Caminhos do pipeline ETL — Painel de Dados Abertos de Sergipe."""
from __future__ import annotations

import os
from pathlib import Path

ETL_DIR = Path(__file__).resolve().parent
REPO_ROOT = ETL_DIR.parent
PAINEL_DIR = str(REPO_ROOT / "painel" / "dados")
BASE = str(REPO_ROOT)
# export Path for ETL helpers
__all__ = []  # noqa — imports by name
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
_LOCAL_IDEB = REPO_ROOT / "00. Bases de Dados" / "02. IDEB"
# Preferir pasta Joinville (planilhas escolas/municípios) se a local só tiver o arquivo UF 2025
_has_escolas = any(_LOCAL_IDEB.rglob("*escolas*.xlsx")) if _LOCAL_IDEB.exists() else False
IDEB_DIR = os.environ.get(
    "SE_IDEB_DIR",
    str(_LOCAL_IDEB) if _has_escolas else str(_DEFAULT_IDEB),
)

# Planilha oficial Regiões/UFs 2025 (preferida) — Desktop ou pasta local do projeto
_UF_2025_CANDIDATES = [
    REPO_ROOT / "00. Bases de Dados" / "02. IDEB" / "divulgacao_regioes_ufs_ideb_2025.xlsx",
    Path(r"C:\Users\mathe\OneDrive\Desktop\divulgacao_regioes_ufs_ideb_2025.xlsx"),
]
UF_OFICIAL_2025 = next((str(p) for p in _UF_2025_CANDIDATES if p.exists()), None)

os.makedirs(PAINEL_DIR, exist_ok=True)
os.makedirs(REPO_ROOT / "00. Bases de Dados" / "02. IDEB", exist_ok=True)
