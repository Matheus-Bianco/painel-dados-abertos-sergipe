# -*- coding: utf-8 -*-
"""Gera se_municipios.geojson (IBGE) e se_dre_lookup.json (INEP escolas + DePara Plurall)."""
import os, json, sys, io
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pandas as pd
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "painel" / "dados"
OUT.mkdir(parents=True, exist_ok=True)

from paths import IDEB_DIR
import gspread

SA = r"C:\Users\mathe\OneDrive\Desktop\Trabalhos\02. Joinville\03. Painel_Migrantes\service_account.json"
SID = "1ljtnetfgex0xV_E8Mtp6nxsr15013KmEHvRk3Zv0E0w"

DRE_NOMES = {
    "DEA": "Diretoria de Ensino de Aracaju",
    "DRE01": "DRE 01",
    "DRE02": "DRE 02",
    "DRE03": "DRE 03",
    "DRE04": "DRE 04",
    "DRE05": "DRE 05",
    "DRE06": "DRE 06",
    "DRE07": "DRE 07",
    "DRE08": "DRE 08",
    "DRE09": "DRE 09",
}


def find_file(name):
    for root, _d, files in os.walk(IDEB_DIR):
        if name in files:
            return os.path.join(root, name)
    raise FileNotFoundError(name)


def load_inep_dre():
    """inep -> dre from Plurall Escolas/DePara."""
    gc = gspread.service_account(filename=SA)
    sh = gc.open_by_key(SID)
    esc = sh.worksheet("Escolas").get_all_values()
    inep_dre = {}
    for row in esc[1:]:
        if len(row) < 3:
            continue
        inep = str(row[0]).replace(".0", "").strip()
        dre = str(row[2]).strip().upper()
        if inep and dre:
            inep_dre[inep] = dre
    return inep_dre


def load_escola_municipio():
    """inep -> (cod_mun, nome_mun) from IDEB escolas SE (AI+AF+EM)."""
    mapping = {}
    for fname in (
        "divulgacao_anos_iniciais_escolas_2023.xlsx",
        "divulgacao_anos_finais_escolas_2023.xlsx",
        "divulgacao_ensino_medio_escolas_2023.xlsx",
    ):
        try:
            fpath = find_file(fname)
        except FileNotFoundError:
            continue
        print(f"  Lendo {fname}...")
        df = pd.read_excel(fpath, header=9)
        df = df[df["SG_UF"].astype(str).str.strip() == "SE"]
        # coluna de código da escola
        cod_col = None
        for c in ("ID_ESCOLA", "CO_ENTIDADE", "CO_ESCOLA"):
            if c in df.columns:
                cod_col = c
                break
        if cod_col is None:
            # tentar achar
            for c in df.columns:
                if "ESCOLA" in str(c).upper() and ("CO" in str(c).upper() or "ID" in str(c).upper()):
                    cod_col = c
                    break
        print(f"    col escola={cod_col}, cols sample={list(df.columns)[:12]}")
        if cod_col is None:
            continue
        for _, row in df.iterrows():
            try:
                inep = str(int(float(row[cod_col])))
            except Exception:
                continue
            try:
                cod = str(int(float(row["CO_MUNICIPIO"])))[:7]
            except Exception:
                continue
            nome = str(row.get("NO_MUNICIPIO", "")).strip()
            if inep and cod:
                mapping[inep] = (cod, nome)
    print(f"  Escolas com municipio: {len(mapping)}")
    return mapping


def build_dre_lookup(inep_dre, inep_mun):
    mun_votes = defaultdict(list)
    mun_nome = {}
    matched = 0
    for inep, dre in inep_dre.items():
        if inep in inep_mun:
            cod, nome = inep_mun[inep]
            mun_votes[cod].append(dre)
            mun_nome[cod] = nome
            matched += 1
    print(f"  Matches inep→mun+dre: {matched}")

    lookup = {"municipios": {}, "dre_list": [], "cre_list": []}  # cre_list alias p/ app.js
    dre_muns = defaultdict(list)
    for cod, dres in mun_votes.items():
        dre = Counter(dres).most_common(1)[0][0]
        nome_dre = DRE_NOMES.get(dre, dre)
        lookup["municipios"][cod] = {
            "dre": dre,
            "nome_dre": nome_dre,
            "nome_municipio": mun_nome.get(cod, cod),
            # aliases usados pelo app UNESCO (CRE)
            "cre": dre,
            "nome_cre": nome_dre,
            "cod_cre": dre,
        }
        dre_muns[dre].append(cod)

    dre_list = []
    for dre in sorted(dre_muns.keys(), key=lambda x: (x != "DEA", x)):
        dre_list.append({
            "cod_dre": dre,
            "nome_dre": DRE_NOMES.get(dre, dre),
            "cod_cre": dre,
            "nome_cre": DRE_NOMES.get(dre, dre),
            "municipios": sorted(dre_muns[dre]),
            "n_municipios": len(dre_muns[dre]),
        })
    lookup["dre_list"] = dre_list
    lookup["cre_list"] = dre_list  # compat app.js
    return lookup


def download_municipios_geojson():
    """Malha municipal SE (IBGE) — API de localidades + geometria simplificada via Brasil API / IBGE."""
    # Usar arquivo geojson do IBGE via raw github community mirror ou API
    # Fonte estável: geojson-brazil / IBGE malhas
    url = "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-28-mun.json"
    out = OUT / "se_municipios.geojson"
    print(f"  Baixando malha municipal SE...\n  {url}")
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            raw = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"  [AVISO] Falha download ({e}). Tentando URL alternativa...")
        url2 = "https://servicodados.ibge.gov.br/api/v3/malhas/estados/28?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=municipio"
        with urllib.request.urlopen(url2, timeout=90) as r:
            raw = json.loads(r.read().decode("utf-8"))

    # Normalizar properties para o app (codarea / CD_MUN / id)
    features = []
    for feat in raw.get("features", []):
        props = feat.get("properties") or {}
        # geodata-br usa id / name / description
        cod = (
            props.get("id")
            or props.get("CD_MUN")
            or props.get("codarea")
            or props.get("codigo_ibg")
        )
        if cod is not None:
            cod = str(cod)[:7]
            if len(cod) == 6:
                cod = "0" + cod
        nome = props.get("name") or props.get("NM_MUN") or props.get("nome") or ""
        new_props = {
            "cod_mun": cod,
            "nome": nome,
            "codarea": cod,
            "CD_MUN": cod,
            "name": nome,
            "NM_MUN": nome,
        }
        features.append({"type": "Feature", "properties": new_props, "geometry": feat.get("geometry")})

    geo = {"type": "FeatureCollection", "features": features}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(geo, f, ensure_ascii=False)
    print(f"  Salvo {out.name} ({len(features)} municipios, {out.stat().st_size/1024:.0f} KB)")
    return out


def enrich_geo_and_dissolve_dres(lookup):
    """Adiciona dre ao geo municipal e gera se_dres.geojson (dissolve)."""
    try:
        import geopandas as gpd
    except ImportError:
        print("  [AVISO] geopandas indisponível — pulando dissolve de DREs")
        return

    mun_path = OUT / "se_municipios.geojson"
    mun_to = lookup.get("mun_to_cre") or {}
    gdf = gpd.read_file(mun_path)
    gdf["cod_mun"] = gdf.apply(
        lambda r: str(r.get("cod_mun") or r.get("CD_MUN") or r.get("id") or "")[:7], axis=1
    )
    gdf["nome"] = gdf.apply(
        lambda r: r.get("nome") or r.get("NM_MUN") or r.get("name") or r["cod_mun"], axis=1
    )
    gdf["dre"] = gdf["cod_mun"].map(lambda c: (mun_to.get(c) or {}).get("cod_cre"))
    gdf["nome_dre"] = gdf["cod_mun"].map(lambda c: (mun_to.get(c) or {}).get("nome_cre"))
    gdf[["cod_mun", "nome", "dre", "nome_dre", "geometry"]].to_file(mun_path, driver="GeoJSON")

    gdf_ok = gdf.dropna(subset=["dre"])
    dre = gdf_ok.dissolve(by="dre", as_index=False).rename(
        columns={"dre": "cod_cre", "nome_dre": "nome_cre"}
    )
    nome_map = {c["cod_cre"]: c["nome_cre"] for c in lookup.get("cre_list", [])}
    dre["nome_cre"] = dre["cod_cre"].map(lambda c: nome_map.get(c, c))
    out_dre = OUT / "se_dres.geojson"
    dre[["cod_cre", "nome_cre", "geometry"]].to_file(out_dre, driver="GeoJSON")
    print(f"  Salvo {out_dre.name} ({len(dre)} DREs)")


def main():
    print("=== GEO + DRE LOOKUP SE ===")
    print("1) DePara Plurall...")
    inep_dre = load_inep_dre()
    print(f"  {len(inep_dre)} escolas com DRE")
    print("2) Municipios via IDEB escolas...")
    inep_mun = load_escola_municipio()
    print("3) Montando lookup...")
    lookup = build_dre_lookup(inep_dre, inep_mun)
    # Compat app UNESCO: mun_to_cre
    if "mun_to_cre" not in lookup:
        lookup["mun_to_cre"] = {
            cod: {
                "cod_cre": info["dre"],
                "nome_cre": info["nome_dre"],
                "cod_dre": info["dre"],
                "nome_dre": info["nome_dre"],
            }
            for cod, info in lookup["municipios"].items()
        }
    if "cre_list" not in lookup and "dre_list" in lookup:
        lookup["cre_list"] = lookup["dre_list"]
    out_lookup = OUT / "se_dre_lookup.json"
    with open(out_lookup, "w", encoding="utf-8") as f:
        json.dump(lookup, f, ensure_ascii=False, indent=2)
    print(f"  Salvo {out_lookup.name}: {len(lookup['municipios'])} municipios, {len(lookup['dre_list'])} DREs")
    for d in lookup["dre_list"]:
        print(f"    {d['cod_dre']}: {d['n_municipios']} mun")

    print("4) GeoJSON municipios...")
    download_municipios_geojson()
    print("5) Dissolve DREs...")
    enrich_geo_and_dissolve_dres(lookup)
    print("OK")


if __name__ == "__main__":
    main()
