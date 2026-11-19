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
    // « Premier tour : les blocs » : la même moyenne, regroupée en quatre blocs.
    var bb = document.getElementById('blocs-chart');
    if (bb) {
      var BL = [{ k: ['FI', 'AG'], nom: 'Gauche', col: '#c0392b' }, { k: ['C'], nom: 'Centre', col: '#d39e00' }, { k: ['D', 'ED', 'XD'], nom: 'Droite', col: '#2f4fa8' }];
      var e0 = P.participation_t1.v, SB = BL.map(function (g) { return { nom: g.nom, col: g.col, pts: X.map(function (q) { return { d: q.d, v: g.k.reduce(function (t, b) { return t + q.x[b]; }, 0) / e0 * 100 }; }) }; });
      var lfi = X.map(function (q) { return { d: q.d, v: q.x.FI / e0 * 100 }; }), rn = X.map(function (q) { return { d: q.d, v: q.x.ED / e0 * 100 }; });
      var dessine = function () {
        bb.querySelectorAll('svg').forEach(function (n) { n.remove(); });
        var W = bb.clientWidth || 600, H = 280, mL = 40, mR = 120, all = [].concat.apply([], SB.map(function (c) { return c.pts; }));
        var x = d3.scaleUtc(d3.extent(all, function (r) { return r.d; }), [mL, W - mR]), y = d3.scaleLinear([0, Math.ceil(d3.max(all, function (r) { return r.v; }) / 10) * 10], [H - 28, 12]);
        var svg = d3.select(bb).append('svg').attr('width', '100%').attr('viewBox', '0 0 ' + W + ' ' + H).attr('role', 'img').attr('aria-label', 'Part de chaque bloc au premier tour, moyenne des sondages');
        svg.append('g').selectAll('line').data(y.ticks(5)).join('line').attr('x1', mL).attr('x2', W - mR).attr('y1', y).attr('y2', y).attr('stroke', 'var(--cds-chart-grid)');
        var gy = svg.append('g').attr('transform', 'translate(' + mL + ',0)').call(d3.axisLeft(y).ticks(5).tickFormat(function (v) { return v + ' %'; }).tickSize(0)); gy.select('.domain').remove(); gy.selectAll('text').style('font-size', 'var(--cds-font-size-caption)');
        var gx = svg.append('g').attr('transform', 'translate(0,' + (H - 28) + ')').call(d3.axisBottom(x).ticks(d3.utcMonth.every((W - mL - mR) < 300 ? 4 : 2)).tickFormat((window.BX && BX.fmtMonth) || d3.utcFormat('%m/%Y')).tickSizeOuter(0));
        gx.selectAll('text').style('font-size', 'var(--cds-font-size-caption)'); gx.select('.domain').attr('stroke', 'var(--cds-chart-axis)'); gx.selectAll('line').attr('stroke', 'var(--cds-chart-axis)');
        var line = d3.line().x(function (r) { return x(r.d); }).y(function (r) { return y(r.v); }), labs = [];
        SB.forEach(function (c) { svg.append('path').datum(c.pts).attr('fill', 'none').attr('stroke', c.col).attr('stroke-width', 2.2).attr('d', line); var l = c.pts[c.pts.length - 1]; labs.push({ y: y(l.v), col: c.col, t: c.nom, v: nf1(l.v) + ' %' }); });
        svg.append('path').datum(lfi).attr('fill', 'none').attr('stroke', '#c0392b').attr('stroke-width', 1.4).attr('stroke-dasharray', '4 3').attr('d', line);
        var ll = lfi[lfi.length - 1]; labs.push({ y: y(ll.v), col: '#c0392b', t: 'dont Mélenchon', v: nf1(ll.v) + ' %' });
        svg.append('path').datum(rn).attr('fill', 'none').attr('stroke', '#2f4fa8').attr('stroke-width', 1.4).attr('stroke-dasharray', '4 3').attr('d', line); var lr = rn[rn.length - 1]; labs.push({ y: y(lr.v), col: '#2f4fa8', t: 'dont Le Pen', v: nf1(lr.v) + ' %' });
        labs.sort(function (a, b) { return a.y - b.y; }); for (var i = 1; i < labs.length; i++) if (labs[i].y - labs[i - 1].y < 28) labs[i].y = labs[i - 1].y + 28;
        if (labs.length) { labs[labs.length - 1].y = Math.min(labs[labs.length - 1].y, H - 24); for (var k2 = labs.length - 2; k2 >= 0; k2--) labs[k2].y = Math.min(labs[k2].y, labs[k2 + 1].y - 28); }
        svg.append('g').selectAll('text').data(labs).join('text').attr('x', W - mR + 6).attr('y', function (l) { return l.y + 4; }).attr('fill', function (l) { return l.col; }).style('font-size', 'var(--cds-font-size-caption)').style('font-weight', 600).each(function (l) { var t = d3.select(this); t.append('tspan').text(l.t); t.append('tspan').attr('x', W - mR + 6).attr('dy', '1.15em').style('font-weight', 700).text(l.v); });
        if (window.BX && BX.xhair) { var dates = SB[0].pts.map(function (q) { return q.d; }); BX.xhair(svg, bb, W, 12, H - 28, function (sx) { var d = dates[d3.bisector(function (q) { return q; }).center(dates, x.invert(sx))]; var rows = SB.map(function (c) { var q = c.pts.filter(function (p) { return +p.d === +d; })[0]; return { c: c.col, n: c.nom, v: q.v, py: y(q.v), s: nf1(q.v) + ' %' }; }); var f = lfi.filter(function (p) { return +p.d === +d; })[0]; rows.push({ c: '#c0392b', n: 'dont Mélenchon', v: f.v, py: y(f.v), s: nf1(f.v) + ' %' }); var g = rn.filter(function (p) { return +p.d === +d; })[0]; rows.push({ c: '#2f4fa8', n: 'dont Le Pen', v: g.v, py: y(g.v), s: nf1(g.v) + ' %' }); rows.sort(function (a, b) { return b.v - a.v; }); return { px: x(d), head: 'Semaine du ' + d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' }), rows: rows }; }); }
      };
      dessine(); window.addEventListener('resize', function () { clearTimeout(dessine.t); dessine.t = setTimeout(dessine, 150); });
      var nm = function (b) { return P.blocs[b].filter(function (n) { return T1.some(function (r) { return r.c === n; }); }).join(', '); };
      document.getElementById('blocs-def').textContent = 'Gauche, y compris l\'extrême gauche : ' + nm('FI') + ', ' + nm('AG') + '. Centre : ' + nm('C') + '. Droite, y compris l\'extrême droite : ' + nm('D') + ', ' + nm('ED') + ', ' + nm('XD') + '. En pointillé, Mélenchon et Le Pen seuls. Classement de Concret, le même que pour les projections du second tour.';
    }
    var proj = function (R, x) { var m = 0, l = 0; B.forEach(function (b) { m += x[b] * R[b][0]; l += x[b] * R[b][1]; }); return 100 * m / (m + l); };
    var noms = Object.keys(P.duels), duel = noms[0], U = null, perso = false, touche = false;
    var tabs = $('proj-duels');
    tabs.innerHTML = noms.map(function (n) { return '<button type="button" data-d="' + esc(n) + '">' + esc(n) + '</button>'; }).join('');
    var data = function () {
      var Q = P.duels[duel];
      var lines = Q.precedents.map(function (p) { return { nom: p.nom, court: p.court, col: p.couleur, pts: X.map(function (q) { return { d: q.d, v: proj(p.reports, q.x) }; }) }; });
      if (perso && touche) lines.push({ nom: 'Votre courbe', col: '#8a2be2', perso: true, pts: X.map(function (q) { return { d: q.d, v: proj(U, q.x) }; }) });
      var T2 = D.sondages_t2.filter(function (r) { return r.candidat_rn === 'Le Pen' && P.duels[duel].adversaires.indexOf(r.adversaire) >= 0 && r.date >= debut; }).map(function (r) { return { d: new Date(r.date), v: +r.score_adversaire, i: r.institut + (P.duels[duel].adversaires.length > 1 ? ' (' + r.adversaire + ')' : '') }; });
      var moy = X.map(function (q) { var L = T2.filter(function (s) { return +s.d <= +q.d && +s.d > +q.d - 30 * J; }); return L.length ? { d: q.d, v: L.reduce(function (t, s) { return t + s.v; }, 0) / L.length } : null; }).filter(Boolean);
      $('projection').classList.toggle('proj-regle', perso && !$('proj-ctrl').hidden);
      draw(lines, T2, moy, duel);
      var rs = $('proj-res'); if (rs) { rs.hidden = !perso; if (perso) { if (!touche) rs.textContent = 'Touchez + ou − ci-dessous : votre courbe apparaît ici, en violet.'; else { var v = lines[lines.length - 1].pts; rs.innerHTML = '<b style="color:#8a2be2">Votre courbe : ' + nf1(v[v.length - 1].v) + ' %</b>' + (moy.length ? ' · sondages ' + nf1(moy[moy.length - 1].v) + ' %' : '') + ' · il faut 50 %'; } } }
      $('projection').classList.toggle('proj-regle', perso && !$('proj-ctrl').hidden); colle();
    };
    var colle = function () { var h = 0; document.querySelectorAll('body *').forEach(function (n) { var cs = getComputedStyle(n); if ((cs.position === 'fixed' || cs.position === 'sticky') && n.offsetHeight < 200 && !n.closest('#projection')) { var r = n.getBoundingClientRect(); if (r.top < 200 && r.bottom < 320 && r.bottom > h) h = r.bottom; } }); $('proj-colle').style.top = Math.round(h) + 'px'; };
    var leg = function () { var Q = P.duels[duel]; $('proj-leg').innerHTML = '<li class="proj-leg-h">Projections, pas des résultats passés :</li>' + Q.precedents.map(function (p) { return '<li><i style="background:' + p.couleur + '"></i><b style="color:' + p.couleur + '">' + esc(p.court) + '</b> : ' + esc(p.legende) + '</li>'; }).join('') + (perso && touche ? '<li><i style="background:#8a2be2;height:4px"></i><b style="color:#8a2be2">Votre courbe</b> : vos réglages, pour ce duel</li>' : '') + '<li><i class="pt"></i><b>Sondages</b> (trait plein et points gris) : les vrais sondages qui testent ce duel, et leur moyenne</li>'; };
    var show = function () {
      var Q = P.duels[duel];
      tabs.querySelectorAll('button').forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.d === duel ? 'true' : 'false'); });
      if (!U) U = JSON.parse(JSON.stringify(Q.precedents[0].reports));
      $('proj-titre').textContent = duel + ' face à Marine Le Pen : score projeté de ' + duel + ', en % des voix';
      $('proj-lead').textContent = 'Au-dessus de la ligne grise (50 %), ' + duel + ' l\'emporte.';
      data(); table(Q, P, duel);
      leg();
      if (P.reperes) { $('proj-rep').textContent = P.reperes.ligne; $('proj-test').innerHTML = P.reperes.detail.map(function (t) { return '<p class="bx-note">' + esc(t) + '</p>'; }).join('') + '<p class="bx-note">' + P.reperes.sources.map(function (x) { return '<a href="' + esc(x.u) + '" target="_blank" rel="noopener">' + esc(x.t) + '</a>'; }).join(' · ') + '</p>'; }
      $('proj-meth').textContent = P.methode + ' Premier tour : chaque semaine, moyenne des sondages des 30 jours précédents ; dans chaque sondage, un candidat compte pour sa moyenne sur toutes les hypothèses (0 là où il n\'est pas testé). Participation supposée : celle du premier tour de 2022, où ' + (P.participation_t1.v * 100).toFixed(2).replace('.', ',') + ' % des inscrits avaient voté pour un candidat ; les autres inscrits forment le groupe « n\'ont pas voté au 1er tour ».';
    };
    var add = $('proj-add'), panel = $('proj-ctrl');
    var ouvrir = function (on) { perso = on; touche = false; panel.hidden = !on; add.setAttribute('aria-expanded', on ? 'true' : 'false'); add.textContent = on ? 'Masquer les curseurs ▴' : '+ Tracer votre courbe'; if (on) { U = JSON.parse(JSON.stringify(P.duels[duel].precedents[0].reports)); controls(P.duels[duel], P, duel); } data(); leg(); };
    add.addEventListener('click', function () { if (perso && touche && !panel.hidden) { panel.hidden = true; add.setAttribute('aria-expanded', 'false'); add.textContent = 'Afficher les curseurs ▾'; data(); return; } ouvrir(!perso); });
    var voir = function () { var c = $('proj-titre'); window.scrollTo({ top: c.getBoundingClientRect().top + window.scrollY - 140, behavior: 'smooth' }); };
    $('projection').addEventListener('click', function (e) { var a = e.target.closest('.proj-voir'); if (a) { e.preventDefault(); voir(); } });
    panel.addEventListener('click', function (e) { if (e.target.closest('.proj-fin')) { ouvrir(false); add.focus(); } else if (e.target.closest('.proj-act .proj-voir')) { panel.hidden = true; add.setAttribute('aria-expanded', 'false'); add.textContent = 'Afficher les curseurs ▾'; data(); } });
    add.addEventListener('click', function (e) { if (perso && panel.hidden) { e.stopImmediatePropagation(); panel.hidden = false; add.setAttribute('aria-expanded', 'true'); add.textContent = 'Masquer les curseurs ▴'; data(); } }, true);
    tabs.addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; var garde = perso && touche ? U : null, ancien = P.duels[duel].bloc; duel = b.dataset.d; U = null; show(); if (perso) { ouvrir(true); if (garde) { var nv = P.duels[duel]; garde[ancien] = nv.precedents[0].reports[ancien].slice(); garde[nv.bloc] = [1, 0, 0]; U = garde; touche = true; controls(nv, P, duel); data(); leg(); } } });
    show();
    window.addEventListener('resize', function () { clearTimeout(data.t); data.t = setTimeout(data, 150); });
    // Réglages : trois curseurs liés par groupe (le total fait toujours 100).
    var regle = function (bk, k, v) {
      var r = U[bk], o = [0, 1, 2].filter(function (j) { return j !== k; }), rest = r[o[0]] + r[o[1]];
      r[k] = v; if (rest > 0) { r[o[0]] = (1 - v) * r[o[0]] / rest; r[o[1]] = (1 - v) * r[o[1]] / rest; } else { r[o[0]] = r[o[1]] = (1 - v) / 2; }
      $('proj-ctrl').querySelectorAll('.bx-cmp-c button').forEach(function (b) { b.setAttribute('aria-pressed', 'false'); });
      perso = true; touche = true; syncCtrl(); data(); leg();
    };
    var glisse = null, posv = function (i, x) { var r = i.getBoundingClientRect(); return Math.max(0, Math.min(1, (x - r.left - 10) / (r.width - 20))); };
    $('proj-ctrl').addEventListener('pointerdown', function (e) { var i = e.target; if (i.type !== 'range') return; e.preventDefault(); glisse = i; try { i.setPointerCapture(e.pointerId); } catch (x) {} regle(i.dataset.b, +i.dataset.k, Math.round(posv(i, e.clientX) * 100) / 100); });
    $('proj-ctrl').addEventListener('pointermove', function (e) { if (glisse && e.target === glisse) regle(glisse.dataset.b, +glisse.dataset.k, Math.round(posv(glisse, e.clientX) * 100) / 100); });
    ['pointerup', 'pointercancel'].forEach(function (t) { $('proj-ctrl').addEventListener(t, function () { glisse = null; }); });
    var pas = function (pm) { var c = U[pm.dataset.b][+pm.dataset.k]; regle(pm.dataset.b, +pm.dataset.k, Math.max(0, Math.min(1, Math.round(c * 100 + +pm.dataset.d) / 100))); };
    var rep_ = null, stop = function () { clearTimeout(rep_); clearInterval(rep_); rep_ = null; };
    $('proj-ctrl').addEventListener('pointerdown', function (e) { var pm = e.target.closest('.proj-pm'); if (!pm) return; e.preventDefault(); pas(pm); stop(); rep_ = setTimeout(function () { rep_ = setInterval(function () { pas(pm); }, 130); }, 420); });
    ['pointerup', 'pointercancel', 'pointerleave'].forEach(function (t) { $('proj-ctrl').addEventListener(t, stop); });
    $('proj-ctrl').addEventListener('contextmenu', function (e) { if (e.target.closest('.proj-pm')) e.preventDefault(); });
    $('proj-ctrl').addEventListener('input', function (e) { var i = e.target; if (i.dataset && i.dataset.b && i.type === 'range') regle(i.dataset.b, +i.dataset.k, +i.value / 100); });
    $('proj-ctrl').addEventListener('click', function (e) {
      var pm = e.target.closest('.proj-pm'); if (pm) { if (e.detail === 0) pas(pm); return; }
      var b = e.target.closest('.bx-cmp-c button'); if (!b) return;
      U = JSON.parse(JSON.stringify(P.duels[duel].precedents[+b.dataset.p].reports));
      $('proj-ctrl').querySelectorAll('.bx-cmp-c button').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      perso = true; touche = true; syncCtrl(); data(); leg();
    });
    function syncCtrl() {
      $('proj-ctrl').querySelectorAll('output[data-b]').forEach(function (o) { o.value = cent(U[o.dataset.b])[+o.dataset.k]; });
    }
    function controls(Q, P, duel) {
      var G = B.filter(function (b) { return b !== Q.bloc && b !== 'NE' && b !== 'ED'; });
      $('proj-ctrl').innerHTML = '<p class="bx-note">Touchez + ou − (gardez le doigt appuyé pour aller vite). Les trois chiffres de chaque groupe font toujours 100.</p><p class="proj-dep">Point de départ :</p>' +
        '<div class="bx-cmp-c" role="group" aria-label="Copier les chiffres d\'une élection passée">' + Q.precedents.map(function (p, i) { return '<button type="button" data-p="' + i + '" aria-pressed="' + (i === 0) + '">' + esc(p.court) + '</button>'; }).join('') + '</div>' +
        G.map(function (b) {
          return '<fieldset class="proj-b"><legend>Sur 100 ' + esc(P.noms_blocs[b]) + '</legend>' +
            [[0, esc(duel)], [1, 'Le Pen'], [2, 'Abstention']].map(function (k) { return '<div class="proj-r"><span class="proj-n">' + k[1] + '</span><button type="button" class="proj-pm" data-b="' + b + '" data-k="' + k[0] + '" data-d="-5" aria-label="' + k[1] + ' moins 5">−</button><output data-b="' + b + '" data-k="' + k[0] + '" aria-live="polite"></output><button type="button" class="proj-pm" data-b="' + b + '" data-k="' + k[0] + '" data-d="5" aria-label="' + k[1] + ' plus 5">+</button></div>'; }).join('') + '</fieldset>';
        }).join('') + '<p class="bx-note">Dans tous les cas, les électeurs de ' + esc(duel) + ' votent pour lui, ceux de Le Pen pour elle.</p><div class="proj-act"><a href="#proj-titre" class="proj-voir">Fermer les réglages</a><button type="button" class="proj-fin">Retirer votre courbe</button></div>';
      syncCtrl();
    }
  }

  // « D'où viennent ces courbes » : chaque précédent en une phrase, puis ce qu'il suppose pour chaque groupe d'électeurs.
  function cent(r) { var a = r.map(function (v) { return v * 100; }), f = a.map(Math.floor), reste = 100 - f.reduce(function (t, v) { return t + v; }, 0); a.map(function (v, i) { return [v - f[i], i]; }).sort(function (x, y) { return y[0] - x[0]; }).slice(0, Math.max(0, reste)).forEach(function (z) { f[z[1]]++; }); return f; }
  function table(Q, P, duel) {
    var bar = function (r) {
      var w = cent(r);
      return '<span class="proj-bar" role="img" aria-label="' + w[0] + ' ' + esc(duel) + ', ' + w[1] + ' Le Pen, ' + w[2] + ' abstention ou blanc"><i style="width:' + w[0] + '%;background:' + COL.x + '"></i><i style="width:' + w[1] + '%;background:' + COL.lp + '"></i><i style="width:' + w[2] + '%;background:' + COL.ab + '"></i></span><small>' + w[0] + ' · ' + w[1] + ' · ' + w[2] + '</small>';
    };
    var G = B.filter(function (b) { return b !== Q.bloc && b !== 'ED'; });
    $('proj-src').innerHTML =
      '<ul class="proj-prec">' + Q.precedents.map(function (p) { return '<li><b style="color:' + p.couleur + '">' + esc(p.nom) + '</b> : ' + esc(p.phrase) + '. <a href="' + esc(p.url) + '" target="_blank" rel="noopener">Résultats officiels</a>.</li>'; }).join('') + '</ul>' +
      '<p class="bx-note">Ce que chaque précédent suppose, sur 100 électeurs de chaque groupe : <b style="color:' + COL.x + '">votent ' + esc(duel) + '</b> · <b style="color:' + COL.lp + '">votent Le Pen</b> · <b>s\'abstiennent ou votent blanc</b> (dans cet ordre, sous chaque barre). Partout, les électeurs de ' + esc(duel) + (Q.bloc === 'C' || Q.bloc === 'D' ? ' et de son camp' : '') + ' votent pour lui, ceux de Le Pen pour elle.</p>' +
      '<div class="proj-tw"><table class="proj-t"><thead><tr><th></th>' + Q.precedents.map(function (p) { return '<th style="color:' + p.couleur + '">' + esc(p.court) + '</th>'; }).join('') + '</tr></thead><tbody>' +
      G.map(function (b) { var nc = P.noms_courts[b]; return '<tr><th>' + esc(nc[0]) + (nc[1] ? '<small>' + esc(nc[1]) + '</small>' : '') + (b === 'FI' && Q.bloc === 'AG' ? '<small>non mesuré : comme les autres électeurs de gauche</small>' : '') + (b === 'XD' ? '<small>peu nombreux dans ces duels (1 à 3 % des inscrits) : chiffres peu précis</small>' : '') + '</th>' + Q.precedents.map(function (p) { return '<td>' + bar(p.reports[b]) + '</td>'; }).join('') + '</tr>'; }).join('') +
      '</tbody></table></div>';
  }

  function draw(C, T2, moy, duel) {
    box.querySelectorAll('svg').forEach(function (n) { n.remove(); });
    var W = box.clientWidth || 600, H = document.getElementById('projection').classList.contains('proj-regle') ? 165 : W < 500 ? 260 : 320, mL = 40, mR = W < 500 ? 132 : 170;
    var all = [].concat.apply([], C.map(function (c) { return c.pts; })).concat(T2);
    var x = d3.scaleUtc(d3.extent(all, function (r) { return r.d; }), [mL, W - mR]);
    var lo = Math.min(30, Math.floor(d3.min(all, function (r) { return r.v; }) / 5) * 5), hi = Math.max(55, Math.ceil(d3.max(all, function (r) { return r.v; }) / 5) * 5);
    var y = d3.scaleLinear([lo, hi], [H - 28, 12]);
    var svg = d3.select(box).append('svg').attr('width', '100%').attr('viewBox', '0 0 ' + W + ' ' + H).attr('role', 'img').attr('aria-label', 'Score projeté de ' + duel + ' face à Marine Le Pen selon les précédents, et sondages');
    svg.append('g').selectAll('line').data(y.ticks(5)).join('line').attr('x1', mL).attr('x2', W - mR).attr('y1', y).attr('y2', y).attr('stroke', 'var(--cds-chart-grid)');
    svg.append('line').attr('x1', mL).attr('x2', W - mR).attr('y1', y(50)).attr('y2', y(50)).attr('stroke', 'var(--cds-chart-reference)').attr('stroke-width', 1.5);
    var gy = svg.append('g').attr('transform', 'translate(' + mL + ',0)').call(d3.axisLeft(y).ticks(5).tickFormat(function (v) { return v + ' %'; }).tickSize(0));
    gy.select('.domain').remove(); gy.selectAll('text').style('font-size', 'var(--cds-font-size-caption)');
    var gx = svg.append('g').attr('transform', 'translate(0,' + (H - 28) + ')').call(d3.axisBottom(x).ticks(d3.utcMonth.every((W - mL - mR) < 200 ? 6 : (W - mL - mR) < 300 ? 4 : 2)).tickFormat((window.BX && BX.fmtMonth) || d3.utcFormat('%m/%Y')).tickSizeOuter(0));
    gx.selectAll('text').style('font-size', 'var(--cds-font-size-caption)'); gx.select('.domain').attr('stroke', 'var(--cds-chart-axis)'); gx.selectAll('line').attr('stroke', 'var(--cds-chart-axis)');
    var line = d3.line().x(function (r) { return x(r.d); }).y(function (r) { return y(r.v); }), labs = [];
    C.forEach(function (c) {
      if (!c.pts.length) return;
      if (c.perso) { var l0 = c.pts[c.pts.length - 1]; labs.push({ y: y(l0.v), col: c.col, t: c.court || c.nom, v: nf1(l0.v) + ' %' }); return; }
      svg.append('path').datum(c.pts).attr('fill', 'none').attr('stroke', c.col).attr('stroke-width', 1.6).attr('stroke-dasharray', '5 3').attr('d', line);
      var l = c.pts[c.pts.length - 1]; labs.push({ y: y(l.v), col: c.col, t: c.court || c.nom, v: nf1(l.v) + ' %' });
    });
    svg.append('g').selectAll('circle').data(T2).join('circle').attr('cx', function (r) { return x(r.d); }).attr('cy', function (r) { return y(r.v); }).attr('r', 3.5).attr('fill', 'var(--cds-chart-muted)').attr('stroke', 'var(--color-fg)')
      .append('title').text(function (r) { return r.i + ', ' + r.d.toLocaleDateString('fr-FR') + ' : ' + duel + ' ' + nf1(r.v) + ' %'; });
    if (moy.length > 1) svg.append('path').datum(moy).attr('fill', 'none').attr('stroke', 'var(--color-fg)').attr('stroke-width', 2.5).attr('d', line);
    if (moy.length) { var lm = moy[moy.length - 1]; var dT = T2.reduce(function (m, r) { return +r.d > +m ? r.d : m; }, T2[0].d), vieux = +C[0].pts[C[0].pts.length - 1].d - +dT > 45 * 864e5; labs.push({ y: y(lm.v), col: 'var(--color-fg)', t: 'Sondages' + (vieux ? ' (' + dT.toLocaleDateString('fr-FR', { month: 'short', year: 'numeric' }) + ')' : ''), v: nf1(lm.v) + ' %' }); }
    C.forEach(function (c) { if (c.perso && c.pts.length) svg.append('path').datum(c.pts).attr('fill', 'none').attr('stroke', c.col).attr('stroke-width', 3.5).attr('stroke-linejoin', 'round').attr('d', line); });
    var pv = C.filter(function (c) { return !c.perso && c.pts.length; }).map(function (c) { return c.pts[c.pts.length - 1].v; });
    box.dataset.resume = (moy.length ? 'Dans les sondages : ' + nf1(moy[moy.length - 1].v) + ' %. ' : '') + 'D\'après les élections passées : de ' + nf1(Math.min.apply(null, pv)) + ' à ' + nf1(Math.max.apply(null, pv)) + ' %. Il faut 50 % pour l\'emporter.';
    // Au toucher : la semaine touchée, la valeur de chaque courbe et la moyenne des sondages.
    if (window.BX && BX.xhair) {
      var dates = C.length ? C[0].pts.map(function (q) { return q.d; }) : [];
      BX.xhair(svg, box, W, 12, H - 28, function (sx) {
        if (!dates.length) return null;
        var d = dates[d3.bisector(function (q) { return q; }).center(dates, x.invert(sx))];
        var rows = C.filter(function (c) { return c.pts.length; }).map(function (c) { var q = c.pts.filter(function (p) { return +p.d === +d; })[0]; return q ? { c: c.col, n: c.court || c.nom, v: q.v, py: y(q.v), s: nf1(q.v) + ' %' } : null; }).filter(Boolean);
        var m = moy.filter(function (q) { return +q.d === +d; })[0]; if (m) rows.push({ c: 'var(--color-fg)', n: 'Sondages (moyenne 30 jours)', v: m.v, py: y(m.v), s: nf1(m.v) + ' %' });
        rows.sort(function (a, b) { return b.v - a.v; });
        return { px: x(d), head: 'Semaine du ' + d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' }) + ' · score de ' + duel, rows: rows, note: 'Projections d\'après les élections passées : pas un sondage.' };
      });
    }
    labs.sort(function (a, b) { return a.y - b.y; });
    for (var i = 1; i < labs.length; i++) if (labs[i].y - labs[i - 1].y < 28) labs[i].y = labs[i - 1].y + 28;
    if (labs.length) { labs[labs.length - 1].y = Math.min(labs[labs.length - 1].y, H - 24); for (var k2 = labs.length - 2; k2 >= 0; k2--) labs[k2].y = Math.min(labs[k2].y, labs[k2 + 1].y - 28); }
    svg.append('g').selectAll('text').data(labs).join('text').attr('x', W - mR + 6).attr('y', function (l) { return l.y + 4; }).attr('fill', function (l) { return l.col; })
      .style('font-size', 'var(--cds-font-size-caption)').style('font-weight', 600).each(function (l) { var t = d3.select(this); t.append('tspan').text(l.t); t.append('tspan').attr('x', W - mR + 6).attr('dy', '1.15em').style('font-weight', 700).text(l.v); });
  }
})();
