# -*- coding: utf-8 -*-
"""
ETL IDEB — Painel SEED/SE — recorte Ensino Médio + Rede Estadual.
Série UF oficial 2025 + por_municipio/escolas (planilha escolas EM até 2023).
"""
import sys, io, os, re, json, time, shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import PAINEL_DIR, IDEB_DIR, UF_OFICIAL_2025, REPO_ROOT  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pandas as pd
import numpy as np

SG_UF = "SE"
UF_NOME = "Sergipe"
ETAPA = "EM"
REDE_KEY = "estadual"
REDE_FILTER = ["Estadual"]
REDE_ROTULO = "Estadual"

NE_UFS = ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"]
UF_NOME_TO_SG = {
    "Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM", "Bahia": "BA",
    "Ceará": "CE", "Distrito Federal": "DF", "Espírito Santo": "ES", "Goiás": "GO",
    "Maranhão": "MA", "Mato Grosso": "MT", "Mato Grosso do Sul": "MS", "Minas Gerais": "MG",
    "Pará": "PA", "Paraíba": "PB", "Paraná": "PR", "Pernambuco": "PE", "Piauí": "PI",
    "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN", "Rio Grande do Sul": "RS",
    "Rondônia": "RO", "Roraima": "RR", "Santa Catarina": "SC", "São Paulo": "SP",
    "Sergipe": "SE", "Tocantins": "TO",
    # Abreviações usadas na planilha oficial INEP (UF e Regiões)
    "R. G. do Norte": "RN",
    "R. G. do Sul": "RS",
    "M. G. do Sul": "MS",
}
# Nome canônico para exibição (ignora aliases abreviados)
UF_SG_TO_NOME = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí",
    "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul",
    "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
    "SE": "Sergipe", "TO": "Tocantins",
}

EM_CFG = {
    "file_esc": "divulgacao_ensino_medio_escolas_2025.xlsx",
    "file_esc_fallback": "divulgacao_ensino_medio_escolas_2023.xlsx",
    "label": "Ensino Médio",
    "anos_ideb": [2005, 2007, 2009, 2011, 2013, 2015, 2017, 2019, 2021, 2023, 2025],
    "anos_proj": [2019, 2021, 2023],
}
MACRO = {"Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste"}


def safe_numeric(val):
    if val is None or val == "" or val == "-" or val == "ND" or val == "nd":
        return None
    try:
        v = float(val)
        return None if np.isnan(v) else v
    except (ValueError, TypeError):
        return None


def find_file(name):
    search_roots = [IDEB_DIR]
    local = str(REPO_ROOT / "00. Bases de Dados" / "02. IDEB")
    for extra in (local, r"C:\Users\mathe\OneDrive\Desktop"):
        if extra not in search_roots and os.path.isdir(extra):
            search_roots.append(extra)
    for base in search_roots:
        for root, _dirs, files in os.walk(base):
            if name in files:
                return os.path.join(root, name)
    raise FileNotFoundError(f"{name} nao encontrado em {search_roots}")


def resolve_uf_oficial_path():
    if UF_OFICIAL_2025 and os.path.exists(UF_OFICIAL_2025):
        return UF_OFICIAL_2025
    return find_file("divulgacao_regioes_ufs_ideb_2025.xlsx")


def find_em_sheet(xl):
    for s in xl.sheet_names:
        if "EM" in s.upper() or "M" in s.upper() and "ENSINO" in s.upper():
            if "EM" in s.upper() or "(EM)" in s.upper() or "Médio" in s or "Medio" in s:
                return s
    for s in xl.sheet_names:
        if "EM" in s.upper():
            return s
    return xl.sheet_names[-1]


def load_dre_lookup():
    path = os.path.join(PAINEL_DIR, "se_dre_lookup.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("municipios") or {}


def parse_uf_sheet_obs(raw):
    codes = [str(c) for c in raw.iloc[9].tolist()]
    obs_cols, extra = {}, {}
    for i, c in enumerate(codes):
        m = re.match(r"VL_(OBSERVADO|NOTA_MEDIA|INDICADOR_REND)_(\d{4})", c)
        if m:
            kind, ano = m.group(1), m.group(2)
            if kind == "OBSERVADO":
                obs_cols[ano] = i
            else:
                extra.setdefault(ano, {})[kind] = i
    return obs_cols, extra, raw.iloc[10:]


def carregar_oficial_em():
    """oficial[rede][sg][EM][ano] + macro_data[nome][rede][EM][ano]."""
    fpath = resolve_uf_oficial_path()
    print(f"  UF oficial: {fpath}")
    xl = pd.ExcelFile(fpath)
    sheet = find_em_sheet(xl)
    print(f"  Aba: {sheet}")
    raw = pd.read_excel(fpath, sheet_name=sheet, header=None)
    obs_cols, extra, data = parse_uf_sheet_obs(raw)
    oficial, macro_data = {}, {}
    for _, row in data.iterrows():
        nome = str(row[0]).strip()
        rede_rotulo = str(row[1]).strip().split(" ")[0]
        if nome in MACRO:
            dest = macro_data.setdefault(nome, {}).setdefault(rede_rotulo, {}).setdefault(ETAPA, {})
            for ano, idx in obs_cols.items():
                v = safe_numeric(row[idx])
                if v is not None:
                    dest[ano] = round(v, 2)
            continue
        sg = UF_NOME_TO_SG.get(nome)
        if not sg:
            continue
        dest = oficial.setdefault(rede_rotulo, {}).setdefault(sg, {}).setdefault(ETAPA, {})
        for ano, idx in obs_cols.items():
            ideb = safe_numeric(row[idx])
            if ideb is None:
                continue
            entry = {"ideb": round(ideb, 2)}
            if ano in extra:
                if "NOTA_MEDIA" in extra[ano]:
                    n = safe_numeric(row[extra[ano]["NOTA_MEDIA"]])
                    if n is not None:
                        entry["nota_saeb"] = round(n, 2)
                if "INDICADOR_REND" in extra[ano]:
                    p = safe_numeric(row[extra[ano]["INDICADOR_REND"]])
                    if p is not None:
                        entry["rendimento"] = round(p, 4)
            dest[ano] = entry
    return oficial, macro_data, obs_cols


def build_por_uf_estadual(oficial):
    out = {}
    est = oficial.get("Estadual") or {}
    for sg, etapas in est.items():
        for et, por_ano in etapas.items():
            for ano, entry in por_ano.items():
                out.setdefault(ano, {}).setdefault(sg, {})[et] = entry.get("ideb")
    return out


def build_referencias(oficial, macro_data, por_uf_estadual):
    refs = {
        "se_publica": {},
        "brasil_publica": {},
        "nordeste_publica": {},
        "nordeste_estadual": {},
    }
    pub_key = "Pública" if "Pública" in oficial else ("Publica" if "Publica" in oficial else None)
    if pub_key:
        se = oficial[pub_key].get(SG_UF, {})
        for et, por_ano in se.items():
            for ano, o in por_ano.items():
                refs["se_publica"].setdefault(ano, {})[et] = o.get("ideb")

    for et in (ETAPA,):
        anos = set()
        for mnome in MACRO:
            for rede in ("Pública", "Publica", "Total"):
                anos |= set((macro_data.get(mnome, {}).get(rede, {}).get(et) or {}).keys())
        for ano in anos:
            vals = []
            for mnome in MACRO:
                v = (macro_data.get(mnome, {}).get("Pública") or macro_data.get(mnome, {}).get("Publica") or {}).get(et, {}).get(ano)
                if v is None:
                    v = macro_data.get(mnome, {}).get("Total", {}).get(et, {}).get(ano)
                if v is not None:
                    vals.append(v)
            if vals:
                refs["brasil_publica"].setdefault(ano, {})[et] = round(float(np.mean(vals)), 2)

    for rede in ("Pública", "Publica", "Total"):
        ne = macro_data.get("Nordeste", {}).get(rede, {})
        if not ne:
            continue
        for et, por_ano in ne.items():
            for ano, v in por_ano.items():
                refs["nordeste_publica"].setdefault(ano, {})[et] = v
        if rede.startswith("P"):
            break

    for ano, ufs in por_uf_estadual.items():
        vals = [ufs[sg][ETAPA] for sg in NE_UFS if sg in ufs and ufs[sg].get(ETAPA) is not None]
        if vals:
            refs["nordeste_estadual"].setdefault(ano, {})[ETAPA] = round(float(np.mean(vals)), 2)
    return refs


def load_esc_em():
    try:
        fpath = find_file(EM_CFG["file_esc"])
    except FileNotFoundError:
        fpath = find_file(EM_CFG["file_esc_fallback"])
    print(f"  Lendo escolas {os.path.basename(fpath)}...", end=" ", flush=True)
    df = pd.read_excel(fpath, header=9)
    df = df[df["SG_UF"].astype(str).str.strip() == SG_UF].copy()
    print(f"{len(df)} escolas SE")
    return df


def extract_serie_escolas(df, rede_filter):
    work = df[df["REDE"].isin(rede_filter)].copy()
    serie = {}
    for ano in EM_CFG["anos_ideb"]:
        obs_col = f"VL_OBSERVADO_{ano}"
        if obs_col not in work.columns:
            continue
        vals = work[obs_col].apply(safe_numeric).dropna()
        if len(vals) == 0:
            continue
        nota_col, rend_col = f"VL_NOTA_MEDIA_{ano}", f"VL_INDICADOR_REND_{ano}"
        entry = {
            "ideb": round(float(vals.mean()), 2),
            "n_escolas": int(len(vals)),
        }
        if nota_col in work.columns:
            n = work.loc[vals.index, nota_col].apply(safe_numeric).dropna()
            if len(n):
                entry["nota_saeb"] = round(float(n.mean()), 2)
        if rend_col in work.columns:
            p = work.loc[vals.index, rend_col].apply(safe_numeric).dropna()
            if len(p):
                entry["rendimento"] = round(float(p.mean()), 4)
        serie[str(ano)] = entry
    return serie


def extract_mun_from_esc(df, rede_filter):
    work = df[df["REDE"].isin(rede_filter)].copy()
    por_ano, lookup = {}, {}
    for ano in EM_CFG["anos_ideb"]:
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
            nome = str(grp["NO_MUNICIPIO"].iloc[0])
            lookup[cod_str] = nome
            mun_data[cod_str] = {
                "ideb": round(float(grp["_ideb"].mean()), 2),
                "n_escolas": len(grp),
            }
        if mun_data:
            por_ano[str(ano)] = {cod: {ETAPA: md} for cod, md in mun_data.items()}
    return por_ano, lookup


def build_escolas(df, rede_filter, dre_lookup, ano):
    work = df[df["REDE"].isin(rede_filter)].copy()
    obs_col = f"VL_OBSERVADO_{ano}"
    if obs_col not in work.columns:
        # fallback último ano disponível
        anos = [a for a in EM_CFG["anos_ideb"] if f"VL_OBSERVADO_{a}" in work.columns]
        ano = str(anos[-1]) if anos else ano
        obs_col = f"VL_OBSERVADO_{ano}"
    lista = []
    for _, row in work.iterrows():
        ideb = safe_numeric(row[obs_col]) if obs_col in work.columns else None
        if ideb is None:
            continue
        eid = str(int(float(row["ID_ESCOLA"]))) if pd.notna(row["ID_ESCOLA"]) else None
        if not eid:
            continue
        cod_mun = str(int(float(row["CO_MUNICIPIO"])))[:7] if pd.notna(row["CO_MUNICIPIO"]) else None
        mun_info = dre_lookup.get(cod_mun) or {}
        lista.append({
            "cod_escola": eid,
            "nome": str(row["NO_ESCOLA"]),
            "cod_mun": cod_mun,
            "nome_mun": str(row["NO_MUNICIPIO"]) if pd.notna(row["NO_MUNICIPIO"]) else "",
            "rede": str(row["REDE"]).strip() if pd.notna(row["REDE"]) else "",
            "dre": mun_info.get("dre") or mun_info.get("cod_dre"),
            "nome_dre": mun_info.get("nome_dre") or mun_info.get("nome_cre"),
            "EM": round(ideb, 2),
        })
    lista.sort(key=lambda e: (-(e.get("EM") or 0), e["nome"]))
    return lista, str(ano)


def build_rankings_municipios(resultado, ano):
    mun_ano = resultado.get("por_municipio", {}).get(ano, {})
    lookup = resultado.get("lookup_municipios", {})
    se_ideb = (resultado.get("serie_temporal", {}).get(ano, {}).get(ETAPA) or {}).get("ideb")
    rows = []
    for cod, vals in mun_ano.items():
        d = vals.get(ETAPA)
        if d and d.get("ideb") is not None:
            delta = round(d["ideb"] - se_ideb, 2) if se_ideb is not None else None
            rows.append({
                "cod": cod, "nome": lookup.get(cod, cod), "ideb": d["ideb"],
                "n_escolas": d.get("n_escolas"), "delta_vs_se": delta,
            })
    rows.sort(key=lambda r: (-r["ideb"], r["nome"]))
    for i, r in enumerate(rows, 1):
        r["pos"] = i
    return {
        "ano": int(ano),
        "etapas": {
            ETAPA: {
                "n": len(rows), "se_ideb": se_ideb,
                "top15": rows[:15],
                "bottom10": list(reversed(rows[-10:])) if len(rows) >= 10 else list(reversed(rows)),
                "todos": rows,
            }
        },
    }


def build_rankings_ufs(por_uf_estadual, ano):
    ufs_ano = por_uf_estadual.get(ano) or {}
    se_ideb = (ufs_ano.get(SG_UF) or {}).get(ETAPA)
    rows = []
    for sg, vals in ufs_ano.items():
        if vals.get(ETAPA) is None:
            continue
        delta = round(vals[ETAPA] - se_ideb, 2) if se_ideb is not None else None
        rows.append({
            "uf": sg, "nome": UF_SG_TO_NOME.get(sg, sg), "ideb": vals[ETAPA],
            "delta_vs_se": delta, "is_se": sg == SG_UF, "is_ne": sg in NE_UFS,
        })
    rows.sort(key=lambda r: (-r["ideb"], r["nome"]))
    for i, r in enumerate(rows, 1):
        r["pos"] = i
    ne_rows = []
    for r in rows:
        if r["is_ne"]:
            ne_rows.append(dict(r))
    for i, r in enumerate(ne_rows, 1):
        r["pos_ne"] = i
    se_row = next((r for r in rows if r["is_se"]), None)
    se_ne = next((r for r in ne_rows if r["is_se"]), None)
    bloco = {
        "n": len(rows), "se_ideb": se_ideb,
        "se_pos": se_row["pos"] if se_row else None, "todos": rows,
    }
    bloco_ne = {
        "n": len(ne_rows), "se_ideb": se_ideb,
        "se_pos": se_ne["pos_ne"] if se_ne else None, "todos": ne_rows,
    }
    return {
        "ano": int(ano), "rede": "Estadual",
        "etapas": {ETAPA: bloco},
        "nordeste": {"etapas": {ETAPA: bloco_ne}},
    }


def build_posicao_se_serie(por_uf_estadual):
    anos = sorted(por_uf_estadual.keys())
    out = {"brasil": {ETAPA: []}, "nordeste": {ETAPA: []}}
    for ano in anos:
        ufs = por_uf_estadual[ano]
        rows = [(sg, ufs[sg][ETAPA]) for sg in ufs if ufs[sg].get(ETAPA) is not None]
        rows.sort(key=lambda x: (-x[1], x[0]))
        pos = next((i + 1 for i, (sg, _) in enumerate(rows) if sg == SG_UF), None)
        out["brasil"][ETAPA].append({
            "ano": ano, "posicao": pos, "n": len(rows),
            "ideb": (ufs.get(SG_UF) or {}).get(ETAPA),
        })
        ne = [(sg, v) for sg, v in rows if sg in NE_UFS]
        ne.sort(key=lambda x: (-x[1], x[0]))
        pos_ne = next((i + 1 for i, (sg, _) in enumerate(ne) if sg == SG_UF), None)
        out["nordeste"][ETAPA].append({
            "ano": ano, "posicao": pos_ne, "n": len(ne),
            "ideb": (ufs.get(SG_UF) or {}).get(ETAPA),
        })
    return out


def main():
    t0 = time.time()
    print("=" * 60)
    print("ETL IDEB — SE · Ensino Médio · Rede Estadual · 2025")
    print("=" * 60)

    dre_lookup = load_dre_lookup()
    df_esc = load_esc_em()

    print("\n  Carregando UF oficial EM...")
    OFICIAL, MACRO_DATA, obs_cols = carregar_oficial_em()
    por_uf = build_por_uf_estadual(OFICIAL)
    REFS = build_referencias(OFICIAL, MACRO_DATA, por_uf)
    anos_uf = sorted(por_uf.keys())
    ano_uf = anos_uf[-1] if anos_uf else "2025"
    print(f"  Anos UF: {anos_uf} · ranking em {ano_uf}")
    print(f"  SE Estadual {ano_uf}: {(por_uf.get(ano_uf) or {}).get(SG_UF, {}).get(ETAPA)}")

    ufs_rank = build_rankings_ufs(por_uf, ano_uf)
    pos_serie = build_posicao_se_serie(por_uf)

    serie_esc = extract_serie_escolas(df_esc, REDE_FILTER)
    por_mun, lookup = extract_mun_from_esc(df_esc, REDE_FILTER)
    anos_mun = sorted(por_mun.keys())
    ano_mun = anos_mun[-1] if anos_mun else "2023"

    resultado = {
        "metadata": {
            "fonte": f"IDEB/INEP — Divulgação {ano_uf}",
            "recorte": "Rede Estadual — Ensino Médio — Sergipe/SE",
            "uf": SG_UF,
            "etapa": ETAPA,
            "rede": REDE_KEY,
            "gerado_em": pd.Timestamp.now().isoformat(),
            "formula": "IDEB = N (Nota SAEB padronizada) × P (Indicador de Rendimento)",
            "nota_metodologica": (
                "Painel restrito ao Ensino Médio da rede estadual. "
                "serie_temporal e por_uf_estadual: planilha oficial Regiões/UFs 2025. "
                f"por_municipio e ranking de escolas: planilha de escolas EM (último ano disponível: {ano_mun})."
            ),
            "serie_temporal_fonte": "INEP — divulgacao_regioes_ufs_ideb_2025 (UF e Regiões EM).",
        },
        "serie_temporal": {},
        "por_municipio": por_mun,
        "por_uf_estadual": por_uf,
        "lookup_municipios": lookup,
        "lookup_ufs": dict(UF_SG_TO_NOME),
        "referencias": REFS,
        "ufs_ne": NE_UFS,
    }

    # série a partir das escolas (n_escolas) + override oficial
    for ano, data in serie_esc.items():
        resultado["serie_temporal"].setdefault(ano, {})[ETAPA] = data

    se_oficial = (OFICIAL.get(REDE_ROTULO) or {}).get(SG_UF, {}).get(ETAPA, {})
    for ano, o in se_oficial.items():
        entry = resultado["serie_temporal"].setdefault(ano, {}).setdefault(ETAPA, {})
        entry["ideb"] = o["ideb"]
        if "nota_saeb" in o:
            entry["nota_saeb"] = o["nota_saeb"]
        if "rendimento" in o:
            entry["rendimento"] = o["rendimento"]
        entry["fonte"] = "oficial_inep_uf"
        if "n_escolas" not in entry and ano in serie_esc:
            entry["n_escolas"] = serie_esc[ano].get("n_escolas")

    # Preencher anos oficiais sem escolas
    for ano, o in se_oficial.items():
        if ano not in resultado["serie_temporal"] or ETAPA not in resultado["serie_temporal"][ano]:
            resultado["serie_temporal"].setdefault(ano, {})[ETAPA] = {**o, "fonte": "oficial_inep_uf"}

    escolas, ano_esc = build_escolas(df_esc, REDE_FILTER, dre_lookup, ano_mun)
    print(f"  Municipios EM ({ano_mun}): {len(por_mun.get(ano_mun, {}))}")
    print(f"  Escolas EM ({ano_esc}): {len(escolas)}")
    print(f"  SE pos BR {ano_uf}: {ufs_rank['etapas'][ETAPA]['se_pos']} · NE: {ufs_rank['nordeste']['etapas'][ETAPA]['se_pos']}")

    resultado["rankings"] = {
        "ano": int(ano_uf),
        "ano_municipios": int(ano_mun),
        "ano_escolas": int(ano_esc),
        "municipios": build_rankings_municipios(resultado, ano_mun),
        "ufs_estadual": ufs_rank,
        "posicao_se_serie": pos_serie,
        "escolas": {"ano": int(ano_esc), "n": len(escolas), "lista": escolas},
    }

    for name in ("4_7_ideb_estadual.json", "4_7_ideb.json"):
        out = os.path.join(PAINEL_DIR, name)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False)
        print(f"  JSON: {name} ({os.path.getsize(out)/1024:.0f} KB)")

    # Remover JSONs de outras redes (painel só estadual)
    for extra in ("municipal", "federal", "privada", "todas"):
        p = os.path.join(PAINEL_DIR, f"4_7_ideb_{extra}.json")
        if os.path.exists(p):
            os.remove(p)
            print(f"  Removido {os.path.basename(p)}")

    print(f"\nTempo total: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
