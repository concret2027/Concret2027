/* Toile (diagramme en radar) : la France, la moyenne de l'UE et les voisins sur tous les indicateurs d'une page, au dernier
   chiffre connu. Chaque axe va de 0 (ou du plus bas des pays affichés s'il est négatif) au plus haut des pays affichés :
   plus loin du centre veut dire « plus élevé », pas « mieux » (la page le dit sous la toile). Aucune note ici.
   Utilisation : ConcretToile.dessiner('toile', { axes: [...], series: [...], omis: [...] }) ; ConcretToile.depuisC(C, cles)
   fabrique les axes à partir des séries des pages Santé, Sécurité, Défense, Vie des Français et Démographie. */
(function () {
  var NS = 'http://www.w3.org/2000/svg';
  var css = '.toile-l{display:flex;flex-wrap:wrap;gap:6px 14px;margin:8px 0 2px;font-size:13px;color:var(--muted)}' +
    '.toile-l span{display:inline-flex;align-items:center;gap:6px}.toile-l i{display:inline-block;width:16px;height:0;border-top:3px solid}' +
    '.toile-l i.d{border-top-style:dashed}' +
    '.toile-svg{display:block;width:100%;max-width:560px;height:auto;margin:4px auto 0;overflow:visible}' +
    '.toile-svg .ax{stroke:var(--line);stroke-width:1;fill:none}.toile-svg .ri{stroke:var(--line);stroke-width:1;fill:none}' +
    '.toile-svg .lb{fill:var(--fg);font-weight:600}.toile-svg .rg{fill:var(--muted);font-size:10px}' +
    '.toile-tab{width:100%;border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums;margin-top:6px}' +
    '.toile-tab th,.toile-tab td{padding:5px 4px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}' +
    '.toile-tab th:first-child,.toile-tab td:first-child{text-align:left;white-space:normal}.toile-tab th{font-size:11.5px;color:var(--muted);font-weight:600}' +
    '.toile-tw{overflow-x:auto;-webkit-overflow-scrolling:touch}.toile-det{margin-top:6px}.toile-det>summary{cursor:pointer;font-size:14px;font-weight:600;color:var(--fr);padding:8px 0;list-style:none}.toile-det>summary::-webkit-details-marker{display:none}.toile-det>summary::after{content:"\\00a0▾"}.toile-det[open]>summary::after{content:"\\00a0▴"}';
  var esc = function (t) { return String(t == null ? '' : t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;'); };
  var fmt = function (v, d) { return new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: d == null ? 1 : d }).format(v).replace(/ /g, ' '); };
  var el = function (n, a) { var e = document.createElementNS(NS, n); for (var k in a) e.setAttribute(k, a[k]); return e; };
  // Coupe un intitulé en lignes d'environ 14 signes.
  var lignes = function (t, n) { var w = String(t).split(' '), out = [], cur = ''; w.forEach(function (m) { if ((cur + ' ' + m).trim().length > n && cur) { out.push(cur); cur = m; } else cur = (cur + ' ' + m).trim(); }); if (cur) out.push(cur); return out; };

  // Le dernier chiffre connu de chaque série d'un critère : l'année la plus récente où la France et la moyenne de l'UE ont un chiffre.
  function depuisC(C, cles, opts) {
    opts = opts || {}; var axes = [], omis = [], notes = [];
    cles.forEach(function (k) {
      var c = C[k];
      if (!c || !c.y || !c.fr) { if (c) omis.push(c.lc || c.l); return; }
      var i = c.y.length - 1;
      var ue = c.ue || c.ue_calc || [];
      while (i >= 0 && (c.fr[i] == null || ue[i] == null || (c.est && c.est[c.y[i]]))) i--;
      if (i < c.y.length - 1 && c.est && c.est[c.y[c.y.length - 1]]) notes.push((c.lc || c.l) + ' : dernier chiffre définitif (' + c.y[i] + '), les années suivantes ne sont que des estimations');
      if (i < 0) { omis.push(c.lc || c.l); return; }
      var v = { ue: ue[i] }; ['fr', 'de', 'es', 'us'].forEach(function (w) { if (c[w] && c[w][i] != null) v[w] = c[w][i]; });
      axes.push({ cle: opts.page ? opts.page + '.' + k : null, l: c.lc || c.l, lt: c.lt, y: c.y[i], u: c.uc != null ? c.uc : (/%/.test(c.unite || '') ? ' %' : ''), dec: c.dec, v: v, cible: (opts.cible || function (k) { return 'ch-' + k; })(k) });
    });
    return { axes: axes, omis: omis, notes: notes };
  }

  function dessiner(id, o) {
    var box = document.getElementById(id); if (!box) return;
    if (!document.getElementById('toile-css')) { var st = document.createElement('style'); st.id = 'toile-css'; st.textContent = css; document.head.appendChild(st); }
    var axes = o.axes.filter(function (a) { return a.v.fr != null && a.v.ue != null; }), S = o.series;
    var n = axes.length; if (n < 3) { box.hidden = true; return; }
    // Sur téléphone, la toile est réduite à environ 75 % : les libellés sont plus gros dans le dessin (11 px au moins à l'écran),
    // sans la plage de l'axe (elle est dans « Les chiffres »), et la toile un peu plus petite pour leur laisser la place.
    var pt = (box.clientWidth || 440) < 500, FS = pt ? 15 : 11.5, LH = pt ? 17 : 13;
    var W = 440, R = pt ? (n > 9 ? 92 : 100) : (n > 9 ? 108 : 118), cx = W / 2, cy = pt ? 200 : 195, H = 400;
    var svg = el('svg', { viewBox: '0 0 ' + W + ' ' + H, class: 'toile-svg', role: 'img', 'aria-label': o.titre || 'Toile des indicateurs' });
    var ang = function (i) { return -Math.PI / 2 + 2 * Math.PI * i / n; };
    // Échelle de chaque axe : de 0 (ou du plus bas, s'il est négatif) au plus haut des pays affichés.
    axes.forEach(function (a) {
      var vals = S.map(function (s) { return a.v[s.k]; }).filter(function (x) { return x != null; });
      a.lo = Math.min(0, Math.min.apply(null, vals)); a.hi = Math.max(0, Math.max.apply(null, vals)); if (a.hi <= a.lo) a.hi = a.lo + 1;
    });
    [0.25, 0.5, 0.75, 1].forEach(function (f) {
      svg.appendChild(el('polygon', { class: 'ri', points: axes.map(function (a, i) { return (cx + R * f * Math.cos(ang(i))) + ',' + (cy + R * f * Math.sin(ang(i))); }).join(' ') }));
    });
    var LB = [];
    axes.forEach(function (a, i) {
      var x = cx + R * Math.cos(ang(i)), y = cy + R * Math.sin(ang(i));
      svg.appendChild(el('line', { class: 'ax', x1: cx, y1: cy, x2: x, y2: y }));
      var c = Math.cos(ang(i)), s = Math.sin(ang(i)), lx = cx + (R + 14) * c, ly = cy + (R + 14) * s;
      var anc = Math.abs(c) < (n > 9 ? 0.1 : 0.25) ? 'middle' : c > 0 ? 'start' : 'end';
      var L = lignes(a.lt || a.l, pt ? 12 : n > 9 ? 13 : 15) /* lt : libellé court sur la toile, nom complet dans « Les chiffres » */, rg = fmt(a.lo, a.dec) + ' à ' + fmt(a.hi, a.dec) + (a.u || '');
      var RG = pt ? [] : lignes(rg, 17), tot = L.length + RG.length, y0 = ly + (s < -0.25 ? -(tot - 1) * LH : s > 0.25 ? 4 : -(tot - 1) * LH / 2 + 4);
      LB.push({ x: lx, y: y0, anc: anc, L: L, rg: RG, h: tot * LH });
    });
    // Chevauchements : de chaque côté, de haut en bas, un libellé descend sous le précédent s'il le touche.
    ['start', 'end'].forEach(function (cote) {
      var l = LB.filter(function (b) { return b.anc === cote; }).sort(function (a, b) { return a.y - b.y; }), bas = -Infinity;
      l.forEach(function (b) { if (b.y < bas + LH + 3) b.y = bas + LH + 3; bas = b.y + b.h - LH; });
    });
    var Hmax = 0;
    LB.forEach(function (b) {
      var t = el('text', { x: b.x, y: b.y, 'text-anchor': b.anc, class: 'lb', 'font-size': FS });
      b.L.forEach(function (m, j) { var ts = el('tspan', { x: b.x, dy: j ? LH : 0 }); ts.textContent = m; t.appendChild(ts); });
      b.rg.forEach(function (m) { var r = el('tspan', { x: b.x, dy: LH, class: 'rg' }); r.textContent = m; t.appendChild(r); });
      svg.appendChild(t); Hmax = Math.max(Hmax, b.y + b.h);
    });
    // Libellés qui dépassent à gauche ou à droite : la vue s'élargit pour les montrer en entier.
    var x0 = 0, x1 = W; LB.forEach(function (b) { var w = Math.max.apply(null, b.L.concat(b.rg).map(function (m) { return m.length; })) * FS * 0.56; if (b.anc === 'end') x0 = Math.min(x0, b.x - w - 4); else if (b.anc === 'start') x1 = Math.max(x1, b.x + w + 4); else { x0 = Math.min(x0, b.x - w / 2 - 4); x1 = Math.max(x1, b.x + w / 2 + 4); } });
    var top = Math.min(0, Math.min.apply(null, LB.map(function (b) { return b.y - LH; })));
    svg.setAttribute('viewBox', x0 + ' ' + top + ' ' + (x1 - x0) + ' ' + (Math.max(H, Hmax + 6) - top));
    // Les pays : le premier de la liste est dessiné en dernier (la France au-dessus).
    S.slice().reverse().forEach(function (s) {
      var P = axes.map(function (a, i) { var v = a.v[s.k]; if (v == null) return null; var f = 0.1 + 0.9 * (v - a.lo) / (a.hi - a.lo); return [cx + R * f * Math.cos(ang(i)), cy + R * f * Math.sin(ang(i))]; });
      var nb = P.filter(Boolean).length; if (nb < 2) return;
      var st = { fill: 'none', stroke: s.c, 'stroke-width': s.main ? 2.6 : 2, 'stroke-dasharray': s.dash ? '5 4' : s.pointille ? '1.5 4' : 'none', 'stroke-linejoin': 'round', 'stroke-linecap': 'round' };
      if (nb === n) {
        var poly = el('polygon', Object.assign({}, st, { points: P.map(function (p) { return p.join(','); }).join(' ') }));
        if (s.main) { poly.setAttribute('fill', s.c); poly.setAttribute('fill-opacity', '0.08'); }
        svg.appendChild(poly);
      } else {
        // Forme coupée là où le pays n'a pas de chiffre : on ne relie que deux axes voisins tous deux renseignés.
        var d = ''; P.forEach(function (p, i) { var q = P[(i + 1) % n]; if (p && q) d += 'M' + p.join(',') + 'L' + q.join(','); });
        if (d) svg.appendChild(el('path', Object.assign({}, st, { d: d })));
      }
      P.forEach(function (p) { if (p) svg.appendChild(el('circle', { cx: p[0], cy: p[1], r: s.main ? 3.6 : 2.8, fill: s.c })); });
    });
    var ys = {}; axes.forEach(function (a) { ys[a.y] = 1; });
    var annees = Object.keys(ys).sort(), an = annees.length === 1 ? annees[0] : annees[0] + ' à ' + annees[annees.length - 1];
    var manque = S.filter(function (s) { return axes.some(function (a) { return a.v[s.k] == null; }); }).map(function (s) {
      var m = axes.filter(function (a) { return a.v[s.k] == null; });
      return s.pointille ? s.n + ' : pas de chiffre publié pour ' + m.length + ' indicateur' + (m.length > 1 ? 's' : '') + ' sur ' + n : s.n + ' : pas de chiffre pour ' + m.map(function (a) { return a.l; }).join(', ');
    });
    var pg = document.querySelector('.brand h1, .brand b, .crumb b, h1'), nomPage = pg ? pg.textContent.trim().split('\n')[0] : '';
    box.innerHTML = '<h2 class="inv"><span class="eyebrow">' + esc((nomPage && nomPage.length < 40 ? nomPage + ' : ' : '') + (o.titre || 'La France et ses voisins')).replace(/ : La France/, ' : la France') + '</span>Dernier chiffre connu de chaque indicateur (' + esc(an) + ')</h2>' +
      '<div class="toile-l">' + S.map(function (s) { return '<span><i class="' + (s.dash ? 'd' : '') + '" style="border-top-color:' + s.c + (s.pointille ? ';border-top-style:dotted' : '') + '"></i>' + esc(s.n) + '</span>'; }).join('') + '</div>';
    box.appendChild(svg);
    var note = document.createElement('p'); note.className = 'note';
    var ax0 = (o.axes || []).filter(function (a) { return a && a.l; })[0];
    note.textContent = 'Plus loin du centre : un chiffre plus élevé, pas forcément mieux' + (ax0 ? ' (par exemple « ' + ax0.l + ' »)' : '') + '. Chaque axe va du plus bas (0, ou moins pour un chiffre négatif) au plus haut des pays affichés ; la plage de chaque axe est dans « Les chiffres ». Aucune note ici : elles sont calculées année par année, plus bas.' +
      (manque.length ? ' ' + manque.join(' ; ') + ' (la forme est coupée à cet endroit).' : '') + (o.notes && o.notes.length ? ' ' + o.notes.join(' ; ') + '.' : '') + (o.omis && o.omis.length ? ' Pas sur la toile, faute de chiffre comparable au même moment : ' + o.omis.join(', ') + '.' : '');
    box.appendChild(note);
    var det = document.createElement('details'); det.className = 'toile-det';
    det.innerHTML = '<summary>Les chiffres</summary><div class="toile-tw"><table class="toile-tab"><thead><tr><th></th>' + S.map(function (s) { return '<th>' + esc(s.court || s.n) + '</th>'; }).join('') + '</tr></thead><tbody>' +
      axes.map(function (a) { return '<tr><td>' + esc(a.l) + ' <small>(' + a.y + (a.u ? ',' + esc(a.u) : '') + ' ; axe de ' + fmt(a.lo, a.dec) + ' à ' + fmt(a.hi, a.dec) + ')</small></td>' + S.map(function (s) { var v = a.v[s.k]; return '<td>' + (v == null ? '—' : fmt(v, a.dec)) + '</td>'; }).join('') + '</tr>'; }).join('') + '</tbody></table></div>' +
      // Chaque case vide dit pourquoi, sous le tableau (règle : toute donnée absente s'explique là où on la voit).
      (function () {
        var vides = S.map(function (s) { var l = axes.filter(function (a) { return a.v[s.k] == null; }); return l.length ? s.n + ' : ' + l.map(function (a) { return a.l + ' (' + a.y + ')'; }).join(', ') : ''; }).filter(Boolean);
        return vides.length ? '<p class="note">« — » : pas de chiffre publié par la source pour cette année. ' + esc(vides.join(' ; ')) + '.</p>' : '';
      })();
    box.appendChild(det);
    box.hidden = false;
    // Le bouton « Partager » (commun/partage.js) a été effacé avec l'ancien contenu : on le laisse le reposer.
    box.removeAttribute('data-partage');
  }
  // Les séries affichées par défaut, dans les couleurs des courbes du site.
  var SERIES = [
    { k: 'fr', n: 'France', c: 'var(--fr)', main: 1 }, { k: 'ue', n: 'Moyenne de l\'UE', court: 'UE', c: 'var(--ea)', dash: 1 },
    { k: 'de', n: 'Allemagne', court: 'All.', c: 'var(--de)' }, { k: 'es', n: 'Espagne', court: 'Esp.', c: 'var(--es)' }
  ];
  window.ConcretToile = { dessiner: dessiner, depuisC: depuisC, SERIES: SERIES };
})();
