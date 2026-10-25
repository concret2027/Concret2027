/* Menu du site pour tous : sur téléphone, un bouton « Menu » toujours visible au bout du bandeau (qui ouvre la liste des
   pages en grands boutons, avec une ligne d'explication chacune), un dégradé qui montre que le bandeau continue, et en bas
   de chaque page un bloc « Les autres pages ». Sur un grand écran, le bandeau tient en entier : seul le bloc du bas s'ajoute. */
(function () {
  var PAGES = [
    { u: '/', l: 'Accueil', t: 'Le classement des présidents et le pouls de la France' },
    { u: '/barometre/', l: 'Baromètre 2027', t: 'Sondages, parieurs et agenda de la présidentielle' },
    { u: '/quiz/', l: 'Quiz du jour', t: 'Huit questions, deux minutes, la réponse sourcée' },
    { u: '/vie/', l: 'Vie des Français', t: 'Pouvoir d\'achat, pauvreté, logement, travail, moral' },
    { u: '/finances/', l: 'Finances publiques', t: 'Dette, déficit, impôts, dépenses, croissance' },
    { u: '/sante/', l: 'Santé', t: 'Espérance de vie, accès aux soins, coût, prévention' },
    { u: '/education/', l: 'Éducation', t: 'PISA, décrochage, diplômés, chômage des jeunes' },
    { u: '/securite/', l: 'Sécurité et justice', t: 'Homicides, cambriolages, prisons, police, justice' },
    { u: '/defense/', l: 'Défense', t: 'Budget, objectif de l\'OTAN, équipement, effectifs' }
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
    '.mn-liste{display:grid;gap:8px}' +
    '.mn-liste a{display:grid;gap:2px;padding:12px 14px;border-radius:12px;border:1px solid ' + V.line + ';background:' + V.panel + ';color:' + V.fg + ';text-decoration:none}' +
    '.mn-liste a b{font-size:17px;font-weight:700}.mn-liste a span{font-size:13.5px;color:' + V.muted + ';line-height:1.35}' +
    '.mn-liste a[aria-current]{border:2px solid ' + V.fr + '}.mn-liste a[aria-current] b::after{content:" · vous êtes ici";font-size:12.5px;font-weight:600;color:' + V.fr + '}' +
    '.mn-autres{display:grid;gap:10px;margin:8px 0 4px}.mn-autres h2{font-size:19px;font-weight:600;margin:0;color:' + V.fg + '}' +
    '.mn-autres .mn-liste{grid-template-columns:repeat(auto-fit,minmax(min(100%,15rem),1fr))}';
  var ici = location.pathname.replace(/index\.html$/, '');
  var lien = function (p) { return '<a href="' + p.u + '"' + (p.u === ici ? ' aria-current="page"' : '') + '><b>' + p.l + '</b><span>' + p.t + '</span></a>'; };

  function ouvrir(btn) {
    var v = document.createElement('div'); v.className = 'mn-voile';
    v.innerHTML = '<div class="mn-panneau" role="dialog" aria-modal="true" aria-label="Les pages de Concret"><div class="mn-haut"><b>Les pages de Concret</b><button type="button" class="mn-ferme">Fermer ✕</button></div><nav class="mn-liste">' + PAGES.map(lien).join('') + '</nav></div>';
    var fermer = function () { v.remove(); document.removeEventListener('keydown', esc); document.documentElement.style.overflow = ''; btn.focus(); };
    var esc = function (e) { if (e.key === 'Escape') fermer(); };
    v.addEventListener('click', function (e) { if (e.target === v || e.target.closest('.mn-ferme')) fermer(); });
    document.addEventListener('keydown', esc); document.documentElement.style.overflow = 'hidden';
    document.body.appendChild(v); v.querySelector('.mn-ferme').focus();
  }

  function init() {
    if (!document.getElementById('mn-css')) { var st = document.createElement('style'); st.id = 'mn-css'; st.textContent = css; document.head.appendChild(st); }
    var nav = document.querySelector('nav.site');
    if (nav && !nav.querySelector('.mn-btn')) {
      var b = document.createElement('button'); b.type = 'button'; b.className = 'mn-btn'; b.setAttribute('aria-haspopup', 'dialog');
      b.innerHTML = '<span>☰ Menu</span>'; b.addEventListener('click', function () { ouvrir(b); }); nav.appendChild(b);
      // Le bandeau défile jusqu'à la page en cours, pour qu'elle ne soit pas cachée derrière le bouton.
      var cur = nav.querySelector('a[aria-current]:not(.logo)');
      if (cur && nav.scrollWidth > nav.clientWidth) nav.scrollLeft = Math.max(0, cur.offsetLeft - nav.offsetLeft - 110);
    }
    // En bas de page (pas sur l'accueil, qui a déjà la liste des missions) : les autres pages.
    if (ici !== '/' && !document.querySelector('.mn-autres')) {
      var f = document.querySelector('footer'), sec = document.createElement('section');
      sec.className = 'mn-autres'; sec.setAttribute('aria-label', 'Les autres pages'); sec.setAttribute('data-partage', 'non');
      sec.innerHTML = '<h2>Les autres pages</h2><nav class="mn-liste">' + PAGES.filter(function (p) { return p.u !== ici; }).map(lien).join('') + '</nav>';
      if (f && f.parentNode) f.parentNode.insertBefore(sec, f); else (document.querySelector('.wrap, .bx') || document.body).appendChild(sec);
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
