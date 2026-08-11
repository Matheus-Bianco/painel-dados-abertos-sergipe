# -*- coding: utf-8 -*-
"""
ETL IDEB — Painel SEED/SE — AI + AF + EM · Rede Estadual.
Série UF oficial 2025 + por_municipio/escolas (planilhas escolas por etapa).
"""
import sys, io, os, re, json, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import PAINEL_DIR, IDEB_DIR, UF_OFICIAL_2025, REPO_ROOT  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pandas as pd
import numpy as np

SG_UF = "SE"
UF_NOME = "Sergipe"
ETAPAS = ("AI", "AF", "EM")
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
    "R. G. do Norte": "RN",
    "R. G. do Sul": "RS",
    "M. G. do Sul": "MS",
}
UF_SG_TO_NOME = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí",
    "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul",
    "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
    "SE": "Sergipe", "TO": "Tocantins",
}

ANOS_IDEB = [2005, 2007, 2009, 2011, 2013, 2015, 2017, 2019, 2021, 2023, 2025]
ETAPA_CFG = {
    "AI": {
        "file_esc": "divulgacao_anos_iniciais_escolas_2025.xlsx",
        "file_esc_fallback": "divulgacao_anos_iniciais_escolas_2023.xlsx",
        "label": "Anos Iniciais",
        "sheet_tokens": ("(AI)", " AI", "INICIAIS"),
    },
    "AF": {
        "file_esc": "divulgacao_anos_finais_escolas_2025.xlsx",
        "file_esc_fallback": "divulgacao_anos_finais_escolas_2023.xlsx",
        "label": "Anos Finais",
        "sheet_tokens": ("(AF)", " AF", "FINAIS"),
    },
    "EM": {
        "file_esc": "divulgacao_ensino_medio_escolas_2025.xlsx",
        "file_esc_fallback": "divulgacao_ensino_medio_escolas_2023.xlsx",
        "label": "Ensino Médio",
        "sheet_tokens": ("(EM)", " EM", "MÉDIO", "MEDIO"),
    },
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
    for extra in (
        local,
        r"C:\Users\mathe\OneDrive\Desktop",
        r"C:\Users\mathe\OneDrive\Desktop\Trabalhos",
    ):
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


def find_etapa_sheet(xl, etapa):
    tokens = ETAPA_CFG[etapa]["sheet_tokens"]
    names = list(xl.sheet_names)
    for s in names:
        su = s.upper()
        if any(t.upper() in su for t in tokens):
            return s
    # fallback por sigla isolada
    for s in names:
        if f"({etapa})" in s.upper() or s.upper().endswith(etapa) or f" {etapa}" in s.upper():
            return s
    raise KeyError(f"Aba UF para etapa {etapa} nao encontrada em {names}")


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


def _parse_uf_sheet_into(oficial, macro_data, fpath, sheet, etapa):
    raw = pd.read_excel(fpath, sheet_name=sheet, header=None)
    obs_cols, extra, data = parse_uf_sheet_obs(raw)
    for _, row in data.iterrows():
        nome = str(row[0]).strip()
        rede_rotulo = str(row[1]).strip().split(" ")[0]
        if nome in MACRO:
            dest = macro_data.setdefault(nome, {}).setdefault(rede_rotulo, {}).setdefault(etapa, {})
            for ano, idx in obs_cols.items():
                v = safe_numeric(row[idx])
                if v is not None:
                    dest[ano] = round(v, 2)
            continue
        sg = UF_NOME_TO_SG.get(nome)
        if not sg:
            continue
        dest = oficial.setdefault(rede_rotulo, {}).setdefault(sg, {}).setdefault(etapa, {})
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
    return obs_cols


def carregar_oficial():
    """oficial[rede][sg][et][ano] + macro_data[nome][rede][et][ano]."""
    fpath = resolve_uf_oficial_path()
    print(f"  UF oficial: {fpath}")
    xl = pd.ExcelFile(fpath)
    oficial, macro_data = {}, {}
    obs_by_et = {}
    for et in ETAPAS:
        sheet = find_etapa_sheet(xl, et)
        print(f"  Aba {et}: {sheet}")
        obs_by_et[et] = _parse_uf_sheet_into(oficial, macro_data, fpath, sheet, et)
    return oficial, macro_data, obs_by_et


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

    for et in ETAPAS:
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
        for et in ETAPAS:
            vals = [ufs[sg][et] for sg in NE_UFS if sg in ufs and ufs[sg].get(et) is not None]
            if vals:
                refs["nordeste_estadual"].setdefault(ano, {})[et] = round(float(np.mean(vals)), 2)
    return refs


def load_esc_etapa(etapa):
    cfg = ETAPA_CFG[etapa]
    try:
        fpath = find_file(cfg["file_esc"])
    except FileNotFoundError:
        fpath = find_file(cfg["file_esc_fallback"])
    print(f"  Lendo escolas {etapa} {os.path.basename(fpath)}...", end=" ", flush=True)
    df = pd.read_excel(fpath, header=9)
    df = df[df["SG_UF"].astype(str).str.strip() == SG_UF].copy()
    print(f"{len(df)} escolas SE")
    return df


def extract_serie_escolas(df, rede_filter):
    work = df[df["REDE"].isin(rede_filter)].copy()
    serie = {}
    for ano in ANOS_IDEB:
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


def extract_mun_from_esc(df, rede_filter, etapa):
    work = df[df["REDE"].isin(rede_filter)].copy()
    por_ano, lookup = {}, {}
    for ano in ANOS_IDEB:
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
            por_ano[str(ano)] = {cod: {etapa: md} for cod, md in mun_data.items()}
    return por_ano, lookup


def merge_por_municipio(base, extra):
    """Mescla por_municipio[ano][cod][etapa]."""
    for ano, muns in extra.items():
        dest_ano = base.setdefault(ano, {})
        for cod, etapas in muns.items():
            dest_ano.setdefault(cod, {}).update(etapas)
    return base


def _ano_anterior_ideb(ano):
    try:
        return str(int(ano) - 2)
    except (TypeError, ValueError):
        return None


def build_escolas(df, rede_filter, dre_lookup, ano, etapa, se_ideb=None):
    work = df[df["REDE"].isin(rede_filter)].copy()
    obs_col = f"VL_OBSERVADO_{ano}"
    if obs_col not in work.columns:
        anos = [a for a in ANOS_IDEB if f"VL_OBSERVADO_{a}" in work.columns]
        ano = str(anos[-1]) if anos else ano
        obs_col = f"VL_OBSERVADO_{ano}"
    ano_ant = _ano_anterior_ideb(ano)
    obs_ant = f"VL_OBSERVADO_{ano_ant}" if ano_ant else None
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
        ideb_ant = safe_numeric(row[obs_ant]) if obs_ant and obs_ant in work.columns else None
        delta_ant = round(ideb - ideb_ant, 2) if ideb_ant is not None else None
        delta_se = round(ideb - se_ideb, 2) if se_ideb is not None else None
        lista.append({
            "cod_escola": eid,
            "nome": str(row["NO_ESCOLA"]),
            "cod_mun": cod_mun,
            "nome_mun": str(row["NO_MUNICIPIO"]) if pd.notna(row["NO_MUNICIPIO"]) else "",
            "rede": str(row["REDE"]).strip() if pd.notna(row["REDE"]) else "",
            "dre": mun_info.get("dre") or mun_info.get("cod_dre"),
            "nome_dre": mun_info.get("nome_dre") or mun_info.get("nome_cre"),
            etapa: round(ideb, 2),
            "ideb": round(ideb, 2),
            "ideb_ant": round(ideb_ant, 2) if ideb_ant is not None else None,
            "delta_vs_ant": delta_ant,
            "delta_vs_se": delta_se,
            "ano_ant": int(ano_ant) if ano_ant and ideb_ant is not None else None,
        })
    lista.sort(key=lambda e: (-(e.get("ideb") or 0), e["nome"]))
    return lista, str(ano)


def build_rankings_municipios(resultado, ano):
    mun_ano = resultado.get("por_municipio", {}).get(ano, {})
    ano_ant = _ano_anterior_ideb(ano)
    mun_ant = resultado.get("por_municipio", {}).get(ano_ant, {}) if ano_ant else {}
    lookup = resultado.get("lookup_municipios", {})
    etapas_out = {}
    for et in ETAPAS:
        se_ideb = (resultado.get("serie_temporal", {}).get(ano, {}).get(et) or {}).get("ideb")
        rows = []
        for cod, vals in mun_ano.items():
            d = vals.get(et)
            if d and d.get("ideb") is not None:
                delta = round(d["ideb"] - se_ideb, 2) if se_ideb is not None else None
                ideb_ant = (mun_ant.get(cod) or {}).get(et, {}).get("ideb")
                delta_ant = round(d["ideb"] - ideb_ant, 2) if ideb_ant is not None else None
                rows.append({
                    "cod": cod, "nome": lookup.get(cod, cod), "ideb": d["ideb"],
                    "n_escolas": d.get("n_escolas"), "delta_vs_se": delta,
                    "ideb_ant": ideb_ant,
                    "delta_vs_ant": delta_ant,
                    "ano_ant": int(ano_ant) if ano_ant and ideb_ant is not None else None,
                })
        rows.sort(key=lambda r: (-r["ideb"], r["nome"]))
        for i, r in enumerate(rows, 1):
            r["pos"] = i
        etapas_out[et] = {
            "n": len(rows), "se_ideb": se_ideb,
            "top15": rows[:15],
            "bottom10": list(reversed(rows[-10:])) if len(rows) >= 10 else list(reversed(rows)),
            "todos": rows,
        }
    return {
        "ano": int(ano),
        "ano_ant": int(ano_ant) if ano_ant else None,
        "etapas": etapas_out,
    }


def _annotate_empates(rows, pos_key="pos", ideb_key="ideb", uf_key="uf"):
    from collections import defaultdict
    groups = defaultdict(list)
    for i, r in enumerate(rows):
        groups[r[ideb_key]].append(i)
    for idxs in groups.values():
        n = len(idxs)
        posicoes = [rows[i][pos_key] for i in idxs]
        pmin, pmax = min(posicoes), max(posicoes)
        ufs = [rows[i][uf_key] for i in idxs]
        for i in idxs:
            rows[i]["empate_n"] = n
            rows[i]["empate_com"] = n - 1
            rows[i]["posicao_min"] = pmin
            rows[i]["posicao_max"] = pmax
            rows[i]["empatados"] = [u for u in ufs if u != rows[i][uf_key]]
    return rows


def _se_empate_resumo(rows, pos_key="pos"):
    se = next((r for r in rows if r.get("is_se") or r.get("uf") == SG_UF), None)
    if not se:
        return None
    return {
        "pos": se[pos_key],
        "posicao_min": se.get("posicao_min", se[pos_key]),
        "posicao_max": se.get("posicao_max", se[pos_key]),
        "empate_n": se.get("empate_n", 1),
        "empate_com": se.get("empate_com", 0),
        "empatados": se.get("empatados") or [],
        "ideb": se.get("ideb"),
    }


def build_rankings_ufs(por_uf_estadual, ano):
    ufs_ano = por_uf_estadual.get(ano) or {}
    ano_ant = _ano_anterior_ideb(ano)
    ufs_ant = por_uf_estadual.get(ano_ant) or {} if ano_ant else {}
    etapas_out, etapas_ne = {}, {}
    for et in ETAPAS:
        se_ideb = (ufs_ano.get(SG_UF) or {}).get(et)
        rows = []
        for sg, vals in ufs_ano.items():
            if vals.get(et) is None:
                continue
            delta = round(vals[et] - se_ideb, 2) if se_ideb is not None else None
            ideb_ant = (ufs_ant.get(sg) or {}).get(et)
            delta_ant = round(vals[et] - ideb_ant, 2) if ideb_ant is not None else None
            rows.append({
                "uf": sg, "nome": UF_SG_TO_NOME.get(sg, sg), "ideb": vals[et],
                "delta_vs_se": delta, "is_se": sg == SG_UF, "is_ne": sg in NE_UFS,
                "ideb_ant": ideb_ant,
                "delta_vs_ant": delta_ant,
                "ano_ant": int(ano_ant) if ano_ant and ideb_ant is not None else None,
            })
        rows.sort(key=lambda r: (-r["ideb"], r["nome"]))
        for i, r in enumerate(rows, 1):
            r["pos"] = i
        _annotate_empates(rows, pos_key="pos")
        ne_rows = [dict(r) for r in rows if r["is_ne"]]
        for i, r in enumerate(ne_rows, 1):
            r["pos_ne"] = i
        _annotate_empates(ne_rows, pos_key="pos_ne")
        se_row = next((r for r in rows if r["is_se"]), None)
        se_ne = next((r for r in ne_rows if r["is_se"]), None)
        etapas_out[et] = {
            "n": len(rows), "se_ideb": se_ideb,
            "se_pos": se_row["pos"] if se_row else None,
            "se_empate": _se_empate_resumo(rows, "pos"),
            "todos": rows,
        }
        etapas_ne[et] = {
            "n": len(ne_rows), "se_ideb": se_ideb,
            "se_pos": se_ne["pos_ne"] if se_ne else None,
            "se_empate": _se_empate_resumo(ne_rows, "pos_ne"),
            "todos": ne_rows,
        }
    return {
        "ano": int(ano),
        "ano_ant": int(ano_ant) if ano_ant else None,
        "rede": "Estadual",
        "etapas": etapas_out,
        "nordeste": {"etapas": etapas_ne},
    }


def _empate_from_sorted_pairs(rows, sg_alvo):
    pos = next((i + 1 for i, (sg, _) in enumerate(rows) if sg == sg_alvo), None)
    if pos is None:
        return None
    ideb = next(v for sg, v in rows if sg == sg_alvo)
    grupo = [(i + 1, sg) for i, (sg, v) in enumerate(rows) if v == ideb]
    ufs = [sg for _, sg in grupo]
    return {
        "posicao": pos,
        "posicao_min": min(p for p, _ in grupo),
        "posicao_max": max(p for p, _ in grupo),
        "empate_n": len(grupo),
        "empate_com": len(grupo) - 1,
        "empatados": [sg for sg in ufs if sg != sg_alvo],
        "n": len(rows),
        "ideb": ideb,
    }


def build_posicao_se_serie(por_uf_estadual):
    anos = sorted(por_uf_estadual.keys())
    out = {"brasil": {et: [] for et in ETAPAS}, "nordeste": {et: [] for et in ETAPAS}}
    for ano in anos:
        ufs = por_uf_estadual[ano]
        for et in ETAPAS:
            rows = [(sg, ufs[sg][et]) for sg in ufs if ufs[sg].get(et) is not None]
            rows.sort(key=lambda x: (-x[1], x[0]))
            info = _empate_from_sorted_pairs(rows, SG_UF)
            if info:
                out["brasil"][et].append({"ano": ano, **info})
            ne = [(sg, v) for sg, v in rows if sg in NE_UFS]
            ne.sort(key=lambda x: (-x[1], x[0]))
            info_ne = _empate_from_sorted_pairs(ne, SG_UF)
            if info_ne:
                out["nordeste"][et].append({"ano": ano, **info_ne})
    return out


def main():
    t0 = time.time()
    print("=" * 60)
    print("ETL IDEB — SE · AI + AF + EM · Rede Estadual · 2025")
    print("=" * 60)

    dre_lookup = load_dre_lookup()

    print("\n  Carregando UF oficial (AI/AF/EM)...")
    OFICIAL, MACRO_DATA, _obs = carregar_oficial()
    por_uf = build_por_uf_estadual(OFICIAL)
    REFS = build_referencias(OFICIAL, MACRO_DATA, por_uf)
    anos_uf = sorted(por_uf.keys())
    ano_uf = anos_uf[-1] if anos_uf else "2025"
    print(f"  Anos UF: {anos_uf} · ranking em {ano_uf}")
    se_uf = (por_uf.get(ano_uf) or {}).get(SG_UF) or {}
    print(f"  SE Estadual {ano_uf}: AI={se_uf.get('AI')} AF={se_uf.get('AF')} EM={se_uf.get('EM')}")

    ufs_rank = build_rankings_ufs(por_uf, ano_uf)
    pos_serie = build_posicao_se_serie(por_uf)

    por_mun = {}
    lookup = {}
    serie_por_et = {}
    escolas_por_et = {}
    anos_mun_all = set()
    ano_esc_by_et = {}

    for et in ETAPAS:
        print(f"\n  --- Etapa {et} ---")
        df_esc = load_esc_etapa(et)
        serie_esc = extract_serie_escolas(df_esc, REDE_FILTER)
        serie_por_et[et] = serie_esc
        mun_et, lookup_et = extract_mun_from_esc(df_esc, REDE_FILTER, et)
        merge_por_municipio(por_mun, mun_et)
        lookup.update(lookup_et)
        anos_mun_all |= set(mun_et.keys())

        # placeholder — se_ideb preenchido após serie_temporal
        escolas_por_et[et] = {"df": df_esc, "serie": serie_esc}

    anos_mun = sorted(anos_mun_all)
    ano_mun = anos_mun[-1] if anos_mun else "2025"

    resultado = {
        "metadata": {
            "fonte": f"IDEB/INEP — Divulgação {ano_uf}",
            "recorte": "Rede Estadual — AI/AF/EM — Sergipe/SE",
            "uf": SG_UF,
            "etapas": list(ETAPAS),
            "rede": REDE_KEY,
            "gerado_em": pd.Timestamp.now().isoformat(),
            "formula": "IDEB = N (Nota SAEB padronizada) × P (Indicador de Rendimento)",
            "nota_metodologica": (
                "Painel da rede estadual com Anos Iniciais, Anos Finais e Ensino Médio. "
                "serie_temporal e por_uf_estadual: planilha oficial Regiões/UFs 2025. "
                f"por_municipio e ranking de escolas: planilhas de escolas por etapa (último ano: {ano_mun})."
            ),
            "serie_temporal_fonte": "INEP — divulgacao_regioes_ufs_ideb_2025 (UF e Regiões AI/AF/EM).",
        },
        "serie_temporal": {},
        "por_municipio": por_mun,
        "por_uf_estadual": por_uf,
        "lookup_municipios": lookup,
        "lookup_ufs": dict(UF_SG_TO_NOME),
        "referencias": REFS,
        "ufs_ne": NE_UFS,
    }

    for et in ETAPAS:
        serie_esc = serie_por_et[et]
        for ano, data in serie_esc.items():
            resultado["serie_temporal"].setdefault(ano, {})[et] = dict(data)

        se_oficial = (OFICIAL.get(REDE_ROTULO) or {}).get(SG_UF, {}).get(et, {})
        for ano, o in se_oficial.items():
            entry = resultado["serie_temporal"].setdefault(ano, {}).setdefault(et, {})
            entry["ideb"] = o["ideb"]
            if "nota_saeb" in o:
                entry["nota_saeb"] = o["nota_saeb"]
            if "rendimento" in o:
                entry["rendimento"] = o["rendimento"]
            entry["fonte"] = "oficial_inep_uf"
            if "n_escolas" not in entry and ano in serie_esc:
                entry["n_escolas"] = serie_esc[ano].get("n_escolas")

    # Escolas por etapa
    esc_etapas = {}
    ano_esc_max = ano_mun
    for et in ETAPAS:
        se_ideb_esc = (resultado["serie_temporal"].get(str(ano_mun), {}) or {}).get(et, {}).get("ideb")
        if se_ideb_esc is None:
            se_ideb_esc = (por_uf.get(str(ano_uf), {}) or {}).get(SG_UF, {}).get(et)
        lista, ano_esc = build_escolas(
            escolas_por_et[et]["df"], REDE_FILTER, dre_lookup, ano_mun, et, se_ideb=se_ideb_esc
        )
        ano_esc_by_et[et] = ano_esc
        if int(ano_esc) > int(ano_esc_max):
            ano_esc_max = ano_esc
        esc_etapas[et] = {
            "ano": int(ano_esc),
            "ano_ant": (lambda a: int(a) if a else None)(_ano_anterior_ideb(ano_esc)),
            "n": len(lista),
            "lista": lista,
            "se_ideb": se_ideb_esc,
        }
        print(f"  Municipios {et} ({ano_mun}): {sum(1 for m in por_mun.get(ano_mun, {}).values() if et in m)}")
        print(f"  Escolas {et} ({ano_esc}): {len(lista)}")
        pos_br = ufs_rank["etapas"][et]["se_pos"]
        pos_ne = ufs_rank["nordeste"]["etapas"][et]["se_pos"]
        print(f"  SE pos BR {et} {ano_uf}: {pos_br} · NE: {pos_ne}")

    resultado["rankings"] = {
        "ano": int(ano_uf),
        "ano_municipios": int(ano_mun),
        "ano_escolas": int(ano_esc_max),
        "municipios": build_rankings_municipios(resultado, ano_mun),
        "ufs_estadual": ufs_rank,
        "posicao_se_serie": pos_serie,
        "escolas": {
            "ano": int(ano_esc_max),
            "etapas": esc_etapas,
        },
    }

    for name in ("4_7_ideb_estadual.json", "4_7_ideb.json"):
        out = os.path.join(PAINEL_DIR, name)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False)
        print(f"  JSON: {name} ({os.path.getsize(out)/1024:.0f} KB)")

    for extra in ("municipal", "federal", "privada", "todas"):
        p = os.path.join(PAINEL_DIR, f"4_7_ideb_{extra}.json")
        if os.path.exists(p):
            os.remove(p)
            print(f"  Removido {os.path.basename(p)}")

    print(f"\nTempo total: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
