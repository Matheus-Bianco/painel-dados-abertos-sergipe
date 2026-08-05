# -*- coding: utf-8 -*-
"""
ETL IDEB — Painel de Dados Abertos de Sergipe (SEED/SE)
Série UF oficial (Regiões/UFs) + por_municipio (planilhas municípios/escolas).
"""
import sys, io, os, re, json, time, shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import PAINEL_DIR, IDEB_DIR  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pandas as pd
import numpy as np

SG_UF = "SE"
UF_NOME = "Sergipe"

ETAPAS = {
    "AI": {
        "file_esc": "divulgacao_anos_iniciais_escolas_2023.xlsx",
        "file_mun": "divulgacao_anos_iniciais_municipios_2023.xlsx",
        "label": "Anos Iniciais (5º ano)",
        "anos_ideb": [2005, 2007, 2009, 2011, 2013, 2015, 2017, 2019, 2021, 2023],
        "anos_proj": [2007, 2009, 2011, 2013, 2015, 2017, 2019, 2021],
    },
    "AF": {
        "file_esc": "divulgacao_anos_finais_escolas_2023.xlsx",
        "file_mun": "divulgacao_anos_finais_municipios_2023.xlsx",
        "label": "Anos Finais (9º ano)",
        "anos_ideb": [2005, 2007, 2009, 2011, 2013, 2015, 2017, 2019, 2021, 2023],
        "anos_proj": [2007, 2009, 2011, 2013, 2015, 2017, 2019, 2021],
    },
    "EM": {
        "file_esc": "divulgacao_ensino_medio_escolas_2023.xlsx",
        "file_mun": None,
        "label": "Ensino Médio",
        "anos_ideb": [2017, 2019, 2021, 2023],
        "anos_proj": [2019, 2021],
    },
}

REDES = {
    "estadual": ["Estadual"],
    "municipal": ["Municipal"],
    "federal": ["Federal"],
    "privada": ["Privada"],
    "todas": None,
}

UF_OFICIAL_NAME = "divulgacao_regioes_ufs_ideb_2023.xlsx"
UF_SHEETS = {"AI": "UF e Regiões (AI)", "AF": "UF e Regiões (AF)", "EM": "UF e Regiões (EM)"}
REDE_OFICIAL_MAP = {
    "estadual": "Estadual",
    "privada": "Privada",
    "todas": "Total",
    # "municipal" e "federal" não constam no agregado UF — ficam com média escolar
}


def safe_numeric(val):
    if val is None or val == "" or val == "-" or val == "ND" or val == "nd":
        return None
    try:
        v = float(val)
        return None if np.isnan(v) else v
    except (ValueError, TypeError):
        return None


def find_file(name):
    for root, _dirs, files in os.walk(IDEB_DIR):
        if name in files:
            return os.path.join(root, name)
    raise FileNotFoundError(f"{name} nao encontrado em {IDEB_DIR}")


def carregar_oficial_uf():
    """oficial[rede_rotulo][etapa][ano] = {ideb, nota_saeb?, rendimento?}"""
    fpath = find_file(UF_OFICIAL_NAME)
    oficial = {}
    for etapa, sheet in UF_SHEETS.items():
        raw = pd.read_excel(fpath, sheet_name=sheet, header=None)
        codes = [str(c) for c in raw.iloc[9].tolist()]
        col = {}
        for i, c in enumerate(codes):
            m = re.match(r"VL_(OBSERVADO|NOTA_MEDIA|INDICADOR_REND)_(\d{4})", c)
            if m:
                col.setdefault(m.group(2), {})[m.group(1)] = i
        data = raw.iloc[10:]
        se = data[data[0].astype(str).str.strip() == UF_NOME]
        for _, row in se.iterrows():
            rede_rotulo = str(row[1]).strip().split(" ")[0]
            dest = oficial.setdefault(rede_rotulo, {}).setdefault(etapa, {})
            for ano, idx in col.items():
                ideb = safe_numeric(row[idx["OBSERVADO"]]) if "OBSERVADO" in idx else None
                if ideb is None:
                    continue
                entry = {"ideb": round(ideb, 2)}
                if "NOTA_MEDIA" in idx:
                    n = safe_numeric(row[idx["NOTA_MEDIA"]])
                    if n is not None:
                        entry["nota_saeb"] = round(n, 2)
                if "INDICADOR_REND" in idx:
                    p = safe_numeric(row[idx["INDICADOR_REND"]])
                    if p is not None:
                        entry["rendimento"] = round(p, 4)
                dest[ano] = entry
    return oficial


def carregar_refs_publica(oficial):
    """Referências SE pública + Brasil (~média 5 macrorregiões) a partir da planilha UF."""
    fpath = find_file(UF_OFICIAL_NAME)
    refs = {"se_publica": {}, "brasil_publica": {}}
    # SE Pública do oficial carregado
    if "Pública" in oficial or "Publica" in oficial:
        key = "Pública" if "Pública" in oficial else "Publica"
        for etapa, por_ano in oficial[key].items():
            for ano, o in por_ano.items():
                refs["se_publica"].setdefault(ano, {})[etapa] = o.get("ideb")

    # Brasil: média das 5 macrorregiões (planilha não tem linha Brasil)
    macro = {"Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste"}
    for etapa, sheet in UF_SHEETS.items():
        raw = pd.read_excel(fpath, sheet_name=sheet, header=None)
        codes = [str(c) for c in raw.iloc[9].tolist()]
        obs_cols = {}
        for i, c in enumerate(codes):
            m = re.match(r"VL_OBSERVADO_(\d{4})", c)
            if m:
                obs_cols[m.group(1)] = i
        data = raw.iloc[10:]
        for ano, idx in obs_cols.items():
            vals = []
            for _, row in data.iterrows():
                nome = str(row[0]).strip()
                rede = str(row[1]).strip().split(" ")[0]
                if nome in macro and rede in ("Pública", "Publica", "Total"):
                    # Prefer Pública; fallback Total
                    if rede.startswith("P"):
                        v = safe_numeric(row[idx])
                        if v is not None:
                            vals.append(v)
            if not vals:
                for _, row in data.iterrows():
                    nome = str(row[0]).strip()
                    rede = str(row[1]).strip().split(" ")[0]
                    if nome in macro and rede == "Total":
                        v = safe_numeric(row[idx])
                        if v is not None:
                            vals.append(v)
            if vals:
                refs["brasil_publica"].setdefault(ano, {})[etapa] = round(float(np.mean(vals)), 2)
    return refs


def load_esc_file(etapa_key):
    cfg = ETAPAS[etapa_key]
    fpath = find_file(cfg["file_esc"])
    print(f"  Lendo escolas {cfg['file_esc']}...", end=" ", flush=True)
    df = pd.read_excel(fpath, header=9)
    df = df[df["SG_UF"].astype(str).str.strip() == SG_UF].copy()
    print(f"{len(df)} escolas SE")
    return df


def load_mun_file(etapa_key):
    cfg = ETAPAS[etapa_key]
    if not cfg.get("file_mun"):
        return None
    try:
        fpath = find_file(cfg["file_mun"])
    except FileNotFoundError:
        return None
    print(f"  Lendo municipios {cfg['file_mun']}...", end=" ", flush=True)
    df = pd.read_excel(fpath, header=9)
    df["CO_MUNICIPIO"] = df["CO_MUNICIPIO"].apply(
        lambda x: str(int(float(x)))[:7] if pd.notna(x) and str(x) not in ("", "nan") else None
    )
    df = df[df["SG_UF"].astype(str).str.strip() == SG_UF].copy()
    print(f"{len(df)} linhas SE")
    return df


def extract_etapa_escolas(df, etapa_key, rede_filter=None):
    cfg = ETAPAS[etapa_key]
    if rede_filter:
        df = df[df["REDE"].isin(rede_filter)].copy()
    serie = {}
    for ano in cfg["anos_ideb"]:
        obs_col = f"VL_OBSERVADO_{ano}"
        nota_col = f"VL_NOTA_MEDIA_{ano}"
        rend_col = f"VL_INDICADOR_REND_{ano}"
        proj_col = f"VL_PROJECAO_{ano}" if ano in cfg["anos_proj"] else None
        if obs_col not in df.columns:
            continue
        vals_obs = df[obs_col].apply(safe_numeric)
        vals_nota = df[nota_col].apply(safe_numeric) if nota_col in df.columns else pd.Series(dtype=float, index=df.index)
        vals_rend = df[rend_col].apply(safe_numeric) if rend_col in df.columns else pd.Series(dtype=float, index=df.index)
        vals_proj = df[proj_col].apply(safe_numeric) if proj_col and proj_col in df.columns else pd.Series(dtype=float, index=df.index)
        valid_idx = vals_obs.dropna().index
        n_escolas = len(valid_idx)
        if n_escolas == 0:
            continue
        entry = {
            "ideb": round(float(vals_obs.loc[valid_idx].mean()), 2),
            "nota_saeb": round(float(vals_nota.loc[valid_idx].mean()), 2) if vals_nota.loc[valid_idx].notna().sum() > 0 else None,
            "rendimento": round(float(vals_rend.loc[valid_idx].mean()), 4) if vals_rend.loc[valid_idx].notna().sum() > 0 else None,
            "n_escolas": int(n_escolas),
        }
        proj_valid = vals_proj.loc[valid_idx].dropna()
        if len(proj_valid) > 0:
            entry["meta"] = round(float(proj_valid.mean()), 2)
        serie[str(ano)] = entry
    return serie


def extract_mun_all_years_from_mun(df, etapa_key, rede_filter=None):
    """por_municipio a partir da planilha oficial de municípios."""
    cfg = ETAPAS[etapa_key]
    if df is None:
        return {}, {}
    work = df.copy()
    if rede_filter:
        work = work[work["REDE"].astype(str).str.strip().isin(rede_filter)].copy()
    por_ano, lookup = {}, {}
    for ano in cfg["anos_ideb"]:
        obs_col = f"VL_OBSERVADO_{ano}"
        proj_col = f"VL_PROJECAO_{ano}" if ano in cfg["anos_proj"] else None
        if obs_col not in work.columns:
            continue
        work["_ideb"] = work[obs_col].apply(safe_numeric)
        valid = work[work["_ideb"].notna() & work["CO_MUNICIPIO"].notna()].copy()
        if len(valid) == 0:
            continue
        mun_data = {}
        for cod, grp in valid.groupby("CO_MUNICIPIO"):
            cod_str = str(cod)[:7]
            nome = str(grp["NO_MUNICIPIO"].iloc[0])
            lookup[cod_str] = nome
            entry = {"ideb": round(float(grp["_ideb"].iloc[0]), 2), "n_escolas": 1}
            if proj_col and proj_col in grp.columns:
                meta = safe_numeric(grp[proj_col].iloc[0])
                if meta is not None:
                    entry["meta"] = round(meta, 2)
            mun_data[cod_str] = entry
        if mun_data:
            por_ano[str(ano)] = mun_data
    return por_ano, lookup


def extract_mun_all_years_from_esc(df, etapa_key, rede_filter=None):
    cfg = ETAPAS[etapa_key]
    work = df.copy()
    if rede_filter:
        work = work[work["REDE"].isin(rede_filter)].copy()
    por_ano, lookup = {}, {}
    for ano in cfg["anos_ideb"]:
        obs_col = f"VL_OBSERVADO_{ano}"
        if obs_col not in work.columns:
            continue
        work["_ideb"] = work[obs_col].apply(safe_numeric)
        valid = work[work["_ideb"].notna()].copy()
        if len(valid) == 0:
            continue
        mun_data = {}
        for cod, grp in valid.groupby("CO_MUNICIPIO"):
            cod_str = str(int(cod))[:7]
            nome = grp["NO_MUNICIPIO"].iloc[0]
            lookup[cod_str] = nome
            mun_data[cod_str] = {
                "ideb": round(float(grp["_ideb"].mean()), 2),
                "n_escolas": len(grp),
            }
        if mun_data:
            por_ano[str(ano)] = mun_data
    return por_ano, lookup


def build_rankings_se(resultado, ano="2023"):
    """Ranking de municípios SE no ano (AI/AF/EM)."""
    mun_ano = resultado.get("por_municipio", {}).get(ano, {})
    lookup = resultado.get("lookup_municipios", {})
    out = {"ano": int(ano), "etapas": {}}
    for et in ("AI", "AF", "EM"):
        rows = []
        for cod, vals in mun_ano.items():
            d = vals.get(et)
            if d and d.get("ideb") is not None:
                rows.append({
                    "cod": cod,
                    "nome": lookup.get(cod, cod),
                    "ideb": d["ideb"],
                    "n_escolas": d.get("n_escolas"),
                })
        rows.sort(key=lambda r: (-r["ideb"], r["nome"]))
        for i, r in enumerate(rows, 1):
            r["pos"] = i
        out["etapas"][et] = {
            "n": len(rows),
            "top15": rows[:15],
            "bottom10": list(reversed(rows[-10:])) if len(rows) >= 10 else list(reversed(rows)),
            "todos": rows,
        }
    return out


def main():
    t0 = time.time()
    print("=" * 60)
    print("ETL IDEB — MULTI-REDE SERGIPE (SE)")
    print("=" * 60)
    print(f"IDEB_DIR: {IDEB_DIR}")

    raw_esc, raw_mun = {}, {}
    for etapa_key in ETAPAS:
        raw_esc[etapa_key] = load_esc_file(etapa_key)
        raw_mun[etapa_key] = load_mun_file(etapa_key)

    print("\n  Carregando valores oficiais agregados (Regioes/UFs)...")
    OFICIAL = carregar_oficial_uf()
    if OFICIAL:
        print(f"  Redes oficiais SE: {sorted(OFICIAL.keys())}")
    REFS = carregar_refs_publica(OFICIAL)

    for rede_key, rede_filter in REDES.items():
        print(f"\n{'=' * 60}\n  REDE: {rede_key.upper()}\n{'=' * 60}")
        resultado = {
            "metadata": {
                "fonte": "IDEB/INEP — Divulgação 2023",
                "recorte": f"Rede {rede_key.title()} — Sergipe/SE",
                "uf": SG_UF,
                "gerado_em": pd.Timestamp.now().isoformat(),
                "formula": "IDEB = N (Nota SAEB padronizada) × P (Indicador de Rendimento)",
                "nota_metodologica": (
                    "serie_temporal usa valores oficiais UF/rede do INEP quando disponíveis. "
                    "por_municipio usa planilha oficial de municípios (AI/AF) ou média escolar (EM)."
                ),
            },
            "serie_temporal": {},
            "por_municipio": {},
            "lookup_municipios": {},
            "referencias": REFS,
        }
        all_lookup = {}

        for etapa_key in ETAPAS:
            df_esc = raw_esc[etapa_key]
            serie = extract_etapa_escolas(df_esc, etapa_key, rede_filter)
            for ano, data in serie.items():
                resultado["serie_temporal"].setdefault(ano, {})[etapa_key] = data

            df_mun = raw_mun[etapa_key]
            if df_mun is not None:
                por_ano, lookup = extract_mun_all_years_from_mun(df_mun, etapa_key, rede_filter)
            else:
                por_ano, lookup = extract_mun_all_years_from_esc(df_esc, etapa_key, rede_filter)
            all_lookup.update(lookup)
            for ano, mun_data in por_ano.items():
                resultado["por_municipio"].setdefault(ano, {})
                for cod, md in mun_data.items():
                    resultado["por_municipio"][ano].setdefault(cod, {})[etapa_key] = md

            anos_disp = sorted(serie.keys())
            if anos_disp:
                d = serie[anos_disp[-1]]
                print(f"  {etapa_key}: IDEB {anos_disp[-1]} = {d['ideb']} ({d.get('n_escolas')} esc) [pre-override]")

        rotulo = REDE_OFICIAL_MAP.get(rede_key)
        if rotulo and rotulo in OFICIAL:
            n_over = 0
            for etapa_key, por_ano in OFICIAL[rotulo].items():
                for ano, o in por_ano.items():
                    entry = resultado["serie_temporal"].setdefault(ano, {}).setdefault(etapa_key, {})
                    entry["ideb"] = o["ideb"]
                    if "nota_saeb" in o:
                        entry["nota_saeb"] = o["nota_saeb"]
                    if "rendimento" in o:
                        entry["rendimento"] = o["rendimento"]
                    entry["fonte"] = "oficial_inep_uf"
                    n_over += 1
            resultado["metadata"]["serie_temporal_fonte"] = (
                "Valores oficiais agregados por UF/rede (INEP — divulgacao_regioes_ufs_ideb_2023)."
            )
            print(f"  [OVERRIDE OFICIAL] {n_over} valores (rotulo '{rotulo}')")
        else:
            resultado["metadata"]["serie_temporal_fonte"] = (
                "Sem agregado oficial UF para esta rede; serie_temporal = media dos IDEBs das escolas."
            )
            print(f"  [SEM OVERRIDE] rede '{rede_key}'")

        resultado["lookup_municipios"] = all_lookup
        resultado["rankings"] = build_rankings_se(resultado, "2023")

        out_json = os.path.join(PAINEL_DIR, f"4_7_ideb_{rede_key}.json")
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False)
        print(f"  JSON: {os.path.basename(out_json)} ({os.path.getsize(out_json)/1024:.0f} KB)")

    src = os.path.join(PAINEL_DIR, "4_7_ideb_estadual.json")
    dst = os.path.join(PAINEL_DIR, "4_7_ideb.json")
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print("\n[COMPAT] Copiado -> 4_7_ideb.json")
    print(f"\nTempo total: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
