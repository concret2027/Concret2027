/* « En bref », en tête de chaque page : sur combien d'indicateurs la France fait mieux que la moyenne de l'UE au dernier
   chiffre connu, la liste dans un menu déroulant (chaque indicateur mène à sa courbe : un raccourci), et la note de chaque
   président sur la page. Chaque page calcule ses indicateurs et ses notes (commun/notes.js) et appelle ConcretBref.render. */
(function () {
  var css = '.bref-top{display:flex;align-items:center;gap:14px;margin:6px 0 4px}' +
    '.bref-n{font-family:var(--serif);font-size:60px;line-height:1;color:var(--fg);white-space:nowrap}.bref-n small{font-size:26px;color:var(--muted)}' +
    '.bref-t{font-size:14.5px;color:var(--muted);line-height:1.35}' +
    '.bref-det{margin:6px 0 14px}.bref-det>summary{cursor:pointer;list-style:none;display:inline-flex;align-items:center;gap:6px;font-size:13.5px;font-weight:600;color:var(--fr);padding:4px 0}' +
    '.bref-det>summary::-webkit-details-marker{display:none}.bref-det>summary::after{content:"▾"}.bref-det[open]>summary::after{content:"▴"}' +
    '.bref-chips{display:flex;flex-wrap:wrap;gap:4px 5px;margin:8px 0 2px}' +
    '.bref-chips a{font-size:11.5px;font-weight:500;padding:2px 8px;border-radius:999px;border:1px solid var(--line);color:var(--muted);text-decoration:none}' +
    '.bref-chips a:hover,.bref-chips a:focus{border-color:var(--fr);color:var(--fg)}' +
    '.bref-chips a i{font-style:normal;font-weight:700;margin-right:3px;color:var(--bad)}.bref-chips a.g i{color:var(--ok)}.bref-chips a.m i{color:var(--mid)}' +
    '.bref-pres{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:8px 0 10px}' +
    '.bref-pres a{position:relative;display:flex;flex-direction:column;align-items:center;gap:2px;padding:10px 4px 12px;border-radius:12px;background:var(--bg);border:1px solid var(--line);color:var(--fg);text-decoration:none;overflow:hidden}' +
    '.bref-pres a span{font-size:12.5px;color:var(--muted);font-weight:600}.bref-pres a b{font-family:var(--serif);font-size:28px;font-weight:500;line-height:1.1}' +
    '.bref-pres a i{position:absolute;left:0;bottom:0;height:4px;background:var(--bad)}.bref-pres a.g i{background:var(--ok)}.bref-pres a.m i{background:var(--mid)}' +
    '.bref-pres a.g b{color:var(--ok)}.bref-pres a.m b{color:var(--mid)}.bref-pres a.b b{color:var(--bad)}' +
    '@keyframes bref-flash{0%{box-shadow:0 0 0 3px var(--fr)}100%{box-shadow:0 0 0 3px transparent}}.bref-flash{animation:bref-flash 1.6s ease-out}';
  var esc = function (t) { return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;'); };
  var fmt = function (v) { return new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(Math.round(v * 10) / 10); };
  var ICON = { g: '✓', b: '✗', m: '=' };

  // Aller à une courbe : ouvre les blocs repliés qui la contiennent (elle se dessine à l'ouverture), puis y descend.
  function aller(id) {
    var el = document.getElementById(id); if (!el) return;
    for (var d = el; d; d = d.parentElement) if (d.tagName === 'DETAILS' && !d.open) d.open = true;
    setTimeout(function () {
      var c = el.closest('section, .card, .mo') || el;
      c.scrollIntoView({ behavior: 'smooth', block: 'start' });
      c.classList.remove('bref-flash'); void c.offsetWidth; c.classList.add('bref-flash');
    }, 200);
  }

  // o.items : [{ l, cl ('g' mieux, 'b' moins bien, 'm' égal), cible (id de la courbe) }] ; o.pres : [{ n, v }] ; o.ref : la référence.
  function render(o) {
    var box = document.getElementById('reponse'); if (!box) return;
    if (!document.getElementById('bref-css')) { var st = document.createElement('style'); st.id = 'bref-css'; st.textContent = css; document.head.appendChild(st); }
    var l = o.items.filter(Boolean), ok = l.filter(function (x) { return x.cl === 'g'; }).length, ref = o.ref || 'la moyenne de l\'UE';
    var tri = l.slice().sort(function (a, b) { var r = { g: 0, m: 1, b: 2 }; return r[a.cl] - r[b.cl]; });
    // Le nom de la page dans le titre : l'image partagée dit de quelle mission il s'agit.
    var page = document.querySelector('.brand h1, .brand b'), nom = page ? page.textContent.trim() : '';
    box.innerHTML = '<h2><span class="eyebrow">' + (nom ? esc(nom) + ', en bref' : 'En bref') + '</span>La France face à ' + esc(ref) + '</h2>' +
      '<div class="bref-top"><span class="bref-n">' + ok + '<small>/' + l.length + '</small></span><span class="bref-t">indicateurs où la France fait mieux que ' + esc(ref) + ', au dernier chiffre connu' + (o.precision ? ' (' + esc(o.precision) + ')' : '') + '</span></div>' +
      '<details class="bref-det"><summary>Voir les ' + l.length + ' indicateurs</summary><div class="bref-chips">' +
      tri.map(function (x) { return '<a class="' + x.cl + '" href="#' + esc(x.cible) + '" data-cible="' + esc(x.cible) + '" title="Voir la courbe"><i>' + ICON[x.cl] + '</i>' + esc(x.l) + '</a>'; }).join('') +
      '</div></details>' +
      '<span class="eyebrow" style="margin:4px 0 0">La note des présidents sur cette page</span><div class="bref-pres">' +
      o.pres.map(function (p) {
        var c = p.v == null ? '' : p.v >= 10 ? 'g' : p.v >= 6 ? 'm' : 'b';
        return '<a class="' + c + '" href="#bulletin"><span>' + esc(p.n.split(' ').slice(-1)[0]) + '</span><b>' + (p.v == null ? '—' : fmt(p.v)) + '</b><i style="width:' + (p.v == null ? 0 : 5 * p.v) + '%"></i></a>';
      }).join('') + '</div>' +
      '<p class="note">Sur 20 ; 10 = aussi bien que la moyenne de l\'UE. <a class="pt-hors" href="#bulletin">Le détail et les gouvernements ↓</a></p>';
    // Le bouton « Partager » (commun/partage.js) a pu être posé sur le bloc encore vide : on le laisse le reposer.
    box.removeAttribute('data-partage');
    box.querySelectorAll('.bref-chips a').forEach(function (a) { a.addEventListener('click', function (ev) { ev.preventDefault(); aller(a.dataset.cible); }); });
  }
  // « Depuis votre dernière visite » : d'abord ce qui est nouveau (chiffres, actualités), puis, s'il n'y a
  // pas de nouveau chiffre, la dernière actualité et le prochain rendez-vous de l'agenda. Renvoie les morceaux de la ligne.
  // o : { chiffres: [html], actu: [{date, texte}], agenda: [{date, quand, evenement}], depuis: horodatage, jour: bool, prochains: texte }
  function nouveau(o) {
    var iso = function (d) { return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2); };
    var dfr = function (s) { return new Date(s + 'T12:00:00').toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' }).replace(/^1 /, '1er '); };
    var min1 = function (t) { t = String(t); return t.charAt(0).toLowerCase() + t.slice(1); };
    var court = function (t) { t = String(t); if (t.length <= 120) return t.replace(/\.$/, ''); var c = t.slice(0, 117); return c.slice(0, c.lastIndexOf(' ')) + '…'; };
    var lien = function (id, h) { return '<a href="#' + id + '" data-cible="' + id + '">' + h + '</a>'; };
    var dep = iso(new Date(o.depuis)), auj = iso(new Date()), ch = (o.chiffres || []).slice(), parts = ch.slice();
    var A = (o.actu || []).filter(function (a) { return a.texte && a.date; }).sort(function (a, b) { return a.date < b.date ? 1 : -1; });
    var na = A.filter(function (a) { return a.date > dep; });
    if (na.length) parts.push(lien('acc-actu', '<b>' + na.length + ' nouvelle' + (na.length > 1 ? 's' : '') + ' actualité' + (na.length > 1 ? 's' : '') + '</b>') + ' : « ' + esc(court(na[0].texte)) + ' »');
    if (!ch.length) {
      // La dernière actualité seulement si elle est récente (moins de 15 jours) : au-delà, ce n'est plus du nouveau.
      if (!na.length && A[0] && (new Date(auj) - new Date(A[0].date)) / 864e5 < 15) parts.push('dernière actualité, le ' + dfr(A[0].date) + ' : ' + lien('acc-actu', '« ' + esc(court(A[0].texte)) + ' »'));
      var g = (o.agenda || []).filter(function (a) { return a.date && a.date >= auj; }).sort(function (a, b) { return a.date < b.date ? -1 : 1; })[0];
      parts.push('pas de nouveau chiffre' + (g ? ' ; prochain rendez-vous, ' + esc(min1(g.quand || dfr(g.date))) + ' : ' + esc(String(g.evenement).replace(/\.$/, '')) : o.prochains ? ' (' + o.prochains + ')' : ''));
    }
    return parts;
  }
  // Les liens de la ligne mènent au bloc visé (ouvert s'il est replié).
  function lier(box) { box.querySelectorAll('a[data-cible]').forEach(function (a) { a.addEventListener('click', function (ev) { ev.preventDefault(); aller(a.dataset.cible); }); }); }
  // Lien venu d'une autre page (par exemple le quiz) vers une courbe repliée : on attend qu'elle existe, puis on l'ouvre.
  if (location.hash.length > 1) {
    var vise = decodeURIComponent(location.hash.slice(1)), essais = 0;
    var t = setInterval(function () { var el = document.getElementById(vise); if (el || ++essais > 40) { clearInterval(t); if (el) aller(vise); } }, 250);
  }
  window.ConcretBref = { render: render, aller: aller, nouveau: nouveau, lier: lier };
})();
