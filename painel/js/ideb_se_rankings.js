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

    const kpiCards = etapas.map(et => {
      const info = rk.etapas[et];
      const se = info.se_ideb;
      return `
        <div class="kpi-card" style="padding:12px 16px;border-top:3px solid ${ET_COLOR[et]}">
          <div class="kpi-label">SE — ${ET_LABEL[et]}</div>
          <div class="kpi-value" style="font-size:1.5rem">${fmtNum(se)}</div>
          <div class="kpi-footer"><span>${info.n} municípios com IDEB</span><span class="kpi-abs">${ano}</span></div>
        </div>`;
    }).join('');

    const buildTable = (et) => {
      let rows = filterMunRows(rk.etapas[et]?.todos || [], creSel);
      // re-rank after DRE filter
      rows = rows.map(r => ({ ...r })).sort((a, b) => (b.ideb - a.ideb) || a.nome.localeCompare(b.nome, 'pt-BR'));
      rows.forEach((r, i) => { r.pos = i + 1; });
      const contraste = rows.slice(0, 15);
      const seIdeb = rk.etapas[et]?.se_ideb;
      const body = contraste.map(r => {
        const delta = r.delta_vs_se != null ? r.delta_vs_se : (seIdeb != null ? +(r.ideb - seIdeb).toFixed(2) : null);
        return `<tr data-pos="${r.pos}" data-nome="${norm(r.nome)}" data-ideb="${r.ideb ?? ''}" data-delta="${delta ?? ''}">
          ${td(r.pos, 'center', 'font-weight:700;color:#1a365d')}
          ${td(r.nome)}
          ${td(fmtNum(r.ideb), 'center', `font-weight:700;color:${idebColor(r.ideb)}`)}
          ${td(fmtDelta(delta), 'center')}
        </tr>`;
      }).join('');
      return `
        <div class="chart-card" style="padding:0;overflow:hidden">
          <div style="padding:10px 14px;border-bottom:1px solid #e8ecf1;display:flex;justify-content:space-between;align-items:center;gap:8px">
            <div class="chart-title" style="margin:0">Ranking SE — ${ET_LABEL[et]} (${ano})</div>
            <div style="font-size:10.5px;color:#555">SE: <strong style="color:#1a365d">${fmtNum(seIdeb)}</strong> · ${rows.length} mun.</div>
          </div>
          <div style="max-height:340px;overflow-y:auto">
            <table id="ideb-se-mun-${et.toLowerCase()}-table" style="width:100%;border-collapse:collapse">
              <thead><tr>
                ${th('pos', 'Pos.', 'center')}
                ${th('nome', 'Município')}
                ${th('ideb', 'IDEB', 'center')}
                ${th('delta', 'Δ vs SE', 'center')}
              </tr></thead>
              <tbody>${body}</tbody>
            </table>
          </div>
          <div class="chart-source" style="padding:8px 12px">Top 15 · Δ vs média/IDEB estadual da rede · Fonte: IDEB/INEP ${ano}</div>
        </div>`;
    };

    // Ranking completo (AI como principal + tabs via select)
    const fullEt = etapas[0] || 'AI';
    let fullRows = filterMunRows(rk.etapas[fullEt]?.todos || [], creSel);
    fullRows = fullRows.map(r => ({ ...r })).sort((a, b) => (b.ideb - a.ideb) || a.nome.localeCompare(b.nome, 'pt-BR'));
    fullRows.forEach((r, i) => { r.pos = i + 1; });

    const fullBody = fullRows.map(r => {
      const delta = r.delta_vs_se;
      return `<tr data-pos="${r.pos}" data-nome="${norm(r.nome)}" data-ideb="${r.ideb ?? ''}" data-delta="${delta ?? ''}">
        <td style="padding:6px 8px;text-align:center;border-bottom:1px solid #eee;font-size:11px;font-weight:700;color:#1a365d">${r.pos}</td>
        <td style="padding:6px 8px;border-bottom:1px solid #eee;font-size:11px">${r.nome}</td>
        <td style="padding:6px 8px;text-align:center;border-bottom:1px solid #eee;font-size:11px;font-weight:700;color:${idebColor(r.ideb)}">${fmtNum(r.ideb)}</td>
        <td style="padding:6px 8px;text-align:center;border-bottom:1px solid #eee;font-size:11px">${fmtDelta(delta)}</td>
      </tr>`;
    }).join('');

    const gridCols = etapas.length === 3 ? '1fr 1fr 1fr' : (etapas.length === 2 ? '1fr 1fr' : '1fr');

    return `
      <div class="section-divider">
        <span class="section-divider-icon"><img src="img/icons/panorama.png" alt=""></span>
        <span class="section-divider-text">Ranking e contrastes — Municípios SE (${ano})</span>
        <span class="section-divider-line"></span>
      </div>
      <div style="display:grid;grid-template-columns:repeat(${etapas.length},1fr);gap:10px;margin-bottom:10px">
        ${kpiCards}
      </div>
      <div class="charts-grid" style="display:grid;grid-template-columns:${gridCols};gap:10px;margin-bottom:10px">
        ${etapas.map(buildTable).join('')}
      </div>
      <div class="chart-card" style="padding:0;overflow:hidden;margin-bottom:10px">
        <div style="padding:10px 14px;border-bottom:1px solid #e8ecf1;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
          <div class="chart-title" style="margin:0">Ranking completo — ${ET_LABEL[fullEt]}</div>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
            <select id="ideb-se-mun-full-et" style="font-size:11px;padding:4px 8px;border-radius:5px;border:1px solid #ccc;background:#fff">
              ${etapas.map(et => `<option value="${et}" ${et === fullEt ? 'selected' : ''}>${ET_LABEL[et]}</option>`).join('')}
            </select>
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

    const kpis = etapas.map(et => {
      const info = scopeData.etapas[et];
      const label = mode === 'nordeste' ? 'Nordeste' : 'Brasil';
      return `
        <div class="kpi-card" style="padding:12px 16px;border-top:3px solid ${ET_COLOR[et]}">
          <div class="kpi-label">Posição SE — ${ET_LABEL[et]} (${label})</div>
          <div class="kpi-value" style="font-size:1.5rem">${info.se_pos ?? '—'}º <span style="font-size:.85rem;font-weight:500;color:#666">de ${info.n}</span></div>
          <div class="kpi-footer"><span>IDEB ${fmtNum(info.se_ideb)}</span><span class="kpi-abs">rede estadual</span></div>
        </div>`;
    }).join('');

    const buildUfTable = (et) => {
      const rows = scopeData.etapas[et]?.todos || [];
      const posKey = mode === 'nordeste' ? 'pos_ne' : 'pos';
      const body = rows.map(r => {
        const pos = r[posKey] ?? r.pos;
        const bg = r.is_se ? 'background:rgba(26,54,93,.08);font-weight:700;' : '';
        return `<tr style="${bg}" data-pos="${pos ?? ''}" data-nome="${norm(r.nome)}" data-ideb="${r.ideb ?? ''}" data-delta="${r.is_se ? 0 : (r.delta_vs_se ?? '')}">
          ${td(pos, 'center', 'font-weight:700;color:#1a365d')}
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
          <div class="chart-source" style="padding:8px 12px">Rede Estadual · INEP ${ano}</div>
        </div>`;
    };

    return `
      <div class="section-divider">
        <span class="section-divider-icon"><img src="img/icons/panorama.png" alt=""></span>
        <span class="section-divider-text">Comparativo entre UFs — Rede Estadual (${ano})</span>
        <span class="section-divider-line"></span>
      </div>
      <div style="display:flex;gap:8px;margin-bottom:10px;align-items:center;flex-wrap:wrap">
        <span style="font-size:11px;font-weight:600;color:#555">Recorte:</span>
        <button type="button" class="rede-toggle-btn${mode === 'brasil' ? ' active' : ''}" id="ideb-uf-scope-brasil" data-scope="brasil">Brasil (27 UFs)</button>
        <button type="button" class="rede-toggle-btn${mode === 'nordeste' ? ' active' : ''}" id="ideb-uf-scope-ne" data-scope="nordeste">Só Nordeste</button>
        <span style="font-size:10px;color:#888;margin-left:4px">Sempre rede estadual oficial do INEP</span>
      </div>
      <div style="display:grid;grid-template-columns:repeat(${Math.max(etapas.length, 1)},1fr);gap:10px;margin-bottom:10px">
        ${kpis}
      </div>
      <div class="charts-grid" style="display:grid;grid-template-columns:${etapas.length === 3 ? '1fr 1fr 1fr' : '1fr 1fr'};gap:10px;margin-bottom:10px">
        ${etapas.map(buildUfTable).join('')}
      </div>
      <div class="chart-card" style="margin-bottom:10px">
        <div class="chart-title">Posição de Sergipe ao longo do tempo (${mode === 'nordeste' ? 'Nordeste' : 'Brasil'})</div>
        <div style="height:260px"><canvas id="chart-ideb-se-posicao"></canvas></div>
        <div class="chart-source">${typeof FONTE_IDEB !== 'undefined' ? FONTE_IDEB : 'Fonte: IDEB/INEP'} · Eixo Y invertido (1º = melhor)</div>
      </div>`;
  }

  function paintPosicaoChart(ideb) {
    const el = document.getElementById('chart-ideb-se-posicao');
    if (!el || typeof Chart === 'undefined') return;
    const serie = ideb?.rankings?.posicao_se_serie;
    if (!serie) return;
    const mode = (global.S && global.S.idebUfScope) || 'nordeste';
    const block = serie[mode] || serie.brasil;
    const anosSet = new Set();
    const ets = ETAPAS_ATIVAS();
    ets.forEach(et => (block[et] || []).forEach(p => anosSet.add(p.ano)));
    const anos = [...anosSet].sort();
    const datasets = ets.map(et => {
      const map = Object.fromEntries((block[et] || []).map(p => [p.ano, p.posicao]));
      return {
        label: ET_LABEL[et],
        data: anos.map(a => map[a] ?? null),
        borderColor: ET_COLOR[et],
        backgroundColor: ET_COLOR[et] + '22',
        borderWidth: 2.2,
        pointRadius: 4,
        tension: 0.25,
        spanGaps: true,
      };
    }).filter(ds => ds.data.some(v => v != null));

    const maxN = Math.max(
      ...ets.flatMap(et => (block[et] || []).map(p => p.n || 0)),
      9
    );

    const chart = new Chart(el, {
      type: 'line',
      data: { labels: anos, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: true, position: 'bottom', labels: { font: { size: 11, weight: '600' }, boxWidth: 12 } },
          datalabels: {
            display: true,
            anchor: 'end',
            align: 'top',
            font: { size: 9, weight: '700' },
            formatter: v => (v != null ? v + 'º' : ''),
          },
        },
        scales: {
          y: {
            reverse: true,
            min: 1,
            max: Math.min(maxN, mode === 'nordeste' ? 9 : 27),
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
    // mun contraste tables
    ['ai', 'af', 'em'].forEach(slug => {
      bindSortable(document.getElementById(`ideb-se-mun-${slug}-table`), { defaultCol: 'pos', defaultAsc: true });
    });
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

  /** HTML dos três blocos (inserir após evolução). */
  function buildBlocksHTML(ideb, anoSel, creSel, munSel) {
    if (!ideb) return '';
    if (global.S && !global.S.idebUfScope) global.S.idebUfScope = 'nordeste';
    return (
      buildMunicipiosHTML(ideb, anoSel, creSel) +
      buildUfsHTML(ideb) +
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
            <option value="brasil" ${cmp === 'brasil' ? 'selected' : ''}>Brasil (rede pública)</option>
            <option value="nordeste" ${cmp === 'nordeste' ? 'selected' : ''}>Nordeste (rede estadual)</option>
            <option value="uf" ${cmp === 'uf' ? 'selected' : ''}>UF específica (rede estadual)</option>
          </select>
        </label>
        <label id="ideb-se-cmp-uf-wrap" style="font-size:11px;color:#555;display:${cmp === 'uf' ? 'flex' : 'none'};align-items:center;gap:6px">
          UF
          <select id="ideb-se-cmp-uf" style="font-size:11px;padding:4px 8px;border-radius:5px;border:1px solid #ccc;background:#fff">
            ${ufs.map(sg => `<option value="${sg}" ${sg === cmpUf ? 'selected' : ''}>${sg} — ${lookup[sg]}</option>`).join('')}
          </select>
        </label>
        <span style="font-size:10px;color:#888">Overlays interestaduais usam série oficial estadual (exceto Brasil pública)</span>
      </div>`;
  }

  function bindEvoControls() {
    const cmp = document.getElementById('ideb-se-cmp');
    const ufWrap = document.getElementById('ideb-se-cmp-uf-wrap');
    const ufSel = document.getElementById('ideb-se-cmp-uf');
    if (!cmp) return;
    const apply = () => {
      if (global.S) {
        global.S.idebCmp = cmp.value;
        if (ufSel) global.S.idebCmpUf = ufSel.value;
      }
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
    const ds = [];
    if (cmp === 'brasil') {
      const data = chartLabels.map(a => refs.brasil_publica?.[a]?.[etapa] ?? null);
      if (data.some(v => v != null)) {
        ds.push({
          label: `Brasil pública — ${ET_LABEL[etapa]}`,
          data, _isMeta: true, borderColor: '#90A4AE', borderWidth: 1.5, borderDash: [4, 3],
          pointRadius: 0, tension: 0.3, spanGaps: true,
        });
      }
    } else if (cmp === 'nordeste') {
      const data = chartLabels.map(a => refs.nordeste_estadual?.[a]?.[etapa] ?? null);
      if (data.some(v => v != null)) {
        ds.push({
          label: `Nordeste estadual — ${ET_LABEL[etapa]}`,
          data, _isMeta: true, borderColor: '#78909C', borderWidth: 1.6, borderDash: [5, 4],
          pointRadius: 0, tension: 0.3, spanGaps: true,
        });
      }
    } else if (cmp === 'uf') {
      const sg = (global.S && global.S.idebCmpUf) || 'BA';
      const nome = (ideb.lookup_ufs || {})[sg] || sg;
      const data = chartLabels.map(a => porUf?.[a]?.[sg]?.[etapa] ?? null);
      if (data.some(v => v != null)) {
        ds.push({
          label: `${sg} estadual — ${ET_LABEL[etapa]}`,
          data, _isMeta: true, borderColor: '#5C6BC0', borderWidth: 1.8, borderDash: [6, 4],
          pointRadius: 2, pointBackgroundColor: '#5C6BC0', tension: 0.3, spanGaps: true,
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
