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
    '.bref-chips a{display:inline-flex;align-items:center;min-height:24px;box-sizing:border-box;font-size:11.5px;font-weight:500;padding:2px 8px;border-radius:999px;border:1px solid var(--line);color:var(--muted);text-decoration:none}' +
    '.bref-chips a:hover,.bref-chips a:focus{border-color:var(--fr);color:var(--fg)}' +
    '.bref-chips a i{font-style:normal;font-weight:700;margin-right:3px;color:var(--bad)}.bref-chips a.g i{color:var(--ok)}.bref-chips a.m i{color:var(--mid)}' +
    '.bref-pres{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:8px 0 10px}' +
    '.bref-pres a{position:relative;display:flex;flex-direction:column;align-items:center;gap:2px;padding:10px 4px 12px;border-radius:12px;background:var(--bg);border:1px solid var(--line);color:var(--fg);text-decoration:none;overflow:hidden}' +
    '.bref-pres a span{font-size:12.5px;color:var(--muted);font-weight:600}.bref-pres a b{font-family:var(--serif);font-size:clamp(22px,7vw,28px);font-weight:500;line-height:1.1}' +
    '.bref-pres a i{position:absolute;left:0;bottom:0;height:4px;background:var(--bad)}.bref-pres a.g i{background:var(--ok)}.bref-pres a.m i{background:var(--mid)}' +
    '.bref-pres a.g b{color:var(--ok)}.bref-pres a.m b{color:var(--mid)}.bref-pres a.b b{color:var(--bad)}' +
    // Le sommaire des thèmes : une ligne par thème (son liseré de couleur, ses ✓ ✗, le nom de chaque indicateur), un toucher mène au thème.
    '.som-cap{margin:12px 0 0;font-size:13px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}' +
    '.som-l{display:grid;gap:8px;margin:8px 0 6px}' +
    '.som-l a{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:3px 10px;align-items:center;padding:11px 12px 11px 14px;border:1px solid var(--line);border-left:6px solid var(--th);border-radius:12px;background:color-mix(in srgb,var(--th) 7%,var(--panel));color:var(--fg);text-decoration:none;min-height:56px;box-sizing:border-box}' +
    '.som-l a:hover,.som-l a:focus-visible{border-color:var(--th)}' +
    '.som-l b{font-size:17px;line-height:1.25;font-weight:700}' +
    '.som-ic{display:inline-flex;align-items:center;gap:5px;font-weight:700;font-size:17px;white-space:nowrap}.som-ic i{font-style:normal}.som-ic .g,.som-l small .g{color:var(--ok)}.som-ic .b,.som-l small .b{color:var(--bad)}.som-ic .m,.som-l small .m{color:var(--mid)}' +
    '.som-ic .fl{color:var(--th);font-size:20px;margin-left:3px}' +
    '.som-l small{grid-column:1/-1;font-size:14px;line-height:1.4;color:var(--muted)}.som-l small i{font-style:normal;font-weight:700}' +
    '.som-l small .som-hors{display:block}' +
    '.bref-cache{display:none!important}' +
    // Sur ordinateur, la toile se range à côté d'« En bref » ; sur téléphone, sous les thèmes.
    '.bref-grille{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,1fr);gap:16px;align-items:start}.bref-grille>*{margin:0!important}' +
    // Thèmes des pages Finances et Éducation (sans ligne ✓ ✗ écrite par la page) : la même ligne que sur les autres pages.
    '.theme>.t-sum.bref-tsum{margin:0;font-size:14px;color:var(--muted)}.t-sum.bref-tsum .ic{display:inline-flex;gap:4px;margin-right:8px}.t-sum.bref-tsum .ic i{font-style:normal;font-weight:700}.t-sum.bref-tsum .ic i.g{color:var(--ok)}.t-sum.bref-tsum .ic i.b{color:var(--bad)}.t-sum.bref-tsum .ic i.m{color:var(--mid)}' +
    '@keyframes bref-flash{0%{box-shadow:0 0 0 3px var(--fr)}100%{box-shadow:0 0 0 3px transparent}}.bref-flash{animation:bref-flash 1.6s ease-out}';
  var esc = function (t) { return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;'); };
  var fmt = function (v) { return new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(Math.round(v * 10) / 10); };
  var ICON = { g: '✓', b: '✗', m: '=' };
  // Haut de page : la date du jour n'est pas répétée au-dessus de la ligne « Dernière mise à jour le… » ; dans les puces, le lien est « Voir ↓ ».
  (function () {
    var st = document.createElement('style'); st.id = 'bref-tete-css';
    st.textContent = '.brand:has(+ #upd) > #today{display:none}.bref-voir{white-space:nowrap;font-weight:600}';
    (document.head || document.documentElement).appendChild(st);
  })();

  // Aller à une courbe : ouvre les blocs repliés qui la contiennent (elle se dessine à l'ouverture), puis y descend.
  // Une petite courbe (« Toucher pour agrandir ») n'existe qu'agrandie : on touche sa vignette, comme à l'arrivée par un lien.
  function aller(id) {
    var el = document.getElementById(id);
    if (!el) { var mini = document.querySelector('.mini[data-courbe="' + id + '"]'); if (mini) { mini.click(); el = document.getElementById(id); } }
    if (!el) return;
    for (var d = el; d; d = d.parentElement) if (d.tagName === 'DETAILS' && !d.open) d.open = true;
    // « Le détail, président par président » : replié en bas de page, il s'ouvre quand on y va depuis les cartes des présidents.
    if (el.id === 'bulletin') { var bp = el.querySelector('details.bul-pli'); if (bp && !bp.open) bp.open = true; }
    // Défilement dès l'image suivante (le bloc ouvert a pris sa place), sans attente.
    requestAnimationFrame(function () {
      // Un chiffre du jour ou du mois : la tuile entière, en tête de son thème.
      var c = el.closest('.dc') || el.closest('.card, .mo') || el.closest('section') || el;
      c.scrollIntoView({ behavior: window.ConcretMenu ? ConcretMenu.doux() : 'smooth', block: 'start' });
      c.classList.remove('bref-flash'); void c.offsetWidth; c.classList.add('bref-flash');
      // La page bouge encore (courbes qui se dessinent au-dessus) : une fois posée, on remet la courbe en haut.
      setTimeout(function () { var h = c.getBoundingClientRect().top; if (h < 60 || h > 260) c.scrollIntoView({ block: 'start' }); }, 1300);
    });
  }

  // Le sommaire des thèmes (« En bref » des pages de mission, et Démographie sans ✓ ✗) : une ligne par thème, dans l'ordre de la page,
  // avec la couleur que commun/menu.js donne au thème (--th1 à --th5, dans le même ordre). th : [{ id, l, items: [{ l, cl }], sans, hors }].
  function sommaire(th) {
    return '<p class="som-cap">Les ' + th.length + ' thèmes de la page</p><div class="som-l">' + th.map(function (t, i) {
      var it = (t.items || []).filter(Boolean);
      var ic = it.map(function (x) { return '<i class="' + x.cl + '">' + ICON[x.cl] + '</i>'; }).join('');
      var det = t.sans ? esc(t.sans) : it.map(function (x) { return '<i class="' + x.cl + '">' + ICON[x.cl] + '</i> ' + esc(x.l); }).join(' · ');
      if (t.hors) det += '<span class="som-hors">' + esc(t.hors) + '</span>';
      var lu = it.length ? it.map(function (x) { return x.l + (x.cl === 'g' ? ' : mieux que la moyenne de l\'UE' : x.cl === 'm' ? ' : égal' : ' : pas mieux'); }).join(', ') : (t.sans || '');
      return '<a href="#' + esc(t.id) + '" data-cible="' + esc(t.id) + '" style="--th:var(--th' + (i % 5 + 1) + ')" aria-label="' + esc(t.l + ' : ' + lu + (t.hors ? '. ' + t.hors : '') + '. Aller au thème') + '"><b>' + esc(t.l) + '</b><span class="som-ic" aria-hidden="true">' + ic + '<span class="fl">›</span></span><small aria-hidden="true">' + det + '</small></a>';
    }).join('') + '</div>';
  }
  // Le sommaire posé dans un bloc (Démographie, qui a son propre « En bref ») : après l'élément « apres » du bloc.
  function poserSommaire(box, th, apres) {
    if (!box) return; css1();
    var d = document.createElement('div'); d.className = 'som'; d.innerHTML = sommaire(th);
    if (apres && apres.parentNode === box) box.insertBefore(d, apres.nextSibling); else box.appendChild(d);
    lierSommaire(d);
  }
  function css1() { if (!document.getElementById('bref-css')) { var st = document.createElement('style'); st.id = 'bref-css'; st.textContent = css; document.head.appendChild(st); } }
  function lierSommaire(box) { box.querySelectorAll('.som-l a').forEach(function (a) { a.addEventListener('click', function (ev) { ev.preventDefault(); aller(a.dataset.cible); if (history.replaceState) history.replaceState(null, '', '#' + a.dataset.cible); }); }); }
  // La ligne ✓ ✗ d'un thème écrit dans la page (Finances, Éducation) : les mêmes signes que dans le sommaire.
  function ligneTheme(t) {
    var el = document.getElementById(t.id); if (!el || el.querySelector(':scope > .t-sum')) return;
    var it = (t.items || []).filter(Boolean), n = it.length, ok = it.filter(function (x) { return x.cl === 'g'; }).length, p = document.createElement('p');
    p.className = 't-sum bref-tsum';
    p.innerHTML = t.sans ? esc(t.sans) : '<span class="ic">' + it.map(function (x) { return '<i class="' + x.cl + '">' + ICON[x.cl] + '</i>'; }).join('') + '</span>' +
      (n === 1 ? (ok ? 'La France fait mieux que la moyenne de l\'UE sur cet indicateur' : 'La France ne fait pas mieux que la moyenne de l\'UE sur cet indicateur') : ok ? 'La France fait mieux que la moyenne de l\'UE sur ' + ok + ' indicateur' + (ok > 1 ? 's' : '') + ' sur ' + n : 'La France ne fait mieux que la moyenne de l\'UE sur aucun des ' + n + ' indicateurs') +
      ' (dernier chiffre connu)' + (n > 1 ? ' : ' + it.map(function (x) { return esc(x.l); }).join(', ') : '') + '.' + (t.note ? ' ' + esc(t.note) : '');
    var h = el.querySelector(':scope > h2'); el.insertBefore(p, h ? h.nextSibling : el.firstChild);
  }
  // La toile : à côté d'« En bref » sur ordinateur ; sur téléphone, sous les thèmes et le détail par président, avant « L'actualité ».
  var LARGE = window.matchMedia ? matchMedia('(min-width: 900px)') : null;
  function placerToile() {
    var rep = document.getElementById('reponse'), to = document.getElementById('toile'), act = document.getElementById('actualite'), g = document.getElementById('bref-grille');
    if (!rep || !to) return;
    var avant = to.parentNode && to.parentNode.id === 'bref-grille';
    if (LARGE && LARGE.matches) {
      if (!g) { g = document.createElement('div'); g.id = 'bref-grille'; g.className = 'bref-grille'; rep.parentNode.insertBefore(g, rep); }
      g.appendChild(rep); g.appendChild(to);
    } else {
      if (g) { g.parentNode.insertBefore(rep, g); g.remove(); }
      if (act && to.nextElementSibling !== act) act.parentNode.insertBefore(to, act);
    }
    var apres = to.parentNode && to.parentNode.id === 'bref-grille';
    if (avant !== apres && window.ConcretPays && ConcretPays.redessiner) ConcretPays.redessiner('toile');
  }
  if (LARGE) { if (LARGE.addEventListener) LARGE.addEventListener('change', placerToile); else if (LARGE.addListener) LARGE.addListener(placerToile); }

  // o.items : [{ l, cl ('g' mieux, 'b' moins bien, 'm' égal), cible (id de la courbe) }] ; o.pres : [{ n, v }] ; o.ref : la référence.
  // o.themes : le sommaire des thèmes (voir sommaire()) ; o.lignes : écrire aussi la ligne ✓ ✗ de chaque thème (pages aux thèmes écrits dans le HTML).
  function render(o) {
    var box = document.getElementById('reponse'); if (!box) return;
    css1();
    var l = o.items.filter(Boolean), ok = l.filter(function (x) { return x.cl === 'g'; }).length, ref = o.ref || 'la moyenne de l\'UE';
    var tri = l.slice().sort(function (a, b) { var r = { g: 0, m: 1, b: 2 }; return r[a.cl] - r[b.cl]; });
    // Le nom de la page dans le titre : l'image partagée dit de quelle mission il s'agit.
    var page = document.querySelector('.brand h1, .brand b'), nom = page ? page.textContent.trim() : '';
    var th = (o.themes || []).filter(Boolean);
    var chips = '<div class="bref-chips">' + tri.map(function (x) { return '<a class="' + x.cl + '" href="#' + esc(x.cible) + '" data-cible="' + esc(x.cible) + '" title="Voir la courbe"><i>' + ICON[x.cl] + '</i>' + esc(x.l) + '</a>'; }).join('') + '</div>';
    box.innerHTML = '<h2><span class="eyebrow">' + (nom ? esc(nom) + ', en bref' : 'En bref') + '</span>La France face à ' + esc(ref) + (th.length ? ', thème par thème' : '') + '</h2>' +
      '<div class="bref-top"><span class="bref-n">' + ok + '<small>/' + l.length + '</small></span><span class="bref-t">indicateurs où la France fait mieux que ' + esc(ref) + ', au dernier chiffre connu' + (o.precision ? ' (' + esc(o.precision) + ')' : '') + '</span></div>' +
      // Avec le sommaire, la liste des indicateurs y est répartie thème par thème ; elle reste dans la page, cachée, pour les cartes
      // d'aperçu et « Le pouls de la France » (outils/apercu.js la lit telle quelle).
      (th.length ? sommaire(th) + '<div class="bref-cache" aria-hidden="true">' + chips + '</div>' : '<details class="bref-det"><summary>Voir les ' + l.length + ' indicateurs</summary>' + chips + '</details>') +
      '<span class="eyebrow" style="margin:4px 0 0">La France sous chaque président</span><div class="bref-pres">' +
      o.pres.map(function (p) {
        var c = p.v == null ? '' : p.v >= 10 ? 'g' : p.v >= 6 ? 'm' : 'b';
        return '<a class="' + c + '" href="#bulletin"><span>' + esc(p.n.split(' ').slice(-1)[0]) + '</span><b>' + (p.v == null ? '—' : fmt(p.v)) + '</b><i style="width:' + (p.v == null ? 0 : 5 * p.v) + '%"></i></a>';
      }).join('') + '</div>' +
      '<p class="note">Sur 20 ; 10 = aussi bien que la moyenne de l\'UE. Le résultat compte, année par année, si la France progresse mieux que la moyenne de l\'UE (ou garde son avance) ; le chiffre du haut compare seulement le dernier niveau connu. Ce n\'est pas un jugement sur la personne : un calcul, le même pour tous, qui dit si la France a fait mieux que la moyenne de l\'UE pendant le mandat. <a class="pt-hors" href="#bulletin">Le détail et les gouvernements ↓</a></p>';
    // Le bouton « Partager » (commun/partage.js) a pu être posé sur le bloc encore vide : on le laisse le reposer.
    box.removeAttribute('data-partage');
    box.querySelectorAll('.bref-chips a').forEach(function (a) { a.addEventListener('click', function (ev) { ev.preventDefault(); aller(a.dataset.cible); }); });
    lierSommaire(box);
    box.querySelectorAll('a[href="#bulletin"]').forEach(function (a) { a.addEventListener('click', function (ev) { ev.preventDefault(); aller('bulletin'); }); });
    if (o.lignes) th.forEach(ligneTheme);
    placerToile();
  }
  // « Depuis votre dernière visite » : d'abord ce qui est nouveau (chiffres, actualités) ; sinon « rien de nouveau »
  // et le prochain rendez-vous de l'agenda (une actualité déjà vue n'est pas reprise). Renvoie les morceaux de la ligne.
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
      // Rien de neuf depuis la visite : on le dit, sans repêcher une actualité déjà vue ; puis le prochain rendez-vous.
      var g = (o.agenda || []).filter(function (a) { return a.date && a.date >= auj; }).sort(function (a, b) { return a.date < b.date ? -1 : 1; })[0];
      if (!na.length) { parts.push('rien de nouveau' + (!g && o.prochains ? ' (' + o.prochains + ')' : '')); if (g) parts.push('prochain rendez-vous, ' + esc(min1(g.quand || dfr(g.date))) + ' : ' + esc(String(g.evenement).replace(/\.$/, ''))); }
      else if (g) parts.push('prochain rendez-vous, ' + esc(min1(g.quand || dfr(g.date))) + ' : ' + esc(String(g.evenement).replace(/\.$/, '')));
    }
    return parts;
  }
  // Haut de page : au plus deux puces. Après une visite : ce qui a changé depuis (les chiffres nouveaux sur la première,
  // l'actualité ou le prochain rendez-vous sur la seconde) ; à la première visite : les dernières nouvelles de la page.
  function afficher(box, titre, parts) {
    if (!box) return; var L = (parts || []).filter(Boolean);
    if (L.length > 2) L = [L.slice(0, L.length - 1).join(' ; '), L[L.length - 1]];
    if (!L.length) { box.hidden = true; return; }
    var maj = function (h) { return h.replace(/^((?:<[^>]+>)*)([a-zà-ÿ])/, function (m, t, c) { return t + c.toUpperCase(); }); };
    var div = document.createElement('div'); div.className = box.className.replace(/\s*visit-res\b/, ''); div.id = box.id;
    div.innerHTML = '<b>' + titre + '</b><ul class="vis-l">' + L.map(function (x) { var t = maj(x), fin = t.replace(/<[^>]+>/g, '').trim().slice(-1); return '<li>' + t + (/[.…!?↓]/.test(fin) ? '' : '.') + '</li>'; }).join('') + '</ul>';
    box.parentNode.replaceChild(div, box); lier(div);
  }
  function premiere(box, o) {
    o = o || {};
    // Les accroches (dernier chiffre, actualité) sont écrites par la page juste après : on les lit un instant plus tard.
    setTimeout(function () {
      // La phrase en texte, puis « Voir ↓ » seul en lien, vers le même bloc.
      var parts = [], lien = function (id, h) { h = h.replace(/\s+$/, ''); var fin = h.replace(/<[^>]+>/g, '').trim().slice(-1); return h + (/[.…!?]/.test(fin) ? '' : '.') + ' <a class="bref-voir" href="#' + id + '" data-cible="' + id + '">Voir ↓</a>'; };
      var dfr = function (s) { return new Date(s + 'T12:00:00').toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' }).replace(/^1 /, '1er '); };
      var court = function (t) { t = String(t); if (t.length <= 110) return t.replace(/\.$/, ''); var c = t.slice(0, 107); return c.slice(0, c.lastIndexOf(' ')) + '…'; };
      // Le dernier chiffre du jour ou du mois : sa tuile, en tête de son thème (data-bref : le libellé ; .dc-bref : la phrase, écrite par la page).
      var tu = document.querySelector('[data-bref]'), tb = tu && tu.querySelector('.dc-bref');
      if (tb && tb.textContent.trim()) parts.push(lien(tu.id, tu.dataset.bref + ' : ' + tb.innerHTML));
      else {
        var acc = Array.prototype.filter.call(document.querySelectorAll('details.acc'), function (d) { return /aujourd'hui|ce mois-ci|du mois/i.test((d.querySelector('.acc-h') || {}).textContent || ''); })[0];
        var tz = acc && acc.querySelector('.acc-t');
        if (tz && tz.textContent.trim() && tz.textContent.trim() !== '—') parts.push(lien(acc.id, ((acc.querySelector('.acc-h') || {}).textContent || '').trim() + ' : ' + tz.innerHTML));
      }
      var A = (o.actu || []).filter(function (a) { return a.texte && a.date; }).sort(function (a, b) { return a.date < b.date ? 1 : -1; });
      if (A[0]) parts.push(lien('acc-actu', 'Actualité du ' + esc(dfr(A[0].date)) + ' : ' + esc(court(A[0].texte))));
      afficher(box, 'Les dernières nouvelles', parts);
    }, 300);
  }
  // Les liens de la ligne mènent au bloc visé (ouvert s'il est replié).
  function lier(box) { box.querySelectorAll('a[data-cible]').forEach(function (a) { a.addEventListener('click', function (ev) { ev.preventDefault(); aller(a.dataset.cible); }); }); }
  // Lien venu d'une autre page (par exemple le quiz) vers une courbe repliée : on attend qu'elle existe, puis on l'ouvre.
  if (location.hash.length > 1) {
    var vise = decodeURIComponent(location.hash.slice(1)), essais = 0;
    // Une petite courbe (« Toucher pour agrandir ») n'existe qu'agrandie : on touche sa vignette, puis on y descend.
    var t = setInterval(function () {
      var el = document.getElementById(vise), mini = !el && document.querySelector('.mini[data-courbe="' + vise + '"]');
      if (mini) { mini.click(); el = document.getElementById(vise); }
      if (el || ++essais > 40) { clearInterval(t); if (el) aller(vise); }
    }, 250);
  }
  window.ConcretBref = { render: render, sommaire: sommaire, poserSommaire: poserSommaire, lierSommaire: lierSommaire, placerToile: placerToile, aller: aller, nouveau: nouveau, lier: lier, afficher: afficher, premiere: premiere };
})();
