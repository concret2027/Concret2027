/* Menu du site pour tous : sur téléphone, un bouton « Menu » toujours visible au bout du bandeau (qui ouvre la liste des
   pages en grands boutons, avec une ligne d'explication chacune), un dégradé qui montre que le bandeau continue, et en bas
   de chaque page un bloc « Les autres pages ». Sur un grand écran, le bandeau tient en entier : seul le bloc du bas s'ajoute. */
// Taille du texte réglée sur le téléphone. Sur iPhone et iPad (Réglages > Luminosité et affichage > Taille du texte), Safari la
// donne par la police -apple-system-body, 17 px au réglage par défaut : chaque taille de texte en px des feuilles de style et
// des attributs style est multipliée par le même rapport (jamais réduite, au plus 1,6 fois) ; les courbes (SVG) gardent la leur.
// Le texte grossit et passe à la ligne, la page ne déborde pas. Ailleurs (Android, ordinateur), le navigateur applique lui-même
// son réglage de taille ou de zoom.
(function () {
  var r = 1;
  try {
    if (window.CONCRET_TEXTE) r = +window.CONCRET_TEXTE; // essais seulement
    else {
      var p = document.createElement('span'); p.style.font = '-apple-system-body';
      if (p.style.font) { p.textContent = 'a'; (document.body || document.documentElement).appendChild(p); r = parseFloat(getComputedStyle(p).fontSize) / 17; p.remove(); }
    }
  } catch (e) { r = 1; }
  r = Math.min(1.6, r || 1);
  if (r < 1.03) return;
  var vu = typeof WeakSet === 'function' ? new WeakSet() : null; if (!vu) return;
  var SVG = /(^|[\s>+~,(])(svg|text|tspan)\b/i, PX = /^([\d.]+)px$/;
  // Le petit texte grossit le plus ; un titre ou un grand chiffre, déjà lisible, un peu moins (rien au-delà de 32 px), comme le fait le téléphone.
  var gros = function (v) { var f = parseFloat(v), w = Math.min(1, Math.max(0, (32 - f) / 17)); return Math.round(f * (1 + (r - 1) * w) * 10) / 10 + 'px'; };
  function regles(l) {
    l = Array.prototype.slice.call(l);
    for (var i = 0; i < l.length; i++) {
      var x = l[i];
      if (x.style && !vu.has(x)) {
        vu.add(x);
        for (var j = 0; j < x.style.length; j++) { // tailles données par des variables (--…font-size…)
          var nm = x.style[j], vv = x.style.getPropertyValue(nm).trim();
          if (nm.indexOf('--') === 0 && /font-size/.test(nm) && PX.test(vv)) x.style.setProperty(nm, gros(vv));
        }
        var f = x.style.fontSize;
        if (PX.test(f) && !SVG.test(x.selectorText || '')) {
          var imp = x.style.getPropertyPriority('font-size');
          x.style.setProperty('font-size', gros(f), imp);
          // Les textes des courbes (SVG) gardent leur taille : règle ajoutée juste après, pour eux seuls.
          try {
            var pa = x.parentRule || x.parentStyleSheet, k = Array.prototype.indexOf.call(pa.cssRules, x) + 1;
            pa.insertRule(':is(' + x.selectorText + '):is(svg *){font-size:' + f + (imp ? ' !important' : '') + '}', k);
            vu.add(pa.cssRules[k]);
          } catch (e) {}
        }
      }
      if (x.cssRules && x.cssRules.length) regles(x.cssRules); // @media, @supports, règles imbriquées
    }
  }
  function feuilles() { for (var i = 0; i < document.styleSheets.length; i++) { try { regles(document.styleSheets[i].cssRules); } catch (e) {} } }
  function attr(el) {
    if (el.nodeType !== 1 || el.ownerSVGElement || el.tagName === 'svg' || vu.has(el)) return;
    vu.add(el);
    var f = el.style && el.style.fontSize; if (f && PX.test(f)) el.style.fontSize = gros(f);
  }
  function arbre(n) { attr(n); if (n.querySelectorAll) Array.prototype.forEach.call(n.querySelectorAll('[style*="font-size"]'), attr); }
  feuilles(); arbre(document.documentElement);
  // Un mot trop long pour sa case passe à la ligne (coupé en français), un tableau trop large défile dans son cadre.
  var st = document.createElement('style');
  st.textContent = 'body{overflow-wrap:break-word;-webkit-hyphens:auto;hyphens:auto}td,th{-webkit-hyphens:manual;hyphens:manual}';
  vu.add(st); (document.head || document.documentElement).appendChild(st);
  var att = 0;
  function tableaux() {
    clearTimeout(att);
    att = setTimeout(function () {
      Array.prototype.forEach.call(document.querySelectorAll('table'), function (t) {
        var pa = t.parentElement; if (!pa || t.closest('svg')) return;
        for (var a = pa; a && a !== document.body; a = a.parentElement) { var o = getComputedStyle(a).overflowX; if (o === 'auto' || o === 'scroll' || o === 'hidden') return; }
        var lim = (pa.children.length === 1 ? pa.parentElement : pa).clientWidth;
        if (t.getBoundingClientRect().width <= lim + 1) return;
        if (pa.children.length === 1 && pa !== document.body) { pa.style.overflowX = 'auto'; pa.style.maxWidth = '100%'; pa.style.minWidth = '0'; return; }
        var d = document.createElement('div'); d.style.overflowX = 'auto'; d.style.maxWidth = '100%';
        pa.insertBefore(d, t); d.appendChild(t);
      });
    }, 150);
  }
  // Styles et blocs ajoutés ensuite par les scripts des pages.
  new MutationObserver(function (m) {
    var css = false;
    m.forEach(function (x) {
      Array.prototype.forEach.call(x.addedNodes, function (n) {
        if (n.nodeType !== 1) return;
        if (n.tagName === 'STYLE') css = true;
        else if (n.tagName === 'LINK') n.addEventListener('load', feuilles);
        else arbre(n);
      });
    });
    if (css) feuilles();
    tableaux();
  }).observe(document.documentElement, { childList: true, subtree: true });
  window.addEventListener('load', function () { feuilles(); tableaux(); });
  window.addEventListener('resize', tableaux);
})();
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
  var css = '.acc-fixe>summary{cursor:default;border-bottom:0!important;margin-bottom:0!important;padding-bottom:2px}.acc-fixe>summary .acc-t,.acc-fixe>summary .acc-cta{display:none}.mn-btn{position:sticky;right:0;margin-left:auto;flex:none;display:none;align-items:center;gap:6px;font:inherit;font-size:14px;font-weight:700;color:' + V.fg + ';' +
      'background:linear-gradient(to right,transparent,' + V.bg + ' 26px);box-shadow:24px 0 0 0 ' + V.bg + ';border:0;padding:4px 2px 4px 34px;cursor:pointer}' +
    '.mn-btn span{display:inline-flex;align-items:center;gap:6px;border:1.5px solid ' + V.fg + ';border-radius:999px;padding:9px 14px;background:' + V.panel + '}' +
    // Zones à toucher de 44 px au moins (pages du bandeau, raccourcis « Aller à »), pour tous les doigts.
    'nav.site>a{display:inline-flex;align-items:center;min-height:44px;min-width:44px;justify-content:center;padding:0 4px;box-sizing:border-box}' +
    // En flex, l'espace en tête de « 2027 », « du jour », « les lois » disparaît : on le remet (sinon « Baromètre2027 » sur ordinateur).
    'nav.site>a .lg{margin-left:.28em}' +
    'nav.jump a,.jump-l1>a{display:inline-flex;align-items:center;min-height:44px;box-sizing:border-box}' +
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
    '.mn-pied{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,150px),1fr));gap:8px;margin:0 0 12px}.mn-pied a,.mn-pied button{display:flex;align-items:center;gap:6px;text-align:left;line-height:1.2;font:inherit;font-size:14px;font-weight:600;color:' + V.fg + ';background:' + V.panel + ';border:1px solid ' + V.line + ';border-radius:999px;padding:6px 14px 6px 8px;text-decoration:none;cursor:pointer;min-height:44px}' +
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
    '.nt-pli{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:var(--nt-l,2);line-clamp:var(--nt-l,2);overflow:hidden}' +
    '.nt-btn{font:inherit;font-size:13.5px;font-weight:600;color:' + V.fr + ';background:none;border:0;padding:6px 0;margin-top:-6px;min-height:36px;cursor:pointer;justify-self:start;align-self:start;text-align:left}' +
    '.nt-btn:focus-visible{outline:2px solid ' + V.fr + ';outline-offset:2px}' +
    // Sur toutes les pages, les dépliants qui cachent des courbes (« Voir 2 autres courbes… ») se voient : fond bleu, gras, trait à gauche.
    '.fold>summary,details.plus>summary{font-weight:700;color:' + V.fr + ';background:rgba(47,91,211,.10);background:color-mix(in srgb,' + V.fr + ' 13%,transparent);border-left:4px solid ' + V.fr + ';border-radius:12px;justify-content:space-between;gap:10px}' +
    '.fold>summary:hover,details.plus>summary:hover,.fold[open]>summary,details.plus[open]>summary{background:rgba(47,91,211,.16);background:color-mix(in srgb,' + V.fr + ' 20%,transparent)}';
  var ici = location.pathname.replace(/index\.html$/, '');
  var lien = function (p) { return '<a href="' + p.u + '"' + (p.large ? ' class="mn-large"' : '') + (p.u === ici ? ' aria-current="page"' : '') + '>' + icone(p.ic) + '<b>' + p.l + '</b><span>' + p.t + '</span></a>'; };
  // Les pages par groupe (« Chaque jour », « Les missions notées », « Repères, sans note ») : un intitulé avant chaque groupe.
  var liste = function (L) { var g = null; return L.map(function (p) { var h = p.g && p.g !== g ? '<h3 class="mn-g">' + p.g + '</h3>' : ''; g = p.g || g; return h + lien(p); }).join(''); };

  function ouvrir(btn) {
    var v = document.createElement('div'); v.className = 'mn-voile';
    v.innerHTML = '<div class="mn-panneau" role="dialog" aria-modal="true" aria-label="Les pages de Concret"><div class="mn-haut"><b>Les pages de Concret</b><button type="button" class="mn-ferme">Fermer ✕</button></div><div class="mn-pied">' + (document.querySelector('.rech-b') ? '<button type="button" class="mn-cherche">' + icone('cherche') + 'Rechercher un chiffre</button>' : '') + (ici !== '/contact/' ? '<a href="/contact/">' + icone('lettre') + 'Écrire à Concret</a>' : '') + '</div><nav class="mn-liste">' + liste(PAGES) + '</nav></div>';
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
  // Sur toute page, un texte marqué class="replie" aussi (« Voir le détail », --nt-l : lignes montrées, 2 par défaut), et une liste
  // marquée ainsi montre ses premiers éléments (data-n, 2 par défaut ; data-voir : le libellé, {n} pour leur nombre).
  // Une explication de ce qui n'est pas compté, ni les mentions obligatoires d'un sondage (class="mentions"), ne se replient jamais.
  var NT = '.chart ~ p.note, .toile-svg ~ p.note, .bx-card > p.bx-note, .bx-group > p.bx-note, p.retenir, p.dernier, .replie:not(ul):not(ol)';
  function bouton(n) {
    var b = n.nextElementSibling;
    if (!b || !b.classList.contains('nt-btn')) {
      b = document.createElement('button'); b.type = 'button'; b.className = 'nt-btn'; b.hidden = true;
      b.addEventListener('click', function () { n.dataset.ntOuvert = n.dataset.ntOuvert ? '' : '1'; plier(); });
      n.parentNode.insertBefore(b, n.nextSibling);
    }
    return b;
  }
  // Ce qui n'est pas compté s'explique là où on le voit, jamais replié : dans une note qui va être repliée, les phrases
  // « Non compté… », « … ne sont pas comptées », « Affiché, pas compté… », « France seule… » passent dans une ligne à part,
  // toujours visible, juste au-dessus de la note (p.nt-garde) ; le reste (méthode, sources) peut se replier.
  var GARDE = /non compt|pas compté|ces années ne sont pas comptées|ne sont pas comptées|pas encore publi|France seule/i, REGLE = /sous 70 %/;
  function phrases(html) {
    // Coupe après « . » ou « ; » suivi d'une majuscule, sans couper au milieu d'un lien (sans lookbehind : vieux Safari).
    var L = [], cur = '', re = /([.;])(\s+)(?=[A-ZÀ-ÖØ-Ý«(])/g, i = 0, m, ouvert = function (t) { return (t.match(/<a\b/g) || []).length > (t.match(/<\/a>/g) || []).length; };
    while ((m = re.exec(html))) { cur += html.slice(i, m.index + 1); i = m.index + m[0].length; if (!ouvert(cur)) { L.push(cur); cur = ''; } else cur += m[2]; }
    cur += html.slice(i); if (cur) L.push(cur); return L;
  }
  // Les phrases « Non compté » les plus fréquentes, regroupées en une phrase courte (« Non compté : 2005 (…) ; 2020 et 2022 (…) ») ;
  // les phrases complètes restent dans le détail replié.
  var MODELES = [
    [/^Non compté : en (\d{4}), (la France|la moyenne européenne|la France et la moyenne européenne) (?:a|ont) changé (?:sa|leur) façon de mesurer ce chiffre ; son évolution par rapport à \d{4} ne compte pas\.$/, function (m) { return { k: 'm' + m[2], y: +m[1], t: m[2] + (m[2].indexOf(' et ') > 0 ? ' ont' : ' a') + ' changé sa façon de mesurer ce chiffre' }; }],
    [/^En (\d{4}) : non compté, les pays de l'UE qui publient ce chiffre cette année-là et la précédente font moins de 70 % de sa population\.$/, function (m) { return { k: 'p', y: +m[1], t: 'trop peu de pays de l\'UE publient ce chiffre' }; }],
    [/^La moyenne de l'UE ne commence qu'en (\d{4}) : avant, elle n'est pas publiée, ces années ne sont pas comptées\.$/, function (m) { return { k: 'd', y: +m[1], avant: true, t: 'pas de moyenne de l\'UE publiée' }; }]
  ];
  function resumer(g) {
    var G = {}, ordre = [], reste = [];
    g.forEach(function (x) {
      var tx = x.replace(/<[^>]+>/g, '').trim(), f = null;
      MODELES.some(function (M) { var m = M[0].exec(tx); if (m) { f = M[1](m); return true; } return false; });
      if (!f) { reste.push(x); return; }
      if (!G[f.k]) { G[f.k] = { t: f.t, y: [], avant: f.avant }; ordre.push(f.k); }
      if (G[f.k].y.indexOf(f.y) < 0) G[f.k].y.push(f.y);
    });
    if (!ordre.length) return null;
    var et = function (L) { return L.length > 1 ? L.slice(0, -1).join(', ') + ' et ' + L[L.length - 1] : String(L[0]); };
    var parts = ordre.map(function (k) { var x = G[k]; x.y.sort(); return { y: x.y[0], t: (x.avant ? 'avant ' + x.y[0] : et(x.y)) + ' (' + x.t + ')' }; }).sort(function (a, b) { return a.y - b.y; });
    return ['Non compté : ' + parts.map(function (p) { return p.t; }).join(' ; ') + '.'].concat(reste);
  }
  function garder(n) {
    if (n._ntSet != null && n._ntSet === n.innerHTML) return;
    if (n.dataset.ntVide) { n.hidden = false; delete n.dataset.ntVide; }
    var g = [], r = [];
    phrases(n.innerHTML).forEach(function (x) { var tx = x.replace(/<[^>]+>/g, ''); (GARDE.test(tx) && !REGLE.test(tx) ? g : r).push(x); });
    if (!g.length) return;
    // Deux phrases regroupables ou plus : la phrase courte reste visible, les phrases complètes passent à la fin du détail replié.
    var court = g.length > 1 ? resumer(g) : null;
    if (court) { r = r.concat(g.filter(function (x) { return court.indexOf(x) < 0; })); g = court; }
    // La ligne gardée va sous la note et son bouton (la page cherche sa note avec querySelector('.note') : elle doit rester la première).
    var sib = n._garde && n._garde.parentNode ? n._garde : null;
    // La ligne gardée va juste au-dessus de la note (sans la classe « note » : la page cherche sa note avec querySelector('.note')),
    // avec la même apparence que la note.
    if (!sib) { sib = document.createElement('p'); sib.className = 'nt-garde'; n._garde = sib; var cs = getComputedStyle(n); ['fontSize', 'lineHeight', 'color', 'fontFamily'].forEach(function (k) { sib.style[k] = cs[k]; }); sib.style.margin = '0'; n.parentNode.insertBefore(sib, n); }
    if (sib.innerHTML !== g.join(' ')) sib.innerHTML = g.join(' ');
    n.innerHTML = r.join(' '); n._ntSet = n.innerHTML;
    if (!r.length) { n.hidden = true; n.dataset.ntVide = '1'; }
  }
  function plier() {
    Array.prototype.forEach.call(document.querySelectorAll('ul.replie, ol.replie'), function (n) {
      var b = bouton(n), ouvert = !!n.dataset.ntOuvert, k = n.dataset.n ? +n.dataset.n : 2, L = n.children, reste = L.length - k;
      for (var i = 0; i < L.length; i++) { var h = !ouvert && i >= k; if (L[i].hidden !== h) L[i].hidden = h; }
      var t = reste <= 0 ? '' : ouvert ? 'Masquer ▴' : (n.dataset.voir ? n.dataset.voir.replace('{n}', reste) : k ? 'Voir les ' + reste + ' autres' : 'Voir le détail') + ' ▾';
      if (b.textContent !== t) b.textContent = t;
      if (b.hidden === !!t) b.hidden = !t;
      b.setAttribute('aria-expanded', ouvert ? 'true' : 'false');
    });
    Array.prototype.forEach.call(document.querySelectorAll(NT), function (n) {
      if (n.classList.contains('pt-hors') || n.classList.contains('defs') || n.classList.contains('mentions')) return; // mentions légales d'un sondage : jamais repliées
      garder(n);
      var b = bouton(n);
      var ouvert = !!n.dataset.ntOuvert, deja = n.classList.contains('nt-pli');
      if (deja) n.classList.remove('nt-pli');
      var cs = getComputedStyle(n), lh = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.45 || 20, nl = parseFloat(cs.getPropertyValue('--nt-l')) || 2, long = n.offsetHeight > lh * (nl + 1.4);
      if (long && !ouvert) n.classList.add('nt-pli');
      var rp = n.classList.contains('replie'), bx = !rp && (n.classList.contains('bx-note') || n.classList.contains('retenir') || n.classList.contains('dernier'));
      var t = !long ? '' : ouvert ? (bx || rp ? 'Masquer ▴' : 'Masquer le détail ▴') : rp ? 'Voir le détail ▾' : bx ? 'Lire la suite ▾' : 'Détail du graphe ▾';
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
  // Une page qui vient de s'ouvrir (moins de 4 s, rien touché) et qui est en retard — le navigateur la garde jusqu'à 10 minutes —
  // se recharge seule, sans bandeau, une fois par version et par page ; le bandeau reste pour une page ouverte depuis longtemps.
  var vPage = (document.querySelector('meta[name="concret-version"]') || {}).content, vVu = 0, vT0 = Date.now(), vTouche = false, vRecharge = /[?&]maj=/.test(location.search);
  ['pointerdown', 'keydown', 'scroll'].forEach(function (e) { addEventListener(e, function () { vTouche = true; }, { once: true, passive: true }); });
  function verifierVersion() {
    if (!vPage || !window.fetch || Date.now() - vVu < 60000 || document.getElementById('mn-maj')) return;
    vVu = Date.now();
    fetch('/donnees/version.json?t=' + Date.now(), { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; }).then(function (o) {
      if (!o || !o.v || o.v === vPage || document.getElementById('mn-maj')) return;
      var cle = o.v + location.pathname, deja = null;
      try { deja = sessionStorage.getItem('mn-maj-auto'); } catch (e) {}
      if (!vTouche && !vRecharge && Date.now() - vT0 < 4000 && deja !== cle) {
        try { sessionStorage.setItem('mn-maj-auto', cle); } catch (e) {}
        location.replace(location.pathname + '?maj=' + o.v + location.hash); return;
      }
      var b = document.createElement('button'); b.type = 'button'; b.id = 'mn-maj'; b.className = 'mn-maj';
      b.innerHTML = '<span>Une nouvelle version de Concret est en ligne.</span><b>Mettre à jour</b>';
      b.addEventListener('click', function () { b.disabled = true; location.replace(location.pathname + '?maj=' + Date.now() + location.hash); });
      document.body.appendChild(b);
    }).catch(function () {});
  }
  // Ce que les visiteurs ouvrent, pour savoir ce qu'il faut montrer d'emblée : le compteur de Concret reçoit seulement des totaux par page
  // (pages vues, petites courbes agrandies, « Voir les chiffres », « Définitions et sources », dépliants de courbes, « Détail du graphe »),
  // chacun compté une fois par visite de la page, sans rien qui identifie la personne. Seulement sur concret2027.fr (pas les essais).
  // Compte rendu pour l'éditeur : node outils/vues_stats.js (rien n'est affiché sur le site).
  var VUES = 'https://compteur.square-brook-9d65.workers.dev/hit?n=1&i=0&k=', vuesFaites = {};
  var pageNom = (location.pathname.replace(/index\.html$/, '').replace(/^\/|\/$/g, '') || 'accueil').replace(/[^a-z0-9-]+/g, '-');
  function compter(quoi) {
    if (location.hostname !== 'concret2027.fr' || vuesFaites[quoi] || !window.fetch) return; vuesFaites[quoi] = 1;
    try { fetch(VUES + encodeURIComponent('quiz-vue-' + pageNom + (quoi === 'page' ? '' : '-' + quoi)), { method: 'POST', cache: 'no-store', keepalive: true }).catch(function () {}); } catch (e) {}
  }
  function compterOuvertures() {
    compter('page');
    document.addEventListener('toggle', function (e) {
      var d = e.target; if (!d || !d.open || !d.classList) return;
      if (d.classList.contains('acc-fixe')) return; // ouvert d'office, pas une ouverture du visiteur
      compter(d.classList.contains('tab-pli') ? 'chiffres' : d.classList.contains('defs-pli') ? 'defs' : d.classList.contains('fold') || d.classList.contains('plus') ? 'replis' : 'autres');
    }, true);
    document.addEventListener('click', function (e) { if (e.target.closest && e.target.closest('.nt-btn')) compter('detail'); }, true);
    document.addEventListener('concret:vue', function (e) { compter(e.detail || 'courbe'); });
  }
  function init() {
    compterOuvertures();
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
    // Les blocs d'actualité restent ouverts : leur titre n'est pas un bouton (le bouton Partager qu'il porte, si.)
    document.addEventListener('click', function (e) { var su = e.target.closest && e.target.closest('details.acc-fixe > summary'); if (su && !e.target.closest('button, a')) e.preventDefault(); }, true);
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
