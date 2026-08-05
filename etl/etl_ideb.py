# -*- coding: utf-8 -*-
"""
ETL IDEB — Painel de Dados Abertos de Sergipe (SEED/SE)
Série UF oficial + por_municipio + por_uf_estadual + rankings (mun/UF/escolas).
"""
import sys, io, os, re, json, time, shutil
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import PAINEL_DIR, IDEB_DIR  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pandas as pd
import numpy as np

SG_UF = "SE"
UF_NOME = "Sergipe"

NE_UFS = ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"]
NE_NOMES = {
    "Alagoas", "Bahia", "Ceará", "Maranhão", "Paraíba",
    "Pernambuco", "Piauí", "Rio Grande do Norte", "Sergipe",
}
# Nome planilha → SG
UF_NOME_TO_SG = {
    "Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM", "Bahia": "BA",
    "Ceará": "CE", "Distrito Federal": "DF", "Espírito Santo": "ES", "Goiás": "GO",
    "Maranhão": "MA", "Mato Grosso": "MT", "Mato Grosso do Sul": "MS", "Minas Gerais": "MG",
    "Pará": "PA", "Paraíba": "PB", "Paraná": "PR", "Pernambuco": "PE", "Piauí": "PI",
    "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN", "Rio Grande do Sul": "RS",
    "Rondônia": "RO", "Roraima": "RR", "Santa Catarina": "SC", "São Paulo": "SP",
    "Sergipe": "SE", "Tocantins": "TO",
}
UF_SG_TO_NOME = {v: k for k, v in UF_NOME_TO_SG.items()}

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
    for root, _dirs, files in os.walk(IDEB_DIR):
        if name in files:
            return os.path.join(root, name)
    raise FileNotFoundError(f"{name} nao encontrado em {IDEB_DIR}")


def load_dre_lookup():
    path = os.path.join(PAINEL_DIR, "se_dre_lookup.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("municipios") or {}


def parse_uf_sheet_obs(raw):
    """Retorna (obs_cols, data_rows) — obs_cols[ano]=idx, data a partir da linha 10."""
    codes = [str(c) for c in raw.iloc[9].tolist()]
    obs_cols = {}
    extra = {}
    for i, c in enumerate(codes):
        m = re.match(r"VL_(OBSERVADO|NOTA_MEDIA|INDICADOR_REND)_(\d{4})", c)
        if m:
            kind, ano = m.group(1), m.group(2)
            if kind == "OBSERVADO":
                obs_cols[ano] = i
            else:
                extra.setdefault(ano, {})[kind] = i
    return obs_cols, extra, raw.iloc[10:]


def carregar_oficial_todas_ufs():
    """
    oficial[rede_rotulo][sg_uf][etapa][ano] = {ideb, nota_saeb?, rendimento?}
    Também guarda linhas de macrorregião em oficial['_macro'][nome][rede][etapa][ano]
    """
    fpath = find_file(UF_OFICIAL_NAME)
    oficial = {}
    macro_data = {}
    for etapa, sheet in UF_SHEETS.items():
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
    return oficial, macro_data


def build_por_uf_estadual(oficial):
    """por_uf_estadual[ano][SG][AI|AF|EM] = ideb (number) — rede Estadual."""
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
    # SE Pública
    pub_key = "Pública" if "Pública" in oficial else ("Publica" if "Publica" in oficial else None)
    if pub_key:
        se = oficial[pub_key].get(SG_UF, {})
        for et, por_ano in se.items():
            for ano, o in por_ano.items():
                refs["se_publica"].setdefault(ano, {})[et] = o.get("ideb")

    # Brasil pública = média 5 macrorregiões (prefer Pública)
    for et in ("AI", "AF", "EM"):
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

    # Nordeste pública (linha macrorregião)
    for rede in ("Pública", "Publica", "Total"):
        ne = macro_data.get("Nordeste", {}).get(rede, {})
        if not ne:
            continue
        for et, por_ano in ne.items():
            for ano, v in por_ano.items():
                refs["nordeste_publica"].setdefault(ano, {})[et] = v
        if "Pública" in rede or "Publica" in rede:
            break

    # Nordeste estadual = média simples das 9 UFs NE (rede estadual)
    for ano, ufs in por_uf_estadual.items():
        for et in ("AI", "AF", "EM"):
            vals = [ufs[sg][et] for sg in NE_UFS if sg in ufs and ufs[sg].get(et) is not None]
            if vals:
                refs["nordeste_estadual"].setdefault(ano, {})[et] = round(float(np.mean(vals)), 2)

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
    work = df if not rede_filter else df[df["REDE"].isin(rede_filter)].copy()
    serie = {}
    for ano in cfg["anos_ideb"]:
        obs_col = f"VL_OBSERVADO_{ano}"
        nota_col = f"VL_NOTA_MEDIA_{ano}"
        rend_col = f"VL_INDICADOR_REND_{ano}"
        proj_col = f"VL_PROJECAO_{ano}" if ano in cfg["anos_proj"] else None
        if obs_col not in work.columns:
            continue
        vals_obs = work[obs_col].apply(safe_numeric)
        vals_nota = work[nota_col].apply(safe_numeric) if nota_col in work.columns else pd.Series(dtype=float, index=work.index)
        vals_rend = work[rend_col].apply(safe_numeric) if rend_col in work.columns else pd.Series(dtype=float, index=work.index)
        vals_proj = work[proj_col].apply(safe_numeric) if proj_col and proj_col in work.columns else pd.Series(dtype=float, index=work.index)
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


def build_escolas_se(raw_esc, rede_filter, dre_lookup, ano="2023"):
    """Lista de escolas SE com IDEB AI/AF/EM no ano."""
    by_id = {}
    for et, df in raw_esc.items():
        work = df if not rede_filter else df[df["REDE"].isin(rede_filter)].copy()
        obs_col = f"VL_OBSERVADO_{ano}"
        if obs_col not in work.columns:
            continue
        for _, row in work.iterrows():
            ideb = safe_numeric(row[obs_col])
            if ideb is None:
                continue
            eid = str(int(float(row["ID_ESCOLA"]))) if pd.notna(row["ID_ESCOLA"]) else None
            if not eid:
                continue
            cod_mun = str(int(float(row["CO_MUNICIPIO"])))[:7] if pd.notna(row["CO_MUNICIPIO"]) else None
            mun_info = dre_lookup.get(cod_mun) or {}
            dest = by_id.setdefault(eid, {
                "cod_escola": eid,
                "nome": str(row["NO_ESCOLA"]),
                "cod_mun": cod_mun,
                "nome_mun": str(row["NO_MUNICIPIO"]) if pd.notna(row["NO_MUNICIPIO"]) else "",
                "rede": str(row["REDE"]).strip() if pd.notna(row["REDE"]) else "",
                "dre": mun_info.get("dre") or mun_info.get("cod_dre"),
                "nome_dre": mun_info.get("nome_dre") or mun_info.get("nome_cre"),
            })
            dest[et] = round(ideb, 2)
    escolas = list(by_id.values())
    escolas.sort(key=lambda e: (-(e.get("AI") or e.get("AF") or e.get("EM") or 0), e["nome"]))
    return escolas


def build_rankings_municipios(resultado, ano="2023"):
    mun_ano = resultado.get("por_municipio", {}).get(ano, {})
    lookup = resultado.get("lookup_municipios", {})
    se_serie = resultado.get("serie_temporal", {}).get(ano, {})
    out = {"ano": int(ano), "etapas": {}}
    for et in ("AI", "AF", "EM"):
        se_ideb = (se_serie.get(et) or {}).get("ideb")
        rows = []
        for cod, vals in mun_ano.items():
            d = vals.get(et)
            if d and d.get("ideb") is not None:
                delta = round(d["ideb"] - se_ideb, 2) if se_ideb is not None else None
                rows.append({
                    "cod": cod,
                    "nome": lookup.get(cod, cod),
                    "ideb": d["ideb"],
                    "n_escolas": d.get("n_escolas"),
                    "delta_vs_se": delta,
                })
        rows.sort(key=lambda r: (-r["ideb"], r["nome"]))
        for i, r in enumerate(rows, 1):
            r["pos"] = i
        out["etapas"][et] = {
            "n": len(rows),
            "se_ideb": se_ideb,
            "top15": rows[:15],
            "bottom10": list(reversed(rows[-10:])) if len(rows) >= 10 else list(reversed(rows)),
            "todos": rows,
        }
    return out


def build_rankings_ufs(por_uf_estadual, ano="2023"):
    """Ranking UFs rede estadual + subset Nordeste, Δ vs SE."""
    ufs_ano = por_uf_estadual.get(ano) or {}
    se_vals = ufs_ano.get(SG_UF) or {}
    out = {"ano": int(ano), "rede": "Estadual", "etapas": {}, "nordeste": {"etapas": {}}}
    for et in ("AI", "AF", "EM"):
        se_ideb = se_vals.get(et)
        rows = []
        for sg, vals in ufs_ano.items():
            if vals.get(et) is None:
                continue
            delta = round(vals[et] - se_ideb, 2) if se_ideb is not None else None
            rows.append({
                "uf": sg,
                "nome": UF_SG_TO_NOME.get(sg, sg),
                "ideb": vals[et],
                "delta_vs_se": delta,
                "is_se": sg == SG_UF,
                "is_ne": sg in NE_UFS,
            })
        rows.sort(key=lambda r: (-r["ideb"], r["nome"]))
        for i, r in enumerate(rows, 1):
            r["pos"] = i
        ne_rows = [r for r in rows if r["is_ne"]]
        for i, r in enumerate(ne_rows, 1):
            r = dict(r)
            r["pos_ne"] = i
            ne_rows[i - 1] = r
        se_row = next((r for r in rows if r["is_se"]), None)
        se_ne = next((r for r in ne_rows if r["is_se"]), None)
        out["etapas"][et] = {
            "n": len(rows),
            "se_ideb": se_ideb,
            "se_pos": se_row["pos"] if se_row else None,
            "todos": rows,
        }
        out["nordeste"]["etapas"][et] = {
            "n": len(ne_rows),
            "se_ideb": se_ideb,
            "se_pos": se_ne["pos_ne"] if se_ne else None,
            "todos": ne_rows,
        }
    return out


def build_posicao_se_serie(por_uf_estadual):
    """Série temporal da posição de SE no ranking BR e NE (rede estadual)."""
    anos = sorted(por_uf_estadual.keys())
    out = {"brasil": {}, "nordeste": {}}
    for et in ("AI", "AF", "EM"):
        out["brasil"][et] = []
        out["nordeste"][et] = []
        for ano in anos:
            ufs = por_uf_estadual[ano]
            rows = [(sg, ufs[sg][et]) for sg in ufs if ufs[sg].get(et) is not None]
            rows.sort(key=lambda x: (-x[1], x[0]))
            pos = next((i + 1 for i, (sg, _) in enumerate(rows) if sg == SG_UF), None)
            out["brasil"][et].append({
                "ano": ano, "posicao": pos, "n": len(rows),
                "ideb": (ufs.get(SG_UF) or {}).get(et),
            })
            ne = [(sg, v) for sg, v in rows if sg in NE_UFS]
            ne.sort(key=lambda x: (-x[1], x[0]))
            pos_ne = next((i + 1 for i, (sg, _) in enumerate(ne) if sg == SG_UF), None)
            out["nordeste"][et].append({
                "ano": ano, "posicao": pos_ne, "n": len(ne),
                "ideb": (ufs.get(SG_UF) or {}).get(et),
            })
    return out


def main():
    t0 = time.time()
    print("=" * 60)
    print("ETL IDEB — MULTI-REDE SERGIPE (SE) + UFs/ESCOLAS")
    print("=" * 60)
    print(f"IDEB_DIR: {IDEB_DIR}")

    dre_lookup = load_dre_lookup()
    print(f"  DRE lookup: {len(dre_lookup)} municipios")

    raw_esc, raw_mun = {}, {}
    for etapa_key in ETAPAS:
        raw_esc[etapa_key] = load_esc_file(etapa_key)
        raw_mun[etapa_key] = load_mun_file(etapa_key)

    print("\n  Carregando valores oficiais (todas UFs + macros)...")
    OFICIAL, MACRO_DATA = carregar_oficial_todas_ufs()
    por_uf_estadual = build_por_uf_estadual(OFICIAL)
    REFS = build_referencias(OFICIAL, MACRO_DATA, por_uf_estadual)
    ufs_rank_base = build_rankings_ufs(por_uf_estadual, "2023")
    pos_serie = build_posicao_se_serie(por_uf_estadual)
    print(f"  por_uf_estadual anos: {sorted(por_uf_estadual.keys())}")
    print(f"  UFs 2023 AI: {ufs_rank_base['etapas']['AI']['n']} · SE pos {ufs_rank_base['etapas']['AI']['se_pos']}")

    # Lookup UFs para o front
    lookup_ufs = {sg: nome for nome, sg in UF_NOME_TO_SG.items()}

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
                    "por_municipio usa planilha oficial de municípios (AI/AF) ou média escolar (EM). "
                    "por_uf_estadual e rankings.ufs_estadual usam sempre rede Estadual oficial."
                ),
            },
            "serie_temporal": {},
            "por_municipio": {},
            "por_uf_estadual": por_uf_estadual,
            "lookup_municipios": {},
            "lookup_ufs": lookup_ufs,
            "referencias": REFS,
            "ufs_ne": NE_UFS,
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

        # Override SE série com oficial UF da rede
        rotulo = REDE_OFICIAL_MAP.get(rede_key)
        se_oficial = (OFICIAL.get(rotulo) or {}).get(SG_UF) if rotulo else None
        if se_oficial:
            n_over = 0
            for etapa_key, por_ano in se_oficial.items():
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
        escolas = build_escolas_se(raw_esc, rede_filter, dre_lookup, "2023")
        print(f"  Escolas com IDEB 2023: {len(escolas)}")

        resultado["rankings"] = {
            "ano": 2023,
            "municipios": build_rankings_municipios(resultado, "2023"),
            "ufs_estadual": ufs_rank_base,
            "posicao_se_serie": pos_serie,
            "escolas": {
                "ano": 2023,
                "n": len(escolas),
                "lista": escolas,
            },
        }

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
