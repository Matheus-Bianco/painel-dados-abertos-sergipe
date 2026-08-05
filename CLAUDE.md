# Painel de Dados Abertos — Educação Sergipe (SEED)

Painel estático (HTML/CSS/JS) com GitHub Pages. Recorte: **IDEB Ensino Médio · Rede Estadual · Sergipe**, com dados UF oficiais **2025**. Abre direto na aba IDEB (sem home). Template UNESCO/RS + rankings estilo Joinville.

## Estrutura

```
22. Painel de Dados Abertos de Sergipe/
├── CLAUDE.md
├── .github/workflows/deploy.yml   # Pages a partir de painel/
├── etl/
│   ├── paths.py
│   ├── etl_ideb.py                # gera 4_7_ideb_*.json
│   └── gerar_geo_dre.py           # se_municipios + se_dres + se_dre_lookup
├── 00. Bases de Dados/02. IDEB/   # xlsx INEP (opcional; fallback no paths.py)
└── painel/                        # site publicado
    ├── index.html
    ├── css/styles.css
    ├── js/
    │   ├── app.js                 # SE_MODE = true
    │   └── ideb_se_rankings.js    # rankings mun/UF/escolas + overlays
    ├── img/
    └── dados/
```

## Repo e URL

- GitHub (atual): `Matheus-Bianco/painel-dados-abertos-sergipe`  
  https://github.com/Matheus-Bianco/painel-dados-abertos-sergipe  
  Pages: https://matheus-bianco.github.io/painel-dados-abertos-sergipe/
- Alvo org: `gasefgv/painel-dados-abertos-sergipe` (transferir quando houver permissão de criar repo na org)
- Pages: artifact = pasta `painel/` (workflow em push na `main`)

## Schema IDEB (`4_7_ideb_*.json`)

Além de `serie_temporal`, `por_municipio`, `lookup_municipios`:

| Campo | Conteúdo |
|-------|----------|
| `por_uf_estadual[ano][SG][AI\|AF\|EM]` | IDEB oficial rede **Estadual** de todas as UFs |
| `lookup_ufs` | SG → nome |
| `ufs_ne` | `["AL","BA",…]` |
| `referencias` | `se_publica`, `brasil_publica`, `nordeste_publica`, `nordeste_estadual` |
| `rankings.municipios` | top/todos por etapa + `delta_vs_se` |
| `rankings.ufs_estadual` | ranking BR + subset `nordeste` + `delta_vs_se` |
| `rankings.posicao_se_serie` | posição de SE no tempo (BR/NE) |
| `rankings.escolas.lista` | escolas SE com AI/AF/EM, mun, DRE |

## Como atualizar o IDEB

1. Baixar planilhas oficiais INEP (IDEB 2023) e colocar em `00. Bases de Dados/02. IDEB/` **ou** manter o fallback em `etl/paths.py`.
   - `divulgacao_regioes_ufs_ideb_2023.xlsx`
   - planilhas de municípios/escolas AI, AF e EM 2023
2. Gerar JSONs:
   ```bash
   python etl/etl_ideb.py
   ```
3. (Se DePara/DRE mudar) regenerar geo + lookup:
   ```bash
   python etl/gerar_geo_dre.py
   ```
4. Commit + push na `main` → Actions publica o Pages.

## Modo SE no frontend

- `SE_MODE = true` + objeto `SE` em `app.js`
- Boot: IDEB + `se_municipios.geojson` + `se_dres.geojson` + `se_dre_lookup.json`
- Aba IDEB: KPIs → conceito → evolução (comparar Brasil/NE/UF) → rankings municípios → comparativo UFs → ranking escolas → decomposição N×P → mapa/tabela
- Labels CRE→DRE; metas SEDUC-RS ocultas

## Cache-bust

`index.html` usa `?v=2` em CSS/JS. Incrementar ao publicar mudanças de front.

## Contato / contexto FGV

Projeto Gestão para Aprendizagem — SEDUC/SEED Sergipe. Coordenação de dados e sistemas: Matheus Bianco (FGV DGPE).
