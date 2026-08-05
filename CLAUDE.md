# Painel de Dados Abertos — Educação Sergipe (SEED)

Painel estático (HTML/CSS/JS) com GitHub Pages. MVP: aba **IDEB** completa (multi-rede, UF/DRE/município). Template base: painel estadual UNESCO/RS.

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
    ├── css/ styles.css
    ├── js/ app.js                 # SE_MODE = true
    ├── img/
    └── dados/
```

## Repo e URL

- GitHub (atual): `Matheus-Bianco/painel-dados-abertos-sergipe`  
  https://github.com/Matheus-Bianco/painel-dados-abertos-sergipe  
  Pages: https://matheus-bianco.github.io/painel-dados-abertos-sergipe/
- Alvo org: `gasefgv/painel-dados-abertos-sergipe` (transferir quando houver permissão de criar repo na org)
- Pages: artifact = pasta `painel/` (workflow em push na `main`)

## Como atualizar o IDEB

1. Baixar planilhas oficiais INEP (IDEB 2023) e colocar em `00. Bases de Dados/02. IDEB/` **ou** manter o caminho de fallback em `etl/paths.py` (pasta Joinville/UNESCO com os xlsx nacionais).
   - `divulgacao_regioes_ufs_ideb_2023.xlsx` (série UF)
   - planilhas de municípios/escolas AI, AF e EM 2023
2. Gerar JSONs:
   ```bash
   python etl/etl_ideb.py
   ```
3. (Se DePara/DRE mudar) regenerar geo + lookup:
   ```bash
   python etl/gerar_geo_dre.py
   ```
   Requer `service_account.json` (Joinville) para ler a aba Escolas da Formativa, e `geopandas` para dissolve das DREs.
4. Commit + push na `main` → Actions publica o Pages.

## Modo SE no frontend

Em `painel/js/app.js`:

- `SE_MODE = true` e objeto `SE` (UF, DRE, arquivos geo/lookup)
- Boot carrega só IDEB + `se_municipios.geojson` + `se_dres.geojson` + `se_dre_lookup.json`
- Labels CRE→DRE; metas SEDUC-RS ocultas; referências SE/Brasil pública no gráfico
- Demais abas do template UNESCO ficam ocultas na sidebar (código preservado)

## Cache-bust

`index.html` referencia `css/styles.css?v=1` e `js/app.js?v=1`. Incrementar `?v=` ao publicar mudanças de CSS/JS.

## Contato / contexto FGV

Projeto Gestão para Aprendizagem — SEDUC/SEED Sergipe. Coordenação de dados e sistemas: Matheus Bianco (FGV DGPE).
