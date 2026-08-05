/**
 * Rankings / contrastes IDEB — Sergipe (SEED)
 * Municípios SE · Comparativo UFs (Brasil/Nordeste) · Escolas
 * Carregar antes de app.js (usa Chart, S, FONTE_IDEB, getIdebColor se existir).
 */
(function (global) {
  'use strict';

  const ET_LABEL = { AI: 'Anos Iniciais', AF: 'Anos Finais', EM: 'Ens. Médio' };
  const ET_COLOR = { AI: '#1d71b9', AF: '#F57C00', EM: '#EE302F' };
  const EM_ONLY = () => !!(global.SE_EM_ONLY);
  const ETAPAS_ATIVAS = () => (EM_ONLY() ? ['EM'] : ['AI', 'AF', 'EM']);

  function fmtNum(v) {
    return v == null || v === '' ? '—' : Number(v).toFixed(1).replace('.', ',');
  }

  function fmtDelta(d) {
    if (d == null || Number.isNaN(d)) return '<span style="color:#999">—</span>';
    if (d === 0) return '<span style="color:#666;font-weight:600">0,0</span>';
    // positivo = acima de SE (eles melhores) → vermelho; negativo → verde (SE à frente)
    const cls = d > 0 ? '#C62828' : '#2E7D32';
    const sign = d > 0 ? '+' : '';
    return `<span style="color:${cls};font-weight:700">${sign}${Number(d).toFixed(1).replace('.', ',')}</span>`;
  }

  function idebColor(v) {
    if (typeof global.getIdebColor === 'function') return global.getIdebColor(v);
    if (v == null || v === 0) return '#f0f0f0';
    if (v >= 7) return '#1B5E20';
    if (v >= 6) return '#43A047';
    if (v >= 5) return '#FFCB04';
    if (v >= 4) return '#FB8C00';
    return '#E53935';
  }

  function th(col, txt, align, title) {
    return `<th data-col="${col}" class="sortable" title="${title || 'Clique para ordenar'}"
      style="padding:7px 8px;text-align:${align || 'left'};background:#1a365d;color:#fff;font-size:10.5px;font-weight:700;white-space:nowrap;cursor:pointer;user-select:none">${txt} <span class="sort-ind" style="opacity:.55">↕</span></th>`;
  }

  function td(html, align, extra) {
    return `<td style="padding:6px 8px;text-align:${align || 'left'};border-bottom:1px solid #eee;font-size:11px;${extra || ''}">${html}</td>`;
  }

  function norm(s) {
    return (s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  }

  function getCreMunsSafe(cre) {
    if (typeof global.getCreMuns === 'function') return global.getCreMuns(cre);
    return [];
  }

  /** Filtra lista de municípios do ranking pelo DRE ativo. */
  function filterMunRows(rows, creSel) {
    if (!creSel) return rows;
    const allowed = new Set(getCreMunsSafe(creSel));
    if (!allowed.size) return rows;
    return rows.filter(r => allowed.has(r.cod));
  }

  // ─── Municípios ───────────────────────────────────────────
  function buildMunicipiosHTML(ideb, anoSel, creSel) {
    const rk = ideb?.rankings?.municipios;
    if (!rk) return '';
    const ano = String(rk.ano || anoSel || '2023');
    const etapas = ETAPAS_ATIVAS().filter(et => (rk.etapas?.[et]?.todos || []).length);

    const fullEt = etapas[0] || 'EM';
    let fullRows = filterMunRows(rk.etapas[fullEt]?.todos || [], creSel);
    fullRows = fullRows.map(r => ({ ...r })).sort((a, b) => (b.ideb - a.ideb) || a.nome.localeCompare(b.nome, 'pt-BR'));
    fullRows.forEach((r, i) => { r.pos = i + 1; });
    const seIdeb = rk.etapas[fullEt]?.se_ideb;

    const fullBody = fullRows.map(r => {
      const delta = r.delta_vs_se;
      return `<tr data-pos="${r.pos}" data-nome="${norm(r.nome)}" data-ideb="${r.ideb ?? ''}" data-delta="${delta ?? ''}">
        <td style="padding:6px 8px;text-align:center;border-bottom:1px solid #eee;font-size:11px;font-weight:700;color:#1a365d">${r.pos}</td>
        <td style="padding:6px 8px;border-bottom:1px solid #eee;font-size:11px">${r.nome}</td>
        <td style="padding:6px 8px;text-align:center;border-bottom:1px solid #eee;font-size:11px;font-weight:700;color:${idebColor(r.ideb)}">${fmtNum(r.ideb)}</td>
        <td style="padding:6px 8px;text-align:center;border-bottom:1px solid #eee;font-size:11px">${fmtDelta(delta)}</td>
      </tr>`;
    }).join('');

    return `
      <div class="section-divider">
        <span class="section-divider-icon"><img src="img/icons/panorama.png" alt=""></span>
        <span class="section-divider-text">Ranking completo — Municípios SE (${ano})</span>
        <span class="section-divider-line"></span>
      </div>
      <div class="chart-card" style="padding:0;overflow:hidden;margin-bottom:10px">
        <div style="padding:10px 14px;border-bottom:1px solid #e8ecf1;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
          <div class="chart-title" style="margin:0">Ranking completo — ${ET_LABEL[fullEt]}</div>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
            <span style="font-size:10.5px;color:#555">SE: <strong style="color:#1a365d">${fmtNum(seIdeb)}</strong></span>
            ${etapas.length > 1 ? `
            <select id="ideb-se-mun-full-et" style="font-size:11px;padding:4px 8px;border-radius:5px;border:1px solid #ccc;background:#fff">
              ${etapas.map(et => `<option value="${et}" ${et === fullEt ? 'selected' : ''}>${ET_LABEL[et]}</option>`).join('')}
            </select>` : `<input type="hidden" id="ideb-se-mun-full-et" value="${fullEt}">`}
            <input type="text" id="ideb-se-mun-full-search" placeholder="Buscar município..."
              style="font-size:11px;padding:4px 10px;border-radius:5px;border:1px solid #ccc;min-width:180px">
            <span id="ideb-se-mun-full-count" style="font-size:10.5px;color:#666"></span>
          </div>
        </div>
        <div style="max-height:420px;overflow:auto">
          <table id="ideb-se-mun-full-table" style="width:100%;border-collapse:collapse" data-ano="${ano}">
            <thead><tr>
              ${th('pos', 'Posição', 'center')}
              ${th('nome', 'Município')}
              ${th('ideb', 'IDEB', 'center')}
              ${th('delta', 'Δ vs SE', 'center')}
            </tr></thead>
            <tbody id="ideb-se-mun-full-tbody">${fullBody}</tbody>
          </table>
        </div>
        <div class="chart-source" style="padding:8px 12px">Fonte: IDEB/INEP ${ano} · Δ = município − IDEB SE (mesma rede)</div>
      </div>`;
  }

  function rebuildMunFullTable(ideb, et, creSel) {
    const rk = ideb?.rankings?.municipios;
    const tbody = document.getElementById('ideb-se-mun-full-tbody');
    const countEl = document.getElementById('ideb-se-mun-full-count');
    if (!rk || !tbody) return;
    let rows = filterMunRows(rk.etapas[et]?.todos || [], creSel);
    rows = rows.map(r => ({ ...r })).sort((a, b) => (b.ideb - a.ideb) || a.nome.localeCompare(b.nome, 'pt-BR'));
    rows.forEach((r, i) => { r.pos = i + 1; });
    tbody.innerHTML = rows.map(r => {
      const delta = r.delta_vs_se;
      return `<tr data-pos="${r.pos}" data-nome="${norm(r.nome)}" data-ideb="${r.ideb ?? ''}" data-delta="${delta ?? ''}">
        <td style="padding:6px 8px;text-align:center;border-bottom:1px solid #eee;font-size:11px;font-weight:700;color:#1a365d">${r.pos}</td>
        <td style="padding:6px 8px;border-bottom:1px solid #eee;font-size:11px">${r.nome}</td>
        <td style="padding:6px 8px;text-align:center;border-bottom:1px solid #eee;font-size:11px;font-weight:700;color:${idebColor(r.ideb)}">${fmtNum(r.ideb)}</td>
        <td style="padding:6px 8px;text-align:center;border-bottom:1px solid #eee;font-size:11px">${fmtDelta(delta)}</td>
      </tr>`;
    }).join('');
    const title = document.querySelector('#ideb-se-mun-full-table')?.closest('.chart-card')?.querySelector('.chart-title');
    if (title) title.textContent = `Ranking completo — ${ET_LABEL[et]}`;
    if (countEl) countEl.textContent = `${rows.length} municípios`;
    bindSortable(document.getElementById('ideb-se-mun-full-table'), { defaultCol: 'pos', defaultAsc: true });
    bindSearchFilter('ideb-se-mun-full-search', 'ideb-se-mun-full-tbody', 'ideb-se-mun-full-count', 'município');
  }

  // ─── UFs ──────────────────────────────────────────────────
  function buildUfsHTML(ideb) {
    const rk = ideb?.rankings?.ufs_estadual;
    if (!rk) return '';
    const ano = rk.ano || 2023;
    const mode = (global.S && global.S.idebUfScope) || 'nordeste';

    const scopeData = mode === 'nordeste' ? rk.nordeste : rk;
    const etapas = ETAPAS_ATIVAS().filter(et => (scopeData.etapas?.[et]?.todos || []).length);

    const fmtEmpatePos = (r, posKey) => {
      const pos = r[posKey] ?? r.pos;
      if (!pos) return '—';
      if ((r.empate_com || 0) > 0) {
        const faixa = r.posicao_min != null && r.posicao_max != null && r.posicao_min !== r.posicao_max
          ? `${r.posicao_min}º–${r.posicao_max}º`
          : `${pos}º`;
        return `${pos}º<span style="font-size:9px;font-weight:600;color:#b45309;margin-left:3px" title="Empate de IDEB · faixa ${faixa}">*</span>`;
      }
      return `${pos}º`;
    };

    const empateNote = (et) => {
      const info = scopeData.etapas[et]?.se_empate;
      if (!info || !(info.empate_com > 0)) {
        return `<div style="font-size:10.5px;color:#555;padding:8px 12px;background:#f8fafc;border-top:1px solid #e8ecf1">
          SE em <strong>${info?.pos ?? '—'}º</strong> · sem empate de IDEB com outras UFs · desempate do painel: ordem alfabética da sigla
        </div>`;
      }
      const outros = (info.empatados || []).join(', ');
      const faixa = info.posicao_min !== info.posicao_max
        ? `faixa ${info.posicao_min}º–${info.posicao_max}º`
        : `${info.pos}º`;
      const qtd = info.empate_com === 1 ? '1 outra UF' : `${info.empate_com} outras UFs`;
      return `<div style="font-size:10.5px;color:#334155;padding:8px 12px;background:#fff8eb;border-top:1px solid #fde68a;line-height:1.45">
        <strong>Empate:</strong> SE em <strong>${info.pos}º</strong> com IDEB ${fmtNum(info.ideb)},
        empatado com <strong>${qtd}</strong> (${outros}) · ${faixa}.
        O painel desempatou por ordem alfabética da sigla (INEP não define ranking oficial com desempate).
      </div>`;
    };

    const buildUfTable = (et) => {
      const rows = scopeData.etapas[et]?.todos || [];
      const posKey = mode === 'nordeste' ? 'pos_ne' : 'pos';
      const body = rows.map(r => {
        const pos = r[posKey] ?? r.pos;
        const bg = r.is_se ? 'background:rgba(26,54,93,.08);font-weight:700;' : '';
        return `<tr style="${bg}" data-pos="${pos ?? ''}" data-nome="${norm(r.nome)}" data-ideb="${r.ideb ?? ''}" data-delta="${r.is_se ? 0 : (r.delta_vs_se ?? '')}">
          ${td(fmtEmpatePos(r, posKey), 'center', 'font-weight:700;color:#1a365d')}
          ${td(r.is_se ? `<strong>${r.uf} — ${r.nome}</strong>` : `${r.uf} — ${r.nome}`)}
          ${td(fmtNum(r.ideb), 'center', `font-weight:700;color:${idebColor(r.ideb)}`)}
          ${td(fmtDelta(r.is_se ? 0 : r.delta_vs_se), 'center')}
        </tr>`;
      }).join('');
      return `
        <div class="chart-card" style="padding:0;overflow:hidden">
          <div style="padding:10px 14px;border-bottom:1px solid #e8ecf1">
            <div class="chart-title" style="margin:0">UFs — ${ET_LABEL[et]} (${ano})</div>
          </div>
          <div style="max-height:360px;overflow-y:auto">
            <table id="ideb-se-uf-${et.toLowerCase()}-table" style="width:100%;border-collapse:collapse">
              <thead><tr>
                ${th('pos', 'Pos.', 'center')}
                ${th('nome', 'UF')}
                ${th('ideb', 'IDEB', 'center')}
                ${th('delta', 'Δ vs SE', 'center')}
              </tr></thead>
              <tbody>${body}</tbody>
            </table>
          </div>
          ${empateNote(et)}
          <div class="chart-source" style="padding:8px 12px">* Empate de IDEB · Rede Estadual · INEP ${ano}</div>
        </div>`;
    };

    const serie = ideb?.rankings?.posicao_se_serie;
    const pickSerie = (mode, a) => (serie?.[mode]?.EM || []).find(p => String(p.ano) === String(a));
    const ganhoBanner = (() => {
      if (!serie) return '';
      const br23 = pickSerie('brasil', '2023');
      const br25 = pickSerie('brasil', '2025');
      const ne23 = pickSerie('nordeste', '2023');
      const ne25 = pickSerie('nordeste', '2025');
      if (!br23 || !br25) return '';
      const ganhoBr = br23.posicao - br25.posicao;
      const ganhoNe = (ne23 && ne25) ? (ne23.posicao - ne25.posicao) : null;
      const faixa = (p) => (p.empate_com > 0 && p.posicao_min !== p.posicao_max)
        ? `${p.posicao_min}º–${p.posicao_max}º`
        : `${p.posicao}º`;
      const txtBr = ganhoBr > 0
        ? `Ganho de ${ganhoBr} posições reais`
        : (ganhoBr < 0 ? `Queda de ${Math.abs(ganhoBr)} posições` : 'Sem variação de posição');
      const txtNe = ganhoNe == null ? '' : (ganhoNe > 0
        ? `Ganho de ${ganhoNe} ${ganhoNe === 1 ? 'posição real' : 'posições reais'}`
        : (ganhoNe < 0 ? `Queda de ${Math.abs(ganhoNe)}` : 'Estável'));
      return `
        <div style="display:grid;grid-template-columns:1.4fr 1fr;gap:8px;margin:0 0 10px">
          <div style="padding:10px 12px;border-radius:8px;background:linear-gradient(135deg,#ecfdf5,#f0fdf4);border:1px solid #86efac">
            <div style="font-size:10px;font-weight:600;color:#166534;letter-spacing:.02em">BRASIL · 2023 → 2025</div>
            <div style="font-size:1.15rem;font-weight:800;color:#14532d;margin-top:2px">${txtBr}</div>
            <div style="font-size:10.5px;color:#334155;margin-top:3px">${br23.posicao}º → ${br25.posicao}º
              <span style="color:#64748b"> · faixas ${faixa(br23)} → ${faixa(br25)}</span>
            </div>
          </div>
          <div style="padding:10px 12px;border-radius:8px;background:linear-gradient(135deg,#eff6ff,#f8fafc);border:1px solid #93c5fd">
            <div style="font-size:10px;font-weight:600;color:#1e40af;letter-spacing:.02em">NORDESTE · 2023 → 2025</div>
            <div style="font-size:1.05rem;font-weight:800;color:#1e3a8a;margin-top:2px">${txtNe || '—'}</div>
            <div style="font-size:10.5px;color:#334155;margin-top:3px">${ne23 && ne25 ? `${ne23.posicao}º → ${ne25.posicao}º` : ''}
              ${ne23 && ne25 ? `<span style="color:#64748b"> · faixas ${faixa(ne23)} → ${faixa(ne25)}</span>` : ''}
            </div>
          </div>
        </div>
        <div style="margin:0 0 10px;padding:8px 12px;background:#fff8eb;border:1px solid #fde68a;border-radius:8px;font-size:10.5px;color:#334155;line-height:1.4">
          <strong>Empates:</strong> rótulos com faixa (ex.: 18–22º) indicam UFs com o mesmo IDEB.
          O ganho usa a posição após desempate alfabético da sigla
          ${br23.empate_com ? ` · em 2023 SE empatou com <strong>${br23.empate_com} outras</strong> (${(br23.empatados || []).join(', ')})` : ''}
          ${br25.empate_com ? ` · em 2025 com <strong>${br25.empate_com} outras</strong> (${(br25.empatados || []).join(', ')})` : ''}.
        </div>`;
    })();

    return `
      <div class="section-divider">
        <span class="section-divider-icon"><img src="img/icons/panorama.png" alt=""></span>
        <span class="section-divider-text">Comparativo entre UFs — Rede Estadual (${ano})</span>
        <span class="section-divider-line"></span>
      </div>
      <div style="display:flex;gap:8px;margin-bottom:10px;align-items:center;flex-wrap:wrap">
        <span style="font-size:11px;font-weight:600;color:#555">Recorte:</span>
        <div class="scope-toggle" role="group" aria-label="Recorte geográfico">
          <button type="button" class="scope-toggle-btn${mode === 'brasil' ? ' active' : ''}" id="ideb-uf-scope-brasil" data-scope="brasil">Brasil (27 UFs)</button>
          <button type="button" class="scope-toggle-btn${mode === 'nordeste' ? ' active' : ''}" id="ideb-uf-scope-ne" data-scope="nordeste">Só Nordeste</button>
        </div>
        <span style="font-size:10px;color:#888;margin-left:4px">Sempre rede estadual oficial do INEP</span>
      </div>
      <div class="charts-grid" style="display:grid;grid-template-columns:${etapas.length === 3 ? '1fr 1fr 1fr' : '1fr'};gap:10px;margin-bottom:10px">
        ${etapas.map(buildUfTable).join('')}
      </div>
      <div class="chart-card" style="margin-bottom:10px">
        <div class="chart-title">Posição de Sergipe ao longo do tempo — Nordeste × Brasil</div>
        ${ganhoBanner}
        <div style="height:280px"><canvas id="chart-ideb-se-posicao"></canvas></div>
        <div class="chart-source">${typeof FONTE_IDEB !== 'undefined' ? FONTE_IDEB : 'Fonte: IDEB/INEP'} · Eixo Y invertido (1º = melhor) · rótulo em faixa = empate de IDEB</div>
      </div>`;
  }

  function paintPosicaoChart(ideb) {
    const el = document.getElementById('chart-ideb-se-posicao');
    if (!el || typeof Chart === 'undefined') return;
    const serie = ideb?.rankings?.posicao_se_serie;
    if (!serie) return;
    const ets = ETAPAS_ATIVAS();
    const anosSet = new Set();
    ['nordeste', 'brasil'].forEach(mode => {
      const block = serie[mode];
      if (!block) return;
      ets.forEach(et => (block[et] || []).forEach(p => anosSet.add(p.ano)));
    });
    const anos = [...anosSet].sort();

    const seriesCfg = [
      { mode: 'nordeste', label: 'Posição no Nordeste', color: '#1d71b9' },
      { mode: 'brasil', label: 'Posição no Brasil', color: '#EE302F' },
    ];

    const datasets = [];
    ets.forEach(et => {
      seriesCfg.forEach(cfg => {
        const block = serie[cfg.mode]?.[et] || [];
        const byAno = Object.fromEntries(block.map(p => [p.ano, p]));
        const data = anos.map(a => byAno[a]?.posicao ?? null);
        if (!data.some(v => v != null)) return;
        const multiEt = ets.length > 1;
        datasets.push({
          label: multiEt ? `${cfg.label} — ${ET_LABEL[et]}` : cfg.label,
          data,
          borderColor: cfg.color,
          backgroundColor: cfg.color + '22',
          borderWidth: cfg.mode === 'brasil' ? 2 : 2.4,
          borderDash: cfg.mode === 'brasil' ? [6, 4] : [],
          pointRadius: 4,
          pointBackgroundColor: '#fff',
          pointBorderColor: cfg.color,
          pointBorderWidth: 2,
          tension: 0.25,
          spanGaps: true,
          _metaByAno: byAno,
        });
      });
    });

    const maxN = Math.max(
      9,
      ...ets.flatMap(et => (serie.nordeste?.[et] || []).map(p => p.n || p.posicao_max || 0)),
      ...ets.flatMap(et => (serie.brasil?.[et] || []).map(p => p.n || p.posicao_max || 0)),
      ...datasets.flatMap(d => d.data.filter(v => v != null))
    );

    // Destaque visual do ganho 2023→2025 (Brasil) no canvas
    const ganhoPlugin = {
      id: 'ganhoPosicaoLabel',
      afterDatasetsDraw(chart) {
        const brDs = chart.data.datasets.find(d => (d.label || '').includes('Brasil'));
        if (!brDs) return;
        const dsIdx = chart.data.datasets.indexOf(brDs);
        const meta = chart.getDatasetMeta(dsIdx);
        const i23 = chart.data.labels.indexOf('2023');
        const i25 = chart.data.labels.indexOf('2025');
        if (i23 < 0 || i25 < 0 || !meta?.data?.[i23] || !meta?.data?.[i25]) return;
        const p23 = brDs._metaByAno?.['2023'];
        const p25 = brDs._metaByAno?.['2025'];
        if (!p23 || !p25) return;
        const ganho = p23.posicao - p25.posicao;
        if (ganho <= 0) return;
        const a = meta.data[i23];
        const b = meta.data[i25];
        const ctx = chart.ctx;
        const mx = (a.x + b.x) / 2;
        const my = Math.min(a.y, b.y) - 18;
        const text = `Ganho de ${ganho} posições reais`;
        ctx.save();
        ctx.font = '700 11px Inter, system-ui, sans-serif';
        const w = ctx.measureText(text).width + 16;
        const h = 22;
        const x = mx - w / 2;
        const y = my - h / 2;
        ctx.fillStyle = 'rgba(20, 83, 45, 0.92)';
        ctx.beginPath();
        const r = 6;
        ctx.moveTo(x + r, y);
        ctx.arcTo(x + w, y, x + w, y + h, r);
        ctx.arcTo(x + w, y + h, x, y + h, r);
        ctx.arcTo(x, y + h, x, y, r);
        ctx.arcTo(x, y, x + w, y, r);
        ctx.closePath();
        ctx.fill();
        ctx.fillStyle = '#fff';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, mx, y + h / 2);
        ctx.restore();
      },
    };

    const chart = new Chart(el, {
      type: 'line',
      data: { labels: anos, datasets },
      plugins: [ganhoPlugin],
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: { top: 28, right: 8 } },
        plugins: {
          legend: { display: true, position: 'bottom', labels: { font: { size: 11, weight: '600' }, boxWidth: 12 } },
          tooltip: {
            callbacks: {
              label(ctx) {
                const ano = ctx.label;
                const meta = ctx.dataset._metaByAno?.[ano];
                if (!meta) return ` ${ctx.dataset.label}: ${ctx.parsed.y}º`;
                if (meta.empate_com > 0) {
                  const qtd = meta.empate_com === 1 ? '1 outra UF' : `${meta.empate_com} outras UFs`;
                  const outros = (meta.empatados || []).join(', ');
                  return [
                    ` ${ctx.dataset.label}: ${meta.posicao}º (faixa ${meta.posicao_min}º–${meta.posicao_max}º)`,
                    ` Empatado com ${qtd}: ${outros} · IDEB ${meta.ideb}`,
                  ];
                }
                return ` ${ctx.dataset.label}: ${meta.posicao}º · IDEB ${meta.ideb} · sem empate`;
              },
            },
          },
          datalabels: {
            display: true,
            anchor: 'end',
            align: 'top',
            offset: 2,
            clamp: true,
            font: { size: 8.5, weight: '700' },
            color: ctx => ctx.dataset.borderColor,
            formatter: (_v, ctx) => {
              const ano = ctx.chart.data.labels[ctx.dataIndex];
              const meta = ctx.dataset._metaByAno?.[ano];
              if (!meta || meta.posicao == null) return '';
              if (meta.empate_com > 0 && meta.posicao_min !== meta.posicao_max) {
                return `${meta.posicao_min}–${meta.posicao_max}º`;
              }
              return `${meta.posicao}º`;
            },
          },
        },
        scales: {
          y: {
            reverse: true,
            min: 1,
            max: Math.min(Math.ceil(maxN * 1.05), 27),
            ticks: { stepSize: 1, callback: v => v + 'º' },
            title: { display: true, text: 'Posição (1º = melhor)', font: { size: 10 } },
          },
        },
      },
    });
    if (global.S && Array.isArray(global.S.charts)) global.S.charts.push(chart);
  }

  // ─── Escolas ──────────────────────────────────────────────
  function buildEscolasHTML(ideb, creSel, munSel) {
    const esc = ideb?.rankings?.escolas;
    if (!esc) return '';
    const ano = esc.ano || 2023;
    let lista = esc.lista || [];
    if (munSel) lista = lista.filter(e => e.cod_mun === munSel);
    else if (creSel) {
      const allowed = new Set(getCreMunsSafe(creSel));
      if (allowed.size) lista = lista.filter(e => allowed.has(e.cod_mun));
    }

    const ranked = lista.map(e => ({ ...e })).sort((a, b) => {
      const va = a.EM ?? a.AI ?? a.AF ?? -1;
      const vb = b.EM ?? b.AI ?? b.AF ?? -1;
      return (vb - va) || a.nome.localeCompare(b.nome, 'pt-BR');
    });
    ranked.forEach((r, i) => { r.pos = i + 1; });

    const body = ranked.map(r => `
      <tr data-pos="${r.pos}" data-nome="${norm(r.nome)}" data-mun="${norm(r.nome_mun)}"
        data-em="${r.EM ?? ''}" data-dre="${norm(r.dre || '')}">
        ${td(r.pos, 'center', 'font-weight:700;color:#1a365d')}
        ${td(r.nome)}
        ${td(r.nome_mun || '—')}
        ${td(r.dre || '—', 'center', 'font-size:10px;color:#666')}
        ${td(fmtNum(r.EM), 'center', `font-weight:700;color:${idebColor(r.EM)}`)}
      </tr>`).join('');

    return `
      <div class="section-divider">
        <span class="section-divider-icon"><img src="img/icons/escola.png" alt=""></span>
        <span class="section-divider-text">Ranking de Escolas — Ensino Médio (${ano})</span>
        <span class="section-divider-line"></span>
      </div>
      <div class="chart-card" style="padding:0;overflow:hidden;margin-bottom:10px">
        <div style="padding:10px 14px;border-bottom:1px solid #e8ecf1;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
          <div class="chart-title" style="margin:0">${ranked.length} escolas estaduais com IDEB EM</div>
          <input type="text" id="ideb-se-esc-search" placeholder="Buscar escola ou município..."
            style="font-size:11px;padding:4px 10px;border-radius:5px;border:1px solid #ccc;min-width:220px">
          <span id="ideb-se-esc-count" style="font-size:10.5px;color:#666"></span>
        </div>
        <div style="max-height:480px;overflow:auto">
          <table id="ideb-se-esc-table" style="width:100%;border-collapse:collapse;min-width:640px">
            <thead><tr>
              ${th('pos', 'Pos.', 'center')}
              ${th('nome', 'Escola')}
              ${th('mun', 'Município')}
              ${th('dre', 'DRE', 'center')}
              ${th('em', 'IDEB EM', 'center')}
            </tr></thead>
            <tbody id="ideb-se-esc-tbody">${body}</tbody>
          </table>
        </div>
        <div class="chart-source" style="padding:8px 12px">Fonte: IDEB/INEP ${ano} — escolas da rede estadual (Ensino Médio)</div>
      </div>`;
  }

  // ─── Helpers bind ─────────────────────────────────────────
  function bindSortable(table, opts) {
    if (!table) return;
    const tbody = table.tBodies[0];
    const thead = table.tHead;
    if (!tbody || !thead) return;
    let sortCol = opts?.defaultCol || 'pos';
    let sortAsc = opts?.defaultAsc !== false;
    const ascDefault = new Set(['pos', 'nome', 'mun', 'dre']);

    const paint = () => {
      thead.querySelectorAll('th.sortable').forEach(thEl => {
        const ind = thEl.querySelector('.sort-ind');
        if (!ind) return;
        if (thEl.dataset.col === sortCol) {
          ind.textContent = sortAsc ? '▲' : '▼';
          ind.style.opacity = '1';
        } else {
          ind.textContent = '↕';
          ind.style.opacity = '.55';
        }
      });
    };

    const apply = () => {
      const rows = [...tbody.querySelectorAll('tr')];
      rows.sort((a, b) => {
        if (sortCol === 'nome' || sortCol === 'mun' || sortCol === 'dre') {
          const va = a.dataset[sortCol] || a.dataset.nome || '';
          const vb = b.dataset[sortCol] || b.dataset.nome || '';
          return sortAsc ? va.localeCompare(vb, 'pt-BR') : vb.localeCompare(va, 'pt-BR');
        }
        const rawA = a.dataset[sortCol];
        const rawB = b.dataset[sortCol];
        if ((rawA === '' || rawA == null) && (rawB === '' || rawB == null)) return 0;
        if (rawA === '' || rawA == null) return 1;
        if (rawB === '' || rawB == null) return -1;
        const va = parseFloat(rawA);
        const vb = parseFloat(rawB);
        return sortAsc ? va - vb : vb - va;
      });
      rows.forEach(tr => tbody.appendChild(tr));
      paint();
    };

    thead.onclick = (e) => {
      const thEl = e.target.closest('th.sortable');
      if (!thEl) return;
      const col = thEl.dataset.col;
      if (sortCol === col) sortAsc = !sortAsc;
      else {
        sortCol = col;
        sortAsc = ascDefault.has(col);
      }
      apply();
    };
    paint();
  }

  function bindSearchFilter(inputId, tbodyId, countId, label) {
    const input = document.getElementById(inputId);
    const tbody = document.getElementById(tbodyId);
    const countEl = document.getElementById(countId);
    if (!tbody) return;
    const apply = () => {
      const q = norm(input?.value || '').trim();
      let n = 0;
      tbody.querySelectorAll('tr').forEach(tr => {
        const hay = (tr.dataset.nome || '') + ' ' + (tr.dataset.mun || '');
        const show = !q || hay.includes(q);
        tr.style.display = show ? '' : 'none';
        if (show) n++;
      });
      if (countEl) countEl.textContent = `${n} ${label}${n !== 1 ? 's' : ''}`;
    };
    if (input) input.oninput = apply;
    apply();
  }

  function bindAll(ideb) {
    const S = global.S || {};
    bindSortable(document.getElementById('ideb-se-mun-full-table'), { defaultCol: 'pos', defaultAsc: true });
    bindSearchFilter('ideb-se-mun-full-search', 'ideb-se-mun-full-tbody', 'ideb-se-mun-full-count', 'município');

    const etSel = document.getElementById('ideb-se-mun-full-et');
    if (etSel) {
      etSel.onchange = () => rebuildMunFullTable(ideb, etSel.value, S.creSel);
    }

    // UF scope toggle
    const setScope = (scope) => {
      if (global.S) global.S.idebUfScope = scope;
      // re-render only UF block is heavy — trigger full tab refresh
      if (typeof global.refreshActiveTab === 'function') global.refreshActiveTab();
      else if (typeof global.renderIdeb === 'function') global.renderIdeb();
    };
    const bBr = document.getElementById('ideb-uf-scope-brasil');
    const bNe = document.getElementById('ideb-uf-scope-ne');
    if (bBr) bBr.onclick = () => setScope('brasil');
    if (bNe) bNe.onclick = () => setScope('nordeste');

    ['ai', 'af', 'em'].forEach(slug => {
      bindSortable(document.getElementById(`ideb-se-uf-${slug}-table`), { defaultCol: 'pos', defaultAsc: true });
    });

    paintPosicaoChart(ideb);

    bindSortable(document.getElementById('ideb-se-esc-table'), { defaultCol: 'pos', defaultAsc: true });
    bindSearchFilter('ideb-se-esc-search', 'ideb-se-esc-tbody', 'ideb-se-esc-count', 'escola');
  }

  /** HTML dos blocos (UFs logo após evolução → ranking mun → escolas). */
  function buildBlocksHTML(ideb, anoSel, creSel, munSel) {
    if (!ideb) return '';
    if (global.S && !global.S.idebUfScope) global.S.idebUfScope = 'nordeste';
    return (
      buildUfsHTML(ideb) +
      buildMunicipiosHTML(ideb, anoSel, creSel) +
      buildEscolasHTML(ideb, creSel, munSel)
    );
  }

  /** Controles do gráfico de evolução (comparar com). */
  function buildEvoControlsHTML(ideb) {
    const lookup = ideb?.lookup_ufs || {};
    const ufs = Object.keys(lookup).filter(sg => sg !== 'SE').sort((a, b) => lookup[a].localeCompare(lookup[b], 'pt-BR'));
    const cmp = (global.S && global.S.idebCmp) || 'none';
    const cmpUf = (global.S && global.S.idebCmpUf) || 'BA';
    return `
      <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:0 0 10px;padding:0 2px">
        <label style="font-size:11px;color:#555;display:flex;align-items:center;gap:6px">
          Comparar com
          <select id="ideb-se-cmp" style="font-size:11px;padding:4px 8px;border-radius:5px;border:1px solid #ccc;background:#fff">
            <option value="none" ${cmp === 'none' ? 'selected' : ''}>Nenhuma referência</option>
            <option value="brasil" ${cmp === 'brasil' ? 'selected' : ''}>Média Brasil</option>
            <option value="nordeste" ${cmp === 'nordeste' ? 'selected' : ''}>Média Nordeste</option>
            <option value="uf" ${cmp === 'uf' ? 'selected' : ''}>UF Específica</option>
          </select>
        </label>
        <label id="ideb-se-cmp-uf-wrap" style="font-size:11px;color:#555;display:${cmp === 'uf' ? 'flex' : 'none'};align-items:center;gap:6px">
          UF
          <select id="ideb-se-cmp-uf" style="font-size:11px;padding:4px 8px;border-radius:5px;border:1px solid #ccc;background:#fff">
            ${ufs.map(sg => `<option value="${sg}" ${sg === cmpUf ? 'selected' : ''}>${sg} — ${lookup[sg]}</option>`).join('')}
          </select>
        </label>
        <span style="font-size:10px;color:#888">Brasil = rede pública · Nordeste/UF = rede estadual (INEP)</span>
      </div>`;
  }

  function bindEvoControls() {
    const cmp = document.getElementById('ideb-se-cmp');
    const ufWrap = document.getElementById('ideb-se-cmp-uf-wrap');
    const ufSel = document.getElementById('ideb-se-cmp-uf');
    if (!cmp) return;
    const apply = () => {
      if (!global.S) global.S = {};
      global.S.idebCmp = cmp.value;
      if (ufSel) global.S.idebCmpUf = ufSel.value;
      if (ufWrap) ufWrap.style.display = cmp.value === 'uf' ? 'flex' : 'none';
      if (typeof global.refreshActiveTab === 'function') global.refreshActiveTab();
      else if (typeof global.renderIdeb === 'function') global.renderIdeb();
    };
    cmp.onchange = apply;
    if (ufSel) ufSel.onchange = apply;
  }

  /** Datasets de overlay para o gráfico de evolução (AI/AF/EM). */
  function getOverlayDatasets(ideb, chartLabels, etapa) {
    const cmp = (global.S && global.S.idebCmp) || 'none';
    if (cmp === 'none') return [];
    const refs = ideb.referencias || {};
    const porUf = ideb.por_uf_estadual || {};
    const base = {
      _isMeta: true, fill: false, borderWidth: 1.8, pointRadius: 2,
      tension: 0.3, spanGaps: true, borderDash: [5, 4],
    };
    const ds = [];
    if (cmp === 'brasil') {
      const data = chartLabels.map(a => refs.brasil_publica?.[a]?.[etapa] ?? null);
      if (data.some(v => v != null)) {
        ds.push({
          ...base,
          label: 'Média Brasil (pública)',
          data, borderColor: '#607D8B', pointBackgroundColor: '#607D8B',
        });
      }
    } else if (cmp === 'nordeste') {
      const data = chartLabels.map(a =>
        refs.nordeste_estadual?.[a]?.[etapa] ?? refs.nordeste_publica?.[a]?.[etapa] ?? null
      );
      if (data.some(v => v != null)) {
        ds.push({
          ...base,
          label: 'Média Nordeste (estadual)',
          data, borderColor: '#78909C', pointBackgroundColor: '#78909C',
        });
      }
    } else if (cmp === 'uf') {
      const sg = (global.S && global.S.idebCmpUf) || 'BA';
      const nome = (ideb.lookup_ufs || {})[sg] || sg;
      const data = chartLabels.map(a => porUf?.[a]?.[sg]?.[etapa] ?? null);
      if (data.some(v => v != null)) {
        ds.push({
          ...base,
          label: `${sg} — ${nome}`,
          data, borderColor: '#5C6BC0', pointBackgroundColor: '#5C6BC0',
        });
      }
    }
    return ds;
  }

  global.IdebSE = {
    buildBlocksHTML,
    buildEvoControlsHTML,
    bindAll,
    bindEvoControls,
    getOverlayDatasets,
    fmtNum,
    fmtDelta,
  };
})(typeof window !== 'undefined' ? window : globalThis);
