/* Menu du site pour tous : sur téléphone, un bouton « Menu » toujours visible au bout du bandeau (qui ouvre la liste des
   pages en grands boutons, avec une ligne d'explication chacune), un dégradé qui montre que le bandeau continue, et en bas
   de chaque page un bloc « Les autres pages ». Sur un grand écran, le bandeau tient en entier : seul le bloc du bas s'ajoute. */
(function () {
  var PAGES = [
    { u: '/', l: 'Accueil', t: 'Le classement des présidents et le pouls de la France', ic: 'accueil', large: 1 },
    { u: '/barometre/', l: 'Baromètre 2027', t: 'Sondages et parieurs', ic: 'barometre', g: 'Chaque jour' },
    { u: '/quiz/', l: 'Quiz du jour', t: 'Huit questions sourcées', ic: 'quiz', g: 'Chaque jour' },
    { u: '/votez/', l: 'Votez les lois', t: 'Les vrais votes de l\'Assemblée, à votre tour', ic: 'votez', g: 'Chaque jour' },
    { u: '/vie/', l: 'Vie des Français', t: 'Pouvoir d\'achat, logement, travail', ic: 'vie', g: 'Les missions notées' },
    { u: '/finances/', l: 'Finances publiques', t: 'Dette, déficit, impôts', ic: 'finances', g: 'Les missions notées' },
    { u: '/sante/', l: 'Santé', t: 'Espérance de vie, soins, prévention', ic: 'sante', g: 'Les missions notées' },
    { u: '/education/', l: 'Éducation', t: 'PISA, diplômes, décrochage', ic: 'education', g: 'Les missions notées' },
    { u: '/securite/', l: 'Sécurité et justice', t: 'Homicides, prisons, justice', ic: 'securite', g: 'Les missions notées' },
    { u: '/defense/', l: 'Défense', t: 'Budget, OTAN, effectifs', ic: 'defense', g: 'Les missions notées' },
    { u: '/politique/', l: 'La vie politique', t: 'Lois, votes, grandes dates', ic: 'politique', g: 'Repères, sans note' },
    { u: '/demographie/', l: 'Démographie', t: 'Naissances, âges, migrations', ic: 'demographie', g: 'Repères, sans note' }
  ];
  // Icônes des pages, au trait, dans la couleur d'accent.
  var IC = {
    accueil: '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
    barometre: '<path d="M4 20h16"/><path d="M7 16v-5"/><path d="M12 16V6"/><path d="M17 16v-8"/>',
    quiz: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6v.6"/><path d="M12 17.2v.1"/>',
    vie: '<path d="M4 8h16l-1.5 11h-13z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>',
    finances: '<path d="M17 6.5A6.5 6.5 0 1 0 17 17.5"/><path d="M4 10.5h9"/><path d="M4 13.5h9"/>',
    sante: '<path d="M10 4h4v6h6v4h-6v6h-4v-6H4v-4h6z"/>',
    education: '<path d="M2 9l10-5 10 5-10 5z"/><path d="M6 11v5c3 2 9 2 12 0v-5"/>',
    securite: '<path d="M12 4v16"/><path d="M8 20h8"/><path d="M5 7h14"/><path d="M5 7l-3 6a3 3 0 0 0 6 0z"/><path d="M19 7l-3 6a3 3 0 0 0 6 0z"/>',
    defense: '<path d="M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6z"/>',
    votez: '<path d="M4 12h16v8H4z"/><path d="M7 12V4h10v8"/><path d="M9.5 8l2 2 3.5-3.5"/>',
    politique: '<path d="M3 9l9-5 9 5"/><path d="M5 9v8"/><path d="M10 9v8"/><path d="M14 9v8"/><path d="M19 9v8"/><path d="M3 20h18"/>',
    demographie: '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><circle cx="17" cy="9" r="2.4"/><path d="M16 14.2c2.8.2 5 2.6 5 5.8"/>',
    cherche: '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
    lettre: '<rect x="3" y="5.5" width="18" height="13" rx="2"/><path d="M3.5 7l8.5 6 8.5-6"/>'
  };
  var icone = function (k) { return '<i class="mn-ic" aria-hidden="true"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + IC[k] + '</svg></i>'; };
  // Couleurs des pages (les pages et le Baromètre n'ont pas les mêmes noms de variables).
  var V = { bg: 'var(--bg, var(--color-bg, #f6f6f3))', panel: 'var(--panel, var(--color-panel, #fff))', fg: 'var(--fg, var(--color-fg, #1c1d22))',
    muted: 'var(--muted, var(--color-fg-muted, #62646d))', line: 'var(--line, var(--color-border-line, #e2e2dc))', fr: 'var(--fr, #2f5bd3)' };
  var css = '.mn-btn{position:sticky;right:0;margin-left:auto;flex:none;display:none;align-items:center;gap:6px;font:inherit;font-size:14px;font-weight:700;color:' + V.fg + ';' +
      'background:linear-gradient(to right,transparent,' + V.bg + ' 26px);box-shadow:24px 0 0 0 ' + V.bg + ';border:0;padding:4px 2px 4px 34px;cursor:pointer}' +
    '.mn-btn span{display:inline-flex;align-items:center;gap:6px;border:1.5px solid ' + V.fg + ';border-radius:999px;padding:4px 11px;background:' + V.panel + '}' +
    '.mn-btn:focus-visible span{outline:2px solid ' + V.fr + ';outline-offset:2px}' +
    '.mn-btn{display:inline-flex}' +
    '.mn-voile{position:fixed;inset:0;z-index:50;background:rgba(10,12,18,.5);display:flex;justify-content:flex-end}' +
    '.mn-panneau{background:' + V.bg + ';width:min(100%,420px);height:100%;overflow:auto;padding:max(14px,env(safe-area-inset-top,0px)) 16px max(20px,env(safe-area-inset-bottom,0px));display:grid;align-content:start;gap:10px;box-sizing:border-box}' +
    '.mn-haut{display:flex;justify-content:space-between;align-items:center;padding:4px 2px 6px}.mn-haut b{font-family:"Newsreader",Georgia,serif;font-weight:500;font-size:24px;color:' + V.fg + '}' +
    '.mn-ferme{font:inherit;font-size:15px;font-weight:600;border:1.5px solid ' + V.line + ';background:' + V.panel + ';color:' + V.fg + ';border-radius:999px;padding:6px 14px;cursor:pointer}' +
    '.mn-liste{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.mn-g{grid-column:1/-1;margin:10px 2px 0;font-size:12.5px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:' + V.muted + '}' +
    '.mn-liste a{display:grid;grid-template-columns:auto minmax(0,1fr);column-gap:10px;align-items:center;align-content:center;padding:11px 12px;border-radius:12px;border:1px solid ' + V.line + ';background:' + V.panel + ';color:' + V.fg + ';text-decoration:none;min-height:44px}' +
    '.mn-liste a.mn-large{grid-column:1/-1}' +
    '.mn-ic{grid-row:span 2;display:grid;place-items:center;width:36px;height:36px;border-radius:10px;color:' + V.fr + ';background:rgba(47,91,211,.1)}' +
    '.mn-liste a b{font-size:15.5px;font-weight:700;line-height:1.2}.mn-liste a span{font-size:12.5px;color:' + V.muted + ';line-height:1.3}' +
    '.mn-liste a:hover{border-color:' + V.fr + '}' +
    '.mn-liste a[aria-current]{border:2px solid ' + V.fr + ';padding:10px 11px}.mn-liste a[aria-current] span::before{content:"Vous êtes ici · ";color:' + V.fr + ';font-weight:600}' +
    '.mn-pied{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}.mn-pied a,.mn-pied button{display:inline-flex;align-items:center;gap:6px;font:inherit;font-size:14px;font-weight:600;color:' + V.fg + ';background:' + V.panel + ';border:1px solid ' + V.line + ';border-radius:999px;padding:6px 14px 6px 8px;text-decoration:none;cursor:pointer;min-height:44px}' +
    '.mn-pied .mn-ic{width:28px;height:28px;background:none}' +
    '.pg.mn-avec{grid-template-columns:auto minmax(0,1fr);column-gap:12px}.pg.mn-avec>*{grid-column:2}.pg.mn-avec>.mn-ic{grid-column:1;grid-row:1/span 4;align-self:start;margin-top:2px}' +
    // Dans le Menu : une colonne, une ligne par page. En bas de page : deux colonnes sur téléphone (nom seul), quatre sur grand écran.
    '.mn-panneau .mn-liste{grid-template-columns:minmax(0,1fr);gap:6px}.mn-panneau .mn-liste a{padding:9px 12px}.mn-panneau .mn-liste a[aria-current]{padding:8px 11px}' +
    '.mn-autres .mn-liste a.mn-large{grid-column:auto}' +
    // Sur téléphone, en bas de page : des pastilles (icône et nom) qui se suivent, sans intitulés de groupe, pour tenir en peu de place.
    '@media (max-width:600px){.mn-autres .mn-liste{display:flex;flex-wrap:wrap;gap:6px}.mn-autres .mn-g{display:none}.mn-autres .mn-liste a{display:inline-flex;gap:6px;padding:6px 12px 6px 6px;border-radius:999px;min-height:40px}.mn-autres .mn-liste a span{display:none}.mn-autres .mn-ic{width:28px;height:28px;border-radius:50%}.mn-autres .mn-ic svg{width:16px;height:16px}.mn-autres .mn-liste a b{font-size:14px;font-weight:600}}' +
    '.mn-contact{margin:2px 0 0;font-size:14px;color:' + V.muted + '}.mn-contact a{color:' + V.fr + ';font-weight:600}' +
    '.mn-autres{display:grid;gap:10px;margin:8px 0 4px}.mn-autres h2{font-size:19px;font-weight:600;margin:0;color:' + V.fg + '}' +
    '@media (min-width:760px){.mn-autres .mn-liste{grid-template-columns:repeat(4,minmax(0,1fr))}}' +
    // Le bandeau tient toujours en entier : le logo, les rendez-vous quotidiens (Baromètre, Quiz, Votez), la vie politique et la page
    // en cours ; toutes les pages sont dans le Menu, visible à toutes les largeurs. Sur téléphone : logo, rendez-vous, loupe et Menu.
    'nav.site>a:not(.logo):not([href="/barometre/"]):not([href="/quiz/"]):not([href="/votez/"]):not([href="/politique/"]):not([aria-current]){display:none}' +
    '@media (max-width:520px){nav.site>a[href="/politique/"]:not([aria-current]),nav.site>a[aria-current]:not(.logo):not([href="/barometre/"]):not([href="/quiz/"]):not([href="/votez/"]){display:none}nav.site>a{padding-block:8px}nav.site{gap:11px!important}.mn-btn{padding-left:8px}nav.site .rech-b{display:none}}' +
    '@media (max-width:380px){nav.site{gap:8px!important}nav.site a.logo{font-size:17px!important}.mn-btn span{padding:4px 9px}}' +
    // Les trois rendez-vous quotidiens ressortent dans le bandeau.
    'nav.site>a[href="/barometre/"],nav.site>a[href="/quiz/"],nav.site>a[href="/votez/"]{color:' + V.fg + ';font-weight:600}' +
    // Lisibilité commune à toutes les pages : textes d'appoint pas trop petits, graduations des graphiques lisibles, zones à toucher assez grandes.
    '.note{font-size:14px;line-height:1.45}.bx-note{font-size:13.5px}.eyebrow{font-size:12.5px}svg .tick text{font-size:12px}' +
    // Pastilles des tableaux « Année par année » : point marqué, pas de point, demi-point (égalité).
    '.pt{display:inline-block;width:.8em;height:.8em;border-radius:50%;border:2px solid currentColor;box-sizing:border-box;vertical-align:-.08em}.pt.p1{background:currentColor}.pt.ph{background:linear-gradient(90deg,currentColor 50%,transparent 50%)}' +
    '.rech-b{min-width:44px;min-height:44px;justify-content:center}button.share,.bx-share{min-height:40px}' +
    // Boutons pleins (bleu) en mode sombre : texte foncé, lisible sur le bleu clair du thème sombre.
    '@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .ct-envoyer,:root:not([data-theme="light"]) .qz-btn,:root:not([data-theme="light"]) .vz-suite{color:#0b1530}}:root[data-theme="dark"] .ct-envoyer,:root[data-theme="dark"] .qz-btn,:root[data-theme="dark"] .vz-suite{color:#0b1530}' +
    // Un seul style pour « Voir plus de lignes » sur tout le site : bouton contour, texte bleu.
    'button.more,button.plus,.bx-voir{font:inherit;font-size:14px;font-weight:600;color:' + V.fr + '!important;background:' + V.panel + '!important;border:1px solid ' + V.line + '!important;border-radius:999px!important;min-height:44px;padding:8px 16px;cursor:pointer}' +
    // Lignes de texte pas trop longues sur grand écran.
    '.card>p,.card .note{max-width:72ch}' +
    // Long texte sous une courbe : deux lignes, puis « Détail du graphe » pour lire la suite.
    // Titre d'une courbe : ce qui est mesuré en titre, la conclusion chiffrée dessous, en plus petit.
    'h2.inv,h3.inv{font-size:14.5px;font-weight:400;line-height:1.4;color:' + V.muted + '}h2.inv .eyebrow,h3.inv .eyebrow{font-size:18px;font-weight:700;line-height:1.25;letter-spacing:0;text-transform:none;color:' + V.fg + ';margin-bottom:3px}' +
    '.mn-maj{position:fixed;left:50%;transform:translateX(-50%);bottom:max(16px,env(safe-area-inset-bottom,0px));z-index:60;display:flex;align-items:center;gap:12px;width:min(calc(100% - 24px),480px);box-sizing:border-box;padding:12px 14px;border:0;border-radius:14px;background:' + V.fg + ';color:' + V.bg + ';font:inherit;font-size:14px;text-align:left;box-shadow:0 6px 24px rgba(0,0,0,.25);cursor:pointer}' +
    '.mn-maj span{flex:1}.mn-maj b{flex:none;padding:6px 12px;border-radius:999px;background:' + V.fr + ';color:#fff;font-weight:700}' +
    '.nt-pli{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;line-clamp:2;overflow:hidden}' +
    '.nt-btn{font:inherit;font-size:13.5px;font-weight:600;color:' + V.fr + ';background:none;border:0;padding:6px 0;margin-top:-6px;min-height:36px;cursor:pointer;justify-self:start;align-self:start;text-align:left}' +
    '.nt-btn:focus-visible{outline:2px solid ' + V.fr + ';outline-offset:2px}';
  var ici = location.pathname.replace(/index\.html$/, '');
  var lien = function (p) { return '<a href="' + p.u + '"' + (p.large ? ' class="mn-large"' : '') + (p.u === ici ? ' aria-current="page"' : '') + '>' + icone(p.ic) + '<b>' + p.l + '</b><span>' + p.t + '</span></a>'; };
  // Les pages par groupe (« Chaque jour », « Les missions notées », « Repères, sans note ») : un intitulé avant chaque groupe.
  var liste = function (L) { var g = null; return L.map(function (p) { var h = p.g && p.g !== g ? '<h3 class="mn-g">' + p.g + '</h3>' : ''; g = p.g || g; return h + lien(p); }).join(''); };

  function ouvrir(btn) {
    var v = document.createElement('div'); v.className = 'mn-voile';
    v.innerHTML = '<div class="mn-panneau" role="dialog" aria-modal="true" aria-label="Les pages de Concret"><div class="mn-haut"><b>Les pages de Concret</b><button type="button" class="mn-ferme">Fermer ✕</button></div><nav class="mn-liste">' + liste(PAGES) + '</nav><div class="mn-pied">' + (document.querySelector('.rech-b') ? '<button type="button" class="mn-cherche">' + icone('cherche') + 'Rechercher un chiffre</button>' : '') + (ici !== '/contact/' ? '<a href="/contact/">' + icone('lettre') + 'Écrire à Concret</a>' : '') + '</div></div>';
    var fermer = function () { v.remove(); document.removeEventListener('keydown', esc); document.documentElement.style.overflow = ''; btn.focus(); };
    var esc = function (e) { if (e.key === 'Escape') fermer(); };
    v.addEventListener('click', function (e) { if (e.target === v || e.target.closest('.mn-ferme')) fermer(); else if (e.target.closest('.mn-cherche')) { fermer(); document.querySelector('.rech-b').click(); } });
    document.addEventListener('keydown', esc); document.documentElement.style.overflow = 'hidden';
    document.body.appendChild(v); v.querySelector('.mn-ferme').focus();
  }

  // Hauteur du bandeau du haut (--navh) : les barres « Aller à » se collent juste en dessous, et les ancres ne passent pas dessous.
  function hauteur() {
    var n = document.querySelector('nav.site'); if (!n) return;
    var f = function () { document.documentElement.style.setProperty('--navh', n.offsetHeight + 'px'); };
    f(); if (window.ResizeObserver) new ResizeObserver(f).observe(n); else addEventListener('resize', f);
  }

  // Textes sous les courbes : au-delà de trois lignes, on n'en montre que deux, avec un lien « Détail du graphe » qui déplie
  // le reste. Les pages réécrivent ces textes quand elles redessinent une courbe : on les revoit à chaque changement.
  // Sur le Baromètre, les explications en tête de chaque bloc aussi (« Lire la suite »).
  // Sur la page Démographie, les paragraphes « À retenir » et les introductions longues aussi.
  var NT = '.chart ~ p.note, .toile-svg ~ p.note, .bx-card > p.bx-note, .bx-group > p.bx-note, p.retenir, p.dernier';
  function plier() {
    Array.prototype.forEach.call(document.querySelectorAll(NT), function (n) {
      if (n.classList.contains('pt-hors') || n.classList.contains('defs')) return;
      var b = n.nextElementSibling;
      if (!b || !b.classList.contains('nt-btn')) {
        b = document.createElement('button'); b.type = 'button'; b.className = 'nt-btn'; b.hidden = true;
        b.addEventListener('click', function () { n.dataset.ntOuvert = n.dataset.ntOuvert ? '' : '1'; plier(); });
        n.parentNode.insertBefore(b, n.nextSibling);
      }
      var ouvert = !!n.dataset.ntOuvert, deja = n.classList.contains('nt-pli');
      if (deja) n.classList.remove('nt-pli');
      var lh = parseFloat(getComputedStyle(n).lineHeight) || 20, long = n.offsetHeight > lh * 3.4;
      if (long && !ouvert) n.classList.add('nt-pli');
      var bx = n.classList.contains('bx-note') || n.classList.contains('retenir') || n.classList.contains('dernier'), t = !long ? '' : ouvert ? (bx ? 'Masquer ▴' : 'Masquer le détail ▴') : (bx ? 'Lire la suite ▾' : 'Détail du graphe ▾');
      if (b.textContent !== t) b.textContent = t;
      if (b.hidden === !!t) b.hidden = !t;
      b.setAttribute('aria-expanded', ouvert ? 'true' : 'false');
    });
  }
  var plierPrevu = 0;
  function plierBientot() { if (!plierPrevu) plierPrevu = setTimeout(function () { plierPrevu = 0; plier(); }, 120); }

  // Nouvelle version du site : la page connaît sa version (<meta name="concret-version">, écrite par outils/version.js) et la compare
  // à celle en ligne (donnees/version.json), à l'ouverture et à chaque retour au premier plan (la web app reste ouverte en arrière-plan).
  // Si elles diffèrent, un bandeau propose de recharger la page, sans attendre que le téléphone oublie l'ancienne.
  var vPage = (document.querySelector('meta[name="concret-version"]') || {}).content, vVu = 0;
  function verifierVersion() {
    if (!vPage || !window.fetch || Date.now() - vVu < 60000 || document.getElementById('mn-maj')) return;
    vVu = Date.now();
    fetch('/donnees/version.json?t=' + Date.now(), { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; }).then(function (o) {
      if (!o || !o.v || o.v === vPage || document.getElementById('mn-maj')) return;
      var b = document.createElement('button'); b.type = 'button'; b.id = 'mn-maj'; b.className = 'mn-maj';
      b.innerHTML = '<span>Une nouvelle version de Concret est en ligne.</span><b>Mettre à jour</b>';
      b.addEventListener('click', function () { b.disabled = true; location.replace(location.pathname + '?maj=' + Date.now() + location.hash); });
      document.body.appendChild(b);
    }).catch(function () {});
  }
  function init() {
    // Après une mise à jour, l'adresse perd son « ?maj=… ».
    if (/[?&]maj=/.test(location.search) && history.replaceState) history.replaceState(null, '', location.pathname + location.hash);
    verifierVersion();
    document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'visible') verifierVersion(); });
    addEventListener('pageshow', function (e) { if (e.persisted) verifierVersion(); });
    hauteur();
    plier();
    if (window.MutationObserver) new MutationObserver(function (ms) {
      for (var i = 0; i < ms.length; i++) { var t = ms[i].target; if (t.nodeType !== 1) t = t.parentNode; if (t && t.closest && t.closest('p.note, .chart') || ms[i].addedNodes.length) { plierBientot(); return; } }
    }).observe(document.body, { childList: true, characterData: true, subtree: true });
    addEventListener('resize', plierBientot);
    document.addEventListener('toggle', plierBientot, true);
    if (!document.getElementById('mn-css')) { var st = document.createElement('style'); st.id = 'mn-css'; st.textContent = css; document.head.appendChild(st); }
    var nav = document.querySelector('nav.site');
    if (nav && !nav.querySelector('.mn-btn')) {
      var b = document.createElement('button'); b.type = 'button'; b.className = 'mn-btn'; b.setAttribute('aria-haspopup', 'dialog');
      b.innerHTML = '<span>☰ Menu</span>'; b.addEventListener('click', function () { ouvrir(b); }); nav.appendChild(b);
    }
    // Sur l'accueil : la même icône devant chaque page de la liste des missions, des repères, du Baromètre et du Quiz.
    Array.prototype.forEach.call(document.querySelectorAll('#missions a.pg, #reperes a.pg, #rendez-vous a.pg'), function (a) {
      var p = PAGES.filter(function (x) { return x.u === a.getAttribute('href'); })[0];
      if (!p || a.querySelector('.mn-ic')) return;
      a.classList.add('mn-avec'); a.insertAdjacentHTML('afterbegin', icone(p.ic));
    });
    // En bas de page (pas sur l'accueil, qui a déjà la liste des missions) : les autres pages.
    if (ici !== '/' && !document.querySelector('.mn-autres')) {
      var f = document.querySelector('footer'), sec = document.createElement('section');
      sec.className = 'mn-autres'; sec.setAttribute('aria-label', 'Les autres pages'); sec.setAttribute('data-partage', 'non');
      sec.innerHTML = '<h2>Les autres pages</h2><nav class="mn-liste">' + liste(PAGES.filter(function (p) { return p.u !== ici; })) + '</nav>' +
        (ici !== '/contact/' ? '<p class="mn-contact">Une erreur dans un chiffre, une question ? <a href="/contact/">Écrire à Concret</a></p>' : '');
      if (f && f.parentNode) f.parentNode.insertBefore(sec, f); else (document.querySelector('.wrap, .bx') || document.body).appendChild(sec);
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
