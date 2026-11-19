// « Et si… ? » : second tour face à Marine Le Pen, projeté à partir du premier tour des sondages et des reports
// de voix observés aux élections passées (donnees/projection_t2.json). Brouillon.
(function () {
  'use strict';
  var box = document.getElementById('proj-chart'); if (!box || !window.d3) return;
  var nf1 = function (v) { return (Math.round(v * 10) / 10).toLocaleString('fr-FR'); };
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
  var J = 864e5, B = ['FI', 'AG', 'C', 'D', 'ED', 'XD', 'NE'], $ = function (id) { return document.getElementById(id); };
  var COL = { x: '#e07b1f', lp: '#1d2a5c', ab: '#b9bcc4' };
  Promise.all([fetch('../data.json', { cache: 'no-cache' }).then(function (r) { return r.json(); }), fetch('../donnees/projection_t2.json', { cache: 'no-cache' }).then(function (r) { return r.json(); })])
    .then(function (a) { init(a[0].datasets, a[1]); })
    .catch(function () { box.textContent = 'La projection n\'a pas pu être chargée.'; });

  function init(D, P) {
    var blocOf = {}; Object.keys(P.blocs).forEach(function (b) { P.blocs[b].forEach(function (n) { blocOf[n] = b; }); });
    // Chaque sondage : part moyenne de chaque candidat sur toutes ses hypothèses (0 là où il n'est pas testé) ; un sondage fait 100.
    var Hmax = {}; D.sondages_t1.forEach(function (r) { var k = r.date + '|' + r.institut; Hmax[k] = Math.max(Hmax[k] || 1, +r.hypotheses || 1); });
    var T1 = D.sondages_t1.map(function (r) { var k = r.date + '|' + r.institut; return { d: r.date, k: k, c: r.candidat, v: +r.score * (+r.hypotheses || 1) / Hmax[k] }; });
    var last = T1.reduce(function (m, r) { return r.d > m ? r.d : m; }, ''), debut = new Date(Date.parse(last) - 365 * J).toISOString().slice(0, 10);
    var jours = []; for (var t = Date.parse(last); t >= Date.parse(debut); t -= 7 * J) jours.unshift(new Date(t).toISOString().slice(0, 10));
    var X = jours.map(function (d) {
      var from = new Date(Date.parse(d) - 30 * J).toISOString().slice(0, 10), polls = {};
      T1.forEach(function (r) { if (r.d > from && r.d <= d) (polls[r.k] = polls[r.k] || { d: r.d, L: [] }).L.push(r); });
      var K = Object.keys(polls).sort(function (a, b) { return polls[a].d < polls[b].d ? -1 : 1; }).slice(-15);
      if (K.length < 2) return null;
      var s = { FI: 0, AG: 0, C: 0, D: 0, ED: 0, XD: 0 };
      K.forEach(function (k) { polls[k].L.forEach(function (r) { if (blocOf[r.c]) s[blocOf[r.c]] += r.v / K.length; }); });
      var tot = s.FI + s.AG + s.C + s.D + s.ED + s.XD; if (!tot) return null;
      var e = P.participation_t1.v, x = {}; Object.keys(s).forEach(function (b) { x[b] = s[b] / tot * e; }); x.NE = 1 - e;
      return { d: new Date(d), x: x };
    }).filter(Boolean);
    var proj = function (R, x) { var m = 0, l = 0; B.forEach(function (b) { m += x[b] * R[b][0]; l += x[b] * R[b][1]; }); return 100 * m / (m + l); };
    var noms = Object.keys(P.duels), duel = noms[0], U = null, perso = false;
    var tabs = $('proj-duels');
    tabs.innerHTML = noms.map(function (n) { return '<button type="button" data-d="' + esc(n) + '">' + esc(n) + '</button>'; }).join('');
    var data = function () {
      var Q = P.duels[duel];
      var lines = Q.precedents.map(function (p) { return { nom: p.nom, col: p.couleur, pts: X.map(function (q) { return { d: q.d, v: proj(p.reports, q.x) }; }) }; });
      if (perso) lines.push({ nom: 'Votre courbe', col: 'var(--color-fg)', dash: '6 4', pts: X.map(function (q) { return { d: q.d, v: proj(U, q.x) }; }) });
      var T2 = D.sondages_t2.filter(function (r) { return r.candidat_rn === 'Le Pen' && P.duels[duel].adversaires.indexOf(r.adversaire) >= 0 && r.date >= debut; }).map(function (r) { return { d: new Date(r.date), v: +r.score_adversaire, i: r.institut + (P.duels[duel].adversaires.length > 1 ? ' (' + r.adversaire + ')' : '') }; });
      var moy = X.map(function (q) { var L = T2.filter(function (s) { return +s.d <= +q.d && +s.d > +q.d - 30 * J; }); return L.length ? { d: q.d, v: L.reduce(function (t, s) { return t + s.v; }, 0) / L.length } : null; }).filter(Boolean);
      draw(lines, T2, moy, duel);
    };
    var show = function () {
      var Q = P.duels[duel];
      tabs.querySelectorAll('button').forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.d === duel ? 'true' : 'false'); });
      if (!U) U = JSON.parse(JSON.stringify(Q.precedents[0].reports));
      $('proj-titre').textContent = duel + ' face à Marine Le Pen : score de ' + duel + ' au second tour, en % des voix (trait épais : 50 %, au-dessus il l\'emporte)';
      data(); table(Q, P, duel); controls(Q, P, duel);
      $('proj-meth').textContent = P.methode + ' Premier tour : chaque semaine, moyenne des sondages des 30 jours précédents ; dans chaque sondage, un candidat compte pour sa moyenne sur toutes les hypothèses (0 là où il n\'est pas testé). ' + P.participation_t1.texte + '.';
    };
    tabs.addEventListener('click', function (e) { var b = e.target.closest('button'); if (b) { duel = b.dataset.d; U = null; perso = false; show(); } });
    show();
    window.addEventListener('resize', function () { clearTimeout(data.t); data.t = setTimeout(data, 150); });
    // Réglages : trois curseurs liés par groupe (le total fait toujours 100).
    $('proj-ctrl').addEventListener('input', function (e) {
      var i = e.target; if (!i.dataset || !i.dataset.b) return;
      var r = U[i.dataset.b], k = +i.dataset.k, v = +i.value / 100, o = [0, 1, 2].filter(function (j) { return j !== k; }), rest = r[o[0]] + r[o[1]];
      r[k] = v; if (rest > 0) { r[o[0]] = (1 - v) * r[o[0]] / rest; r[o[1]] = (1 - v) * r[o[1]] / rest; } else { r[o[0]] = r[o[1]] = (1 - v) / 2; }
      $('proj-ctrl').querySelectorAll('.bx-cmp-c button').forEach(function (b) { b.setAttribute('aria-pressed', 'false'); });
      perso = true; syncCtrl(); data();
    });
    $('proj-ctrl').addEventListener('click', function (e) {
      var b = e.target.closest('.bx-cmp-c button'); if (!b) return;
      U = JSON.parse(JSON.stringify(P.duels[duel].precedents[+b.dataset.p].reports));
      $('proj-ctrl').querySelectorAll('.bx-cmp-c button').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      perso = true; syncCtrl(); data();
    });
    function syncCtrl() {
      $('proj-ctrl').querySelectorAll('input').forEach(function (i) { var v = Math.round(U[i.dataset.b][+i.dataset.k] * 100); i.value = v; i.nextElementSibling.value = v; i.setAttribute('aria-valuetext', v + ' sur 100'); });
    }
    function controls(Q, P, duel) {
      var G = B.filter(function (b) { return b !== Q.bloc && b !== 'NE' && b !== 'ED'; });
      $('proj-ctrl').innerHTML = '<p class="bx-note">Les courbes de couleur ne bougent pas. Bougez un curseur : <b>votre courbe</b> apparaît en pointillés noirs. Point de départ :</p>' +
        '<div class="bx-cmp-c" role="group" aria-label="Copier les chiffres d\'une élection passée">' + Q.precedents.map(function (p, i) { return '<button type="button" data-p="' + i + '" aria-pressed="false">' + esc(p.nom.replace(/^Comme (aux |à la )?/, '').replace('un candidat PS ou écologiste en 2024', 'si vu comme PS (2024)').replace(/^./, function (c) { return c.toUpperCase(); })) + '</button>'; }).join('') + '</div>' +
        G.map(function (b) {
          return '<fieldset class="proj-b"><legend>Sur 100 ' + esc(P.noms_blocs[b]) + '</legend>' +
            [[0, esc(duel)], [1, 'Le Pen'], [2, 'Abstention ou blanc']].map(function (k) { return '<label>' + k[1] + ' <input type="range" min="0" max="100" step="1" data-b="' + b + '" data-k="' + k[0] + '"><output></output></label>'; }).join('') + '</fieldset>';
        }).join('');
      syncCtrl();
    }
  }

  // « D'où viennent ces courbes » : chaque précédent en une phrase, puis ce qu'il suppose pour chaque groupe d'électeurs.
  function table(Q, P, duel) {
    var bar = function (r) {
      var w = r.map(function (v) { return Math.round(v * 100); });
      return '<span class="proj-bar" role="img" aria-label="' + w[0] + ' ' + esc(duel) + ', ' + w[1] + ' Le Pen, ' + w[2] + ' abstention ou blanc"><i style="width:' + w[0] + '%;background:' + COL.x + '"></i><i style="width:' + w[1] + '%;background:' + COL.lp + '"></i><i style="width:' + w[2] + '%;background:' + COL.ab + '"></i></span><small>' + w[0] + ' · ' + w[1] + ' · ' + w[2] + '</small>';
    };
    var G = B.filter(function (b) { return b !== Q.bloc && b !== 'ED'; });
    $('proj-src').innerHTML =
      '<ul class="proj-prec">' + Q.precedents.map(function (p) { return '<li><b style="color:' + p.couleur + '">' + esc(p.nom) + '</b> : ' + esc(p.phrase) + '. <a href="' + esc(p.url) + '" target="_blank" rel="noopener">Résultats officiels</a>.</li>'; }).join('') + '</ul>' +
      '<p class="bx-note">Ce que chaque précédent suppose, sur 100 électeurs de chaque groupe : <b style="color:' + COL.x + '">votent ' + esc(duel) + '</b> · <b style="color:' + COL.lp + '">votent Le Pen</b> · <b>s\'abstiennent ou votent blanc</b>. Partout, les électeurs de ' + esc(duel) + (Q.bloc === 'C' || Q.bloc === 'D' ? ' et de son camp' : '') + ' votent pour lui, ceux de Le Pen pour elle.</p>' +
      '<div class="proj-tw"><table class="proj-t"><thead><tr><th></th>' + Q.precedents.map(function (p) { return '<th style="color:' + p.couleur + '">' + esc(p.nom.replace('Comme ', '')) + '</th>'; }).join('') + '</tr></thead><tbody>' +
      G.map(function (b) { var nc = P.noms_courts[b]; return '<tr><th>' + esc(nc[0]) + (nc[1] ? '<small>' + esc(nc[1]) + '</small>' : '') + (b === 'FI' && Q.bloc === 'AG' ? '<small>non mesuré : comme les autres électeurs de gauche</small>' : '') + '</th>' + Q.precedents.map(function (p) { return '<td>' + bar(p.reports[b]) + '</td>'; }).join('') + '</tr>'; }).join('') +
      '</tbody></table></div>';
  }

  function draw(C, T2, moy, duel) {
    box.querySelectorAll('svg').forEach(function (n) { n.remove(); });
    var W = box.clientWidth || 600, H = 320, mL = 40, mR = 150;
    var all = [].concat.apply([], C.map(function (c) { return c.pts; })).concat(T2);
    var x = d3.scaleUtc(d3.extent(all, function (r) { return r.d; }), [mL, W - mR]);
    var lo = Math.min(30, Math.floor(d3.min(all, function (r) { return r.v; }) / 5) * 5), hi = Math.max(55, Math.ceil(d3.max(all, function (r) { return r.v; }) / 5) * 5);
    var y = d3.scaleLinear([lo, hi], [H - 28, 12]);
    var svg = d3.select(box).append('svg').attr('width', '100%').attr('viewBox', '0 0 ' + W + ' ' + H).attr('role', 'img').attr('aria-label', 'Score projeté de ' + duel + ' face à Marine Le Pen selon les précédents, et sondages');
    svg.append('g').selectAll('line').data(y.ticks(5)).join('line').attr('x1', mL).attr('x2', W - mR).attr('y1', y).attr('y2', y).attr('stroke', 'var(--cds-chart-grid)');
    svg.append('line').attr('x1', mL).attr('x2', W - mR).attr('y1', y(50)).attr('y2', y(50)).attr('stroke', 'var(--cds-chart-reference)').attr('stroke-width', 1.5);
    var gy = svg.append('g').attr('transform', 'translate(' + mL + ',0)').call(d3.axisLeft(y).ticks(5).tickFormat(function (v) { return v + ' %'; }).tickSize(0));
    gy.select('.domain').remove(); gy.selectAll('text').style('font-size', 'var(--cds-font-size-caption)');
    var gx = svg.append('g').attr('transform', 'translate(0,' + (H - 28) + ')').call(d3.axisBottom(x).ticks(d3.utcMonth.every((W - mL - mR) < 300 ? 4 : 2)).tickFormat((window.BX && BX.fmtMonth) || d3.utcFormat('%m/%Y')).tickSizeOuter(0));
    gx.selectAll('text').style('font-size', 'var(--cds-font-size-caption)'); gx.select('.domain').attr('stroke', 'var(--cds-chart-axis)'); gx.selectAll('line').attr('stroke', 'var(--cds-chart-axis)');
    var line = d3.line().x(function (r) { return x(r.d); }).y(function (r) { return y(r.v); }), labs = [];
    C.forEach(function (c) {
      if (!c.pts.length) return;
      svg.append('path').datum(c.pts).attr('fill', 'none').attr('stroke', c.col).attr('stroke-width', 2).attr('stroke-dasharray', c.dash || null).attr('d', line);
      var l = c.pts[c.pts.length - 1]; labs.push({ y: y(l.v), col: c.col, t: c.nom.replace('Comme ', '').replace('aux législatives', 'législ.').replace('à la présidentielle', 'présid.').replace('un candidat PS ou écologiste en 2024', 'vu comme PS') + ' ' + nf1(l.v) + ' %' });
    });
    svg.append('g').selectAll('circle').data(T2).join('circle').attr('cx', function (r) { return x(r.d); }).attr('cy', function (r) { return y(r.v); }).attr('r', 3.5).attr('fill', 'var(--cds-chart-muted)').attr('stroke', 'var(--color-fg)')
      .append('title').text(function (r) { return r.i + ', ' + r.d.toLocaleDateString('fr-FR') + ' : ' + duel + ' ' + nf1(r.v) + ' %'; });
    if (moy.length > 1) svg.append('path').datum(moy).attr('fill', 'none').attr('stroke', 'var(--color-fg)').attr('stroke-width', 1.5).attr('stroke-dasharray', '1 3').attr('d', line);
    if (moy.length) { var lm = moy[moy.length - 1]; var dT = T2.reduce(function (m, r) { return +r.d > +m ? r.d : m; }, T2[0].d), vieux = +C[0].pts[C[0].pts.length - 1].d - +dT > 45 * 864e5; labs.push({ y: y(lm.v), col: 'var(--color-fg)', t: 'Sondages ' + nf1(lm.v) + ' %' + (vieux ? ' (dernier : ' + dT.toLocaleDateString('fr-FR', { month: 'short', year: 'numeric' }) + ')' : '') }); }
    labs.sort(function (a, b) { return a.y - b.y; });
    for (var i = 1; i < labs.length; i++) if (labs[i].y - labs[i - 1].y < 14) labs[i].y = labs[i - 1].y + 14;
    svg.append('g').selectAll('text').data(labs).join('text').attr('x', W - mR + 6).attr('y', function (l) { return l.y + 4; }).attr('fill', function (l) { return l.col; })
      .style('font-size', 'var(--cds-font-size-caption)').style('font-weight', 600).text(function (l) { return l.t; });
  }
})();
