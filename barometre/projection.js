// « Et si Mélenchon affrontait Le Pen ? » : projection du second tour à partir du premier tour des sondages
// et des reports de voix mesurés aux élections passées (donnees/projection_t2.json). Brouillon.
(function () {
  'use strict';
  var box = document.getElementById('proj-chart'); if (!box || !window.d3) return;
  var nf1 = function (v) { return (Math.round(v * 10) / 10).toLocaleString('fr-FR'); };
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
  var J = 864e5, B = ['G', 'AG', 'C', 'D', 'ED', 'NE'];
  Promise.all([fetch('../data.json', { cache: 'no-cache' }).then(function (r) { return r.json(); }), fetch('../donnees/projection_t2.json', { cache: 'no-cache' }).then(function (r) { return r.json(); })])
    .then(function (a) { init(a[0].datasets, a[1]); })
    .catch(function () { box.textContent = 'La projection n\'a pas pu être chargée.'; });

  function init(D, P) {
    var blocOf = {}; Object.keys(P.blocs).forEach(function (b) { P.blocs[b].forEach(function (n) { blocOf[n] = b; }); });
    // Chaque sondage : part moyenne de chaque candidat sur toutes ses hypothèses (0 là où il n'est pas testé),
    // soit son score moyen × hypothèses où il est testé ÷ hypothèses du sondage ; un sondage fait ainsi 100.
    var Hmax = {}; D.sondages_t1.forEach(function (r) { var k = r.date + '|' + r.institut; Hmax[k] = Math.max(Hmax[k] || 1, +r.hypotheses || 1); });
    var T1 = D.sondages_t1.map(function (r) { var k = r.date + '|' + r.institut; return { d: r.date, k: k, c: r.candidat, v: +r.score * (+r.hypotheses || 1) / Hmax[k] }; });
    var last = T1.reduce(function (m, r) { return r.d > m ? r.d : m; }, '');
    var debut = new Date(Date.parse(last) - 365 * J).toISOString().slice(0, 10);
    var hors = {};
    // Premier tour, chaque semaine : moyenne des sondages des 30 jours précédents (les 15 plus récents), regroupée en blocs.
    var jours = []; for (var t = Date.parse(last); t >= Date.parse(debut); t -= 7 * J) jours.unshift(new Date(t).toISOString().slice(0, 10));
    var X = jours.map(function (d) {
      var from = new Date(Date.parse(d) - 30 * J).toISOString().slice(0, 10), polls = {};
      T1.forEach(function (r) { if (r.d > from && r.d <= d) (polls[r.k] = polls[r.k] || { d: r.d, L: [] }).L.push(r); });
      var K = Object.keys(polls).sort(function (a, b) { return polls[a].d < polls[b].d ? -1 : 1; }).slice(-15);
      if (K.length < 2) return null;
      var s = { G: 0, AG: 0, C: 0, D: 0, ED: 0 };
      K.forEach(function (k) { polls[k].L.forEach(function (r) { if (!blocOf[r.c]) { hors[r.c] = 1; return; } s[blocOf[r.c]] += r.v / K.length; }); });
      var tot = s.G + s.AG + s.C + s.D + s.ED; if (!tot || !s.G) return null;
      var e = P.participation_t1.v, x = {}; Object.keys(s).forEach(function (b) { x[b] = s[b] / tot * e; }); x.NE = 1 - e;
      return { d: d, x: x, n: K.length };
    }).filter(Boolean);
    var proj = function (R, x) { var m = 0, l = 0; B.forEach(function (b) { m += x[b] * R[b][0]; l += x[b] * R[b][1]; }); return 100 * m / (m + l); };
    var S = P.scenarios.map(function (s) { return { nom: s.nom, col: s.couleur, R: s.reports, pts: X.map(function (p) { return { d: new Date(p.d), v: proj(s.reports, p.x) }; }) }; });
    // Sondages réels : Mélenchon face à Marine Le Pen.
    var T2 = D.sondages_t2.filter(function (r) { return r.candidat_rn === 'Le Pen' && r.adversaire === 'Mélenchon' && r.date >= debut; })
      .map(function (r) { return { d: new Date(r.date), v: +r.score_adversaire, i: r.institut }; });
    var moyT2 = X.map(function (p) { var to = Date.parse(p.d), L = T2.filter(function (q) { return +q.d <= to && +q.d > to - 30 * J; }); return L.length ? { d: new Date(p.d), v: L.reduce(function (t, q) { return t + q.v; }, 0) / L.length } : null; }).filter(Boolean);
    // Cinquième courbe : réglée par le lecteur.
    var U = JSON.parse(JSON.stringify(P.scenarios[2].reports));
    var cur = { nom: 'Vos reports', col: 'var(--color-fg)', dash: '6 4', R: U, pts: [] };
    var redraw = function () { cur.pts = X.map(function (p) { return { d: new Date(p.d), v: proj(U, p.x) }; }); draw(S.concat([cur]), T2, moyT2); };
    controls(P, U, redraw);
    redraw();
    window.addEventListener('resize', function () { clearTimeout(redraw.t); redraw.t = setTimeout(redraw, 150); });
    var notes = document.getElementById('proj-notes');
    notes.innerHTML = '<ul class="bx-note">' + P.scenarios.map(function (s) { return '<li><b style="color:' + s.couleur + '">' + esc(s.nom) + '</b> : ' + esc(s.detail) + (s.url ? ' (<a href="' + esc(s.url) + '" target="_blank" rel="noopener">source</a>)' : '') + '.</li>'; }).join('') + '</ul>' +
      '<p class="bx-note">Premier tour : chaque semaine, moyenne de chaque candidat dans les sondages des 30 jours précédents, regroupée en cinq blocs. Dans chaque sondage, un candidat compte pour sa moyenne sur toutes les hypothèses, 0 là où il n\'est pas testé (Philippe et Attal, rarement testés ensemble, ne s\'additionnent pas) : chaque sondage fait 100. ' + esc(P.participation_t1.texte) + ' (<a href="' + esc(P.participation_t1.url) + '" target="_blank" rel="noopener">source</a>).' + (Object.keys(hors).length ? ' Pas comptés, faute de bloc défini (ils sont rares) : ' + esc(Object.keys(hors).join(', ')) + '.' : '') + '</p>' +
      '<p class="bx-note">' + esc(P.methode) + '</p>';
  }

  function controls(P, U, redraw) {
    var el = document.getElementById('proj-ctrl');
    var pre = '<div class="bx-cmp-c" role="group" aria-label="Partir d\'un scénario">' + P.scenarios.map(function (s, i) { return '<button type="button" data-s="' + i + '" aria-pressed="' + (i === 2) + '">' + esc(s.nom) + '</button>'; }).join('') + '</div>';
    var rows = ['AG', 'C', 'D'].map(function (b) {
      return '<fieldset class="proj-b"><legend>' + esc(P.noms_blocs[b]) + '</legend>' +
        '<label>Mélenchon <input type="range" min="0" max="100" step="1" data-b="' + b + '" data-k="0"><output></output></label>' +
        '<label>Le Pen <input type="range" min="0" max="100" step="1" data-b="' + b + '" data-k="1"><output></output></label>' +
        '<span class="bx-note" data-abs="' + b + '"></span></fieldset>';
    }).join('');
    el.innerHTML = '<p class="bx-note">Sur 100 électeurs de chaque groupe au premier tour, combien votent Mélenchon, Le Pen ; les autres s\'abstiennent ou votent blanc. Partir de :</p>' + pre + rows;
    var sync = function () {
      el.querySelectorAll('input').forEach(function (i) { var v = Math.round(U[i.dataset.b][+i.dataset.k] * 100); i.value = v; i.nextElementSibling.value = v; i.setAttribute('aria-valuetext', v + ' sur 100'); });
      ['AG', 'C', 'D'].forEach(function (b) { el.querySelector('[data-abs="' + b + '"]').textContent = 'abstention ou blanc : ' + Math.round(U[b][2] * 100); });
    };
    el.addEventListener('input', function (e) {
      var i = e.target; if (!i.dataset || !i.dataset.b) return;
      var b = i.dataset.b, k = +i.dataset.k, o = 1 - k, v = +i.value / 100;
      U[b][k] = v; if (U[b][k] + U[b][o] > 1) U[b][o] = 1 - v; U[b][2] = Math.max(0, 1 - U[b][0] - U[b][1]);
      el.querySelectorAll('.bx-cmp-c button').forEach(function (bt) { bt.setAttribute('aria-pressed', 'false'); });
      sync(); redraw();
    });
    el.querySelector('.bx-cmp-c').addEventListener('click', function (e) {
      var bt = e.target.closest('button'); if (!bt) return; var R = P.scenarios[+bt.dataset.s].reports;
      B.forEach(function (b) { U[b] = R[b].slice(); });
      el.querySelectorAll('.bx-cmp-c button').forEach(function (x) { x.setAttribute('aria-pressed', x === bt ? 'true' : 'false'); });
      sync(); redraw();
    });
    sync();
  }

  function draw(C, T2, moyT2) {
    box.querySelectorAll('svg').forEach(function (n) { n.remove(); });
    var W = box.clientWidth || 600, H = 320, mL = 40, mR = 132;
    var all = [].concat.apply([], C.map(function (c) { return c.pts; })).concat(T2);
    var x = d3.scaleUtc(d3.extent(all, function (r) { return r.d; }), [mL, W - mR]);
    var lo = Math.min(30, Math.floor(d3.min(all, function (r) { return r.v; }) / 5) * 5), hi = Math.max(55, Math.ceil(d3.max(all, function (r) { return r.v; }) / 5) * 5);
    var y = d3.scaleLinear([lo, hi], [H - 28, 12]);
    var svg = d3.select(box).append('svg').attr('width', '100%').attr('viewBox', '0 0 ' + W + ' ' + H).attr('role', 'img').attr('aria-label', 'Score projeté de Jean-Luc Mélenchon face à Marine Le Pen au second tour, selon cinq hypothèses de reports de voix, et sondages');
    svg.append('g').selectAll('line').data(y.ticks(5)).join('line').attr('x1', mL).attr('x2', W - mR).attr('y1', y).attr('y2', y).attr('stroke', 'var(--cds-chart-grid)');
    svg.append('line').attr('x1', mL).attr('x2', W - mR).attr('y1', y(50)).attr('y2', y(50)).attr('stroke', 'var(--cds-chart-reference)').attr('stroke-dasharray', '2 3');
    svg.append('text').attr('x', mL + 4).attr('y', y(50) - 4).style('font-size', 'var(--cds-font-size-caption)').attr('fill', 'var(--color-muted, #6b6d73)').text('50 % : majorité');
    var gy = svg.append('g').attr('transform', 'translate(' + mL + ',0)').call(d3.axisLeft(y).ticks(5).tickFormat(function (v) { return v + ' %'; }).tickSize(0));
    gy.select('.domain').remove(); gy.selectAll('text').style('font-size', 'var(--cds-font-size-caption)').attr('fill', 'currentColor');
    var gx = svg.append('g').attr('transform', 'translate(0,' + (H - 28) + ')').call(d3.axisBottom(x).ticks(Math.max(2, Math.floor((W - mL - mR) / 80))).tickFormat((window.BX && BX.fmtMonth) || d3.utcFormat('%m/%Y')).tickSizeOuter(0));
    gx.selectAll('text').style('font-size', 'var(--cds-font-size-caption)'); gx.select('.domain').attr('stroke', 'var(--cds-chart-axis)'); gx.selectAll('line').attr('stroke', 'var(--cds-chart-axis)');
    var line = d3.line().x(function (r) { return x(r.d); }).y(function (r) { return y(r.v); });
    var labs = [];
    C.forEach(function (c) {
      if (!c.pts.length) return;
      svg.append('path').datum(c.pts).attr('fill', 'none').attr('stroke', c.col).attr('stroke-width', 2).attr('stroke-dasharray', c.dash || null).attr('d', line);
      var l = c.pts[c.pts.length - 1]; labs.push({ y: y(l.v), col: c.col, t: c.nom + ' ' + nf1(l.v) + ' %' });
    });
    svg.append('g').selectAll('circle').data(T2).join('circle').attr('cx', function (r) { return x(r.d); }).attr('cy', function (r) { return y(r.v); }).attr('r', 3.5).attr('fill', 'var(--cds-chart-muted)').attr('stroke', 'var(--color-fg)').attr('stroke-width', 1)
      .append('title').text(function (r) { return r.i + ', ' + r.d.toLocaleDateString('fr-FR') + ' : Mélenchon ' + nf1(r.v) + ' %'; });
    if (moyT2.length > 1) { svg.append('path').datum(moyT2).attr('fill', 'none').attr('stroke', 'var(--color-fg)').attr('stroke-width', 1.5).attr('stroke-dasharray', '1 3').attr('d', line); }
    if (moyT2.length) { var lm = moyT2[moyT2.length - 1]; labs.push({ y: y(lm.v), col: 'var(--color-fg)', t: 'Sondages ' + nf1(lm.v) + ' %' }); }
    labs.sort(function (a, b) { return a.y - b.y; });
    for (var i = 1; i < labs.length; i++) if (labs[i].y - labs[i - 1].y < 14) labs[i].y = labs[i - 1].y + 14;
    svg.append('g').selectAll('text').data(labs).join('text').attr('x', W - mR + 6).attr('y', function (l) { return l.y + 4; }).attr('fill', function (l) { return l.col; })
      .style('font-size', 'var(--cds-font-size-caption)').style('font-weight', 600).text(function (l) { return l.t; });
  }
})();
