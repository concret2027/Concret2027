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
    '.cp-msg{font-size:12.5px;color:var(--muted);flex-basis:100%}.cp-sans{margin:6px 0 0}';
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
  // Clavier et lecteur d'écran : la barre est redessinée, le focus revient sur son menu, et le changement est annoncé.
  function annoncer(t) {
    var a = document.getElementById('cp-annonce');
    if (!a) { a = document.createElement('div'); a.id = 'cp-annonce'; a.setAttribute('role', 'status'); a.style.cssText = 'position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap'; document.body.appendChild(a); }
    a.textContent = ''; setTimeout(function () { a.textContent = t; }, 50);
  }
  function refocus(id, avait) {
    if (!avait) return;
    var b = document.querySelector('.cp-bar[data-id="' + id + '"]'), s = b && b.querySelector('select'); if (s) try { s.focus({ preventScroll: true }); } catch (e) { }
  }
  function choisir(id, g) {
    var l = choisis(id).slice(); if (!id || !g || l.indexOf(g) >= 0) return; if (l.length >= MAX) l.shift(); l.push(g); garder(id, l);
    var avait = document.activeElement && document.activeElement.closest && document.activeElement.closest('.cp-bar');
    charger().then(function () { redessiner(id); refocus(id, avait); annoncer('Ajout au graphique, en pointillé : ' + nom(g) + '.'); });
  }
  function retirer(id, g) { garder(id, choisis(id).filter(function (x) { return x !== g; })); redessiner(id); refocus(id, true); annoncer('Retrait du graphique : ' + nom(g) + '.'); }

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
      (ch.length ? '<span class="cp-msg">' + (ch.length > 1 ? 'Pays ajoutés' : 'Pays ajouté') + ' en pointillé sur ce graphique seulement, comme repère : aucun résultat ne change.</span>' : '');
  }
  // Au clavier, sur un menu fermé, chaque flèche change déjà le choix (Windows, Linux) : le pays n'est ajouté qu'avec Entrée
  // ou en quittant le menu, pour qu'on puisse parcourir la liste. À la souris ou au doigt, dès le choix.
  var fleche = 0;
  document.addEventListener('keydown', function (e) {
    var s = e.target; if (!s || s.tagName !== 'SELECT' || !s.closest('.cp-bar')) return;
    if (/^(Arrow|Page|Home|End)/.test(e.key) || e.key.length === 1) fleche = Date.now();
    else if (e.key === 'Enter' && s.value) { e.preventDefault(); fleche = 0; choisir(s.closest('.cp-bar').dataset.id, s.value); }
  });
  document.addEventListener('change', function (e) {
    var b = e.target.closest && e.target.closest('.cp-bar'); if (!b || e.target.tagName !== 'SELECT') return;
    if (Date.now() - fleche < 600) return;
    choisir(b.dataset.id, e.target.value);
  });
  document.addEventListener('focusout', function (e) { var s = e.target; if (s && s.tagName === 'SELECT' && s.value && fleche && s.closest('.cp-bar')) { fleche = 0; choisir(s.closest('.cp-bar').dataset.id, s.value); } });
  document.addEventListener('click', function (e) { var b = e.target.closest && e.target.closest('[data-retirer]'), bar = b && b.closest('.cp-bar'); if (bar) retirer(bar.dataset.id, b.dataset.retirer); });
  function poserBarre(apres, k, id) {
    if (!apres || !apres.parentNode) return;
    var b = apres.nextElementSibling;
    if (!b || !b.classList.contains('cp-bar')) { b = document.createElement('div'); b.className = 'cp-bar'; b.setAttribute('data-partage-ignorer', '1'); apres.parentNode.insertBefore(b, apres.nextSibling); }
    b.dataset.cle = k || ''; b.dataset.id = id; barre(b);
  }

  // Une courbe sans autres pays : la raison, à la place du menu (la page la donne, sinon outils/pays.py dans l'index).
  function sansPays(id) {
    var el = document.getElementById(id); if (!el || !el.parentNode || cle(id)) return;
    var why = (opts.sans || {})[id] || ((index && index.sans) || {})[opts.page + '.' + id.replace(/^ch-/, '')], nx = el.nextElementSibling;
    if (!why || (nx && nx.classList.contains('cp-sans'))) return;
    var ps = document.createElement('p'); ps.className = 'cp-msg cp-sans'; ps.setAttribute('data-partage-ignorer', '1'); ps.textContent = why; el.parentNode.insertBefore(ps, el.nextSibling);
  }

  window.ConcretPays = {
    init: function (o) {
      opts.page = o.page || ''; opts.carte = o.carte || {}; opts.sans = o.sans || {};
      if (!document.getElementById('cp-css')) { var st = document.createElement('style'); st.id = 'cp-css'; st.textContent = css; document.head.appendChild(st); }
      var ids = function () { return Object.keys(choix).filter(function (k) { return k.indexOf(opts.page + ':') === 0; }).map(function (k) { return k.slice(opts.page.length + 1); }); };
      chargerIndex().then(function () { return ids().length ? charger() : null; }).then(function () {
        Object.keys(courbes).concat(Object.keys(toiles)).forEach(redessiner);
        Object.keys(opts.sans).forEach(sansPays);
      }).catch(function () {});
    },
    // La phrase sous le titre d'une courbe : la place de la France parmi les pays de l'UE (calculée par outils/rangs.js).
    // Sans rang (pas assez de pays, ou une source pas encore relue pour les autres pays), l'élément est retiré.
    rang: function (cle, el) {
      if (!el) return;
      chargerIndex().then(function (d) {
        var R = d.rangs && d.rangs[cle]; if (!R) { el.remove(); return; }
        var nf = function (v) { return Number(v).toLocaleString('fr-FR', { minimumFractionDigits: R.dec, maximumFractionDigits: R.dec }).replace(/^-/, '−'); };
        var bas = R.rb < R.rh, k = bas ? R.rb : R.rh, pays = ' des ' + R.n + ' pays de l\'UE' + (R.n < 27 ? ' qui le publient' : '');
        var place = 'le ' + (k === 1 ? '' : k + 'e ') + 'chiffre le plus ' + (bas ? 'bas' : 'élevé');
        var bornes = [R.rh > 1 ? 'le plus élevé : ' + R.haut[0] + ', ' + nf(R.haut[1]) : '', R.rb > 1 ? 'le plus bas : ' + R.bas[0] + ', ' + nf(R.bas[1]) : ''].filter(Boolean).join(' ; ');
        el.textContent = 'En ' + R.y + ', la France a ' + place + pays + (bornes ? ' (' + bornes + ')' : '') + '.';
      }).catch(function () { el.remove(); });
    },
    // Une courbe : la retenir pour la redessiner quand son choix change, et lui ajouter les pays choisis pour elle.
    retenir: function (id, f) { courbes[id] = f; },
    ajouter: function (id, series) {
      var el = document.getElementById(id), k = cle(id), dejaUS = series.some(function (x) { return x && x.c === 'var(--us)'; });
      if (el && !k && index) sansPays(id);
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
