/* Menu du site pour tous : sur téléphone, un bouton « Menu » toujours visible au bout du bandeau (qui ouvre la liste des
   pages en grands boutons, avec une ligne d'explication chacune), un dégradé qui montre que le bandeau continue, et en bas
   de chaque page un bloc « Les autres pages ». Sur un grand écran, le bandeau tient en entier : seul le bloc du bas s'ajoute. */
(function () {
  var PAGES = [
    { u: '/', l: 'Accueil', t: 'Le classement des présidents et le pouls de la France' },
    { u: '/quiz/', l: 'Quiz du jour', t: 'Huit questions, deux minutes, la réponse sourcée' },
    { u: '/barometre/', l: 'Baromètre 2027', t: 'Sondages, parieurs et agenda de la présidentielle', g: 'Politique' },
    { u: '/politique/', l: 'La vie politique', t: 'Les grandes lois de chaque gouvernement, les votes de l\'Assemblée, les dates depuis 1995', g: 'Politique' },
    { u: '/vie/', l: 'Vie des Français', t: 'Pouvoir d\'achat, pauvreté, logement, travail, moral', g: 'Les missions' },
    { u: '/finances/', l: 'Finances publiques', t: 'Dette, déficit, impôts, dépenses, croissance', g: 'Les missions' },
    { u: '/sante/', l: 'Santé', t: 'Espérance de vie, accès aux soins, coût, prévention', g: 'Les missions' },
    { u: '/education/', l: 'Éducation', t: 'PISA, décrochage, diplômés, chômage des jeunes', g: 'Les missions' },
    { u: '/securite/', l: 'Sécurité et justice', t: 'Homicides, cambriolages, prisons, police, justice', g: 'Les missions' },
    { u: '/defense/', l: 'Défense', t: 'Budget, objectif de l\'OTAN, équipement, effectifs', g: 'Les missions' },
    { u: '/demographie/', l: 'Démographie', t: 'Naissances, âges, personnes nées à l\'étranger, titres de séjour (sans note)', g: 'Repères, sans note' }
  ];
  // Couleurs des pages (les pages et le Baromètre n'ont pas les mêmes noms de variables).
  var V = { bg: 'var(--bg, var(--color-bg, #f6f6f3))', panel: 'var(--panel, var(--color-panel, #fff))', fg: 'var(--fg, var(--color-fg, #1c1d22))',
    muted: 'var(--muted, var(--color-fg-muted, #62646d))', line: 'var(--line, var(--color-border-line, #e2e2dc))', fr: 'var(--fr, #2f5bd3)' };
  var css = '.mn-btn{position:sticky;right:0;margin-left:auto;flex:none;display:none;align-items:center;gap:6px;font:inherit;font-size:14px;font-weight:700;color:' + V.fg + ';' +
      'background:linear-gradient(to right,transparent,' + V.bg + ' 26px);box-shadow:24px 0 0 0 ' + V.bg + ';border:0;padding:4px 2px 4px 34px;cursor:pointer}' +
    '.mn-btn span{display:inline-flex;align-items:center;gap:6px;border:1.5px solid ' + V.fg + ';border-radius:999px;padding:4px 11px;background:' + V.panel + '}' +
    '.mn-btn:focus-visible span{outline:2px solid ' + V.fr + ';outline-offset:2px}' +
    '@media (max-width:900px){.mn-btn{display:inline-flex}}' +
    '.mn-voile{position:fixed;inset:0;z-index:50;background:rgba(10,12,18,.5);display:flex;justify-content:flex-end}' +
    '.mn-panneau{background:' + V.bg + ';width:min(100%,420px);height:100%;overflow:auto;padding:max(14px,env(safe-area-inset-top,0px)) 16px max(20px,env(safe-area-inset-bottom,0px));display:grid;align-content:start;gap:10px;box-sizing:border-box}' +
    '.mn-haut{display:flex;justify-content:space-between;align-items:center;padding:4px 2px 6px}.mn-haut b{font-family:"Newsreader",Georgia,serif;font-weight:500;font-size:24px;color:' + V.fg + '}' +
    '.mn-ferme{font:inherit;font-size:15px;font-weight:600;border:1.5px solid ' + V.line + ';background:' + V.panel + ';color:' + V.fg + ';border-radius:999px;padding:6px 14px;cursor:pointer}' +
    '.mn-liste{display:grid;gap:8px}.mn-g{grid-column:1/-1;margin:8px 2px 0;font-size:12.5px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:' + V.muted + '}' +
    '.mn-liste a{display:grid;gap:2px;padding:12px 14px;border-radius:12px;border:1px solid ' + V.line + ';background:' + V.panel + ';color:' + V.fg + ';text-decoration:none}' +
    '.mn-liste a b{font-size:17px;font-weight:700}.mn-liste a span{font-size:13.5px;color:' + V.muted + ';line-height:1.35}' +
    '.mn-liste a[aria-current]{border:2px solid ' + V.fr + '}.mn-liste a[aria-current] b::after{content:" · vous êtes ici";font-size:12.5px;font-weight:600;color:' + V.fr + '}' +
    '.mn-contact{margin:2px 0 0;font-size:14px;color:' + V.muted + '}.mn-contact a{color:' + V.fr + ';font-weight:600}' +
    '.mn-autres{display:grid;gap:10px;margin:8px 0 4px}.mn-autres h2{font-size:19px;font-weight:600;margin:0;color:' + V.fg + '}' +
    '.mn-autres .mn-liste{grid-template-columns:repeat(auto-fit,minmax(min(100%,15rem),1fr))}' +
    // Sur téléphone : « Les autres pages » en grille compacte, sans les descriptions (le Menu les a).
    '@media (max-width:600px){.mn-autres .mn-liste{grid-template-columns:repeat(2,minmax(0,1fr))}.mn-autres .mn-liste a{padding:10px 12px}.mn-autres .mn-liste a span{display:none}.mn-autres .mn-liste a b{font-size:15px}}' +
    // Sur téléphone, le bandeau garde le logo, le Baromètre, le Quiz, la loupe et le Menu ; les autres pages sont dans le Menu.
    '@media (max-width:520px){nav.site>a:not(.logo):not([href="/barometre/"]):not([href="/quiz/"]){display:none}nav.site>a{padding-block:8px}nav.site{gap:12px!important}.mn-btn{padding-left:12px}}' +
    // Le Baromètre et le Quiz, les deux rendez-vous quotidiens, ressortent dans le bandeau.
    'nav.site>a[href="/barometre/"],nav.site>a[href="/quiz/"]{color:' + V.fg + ';font-weight:600}' +
    // Lisibilité commune à toutes les pages : textes d'appoint pas trop petits, graduations des graphiques lisibles, zones à toucher assez grandes.
    '.note{font-size:14px;line-height:1.45}.bx-note{font-size:13.5px}.eyebrow{font-size:12.5px}svg .tick text{font-size:12px}' +
    // Pastilles des tableaux « Année par année » : point marqué, pas de point, demi-point (égalité).
    '.pt{display:inline-block;width:.8em;height:.8em;border-radius:50%;border:2px solid currentColor;box-sizing:border-box;vertical-align:-.08em}.pt.p1{background:currentColor}.pt.ph{background:linear-gradient(90deg,currentColor 50%,transparent 50%)}' +
    '.rech-b{min-width:44px;min-height:44px;justify-content:center}button.share,.bx-share{min-height:40px}' +
    // Long texte sous une courbe : deux lignes, puis « Détail du graphe » pour lire la suite.
    '.nt-pli{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;line-clamp:2;overflow:hidden}' +
    '.nt-btn{font:inherit;font-size:13.5px;font-weight:600;color:' + V.fr + ';background:none;border:0;padding:6px 0;margin-top:-6px;min-height:36px;cursor:pointer;justify-self:start;align-self:start;text-align:left}' +
    '.nt-btn:focus-visible{outline:2px solid ' + V.fr + ';outline-offset:2px}';
  var ici = location.pathname.replace(/index\.html$/, '');
  var lien = function (p) { return '<a href="' + p.u + '"' + (p.u === ici ? ' aria-current="page"' : '') + '><b>' + p.l + '</b><span>' + p.t + '</span></a>'; };
  // Les pages par groupe (« Politique », « Les missions », « Repères ») : un intitulé avant chaque groupe.
  var liste = function (L) { var g = null; return L.map(function (p) { var h = p.g && p.g !== g ? '<h3 class="mn-g">' + p.g + '</h3>' : ''; g = p.g || g; return h + lien(p); }).join(''); };

  function ouvrir(btn) {
    var v = document.createElement('div'); v.className = 'mn-voile';
    v.innerHTML = '<div class="mn-panneau" role="dialog" aria-modal="true" aria-label="Les pages de Concret"><div class="mn-haut"><b>Les pages de Concret</b><button type="button" class="mn-ferme">Fermer ✕</button></div><nav class="mn-liste">' + liste(PAGES) + '</nav></div>';
    var fermer = function () { v.remove(); document.removeEventListener('keydown', esc); document.documentElement.style.overflow = ''; btn.focus(); };
    var esc = function (e) { if (e.key === 'Escape') fermer(); };
    v.addEventListener('click', function (e) { if (e.target === v || e.target.closest('.mn-ferme')) fermer(); });
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
  var NT = '.chart ~ p.note';
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
      var t = !long ? '' : ouvert ? 'Masquer le détail ▴' : 'Détail du graphe ▾';
      if (b.textContent !== t) b.textContent = t;
      if (b.hidden === !!t) b.hidden = !t;
      b.setAttribute('aria-expanded', ouvert ? 'true' : 'false');
    });
  }
  var plierPrevu = 0;
  function plierBientot() { if (!plierPrevu) plierPrevu = setTimeout(function () { plierPrevu = 0; plier(); }, 120); }

  function init() {
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
      // Le bandeau défile jusqu'à la page en cours, pour qu'elle ne soit pas cachée derrière le bouton.
      var cur = nav.querySelector('a[aria-current]:not(.logo)');
      // (Sur téléphone, le bandeau tient en entier : il reste calé à gauche, logo visible.)
      if (cur && nav.scrollWidth > nav.clientWidth + 8 && !(window.matchMedia && matchMedia('(max-width: 520px)').matches)) nav.scrollLeft = Math.max(0, cur.offsetLeft - nav.offsetLeft - 110);
    }
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
