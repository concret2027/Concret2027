/* « + Ajouter un pays » : jusqu'à trois pays ajoutés en pointillé sur une courbe ou sur la toile, seulement sur le graphique
   où ils sont choisis, à côté de la France, de la moyenne de l'UE, de l'Allemagne et de l'Espagne. Les chiffres viennent de donnees/pays.json
   (outils/pays.py : mêmes sources et mêmes filtres que la France, vérifiés à chaque mise à jour), chargé seulement quand
   un pays est choisi. Un pays ajouté est un repère : il ne change aucune note. Le choix de chaque graphique est gardé sur l'appareil.
   Une page : ConcretPays.init({ page: 'sante', carte: { 'id-de-courbe': 'clé' } }) ; dans son lineChart(id, series, o) :
   if (window.ConcretPays) { var s0 = series; ConcretPays.retenir(id, function () { lineChart(id, s0, o); }); series = ConcretPays.ajouter(id, series); } */
(function () {
  var COUL = ['#0f9b8e', '#c2407e', '#4f7a1f'], MAX = 3, CLE = 'concret-pays';
  var css = '.cp-bar{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:6px 0 0;font-size:13px}' +
    '.cp-bar select{font:inherit;font-size:13px;font-weight:600;color:var(--fr);background:var(--panel);border:1px dashed var(--fr);border-radius:999px;padding:5px 10px;min-height:34px;max-width:100%}' +
    '.cp-chip{display:inline-flex;align-items:center;gap:6px;padding:4px 6px 4px 10px;border-radius:999px;border:1px solid var(--line);background:var(--panel);font-weight:600;color:var(--fg)}' +
    '.cp-chip i{display:inline-block;width:16px;height:0;border-top:3px dashed}' +
    '.cp-chip button{font:inherit;border:0;background:none;color:var(--muted);cursor:pointer;padding:2px 6px;min-height:28px}' +
    '.cp-msg{font-size:12.5px;color:var(--muted);flex-basis:100%}';
  var opts = { page: '', carte: {} }, data = null, chargement = null, index = null, chIndex = null, choix = {}, courbes = {}, toiles = {};
  // Le choix est rangé par graphique : { 'sante:ch-esp': ['IT'], 'sante:toile': ['SE', 'US'] }.
  try { var c0 = JSON.parse(localStorage.getItem(CLE) || '{}'); if (c0 && typeof c0 === 'object' && !Array.isArray(c0)) choix = c0; } catch (e) {}
  var NOMS = { BE: 'Belgique', BG: 'Bulgarie', CZ: 'Tchéquie', DK: 'Danemark', EE: 'Estonie', IE: 'Irlande', EL: 'Grèce', HR: 'Croatie', IT: 'Italie', CY: 'Chypre', LV: 'Lettonie', LT: 'Lituanie', LU: 'Luxembourg', HU: 'Hongrie', MT: 'Malte', NL: 'Pays-Bas', AT: 'Autriche', PL: 'Pologne', PT: 'Portugal', RO: 'Roumanie', SI: 'Slovénie', SK: 'Slovaquie', FI: 'Finlande', SE: 'Suède' };
  var nom = function (g) { return (index && index.noms[g]) || NOMS[g] || g; };
  var choisis = function (id) { return choix[opts.page + ':' + id] || []; };
  var couleur = function (id, g) { var i = choisis(id).indexOf(g); return COUL[i < 0 ? 0 : i % COUL.length]; };

  function chargerIndex() {
    if (index) return Promise.resolve(index);
    if (!chIndex) chIndex = fetch('/donnees/pays_index.json', { cache: 'no-cache' }).then(function (r) { return r.json(); }).then(function (d) { index = d; d.set = {}; d.cles.forEach(function (k) { d.set[k] = 1; }); return d; });
    return chIndex;
  }
  function charger() {
    if (data) return Promise.resolve(data);
    if (!chargement) chargement = fetch('/donnees/pays.json', { cache: 'no-cache' }).then(function (r) { return r.json(); }).then(function (d) { data = d; return d; });
    return chargement;
  }
  // La clé des chiffres d'une courbe : la carte de la page, sinon l'identifiant de la courbe (« ch-esp » → « sante.esp »).
  function cle(id) {
    if (opts.carte[id] !== undefined) return opts.carte[id];
    if (!index) return null;
    var r = id.replace(/^ch-/, '');
    return [opts.page + '.' + r, opts.page + '.M.' + r, opts.page + '.S.' + r, opts.page + '.D.' + r].filter(function (k) { return index.set[k]; })[0] || null;
  }
  function valeurs(k, g) {
    var s = data && data.series[k]; if (!s || !s[g]) return null;
    return s.y.map(function (y, i) { return { x: y, v: s[g][i] }; }).filter(function (p) { return p.v != null; });
  }
  function garder(id, l) { var k = opts.page + ':' + id; if (l.length) choix[k] = l; else delete choix[k]; try { localStorage.setItem(CLE, JSON.stringify(choix)); } catch (e) {} }
  function redessiner(id) { var f = courbes[id] || toiles[id]; if (f) try { f(); } catch (e) {} }
  function choisir(id, g) { var l = choisis(id).slice(); if (!id || !g || l.indexOf(g) >= 0) return; if (l.length >= MAX) l.shift(); l.push(g); garder(id, l); charger().then(function () { redessiner(id); }); }
  function retirer(id, g) { garder(id, choisis(id).filter(function (x) { return x !== g; })); redessiner(id); }

  // La barre sous une courbe ou une toile : les pays ajoutés à ce graphique (à retirer d'un toucher) et le menu pour en ajouter.
  function barre(b) {
    var k = b.dataset.cle, id = b.dataset.id, ch = choisis(id), sans = [];
    var h = ch.map(function (g) {
      if (k && data && !valeurs(k, g) && !(g === 'US' && b.dataset.us)) sans.push(nom(g));
      return '<span class="cp-chip"><i style="border-top-color:' + couleur(id, g) + '"></i>' + nom(g) + '<button type="button" data-retirer="' + g + '" aria-label="Retirer ' + nom(g) + '">✕</button></span>';
    }).join('');
    var hors = (index && index.hors_ue) || [], tri = function (a, c) { return nom(a).localeCompare(nom(c), 'fr'); };
    // Seulement les pays qui ont un chiffre pour cette courbe (index.dispo), quand l'index le dit.
    var dispo = index && index.dispo && k && index.dispo[k];
    var liste = Object.keys(index ? index.noms : NOMS).filter(function (g) { return ch.indexOf(g) < 0 && (!dispo || dispo.indexOf(g) >= 0); });
    var opt = function (l) { return l.map(function (g) { return '<option value="' + g + '">' + nom(g) + '</option>'; }).join(''); };
    var ue = liste.filter(function (g) { return hors.indexOf(g) < 0; }).sort(tri), hu = liste.filter(function (g) { return hors.indexOf(g) >= 0; }).sort(tri);
    // Hors UE : un groupe par région (Europe hors UE, Amériques, Asie et Océanie).
    var reg = (index && index.regions) || {}, groupes = [];
    hu.forEach(function (g) { var r = reg[g] || 'Hors UE', x = groupes.filter(function (y) { return y.r === r; })[0]; if (!x) groupes.push(x = { r: r, l: [] }); x.l.push(g); });
    var ordre = ['Europe hors UE', 'Amériques', 'Asie et Océanie', 'Hors UE']; groupes.sort(function (a, c) { return ordre.indexOf(a.r) - ordre.indexOf(c.r); });
    b.innerHTML = h + '<select aria-label="Ajouter un pays"><option value="">+ Ajouter un pays</option>' + (ue.length ? '<optgroup label="Union européenne">' + opt(ue) + '</optgroup>' : '') + groupes.map(function (x) { return '<optgroup label="' + x.r + '">' + opt(x.l) + '</optgroup>'; }).join('') + '</select>' +
      (sans.length ? '<span class="cp-msg">' + sans.join(', ') + ' : pas de chiffre publié pour cet indicateur.</span>' : '') +
      (ch.length ? '<span class="cp-msg">' + (ch.length > 1 ? 'Pays ajoutés' : 'Pays ajouté') + ' en pointillé sur ce graphique seulement, comme repère : aucune note ne change.</span>' : '');
  }
  document.addEventListener('change', function (e) { var b = e.target.closest && e.target.closest('.cp-bar'); if (b && e.target.tagName === 'SELECT') choisir(b.dataset.id, e.target.value); });
  document.addEventListener('click', function (e) { var b = e.target.closest && e.target.closest('[data-retirer]'), bar = b && b.closest('.cp-bar'); if (bar) retirer(bar.dataset.id, b.dataset.retirer); });
  function poserBarre(apres, k, id) {
    if (!apres || !apres.parentNode) return;
    var b = apres.nextElementSibling;
    if (!b || !b.classList.contains('cp-bar')) { b = document.createElement('div'); b.className = 'cp-bar'; b.setAttribute('data-partage-ignorer', '1'); apres.parentNode.insertBefore(b, apres.nextSibling); }
    b.dataset.cle = k || ''; b.dataset.id = id; barre(b);
  }

  window.ConcretPays = {
    init: function (o) {
      opts.page = o.page || ''; opts.carte = o.carte || {};
      if (!document.getElementById('cp-css')) { var st = document.createElement('style'); st.id = 'cp-css'; st.textContent = css; document.head.appendChild(st); }
      var ids = function () { return Object.keys(choix).filter(function (k) { return k.indexOf(opts.page + ':') === 0; }).map(function (k) { return k.slice(opts.page.length + 1); }); };
      chargerIndex().then(function () { return ids().length ? charger() : null; }).then(function () {
        Object.keys(courbes).concat(Object.keys(toiles)).forEach(redessiner);
      }).catch(function () {});
    },
    // Une courbe : la retenir pour la redessiner quand son choix change, et lui ajouter les pays choisis pour elle.
    retenir: function (id, f) { courbes[id] = f; },
    ajouter: function (id, series) {
      var el = document.getElementById(id), k = cle(id), dejaUS = series.some(function (x) { return x && x.c === 'var(--us)'; });
      if (el && k) { poserBarre(el, k, id); var bb = el.nextElementSibling; if (bb && bb.classList.contains('cp-bar')) { if (dejaUS) bb.dataset.us = '1'; else delete bb.dataset.us; barre(bb); } }
      var ch = choisis(id);
      if (!data || !k || !ch.length) return series;
      // Les années du pays ajouté restent dans celles de la courbe (pas de trait qui déborde à gauche ou à droite).
      var xs = []; series.forEach(function (x) { (x && x.data || []).forEach(function (d) { if (d && typeof d.x === 'number' && d.v != null) xs.push(d.x); }); });
      var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs);
      return series.concat(ch.map(function (g) {
        if (g === 'US' && dejaUS) return null;
        var v = valeurs(k, g); if (v && xs.length) v = v.filter(function (d) { return d.x >= x0 && d.x <= x1; });
        return v && v.length && { c: couleur(id, g), n: nom(g), dash: 1, data: v, pays: g };
      }).filter(Boolean));
    },
    // La toile : ses axes reçoivent la valeur du pays à l'année de l'axe (sinon rien : la forme est coupée).
    toile: function (id, dessiner, o) {
      toiles[id] = function () {
        var S = o.series.slice(), axes = o.axes.map(function (a) { return Object.assign({}, a, { v: Object.assign({}, a.v) }); });
        if (data) choisis(id).forEach(function (g) {
          S.push({ k: g, n: nom(g), court: nom(g), c: couleur(id, g), pointille: 1 });
          axes.forEach(function (a) { if (g === 'US' && a.v.us != null) { a.v[g] = a.v.us; return; } var s = a.cle && data.series[a.cle]; var i = s ? s.y.indexOf(a.y) : -1; if (i >= 0 && s[g] && s[g][i] != null) a.v[g] = s[g][i]; });
        });
        dessiner(id, Object.assign({}, o, { series: S, axes: axes }));
        var box = document.getElementById(id), leg = box && box.querySelector('.toile-l');
        if (leg) poserBarre(leg, null, id);
      };
      toiles[id]();
    }
  };
})();
