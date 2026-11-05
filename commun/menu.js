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
  // Un mot trop long pour sa case passe à la ligne (coupé en français), un tableau trop large défile dans son cadre ; un écart en pastille (« 2,7 pt en dessous… ») aussi.
  var st = document.createElement('style');
  st.textContent = 'body{overflow-wrap:break-word;-webkit-hyphens:auto;hyphens:auto}td,th{-webkit-hyphens:manual;hyphens:manual}.delta{white-space:normal;max-width:100%}';
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
    { u: '/', l: 'Accueil', t: 'La France mandat par mandat, et son pouls', ic: 'accueil', large: 1 },
    { u: '/barometre/', l: 'Baromètre 2027', t: 'Présidentielle : sondages, parieurs, Wikipédia', ic: 'barometre', g: 'Chaque jour' },
    { u: '/quiz/', l: 'Quiz du jour', t: 'Huit questions sourcées', ic: 'quiz', g: 'Chaque jour' },
    { u: '/votez/', l: 'Votez les lois', t: 'Les vrais votes de l\'Assemblée, à votre tour', ic: 'votez', g: 'Chaque jour' },
    { u: '/budget/', l: 'Faites le budget 2027', t: 'Choisissez les mesures, voyez déficit et dette jusqu\'en 2031', ic: 'budget', g: 'Chaque jour' },
    { u: '/vie/', l: 'Vie des Français', t: 'Pouvoir d\'achat, logement, travail', ic: 'vie', g: 'Les missions de l\'État' },
    { u: '/finances/', l: 'Finances publiques', t: 'Dette, déficit, impôts', ic: 'finances', g: 'Les missions de l\'État' },
    { u: '/sante/', l: 'Santé', t: 'Espérance de vie, soins, prévention', ic: 'sante', g: 'Les missions de l\'État' },
    { u: '/education/', l: 'Éducation', t: 'PISA, diplômes, décrochage', ic: 'education', g: 'Les missions de l\'État' },
    { u: '/securite/', l: 'Sécurité et justice', t: 'Homicides, prisons, justice', ic: 'securite', g: 'Les missions de l\'État' },
    { u: '/defense/', l: 'Défense', t: 'Budget, OTAN, effectifs', ic: 'defense', g: 'Les missions de l\'État' },
    { u: '/demographie/', l: 'Démographie', t: 'Naissances, âges, migrations', ic: 'demographie', g: 'Repères, sans calcul' },
    { u: '/politique/', l: 'La vie politique', t: 'Lois, votes, grandes dates', ic: 'politique', g: 'Repères, sans calcul' }
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
    budget: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h8"/><path d="M8 11h2"/><path d="M14 11h2"/><path d="M8 15h2"/><path d="M14 15h2"/>',
    votez: '<path d="M4 12h16v8H4z"/><path d="M7 12V4h10v8"/><path d="M9.5 8l2 2 3.5-3.5"/>',
    politique: '<path d="M3 9l9-5 9 5"/><path d="M5 9v8"/><path d="M10 9v8"/><path d="M14 9v8"/><path d="M19 9v8"/><path d="M3 20h18"/>',
    demographie: '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><circle cx="17" cy="9" r="2.4"/><path d="M16 14.2c2.8.2 5 2.6 5 5.8"/>',
    cherche: '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
    lettre: '<rect x="3" y="5.5" width="18" height="13" rx="2"/><path d="M3.5 7l8.5 6 8.5-6"/>',
    wa: '<path d="M4 20l1.3-3.9A8 8 0 1 1 8 18.8z"/>',
    appli: '<rect x="6.5" y="2.5" width="11" height="19" rx="2.5"/><path d="M10.5 18.5h3"/>'
  };
  var icone = function (k) { return '<i class="mn-ic" aria-hidden="true"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + IC[k] + '</svg></i>'; };
  // Couleurs des pages (les pages et le Baromètre n'ont pas les mêmes noms de variables).
  var V = { bg: 'var(--bg, var(--color-bg, #f6f6f3))', panel: 'var(--panel, var(--color-panel, #fff))', fg: 'var(--fg, var(--color-fg, #1c1d22))',
    muted: 'var(--muted, var(--color-fg-muted, #62646d))', line: 'var(--line, var(--color-border-line, #e2e2dc))', fr: 'var(--fr, #2f5bd3)' };
  var css = '@media (prefers-color-scheme: dark){:root:not([data-theme="light"]) #t-pres .tr .v,:root:not([data-theme="light"]) #t-gov .tr .v{color:#15161a}}:root[data-theme="dark"] #t-pres .tr .v,:root[data-theme="dark"] #t-gov .tr .v{color:#15161a}#annees{min-width:0;overflow-x:auto}.nt-btn{white-space:normal;text-align:left;max-width:100%}.vote a{display:inline-flex;align-items:center;min-height:24px}html{scroll-padding-top:140px}.vis-l{margin:4px 0 0;padding-left:18px}.vis-l li{margin:3px 0}.vis-l a,.note a:not([class]){color:' + V.fr + ';text-decoration:underline;text-decoration-thickness:1px;text-underline-offset:2px}.vis-l a{font-weight:500}.vis-l a b{font-weight:inherit}main.mn-main{display:contents}:where(a:not([class])){color:var(--fr,#2f5bd3)}nav.site a.logo{flex-shrink:0}@media (forced-colors: active){.key i,.cp-chip i,svg{forced-color-adjust:none}}.mn-sr{position:absolute!important;top:0;left:0;width:1px;height:1px;margin:-1px;padding:0;border:0;overflow:hidden;clip:rect(0 0 0 0);clip-path:inset(50%);white-space:nowrap}.mn-skip{position:absolute;left:-9999px;top:8px;z-index:1000;background:var(--panel,#fff);color:var(--fg,#111);padding:10px 14px;border:2px solid var(--fr,#2f5bd3);border-radius:10px;font-weight:700}.mn-skip:focus{left:8px}:root{--ea-t:#8a6418;--es-t:#b4531f;--it-t:#1a7a43}@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--ea-t:var(--ea);--es-t:var(--es);--it-t:var(--it)}}:root[data-theme="dark"]{--ea-t:var(--ea);--es-t:var(--es);--it-t:var(--it)}svg text[fill="var(--ea)"]{fill:var(--ea-t)}svg text[fill="var(--es)"]{fill:var(--es-t)}svg text[style*="fill: var(--ea)"]{fill:var(--ea-t)!important}svg text[style*="fill: var(--es)"]{fill:var(--es-t)!important}svg text[style*="fill: var(--it)"],svg text[fill="var(--it)"]{fill:var(--it-t)!important}.acc-fixe>summary{cursor:default;border-bottom:0!important;margin-bottom:0!important;padding-bottom:2px}.acc-fixe>summary .acc-t,.acc-fixe>summary .acc-cta{display:none}.mn-btn{position:sticky;right:0;margin-left:auto;flex:none;display:none;align-items:center;gap:6px;font:inherit;font-size:14px;font-weight:700;color:' + V.fg + ';' +
      'background:linear-gradient(to right,transparent,' + V.bg + ' 26px);box-shadow:24px 0 0 0 ' + V.bg + ';border:0;padding:4px 2px 4px 34px;cursor:pointer}' +
    '.mn-btn span{display:inline-flex;align-items:center;gap:6px;border:1.5px solid ' + V.fg + ';border-radius:999px;padding:9px 14px;background:' + V.panel + '}' +
    // Zones à toucher de 44 px au moins (pages du bandeau, raccourcis « Aller à »), pour tous les doigts.
    'nav.site>a{display:inline-flex;align-items:center;min-height:44px;min-width:44px;justify-content:center;padding:0 4px;box-sizing:border-box}' +
    // En flex, l'espace en tête de « 2027 », « du jour », « les lois » disparaît : on le remet (sinon « Baromètre2027 » sur ordinateur).
    'nav.site>a .lg{margin-left:.28em}' +
    'nav.jump a,.jump-l1>a{display:inline-flex;align-items:center;min-height:44px;box-sizing:border-box}' +
    'nav.jump a.mn-ici{background:' + V.fg + ';color:' + V.bg + ';border-color:' + V.fg + '}' +
    // La barre collante des pages de mission : les thèmes d'abord (leur couleur), puis les autres parties ; le thème en cours rempli
    // de sa couleur ; un fondu à droite tant qu'il reste des raccourcis à faire défiler. Texte de 15 px, zones de 44 px.
    // 55 px de haut en tout (44 px à toucher, 5 px de marge, la bordure), en texte normal comme agrandi.
    'nav.jump.jx{gap:8px;padding-top:5px;padding-bottom:5px}nav.jump.jx a{font-size:15px;padding-top:0;padding-bottom:0}' +
    // Un thème atteint par un toucher s'arrête sous les deux barres collées (celle du site et celle des thèmes), titre visible.
    '.jx-page section.theme[id],.jx-page div.theme[id],.jx-page #reponse,.jx-page #bulletin,.jx-page #toile,.jx-page #actualite,.jx-page #acc-actu,.jx-page #quiz,.jx-page #lois,.jx-page #mots,.jx-page #bref-pres{scroll-margin-top:calc(var(--navh,44px) + var(--jxh,56px) + 10px)}' +
    // En bas de chaque thème : le thème suivant, et le retour au sommaire.
    '.th-suite{display:flex;flex-wrap:wrap;justify-content:space-between;gap:6px 16px;margin:4px 0 0;padding-top:10px;border-top:1px solid ' + V.line + '}' +
    '.th-suite a{display:inline-flex;align-items:center;min-height:44px;font-size:15px;font-weight:600;color:var(--th,' + V.fr + ');text-decoration:none}.th-suite a:hover,.th-suite a:focus-visible{text-decoration:underline}' +
    '.th-suite a.th-haut{color:' + V.muted + '}' +
    'nav.jump.jx .jx-sep{flex:none;width:1px;margin:6px 2px;background:' + V.line + '}' +
    'nav.jump.jx a.th-a.mn-ici{background:var(--th);color:' + V.bg + ';border-color:var(--th)}nav.jump.jx a.th-a.mn-ici::before{background:' + V.bg + '}' +
    // Fond opaque : rien de la page ne se lit à travers la barre. Le fondu de droite est posé sur la barre, pas sur la page.
    'nav.jump{background:' + V.bg + '!important;-webkit-backdrop-filter:none!important;backdrop-filter:none!important}' +
    'nav.jump.jx::after{content:"";flex:none;position:sticky;right:calc(-1 * max(16px, env(safe-area-inset-right, 0px)));width:48px;margin-left:-48px;align-self:stretch;pointer-events:none;opacity:0;background:linear-gradient(to right,transparent,' + V.bg + ' 75%)}nav.jump.jx.jx-defile::after{opacity:1}' +
    // L'icône de la mission à gauche du titre de sa page (la même que dans le Menu et sur l'accueil).
    '.brand .mn-tic{display:inline-grid;place-items:center;flex:none;width:38px;height:38px;border-radius:11px;margin-right:10px;vertical-align:middle;color:' + V.fr + ';background:color-mix(in srgb,' + V.fr + ' 11%,transparent)}.brand .mn-tic svg{width:22px;height:22px}' +
    '.brand h1.mn-avec-ic,.brand b.mn-avec-ic{display:inline-flex;align-items:center}' +
    '.mn-btn:focus-visible span{outline:2px solid ' + V.fr + ';outline-offset:2px}' +
    // Une couleur par thème des pages de mission (titre et raccourci), dans le même ordre sur chaque page : violet, bleu canard,
    // lie-de-vin, olive, brun. Aucune n'est celle d'un pays sur les courbes (France bleu, UE or, Allemagne gris, Espagne orange,
    // États-Unis magenta), ni le vert et le rouge des ✓ et ✗ ; contraste de 3 au moins sur le fond, en clair comme en sombre.
    ':root{--th1:#5b3fb5;--th2:#0b6e86;--th3:#8a1f5c;--th4:#56620a;--th5:#6b3a12}' +
    '@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--th1:#b5a1ff;--th2:#4fd0e6;--th3:#f3a6cf;--th4:#c8d96a;--th5:#e6c3b0}}' +
    ':root[data-theme="dark"]{--th1:#b5a1ff;--th2:#4fd0e6;--th3:#f3a6cf;--th4:#c8d96a;--th5:#e6c3b0}' +
    '.th-c>h2{border-left:5px solid var(--th);padding:5px 10px 5px 12px;border-radius:0 8px 8px 0;background:color-mix(in srgb,var(--th) 9%,transparent)}' +
    '.t-pills a.th-a,nav.jump a.th-a{border:1.5px solid var(--th);gap:7px}.t-pills a.th-a::before,nav.jump a.th-a::before{content:"";flex:none;width:10px;height:10px;border-radius:3px;background:var(--th)}' +
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
    // Les boutons du haut du menu sur une seule ligne : l'icône, et dessous un mot.
    '.mn-pied{grid-template-columns:none;grid-auto-flow:column;grid-auto-columns:minmax(0,1fr);gap:6px}.mn-pied a,.mn-pied button{flex-direction:column;justify-content:center;text-align:center;gap:3px;font-size:12.5px;padding:8px 2px;min-height:62px;border-radius:14px}' +
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
    // Entre téléphone et grand écran (iPad debout, ordinateur zoomé) : sans « La vie politique » ni la page en cours, les liens ne se chevauchent plus.
    // Aucun lien ne rétrécit sous son texte, à toutes les largeurs : s'il n'y a pas la place (texte agrandi), barreAjuste retire le lien de trop.
    'nav.site>a{flex-shrink:0;white-space:nowrap}@media (max-width:860px){nav.site>a .lg{display:none}nav.site .rech-b{display:none}nav.site>a[href="/politique/"]:not([aria-current]),nav.site>a[aria-current]:not(.logo):not([href="/barometre/"]):not([href="/quiz/"]):not([href="/votez/"]){display:none}}' +
    '@media (max-width:520px){nav.site>a[href="/politique/"]:not([aria-current]),nav.site>a[aria-current]:not(.logo):not([href="/barometre/"]):not([href="/quiz/"]):not([href="/votez/"]){display:none}nav.site>a{padding-block:8px}nav.site{gap:9px!important}nav.site a.logo{margin-right:0!important}.mn-btn{padding-left:8px}nav.site .rech-b{display:none}}' +
    '@media (max-width:380px){nav.site{gap:8px!important}nav.site a.logo{font-size:17px!important}.mn-btn span{padding:4px 9px}}' +
    // Logo et bouton Menu (choix de l'éditeur, 5 novembre 2026, avis de deux UX et du marketing) : sur ordinateur, le mot « Concret » ;
    // sur téléphone, le « C » blanc sur carré bleu de l'icône de l'application, seul (lu « Concret, accueil »), et un bouton Menu plus étroit
    // et plus haut (icône et mot « Menu » dessous) : la place gagnée garde Quiz et Votez, et laisse « Budget » quand il tient.
    'nav.site a.logo .lc{display:none}.mn-btn svg{width:18px;height:14px;flex:none}' +
    'nav.site>a[href="/budget/"]{display:block!important;color:' + V.fg + ';font-weight:600}' +
    '@media (max-width:520px){nav.site a.logo{display:inline-flex;flex-direction:column;align-items:center;gap:2px;font-size:inherit!important;line-height:1;padding-block:2px}' +
    'nav.site a.logo .lc{display:grid;place-items:center;width:36px;height:36px;border-radius:9px;background:#2f5bd3;color:#fff;font-family:var(--serif,Georgia,serif);font-size:28px;font-weight:500;line-height:1}' +
    'nav.site a.logo .ln{display:none}' +
    '.mn-btn{padding-left:6px!important}.mn-btn span{flex-direction:column;justify-content:center;gap:3px!important;min-width:56px;min-height:52px;box-sizing:border-box;padding:6px 8px!important;border-radius:12px!important;font-size:12px;line-height:1}' +
    'nav.site{gap:6px!important}}' +
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
  var ici = location.pathname.replace(/index\.html$/, '').replace(/^\/budget\/quinquennat\.html$/, '/budget/');
  // Concret ouvert depuis l'écran d'accueil (web app) : pas de lien vers l'explication pour l'y mettre.
  // Le message des étapes pour installer Concret (le même que sur /application/), à envoyer sur WhatsApp d'un toucher ;
  // un seul lien, celui de /application/ : c'est sa carte (les étapes) que WhatsApp montre en aperçu,
  // y compris depuis Concret déjà installé.
  var APP_MSG = 'Concret sur l\'écran d\'accueil, comme une application :\n' +
    '• iPhone, dans Safari : bouton Partager (ou ⋯ → Partager) → Sur l\'écran d\'accueil → Ajouter\n' +
    '• Android, dans Chrome : ⋮ → Ajouter à l\'écran d\'accueil → Installer\n' +
    '• Ordinateur, dans Chrome ou Edge : l\'icône d\'installation de la barre d\'adresse → Installer (Mac, Safari : Fichier → Ajouter au Dock)\n' +
    'Le détail : https://concret2027.fr/application/';
  var WA = 'https://wa.me/?text=' + encodeURIComponent(APP_MSG);
  var appli = function () { return (window.matchMedia && matchMedia('(display-mode: standalone)').matches) || navigator.standalone === true; };
  var lien = function (p) { return '<a href="' + p.u + '"' + (p.large ? ' class="mn-large"' : '') + (p.u === ici ? ' aria-current="page"' : '') + '>' + icone(p.ic) + '<b>' + p.l + '</b><span>' + p.t + '</span></a>'; };
  // Les pages par groupe (« Chaque jour », « Les missions de l'État », « Repères, sans calcul ») : un intitulé avant chaque groupe.
  var liste = function (L) { var g = null; return L.map(function (p) { var h = p.g && p.g !== g ? '<h3 class="mn-g">' + p.g + '</h3>' : ''; g = p.g || g; return h + lien(p); }).join(''); };

  // Fenêtre ouverte (Menu, Partager) : le Tab tourne dans la fenêtre, sans passer derrière le voile.
  var pieger = function (box, e) {
    if (e.key !== 'Tab') return;
    var f = Array.prototype.filter.call(box.querySelectorAll('a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])'), function (x) { return x.offsetWidth || x.offsetHeight; });
    if (!f.length) return;
    var a = f[0], z = f[f.length - 1], ic = document.activeElement;
    if (e.shiftKey && (ic === a || !box.contains(ic))) { e.preventDefault(); z.focus(); }
    else if (!e.shiftKey && (ic === z || !box.contains(ic))) { e.preventDefault(); a.focus(); }
  };
  function ouvrir(btn) {
    var v = document.createElement('div'); v.className = 'mn-voile';
    v.innerHTML = '<div class="mn-panneau" role="dialog" aria-modal="true" aria-label="Les pages de Concret"><div class="mn-haut"><b>Les pages de Concret</b><button type="button" class="mn-ferme">Fermer ✕</button></div><div class="mn-pied">' + (document.querySelector('.rech-b') ? '<button type="button" class="mn-cherche" aria-label="Rechercher un chiffre">' + icone('cherche') + 'Rechercher</button>' : '') + (ici !== '/contact/' ? '<a href="/contact/" aria-label="Écrire à Concret">' + icone('lettre') + 'Écrire</a>' : '') + (appli() ? '<a href="' + WA + '" target="_blank" rel="noopener" aria-label="Envoyer à quelqu\'un comment installer Concret, sur WhatsApp">' + icone('wa') + 'Envoyer</a>' : ici !== '/application/' ? '<a href="/application/" aria-label="Installer Concret sur l\'écran d\'accueil, ou l\'envoyer sur WhatsApp">' + icone('appli') + 'Installer</a>' : '') + '</div><nav class="mn-liste">' + liste(PAGES) + '</nav></div>';
    var fermer = function () { v.remove(); document.removeEventListener('keydown', esc); document.documentElement.style.overflow = ''; btn.focus(); };
    var esc = function (e) { if (e.key === 'Escape') fermer(); else pieger(v.firstChild, e); };
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
  // Courbes des thèmes (pages de mission) : tout le texte sous la courbe est dans « Détail du graphe » (choix de l'éditeur) ;
  // le bouton dit en quelques mots ce qui n'est pas compté (« Détail du graphe · non compté : 2020 et 2022 »).
  var TOUT = '.courbe-p, .grand .card';
  function nonComptes(html) {
    var Y = [], av = null, fs = false, est = [];
    phrases(html).forEach(function (x) {
      var tx = x.replace(/<[^>]+>/g, ''), e = /(?:^|[.;] )(\d{4}) provisoire :/.exec(tx);
      // Chiffre estimé par Concret en attendant la source (« 2025 provisoire : … ») : dit sur le bouton.
      if (e) { if (est.indexOf(+e[1]) < 0) est.push(+e[1]); return; }
      if (!GARDE.test(tx) || REGLE.test(tx)) return;
      if (/France seule/.test(tx)) { fs = true; return; }
      var m = /ne commence qu'en (\d{4})/.exec(tx); if (m) { av = +m[1]; return; }
      m = /^Non compté : en (\d{4})/.exec(tx) || /^En (\d{4})/.exec(tx) || /(\d{4})/.exec(tx);
      if (m && Y.indexOf(+m[1]) < 0) Y.push(+m[1]); else if (!m) Y.push(0);
    });
    var et = function (L) { return L.length > 1 ? L.slice(0, -1).join(', ') + ' et ' + L[L.length - 1] : String(L[0]); };
    var L = Y.filter(Boolean).sort(), pe = '', nc = '';
    if (est.length) {
      // Année estimée et non comptée (le cas courant) : dit en une fois, « 2025 estimé, non compté ».
      var tous = est.every(function (y) { return L.indexOf(y) >= 0; });
      pe = et(est.sort()) + ' estimé' + (est.length > 1 ? 's' : '') + (tous ? ', non compté' + (est.length > 1 ? 's' : '') : '');
      if (tous) L = L.filter(function (y) { return est.indexOf(y) < 0; });
    }
    // « avant 2009 » couvre déjà les années d'avant (pas de « avant 2009 et 2005 »).
    if (av != null) { L = L.filter(function (y) { return y >= av; }); L.unshift('avant\u00a0' + av); }
    if (L.length > 3 || (!L.length && Y.length && !est.length)) nc = 'années non comptées';
    // Espaces insécables : jamais « : » ni « et 2022 » seuls en début de ligne.
    else if (L.length) nc = 'non compté' + (L.length === 1 && /^avant/.test(L[0]) ? '\u00a0' : '\u00a0: ') + et(L).replace(/ et /, '\u00a0et ');
    else if (fs) nc = 'France seule';
    var parts = [pe, nc].filter(Boolean);
    return parts.length ? ' · ' + parts.join(' · ') : '';
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
      var t = reste <= 0 ? '' : ouvert ? 'Masquer ▴' : (n.dataset.voir ? n.dataset.voir.replace('{n}', reste) : k ? (reste === 1 ? 'Voir l\'autre' : 'Voir les ' + reste + ' autres') : 'Voir le détail') + ' ▾';
      if (b.textContent !== t) b.textContent = t;
      if (b.hidden === !!t) b.hidden = !t;
      b.setAttribute('aria-expanded', ouvert ? 'true' : 'false');
    });
    var libres = [], parCarte = new Map();
    Array.prototype.forEach.call(document.querySelectorAll(NT), function (n) {
      if (n.classList.contains('pt-hors') || n.classList.contains('defs') || n.classList.contains('mentions')) return; // mentions légales d'un sondage : jamais repliées
      var carte = n.closest && n.closest(TOUT);
      if (carte) {
        // Les notes de la carte, cherchées une fois par carte (pas une fois par note).
        var notes = parCarte.get(carte);
        if (!notes) { notes = Array.prototype.filter.call(carte.querySelectorAll('p.note'), function (x) { return x.matches(NT) && x.closest(TOUT) === carte && x.textContent.trim(); }); parCarte.set(carte, notes); }
        var tete = notes[0];
        if (n !== tete) { var o = tete && !!tete.dataset.ntOuvert; n.classList.toggle('nt-pli', !o); var bb = n.nextElementSibling; if (bb && bb.classList.contains('nt-btn')) bb.hidden = true; return; }
        var b0 = bouton(n), ouv = !!n.dataset.ntOuvert;
        n.classList.toggle('nt-pli', !ouv);
        var nc = ouv ? '' : nonComptes(notes.map(function (x) { return x.innerHTML; }).join(' '));
        var t0 = ouv ? 'Masquer le détail\u00a0▴' : (nc ? 'Détail' : 'Détail du graphe') + nc + '\u00a0▾';
        if (b0.textContent !== t0) b0.textContent = t0;
        if (b0.hidden) b0.hidden = false;
        b0.setAttribute('aria-expanded', ouv ? 'true' : 'false');
        return;
      }
      garder(n); libres.push(n);
    });
    // Les textes hors des cartes de courbe : mesurés tous ensemble (tout dépliés, puis toutes les hauteurs lues, puis repliés),
    // pour une seule mise en page au lieu d'une par texte (la page se figeait au chargement).
    libres.forEach(function (n) { n.classList.remove('nt-pli'); });
    var longs = libres.map(function (n) { var cs = getComputedStyle(n), lh = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.45 || 20, nl = parseFloat(cs.getPropertyValue('--nt-l')) || 2; return n.offsetHeight > lh * (nl + 1.4); });
    libres.forEach(function (n, i) {
      var b = bouton(n), ouvert = !!n.dataset.ntOuvert, long = longs[i];
      if (long && !ouvert) n.classList.add('nt-pli');
      var rp = n.classList.contains('replie'), bx = !rp && (n.classList.contains('bx-note') || n.classList.contains('retenir') || n.classList.contains('dernier'));
      var t = !long ? '' : ouvert ? (bx || rp ? 'Masquer ▴' : 'Masquer le détail ▴') : rp ? 'Voir le détail ▾' : bx ? 'Lire la suite ▾' : 'Détail du graphe ▾';
      if (b.textContent !== t) b.textContent = t;
      if (b.hidden === !!t) b.hidden = !t;
      b.setAttribute('aria-expanded', ouvert ? 'true' : 'false');
    });
  }
  var plierPrevu = 0;
  function plierBientot() { if (!plierPrevu) plierPrevu = setTimeout(function () { plierPrevu = 0; plier(); barre(); teinter(); }, 120); }
  // La couleur de chaque thème (pages de mission, Démographie) : posée sur le thème et sur ses raccourcis, dans l'ordre de la page.
  // Les thèmes sont écrits par la page après le chargement des données : revu à chaque changement de la page, comme plier().
  function teinter() {
    Array.prototype.forEach.call(document.querySelectorAll('section.theme[id], div.theme[id]'), function (t, i) {
      var c = 'var(--th' + (i % 5 + 1) + ')';
      [t].concat(Array.prototype.slice.call(document.querySelectorAll('.t-pills a[href="#' + t.id + '"], nav.jump a[href="#' + t.id + '"]'))).forEach(function (e, j) {
        if (e.style.getPropertyValue('--th') !== c) { e.style.setProperty('--th', c); e.classList.add(j ? 'th-a' : 'th-c'); }
      });
    });
  }

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
  if (/^budget(-quinquennat-html)?$/.test(pageNom)) pageNom = 'budget'; // le jeu, à son adresse courte ou longue
  // Les appareils de l'éditeur ne sont pas comptés : concret2027.fr/?moi=1 les retire une fois pour toutes (ici et dans GoatCounter),
  // ?moi=0 les compte de nouveau.
  var editeur = false;
  try {
    var qm = /[?&]moi=([01])/.exec(location.search);
    if (qm) { if (qm[1] === '1') { localStorage.setItem('concret-editeur', '1'); localStorage.setItem('skipgc', 't'); } else { localStorage.removeItem('concret-editeur'); localStorage.removeItem('skipgc'); } }
    editeur = localStorage.getItem('concret-editeur') === '1';
  } catch (e) {}
  var compte = function () { return location.hostname === 'concret2027.fr' && !editeur && !!window.fetch; };
  function envoyer(k, n, i) { try { fetch(VUES.replace('n=1&i=0', 'n=' + (n || 1) + '&i=' + (i || 0)) + encodeURIComponent(k), { method: 'POST', cache: 'no-store', keepalive: true }).catch(function () {}); } catch (e) {} }
  function compter(quoi) {
    if (!compte() || vuesFaites[quoi]) return; vuesFaites[quoi] = 1;
    envoyer('quiz-vue-' + pageNom + (quoi === 'page' ? '' : '-' + quoi));
  }
  // Où vont les visiteurs et combien de temps ils restent, en totaux seulement (rien qui relie deux pages à une personne) :
  // le passage d'une page à l'autre (« entree » quand on arrive d'ailleurs), le temps passé sur la page (par tranches),
  // et pour la visite entière, combien ont duré au moins 10 s, 30 s, 1, 3 et 10 minutes et vu au moins 2, 3, 5 et 10 pages.
  function compterParcours() {
    if (!compte()) return;
    var nomDe = function (ch) { return (ch.replace(/index\.html$/, '').replace(/^\/|\/$/g, '') || 'accueil').replace(/[^a-z0-9-]+/g, '-'); };
    var de = 'entree', v;
    try { var r = document.referrer && new URL(document.referrer); if (r && r.hostname === location.hostname) de = nomDe(r.pathname); } catch (e) {}
    try { v = JSON.parse(sessionStorage.getItem('concret-visite') || 'null'); } catch (e) { return; }
    if (!v || de === 'entree') v = { t: 0, p: 0, seuils: [], pages: [], der: '' };
    if (v.der === pageNom) return; // page rechargée : pas un nouveau passage
    v.p++; v.der = pageNom;
    envoyer('quiz-vue-chemin-' + de + '-' + pageNom);
    [2, 3, 5, 10].forEach(function (n) { if (v.p >= n && v.pages.indexOf(n) < 0) { v.pages.push(n); envoyer('quiz-vue-visite-pages-' + n); } });
    var garder = function () { try { sessionStorage.setItem('concret-visite', JSON.stringify(v)); } catch (e) {} };
    garder();
    var vu = 0, depuis = document.visibilityState === 'visible' ? Date.now() : 0, tempsEnvoye = false;
    document.addEventListener('visibilitychange', function () {
      if (document.visibilityState === 'visible') { depuis = Date.now(); return; }
      if (depuis) { vu += Date.now() - depuis; v.t += Date.now() - depuis; depuis = 0; }
      if (!tempsEnvoye) { tempsEnvoye = true; var s = vu / 1000; envoyer('quiz-vue-temps-' + pageNom, 6, s < 10 ? 0 : s < 30 ? 1 : s < 60 ? 2 : s < 180 ? 3 : s < 600 ? 4 : 5); }
      [10, 30, 60, 180, 600].forEach(function (n) { if (v.t >= n * 1000 && v.seuils.indexOf(n) < 0) { v.seuils.push(n); envoyer('quiz-vue-visite-' + n + 's'); } });
      garder();
    });
  }
  // Appareils : le navigateur garde une marque à la première visite du site (et le jour de la dernière visite comptée) ; le compteur
  // reçoit seulement « un appareil de plus » (depuis le début, ce jour-là, et parmi les nouveaux du jour). Rien qui identifie la personne ; deux appareils d'une
  // même personne comptent deux fois, une navigation privée aussi.
  function compterAppareil() {
    if (!compte()) return;
    var jour = new Date().toLocaleDateString('sv-SE', { timeZone: 'Europe/Paris' }), vu, dernier;
    try { vu = localStorage.getItem('concret-appareil'); dernier = localStorage.getItem('concret-appareil-jour'); } catch (e) { return; }
    var cles = [];
    // Un appareil qui vient pour la première fois compte aussi dans les nouveaux du jour (depuis le 6 novembre 2026, premier jour
    // complet) : les autres appareils du jour sont des appareils revenus.
    if (!vu) cles.push('quiz-vue-appareils', 'quiz-vue-appareils-nouveaux-' + jour);
    if (dernier !== jour) cles.push('quiz-vue-appareils-' + jour);
    if (!cles.length) return;
    try { localStorage.setItem('concret-appareil', vu || jour); localStorage.setItem('concret-appareil-jour', jour); } catch (e) { return; }
    cles.forEach(function (k) { envoyer(k); });
  }
  function compterOuvertures() {
    compter('page'); compterAppareil(); compterParcours();
    document.addEventListener('toggle', function (e) {
      var d = e.target; if (!d || !d.open || !d.classList) return;
      if (d.classList.contains('acc-fixe')) return; // ouvert d'office, pas une ouverture du visiteur
      compter(d.classList.contains('tab-pli') ? 'chiffres' : d.classList.contains('defs-pli') ? 'defs' : d.classList.contains('fold') || d.classList.contains('plus') ? 'replis' : 'autres');
    }, true);
    document.addEventListener('click', function (e) { if (e.target.closest && e.target.closest('.nt-btn')) compter('detail'); }, true);
    document.addEventListener('concret:vue', function (e) { compter(e.detail || 'courbe'); });
  }
  // Défilement doux, sauf si la personne a demandé moins d'animations dans les réglages de son appareil.
  var doux = function () { return window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'; };
  // Clavier et lecteur d'écran : après un raccourci, le focus va au titre de la partie choisie (sinon le Tab suivant repart du haut).
  var focaliser = function (c) {
    var t = /^H[1-4]$|^SUMMARY$/.test(c.tagName) ? c : c.querySelector('h2, h3, summary') || c;
    if (t.tagName !== 'SUMMARY' && !t.hasAttribute('tabindex')) t.setAttribute('tabindex', '-1');
    try { t.focus({ preventScroll: true }); } catch (e) { }
  };
  // Poser un bloc juste sous les barres collées (celle du site, celle des raccourcis), et l'y garder : les courbes dessinées à
  // l'approche changent la hauteur de la page pendant le défilement, on corrige donc la position jusqu'à ce qu'elle tienne.
  var poserId = 0;
  var poser = function (c) {
    var id = ++poserId, ecart = function () { var n = document.querySelector('nav.site'), jp = document.querySelector('nav.jump'); return c.getBoundingClientRect().top - ((n ? n.offsetHeight : 0) + (jp ? jp.offsetHeight : 0) + 10); };
    window.scrollTo({ top: Math.max(0, window.pageYOffset + ecart()), behavior: doux() });
    var k = 0, t = setInterval(function () {
      if (id !== poserId || ++k > 12) return clearInterval(t);
      var d = ecart(); if (Math.abs(d) > 6 && k > 2) window.scrollTo({ top: Math.max(0, window.pageYOffset + d), behavior: 'auto' });
    }, 250);
    // Un geste de la personne arrête les corrections.
    var stop = function () { poserId++; removeEventListener('wheel', stop); removeEventListener('touchstart', stop); };
    setTimeout(function () { addEventListener('wheel', stop, { passive: true, once: true }); addEventListener('touchstart', stop, { passive: true, once: true }); }, 50);
  };
  // Lecteur d'écran : les chiffres de chaque courbe en tableau (une ligne par année, une colonne par pays), caché à l'écran.
  // Les pages l'appellent en dessinant la courbe, avec les mêmes chiffres que ceux montrés au toucher.
  var tableau = function (box, pts, titre) {
    if (!box || !pts || !pts.length || pts.length > 80) return;
    // Fait quand le navigateur est libre, après le dessin des courbes : la page ne se fige pas au chargement.
    // Si la courbe est redessinée entre-temps (pays ajouté), seul le dernier tableau est fait.
    var jeton = box.mnTab = (box.mnTab || 0) + 1;
    var faire = function () {
      if (box.mnTab !== jeton || !box.isConnected) return;
      var old = box.querySelector(':scope > .mn-sr'); if (old) old.remove();
      var e = function (t) { return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;'); }, nom = function (r) { return r.n || 'Valeur'; }, cols = [];
      pts.forEach(function (p) { (p.rows || []).forEach(function (r) { if (cols.indexOf(nom(r)) < 0) cols.push(nom(r)); }); });
      if (!cols.length) return;
      // Le tableau est dans une boîte d'un pixel : un tableau seul garde la largeur de ses colonnes et élargirait la page.
      var w = document.createElement('div'); w.className = 'mn-sr'; w.setAttribute('data-html2canvas-ignore', ''); var t = document.createElement('table'); w.appendChild(t);
      t.innerHTML = '<caption>Les chiffres de la courbe' + (titre ? ' : ' + e(titre) : '') + '</caption><thead><tr><th scope="col">Année</th>' + cols.map(function (c) { return '<th scope="col">' + e(c) + '</th>'; }).join('') + '</tr></thead><tbody>' +
        pts.map(function (p) { var v = {}; (p.rows || []).forEach(function (r) { v[nom(r)] = r.s; }); return '<tr><th scope="row">' + e(p.t) + '</th>' + cols.map(function (c) { return '<td>' + (v[c] != null ? e(v[c]) : 'pas de chiffre') + '</td>'; }).join('') + '</tr>'; }).join('') + '</tbody>';
      box.appendChild(w);
    };
    if (window.requestIdleCallback) requestIdleCallback(faire, { timeout: 4000 }); else setTimeout(faire, 300);
  };
  // Courbe loin de l'écran (ou dans un bloc replié) : dessinée quand on s'en approche, pour que la page ne se fige pas
  // au chargement. Sa place est gardée en attendant (hauteur prévue), pour que la page ne saute pas. Renvoie true si
  // le dessin attend. presser(bloc) dessine tout de suite ce qui attend dans un bloc (avant d'en faire une image).
  var attente = [];
  var plusTard = function (box, fn, haut) {
    if (!box || !window.IntersectionObserver) return false;
    var r = box.getBoundingClientRect();
    if (r.width && r.bottom > -800 && r.top < innerHeight + 800) return false;
    if (box.mnIO) box.mnIO.disconnect();
    var x = { box: box, fn: null };
    x.fn = function () { if (x.fait) return; x.fait = true; if (box.mnIO) { box.mnIO.disconnect(); box.mnIO = null; } attente = attente.filter(function (y) { return y !== x; }); box.style.minHeight = ''; fn(); };
    box.textContent = ''; if (haut) box.style.minHeight = haut + 'px';
    box.mnIO = new IntersectionObserver(function (es) { if (es.some(function (e) { return e.isIntersecting; })) x.fn(); }, { rootMargin: '800px 0px' });
    box.mnIO.observe(box); attente.push(x);
    return true;
  };
  var presser = function (root) { attente.filter(function (x) { return !root || root.contains(x.box); }).forEach(function (x) { x.fn(); }); };
  // IC : les icônes des pages (l'accueil les met sur la toile « Mandat par mandat »).
  window.ConcretMenu = { doux: doux, focaliser: focaliser, pieger: pieger, tableau: tableau, plusTard: plusTard, presser: presser, poser: poser, IC: IC };
  // La barre collante d'une page de mission : un raccourci par thème, en tête, dans l'ordre et la couleur des thèmes, puis les autres
  // parties (Présidents, Actualité…). Les thèmes écrits par le script arrivent après le chargement : la barre est revue à chaque
  // changement de la page (plierBientot), et refaite seulement si la liste des thèmes a changé.
  function barre() {
    var jp = document.querySelector('nav.jump'); if (!jp || jp.querySelector('.jump-l1')) return;
    var th = Array.prototype.slice.call(document.querySelectorAll('section.theme[id], div.theme[id]'));
    if (!th.length) return;
    var sig = th.map(function (t) { return t.id; }).join(',') + (document.getElementById('bref-pres') ? ',pres' : '');
    if (jp.dataset.themes === sig) return;
    jp.dataset.themes = sig; jp.classList.add('jx');
    Array.prototype.forEach.call(jp.querySelectorAll('.jx-th, .jx-sep, a[href="#courbes"]'), function (e) { e.remove(); });
    // Un raccourci vers un thème déjà écrit dans la page (Démographie) : remplacé par celui de la rangée des thèmes.
    Array.prototype.forEach.call(jp.querySelectorAll('a[href^="#"]'), function (e) { if (th.some(function (t) { return e.getAttribute('href') === '#' + t.id; })) e.remove(); });
    // En tête, « Présidents » (couleur neutre) : les résultats des présidents, dans « En bref », à un toucher de partout.
    // Le détail, plus bas, garde son propre raccourci.
    Array.prototype.forEach.call(jp.querySelectorAll('a[href="#bulletin"]'), function (a) { a.textContent = 'Le détail par président'; });
    Array.prototype.forEach.call(jp.querySelectorAll('a.jx-pres'), function (a) { a.remove(); });
    if (document.getElementById('bref-pres')) { var ap = document.createElement('a'); ap.className = 'jx-pres'; ap.href = '#bref-pres'; ap.textContent = 'Présidents'; jp.insertBefore(ap, jp.firstChild); }
    var ref = jp.querySelector('a.jx-pres') ? jp.querySelector('a.jx-pres').nextSibling : jp.firstChild;
    th.forEach(function (t) {
      var a = document.createElement('a'), h = t.querySelector(':scope > h2');
      a.className = 'jx-th'; a.href = '#' + t.id; a.textContent = t.dataset.court || (h ? h.textContent.trim() : t.id);
      jp.insertBefore(a, ref);
    });
    var sep = document.createElement('span'); sep.className = 'jx-sep'; sep.setAttribute('aria-hidden', 'true'); jp.insertBefore(sep, ref);
    // En bas de chaque thème : « Thème suivant : … → » et « ↑ Tous les thèmes » (le sommaire d'« En bref »).
    th.forEach(function (t, i) {
      var old = t.querySelector(':scope > .th-suite'); if (old) old.remove();
      var p = document.createElement('p'), nx = th[i + 1], hn = nx && nx.querySelector(':scope > h2');
      p.className = 'th-suite'; p.setAttribute('data-html2canvas-ignore', '');
      if (nx) { var an = document.createElement('a'); an.className = 'th-next'; an.href = '#' + nx.id; an.style.setProperty('--th', 'var(--th' + ((i + 1) % 5 + 1) + ')'); an.textContent = 'Thème suivant : ' + (nx.dataset.court || (hn ? hn.textContent.trim() : nx.id)) + ' →'; p.appendChild(an); }
      if (document.getElementById('reponse')) { var ah = document.createElement('a'); ah.className = 'th-haut'; ah.href = '#reponse'; ah.textContent = '↑ Tous les thèmes'; p.appendChild(ah); }
      t.appendChild(p);
    });
    document.documentElement.classList.add('jx-page');
    teinter(); fondu(jp); hauteurBarre(jp);
  }
  // La hauteur de la barre des thèmes, pour l'arrêt des défilements juste dessous (--jxh).
  function hauteurBarre(jp) { jp = jp || document.querySelector('nav.jump.jx'); if (jp && jp.offsetHeight) document.documentElement.style.setProperty('--jxh', jp.offsetHeight + 'px'); }
  // Un toucher sur « Thème suivant » ou « Tous les thèmes » : le bloc posé juste sous les deux barres collées.
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('.th-suite a'); if (!a) return;
    var c = document.getElementById(a.getAttribute('href').slice(1)); if (!c) return;
    e.preventDefault();
    focaliser(c); poser(c);
    if (history.replaceState) history.replaceState(null, '', a.getAttribute('href'));
  });
  function fondu(jp) { jp = jp || document.querySelector('nav.jump.jx'); if (!jp) return; jp.classList.toggle('jx-defile', jp.scrollWidth - jp.clientWidth - jp.scrollLeft > 4); }
  function suivre(jp, cib) {
    var liens = function () { return Array.prototype.filter.call(jp.querySelectorAll('a[href^="#"]'), function (l) { return cib(l); }); }, cur = null, choisi = null, fin = 0;
    var montre = function (l) {
      if (l === cur) return; cur = l;
      var ls = liens();
      ls.forEach(function (x) { x.classList.toggle('mn-ici', x === l); if (x === l) x.setAttribute('aria-current', 'true'); else x.removeAttribute('aria-current'); });
      // Le raccourci de la partie en cours est ramené à gauche : on voit ce qui suit.
      if (l) { var r = l.parentNode; if (r.scrollWidth > r.clientWidth) r.scrollLeft = Math.max(0, l.offsetLeft - (r.classList.contains('jx') ? 16 : 40)); }
      fondu(jp);
    };
    var maj = function () {
      if (choisi && Date.now() < fin) return montre(choisi);
      choisi = null;
      var lim = jp.getBoundingClientRect().bottom + 80, ici = null;
      liens().forEach(function (l) { var e = cib(l), r = e && e.getBoundingClientRect(); if (r && r.height && r.top <= lim) ici = l; });
      montre(ici);
    };
    var t = 0; addEventListener('scroll', function () { if (!t) t = requestAnimationFrame(function () { t = 0; maj(); }); }, { passive: true });
    addEventListener('resize', maj); setTimeout(maj, 300);
    jp.addEventListener('click', function (e) {
      var l = e.target.closest && e.target.closest('a[href^="#"]'), c = l && cib(l); if (!c) return;
      e.preventDefault(); choisi = l; fin = Date.now() + 1500; montre(l);
      for (var d = c; d; d = d.parentElement) if (d.tagName === 'DETAILS' && !d.open) d.open = true;
      // Le titre juste sous les deux bandeaux collés (pages, raccourcis), quel que soit le navigateur.
      focaliser(c);
      requestAnimationFrame(function () { poser(c); });
      if (history.replaceState) history.replaceState(null, '', l.getAttribute('href'));
    });
  }
  function init() {
    compterOuvertures();
    // Les raccourcis du haut (nav.jump) suivent toujours l'ordre réel des blocs de la page, même quand un bloc change de place.
    var jp = document.querySelector('nav.jump');
    if (jp) {
      var cib = function (l) { return document.getElementById(decodeURIComponent((l.getAttribute('href') || '').slice(1))); };
      var ls = Array.prototype.filter.call(jp.querySelectorAll('a[href^="#"]'), function (l) { return cib(l); });
      ls.slice().sort(function (p, q) { return cib(p).compareDocumentPosition(cib(q)) & 4 ? -1 : 1; }).forEach(function (l) { l.parentNode.appendChild(l); }); // chacun reste dans sa rangée (Baromètre : .jump-l1)
    }
    // Le raccourci de la partie où l'on se trouve est en noir, comme sur le Baromètre (qui a le sien) : la dernière partie dont
    // le titre est passé sous la rangée. Après un toucher, la partie choisie, posée juste sous la rangée.
    barre();
    if (jp && !jp.querySelector('.jump-l1')) { suivre(jp, cib); jp.addEventListener('scroll', function () { fondu(jp); }, { passive: true }); addEventListener('resize', function () { fondu(jp); hauteurBarre(jp); }); }
    // L'icône de la mission à gauche du titre de sa page.
    var pm = PAGES.filter(function (p) { return p.u === ici && (p.g === 'Les missions de l\'État' || p.ic === 'demographie'); })[0], tt = document.querySelector('.brand h1, .brand b');
    if (pm && tt && !tt.querySelector('.mn-tic')) { tt.classList.add('mn-avec-ic'); tt.insertAdjacentHTML('afterbegin', '<span class="mn-tic" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + IC[pm.ic] + '</svg></span>'); }
    // Clavier et lecteur d'écran : la zone principale de la page, et un lien « Aller au contenu » qui saute les menus.
    // La zone principale : un <main> entre le bandeau des pages et le pied de page, sans rien changer à la mise en page (display: contents).
    var wrap = document.querySelector('.wrap, .bx');
    if (wrap && !document.querySelector('main, [role="main"]')) {
      var kids = Array.prototype.slice.call(wrap.children), i0 = 0, i1 = kids.length;
      while (i0 < i1 && kids[i0].matches('nav.site, .mn-skip, script, style')) i0++;
      while (i1 > i0 && kids[i1 - 1].matches('footer, .mn-autres, script, style')) i1--;
      if (i1 > i0) { var mn = document.createElement('main'); mn.className = 'mn-main'; wrap.insertBefore(mn, kids[i0]); kids.slice(i0, i1).forEach(function (k) { mn.appendChild(k); }); }
    }
    var cible = document.querySelector('.brand, section.hero, h1');
    if (cible && !document.querySelector('.mn-skip')) {
      if (!cible.id) cible.id = 'contenu'; if (!cible.hasAttribute('tabindex')) cible.setAttribute('tabindex', '-1');
      var sk = document.createElement('a'); sk.className = 'mn-skip'; sk.href = '#' + cible.id; sk.textContent = 'Aller au contenu';
      document.body.insertBefore(sk, document.body.firstChild);
    }
    // Après une mise à jour, l'adresse perd son « ?maj=… ».
    if (/[?&]maj=/.test(location.search) && history.replaceState) history.replaceState(null, '', location.pathname + location.hash);
    verifierVersion();
    document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'visible') verifierVersion(); });
    addEventListener('pageshow', function (e) { if (e.persisted) verifierVersion(); });
    hauteur();
    plier(); teinter();
    if (window.MutationObserver) new MutationObserver(function (ms) {
      for (var i = 0; i < ms.length; i++) { var t = ms[i].target; if (t.nodeType !== 1) t = t.parentNode; if (t && t.closest && t.closest('p.note, .chart') || ms[i].addedNodes.length) { plierBientot(); return; } }
    }).observe(document.body, { childList: true, characterData: true, subtree: true });
    addEventListener('resize', plierBientot);
    document.addEventListener('toggle', plierBientot, true);
    // Les blocs d'actualité restent ouverts : leur titre n'est pas un bouton (le bouton Partager qu'il porte, si.)
    document.addEventListener('click', function (e) { var su = e.target.closest && e.target.closest('details.acc-fixe > summary'); if (su && !e.target.closest('button, a')) e.preventDefault(); }, true);
    if (!document.getElementById('mn-css')) { var st = document.createElement('style'); st.id = 'mn-css'; st.textContent = css; document.head.appendChild(st); }
    var nav = document.querySelector('nav.site');
    if (nav) {
      var lgo = nav.querySelector('a.logo');
      if (lgo && !lgo.querySelector('.lc')) { lgo.innerHTML = '<span class="lc" aria-hidden="true">C</span><span class="ln">Concret</span>'; lgo.setAttribute('aria-label', 'Concret, accueil'); }
      // Le jeu du budget dans la barre, après Votez ; retiré le premier quand la place manque (barreAjuste).
      if (!nav.querySelector('a[href="/budget/"]')) {
        var ab = document.createElement('a'); ab.href = '/budget/'; ab.innerHTML = 'Budget<span class="lg"> 2027</span>';
        if (pageNom === 'budget') ab.setAttribute('aria-current', 'page');
        var vz = nav.querySelector('a[href="/votez/"]'), ap = vz ? vz.nextSibling : null;
        if (vz) nav.insertBefore(ab, ap); else nav.appendChild(ab);
      }
    }
    if (nav && !nav.querySelector('.mn-btn')) {
      var b = document.createElement('button'); b.type = 'button'; b.className = 'mn-btn'; b.setAttribute('aria-haspopup', 'dialog');
      b.innerHTML = '<span><svg viewBox="0 0 18 14" aria-hidden="true"><path d="M1 1.5h16M1 7h16M1 12.5h16" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>Menu</span>'; b.addEventListener('click', function () { ouvrir(b); }); nav.appendChild(b);
    }
    // Barre du haut : si les liens ne tiennent pas avant le bouton Menu (texte agrandi, petit écran), on retire d'abord
    // le jeu du budget, puis La vie politique, puis Votez, puis Quiz, puis Baromètre ; ils restent dans le Menu. Jamais de mot coupé ou caché sous le bouton.
    var barreAjuste = function () {
      if (!nav) return; var mb = nav.querySelector('.mn-btn'); if (!mb) return;
      Array.prototype.forEach.call(nav.querySelectorAll('a[data-mn-cache]'), function (a) { a.style.removeProperty('display'); a.removeAttribute('data-mn-cache'); });
      ['/budget/', '/politique/', '/votez/', '/quiz/', '/barometre/'].some(function (u) {
        var vis = Array.prototype.filter.call(nav.querySelectorAll('a:not(.logo)'), function (a) { return a.offsetParent && a.getBoundingClientRect().width; });
        var last = vis[vis.length - 1], pil = mb.querySelector('span') || mb; // le bord visible du bouton (sa marge de gauche n'est qu'un fondu)
        if ((!last || last.getBoundingClientRect().right <= pil.getBoundingClientRect().left - 6) && mb.getBoundingClientRect().right <= document.documentElement.clientWidth) return true;
        var a = nav.querySelector('a[href="' + u + '"]'); if (a && a.offsetParent && a.getAttribute('aria-current') !== 'page') { a.style.setProperty('display', 'none', 'important'); a.setAttribute('data-mn-cache', '1'); }
        return false;
      });
    };
    barreAjuste(); addEventListener('resize', barreAjuste); addEventListener('load', barreAjuste); setTimeout(barreAjuste, 600);
    // Sur l'accueil : la même icône devant chaque page de la liste des missions, des repères, du Baromètre et du Quiz.
    Array.prototype.forEach.call(document.querySelectorAll('#missions a.pg, #reperes a.pg, #rendez-vous a.pg'), function (a) {
      var p = PAGES.filter(function (x) { return x.u === a.getAttribute('href'); })[0];
      if (!p || a.querySelector('.mn-ic')) return;
      a.classList.add('mn-avec'); a.insertAdjacentHTML('afterbegin', icone(p.ic));
    });
    // Dans le pied de chaque page : comment mettre Concret sur l'écran d'accueil (page /application/, à envoyer sur WhatsApp).
    var pied = document.querySelector('footer p:last-of-type') || document.querySelector('footer');
    if (pied && ici !== '/application/' && !pied.querySelector('.mn-app')) pied.insertAdjacentHTML('beforeend', appli() ? ' · <a class="mn-app" href="' + WA + '" target="_blank" rel="noopener">Envoyer Concret sur WhatsApp</a>' : ' · <a class="mn-app" href="/application/">Mettre Concret sur l\'écran d\'accueil</a>');
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
