/* Moteur de recherche de Concret : une loupe dans le menu de chaque page, un index (donnees/recherche.json,
   fabriqué par outils/recherche.js), et l'ouverture du bon bloc quand on arrive par un résultat (#identifiant). */
(function () {
  var INDEX = null, V = (document.currentScript && document.currentScript.src.split('?v=')[1]) || '';
  var norm = function (t) { return String(t || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9%]+/g, ' ').trim(); };
  var esc = function (t) { return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;'); };
  var css = '.rech-b{background:none;border:0;cursor:pointer;color:var(--muted,#62646d);padding:4px 6px;margin:0 2px;display:inline-flex;align-items:center;font:inherit}' +
    '.rech-b svg{width:20px;height:20px}.rech-o{position:fixed;inset:0;background:rgba(0,0,0,.35);z-index:1000;display:flex;justify-content:center;align-items:flex-start;padding:60px 16px 16px}' +
    '.rech-p{background:var(--panel,#fff);color:var(--fg,#1c1d22);width:100%;max-width:560px;border-radius:14px;box-shadow:0 10px 40px rgba(0,0,0,.25);padding:14px;max-height:80vh;display:flex;flex-direction:column}' +
    '.rech-p input{font:inherit;font-size:17px;padding:11px 12px;border:1px solid var(--line,#e2e2dc);border-radius:10px;width:100%;box-sizing:border-box;background:var(--bg,#f6f6f3);color:inherit}' +
    '.rech-r{list-style:none;margin:10px 0 0;padding:0;overflow:auto}.rech-r a{display:block;padding:10px 8px;border-radius:8px;color:inherit;text-decoration:none}' +
    '.rech-r a:hover,.rech-r a:focus,.rech-r a.sel{background:rgba(47,91,211,.08);outline:none}.rech-r small{display:block;color:var(--muted,#62646d);font-size:12px;margin-top:2px}' +
    '.rech-v{color:var(--muted,#62646d);font-size:13px;padding:10px 8px}';
  function charger() {
    if (!INDEX) INDEX = fetch('/donnees/recherche.json' + (V ? '?v=' + V : '')).then(function (r) { return r.json(); }).then(function (d) {
      d.forEach(function (x) { x.nt = norm(x.t); x.nk = norm(x.t + ' ' + x.k + ' ' + x.p); }); return d;
    });
    return INDEX;
  }
  // Tous les mots tapés doivent être présents ; un mot trouvé dans le titre compte plus, la page en cours aussi un peu.
  function chercher(d, q) {
    var mots = norm(q).split(' ').filter(function (m) { return m.length > 1; }); if (!mots.length) return [];
    var ici = location.pathname;
    return d.map(function (x) {
      var s = 0;
      for (var i = 0; i < mots.length; i++) { var m = mots[i]; if (x.nk.indexOf(m) < 0) return null; s += x.nt.indexOf(m) >= 0 ? (x.nt.indexOf(m) === 0 ? 6 : 4) : 1; }
      if (x.u.split('#')[0] === ici) s += 0.5;
      return { x: x, s: s };
    }).filter(Boolean).sort(function (a, b) { return b.s - a.s; }).slice(0, 12).map(function (r) { return r.x; });
  }
  function ouvrir() {
    var o = document.createElement('div'); o.className = 'rech-o'; o.setAttribute('role', 'dialog'); o.setAttribute('aria-label', 'Rechercher sur Concret');
    o.innerHTML = '<div class="rech-p"><input type="search" placeholder="Rechercher : inflation, dette, PISA, prisons…" aria-label="Rechercher" autocomplete="off"><ul class="rech-r"></ul></div>';
    document.body.appendChild(o);
    var inp = o.querySelector('input'), ul = o.querySelector('.rech-r'), sel = -1;
    var fermer = function () { o.remove(); document.removeEventListener('keydown', clavier); };
    var clavier = function (e) {
      var a = ul.querySelectorAll('a');
      if (e.key === 'Escape') fermer();
      else if ((e.key === 'ArrowDown' || e.key === 'ArrowUp') && a.length) { e.preventDefault(); sel = (sel + (e.key === 'ArrowDown' ? 1 : -1) + a.length) % a.length; a.forEach(function (x, i) { x.classList.toggle('sel', i === sel); }); a[sel].scrollIntoView({ block: 'nearest' }); }
      else if (e.key === 'Enter' && a.length) { e.preventDefault(); (a[sel >= 0 ? sel : 0]).click(); }
    };
    document.addEventListener('keydown', clavier);
    o.addEventListener('click', function (e) { if (e.target === o) fermer(); });
    inp.addEventListener('input', function () {
      sel = -1; var q = inp.value;
      if (norm(q).length < 2) { ul.innerHTML = ''; return; }
      charger().then(function (d) {
        var r = chercher(d, q);
        ul.innerHTML = r.length ? r.map(function (x) { return '<li><a href="' + esc(x.u) + '">' + esc(x.t) + '<small>' + esc(x.p) + '</small></a></li>'; }).join('') : '<li class="rech-v">Aucun résultat. Essayez un autre mot (dette, chômage, vaccin, prisons…).</li>';
        Array.prototype.forEach.call(ul.querySelectorAll('a'), function (a) { a.addEventListener('click', function (e) { if (a.getAttribute('href').split('#')[0] === location.pathname) { e.preventDefault(); fermer(); history.replaceState(null, '', a.getAttribute('href')); aller(); } }); });
      });
    });
    charger(); setTimeout(function () { inp.focus(); }, 30);
  }
  // Arrivée sur #identifiant : on attend que la page ait construit le bloc, on ouvre les dépliants qui le cachent, puis on y va.
  function aller() {
    var id = decodeURIComponent(location.hash.slice(1)); if (!id) return;
    var n = 0;
    (function essai() {
      var el = document.getElementById(id);
      if (!el) { if (++n < 40) setTimeout(essai, 150); return; }
      for (var d = el.closest('details'); d; d = d.parentElement && d.parentElement.closest('details')) if (!d.open) { d.open = true; d.dispatchEvent(new Event('toggle')); }
      if (el.tagName === 'DETAILS' && !el.open) { el.open = true; el.dispatchEvent(new Event('toggle')); }
      setTimeout(function () {
        var c = el.closest('section, .card, .mo, details') || el, haut = 0;
        // Barres collées en haut d'écran (menu, raccourcis) : le bloc doit apparaître dessous.
        Array.prototype.forEach.call(document.querySelectorAll('nav, header, .jump, .sticky'), function (e) { var cs = getComputedStyle(e); if ((cs.position === 'sticky' || cs.position === 'fixed') && parseFloat(cs.top || 0) < 200) haut += e.getBoundingClientRect().height; });
        c.style.scrollMarginTop = (haut + 12) + 'px'; c.scrollIntoView({ behavior: 'smooth', block: 'start' });
        c.style.transition = 'box-shadow .3s'; c.style.boxShadow = '0 0 0 3px rgba(47,91,211,.45)'; setTimeout(function () { c.style.boxShadow = ''; }, 1800);
      }, 250);
    })();
  }
  function init() {
    var st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
    var nav = document.querySelector('nav.site'), logo = nav && nav.querySelector('.logo');
    if (nav) {
      var b = document.createElement('button'); b.type = 'button'; b.className = 'rech-b'; b.setAttribute('aria-label', 'Rechercher sur le site'); b.title = 'Rechercher';
      b.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5 21 21"/></svg>';
      b.addEventListener('click', ouvrir);
      if (logo && logo.nextSibling) nav.insertBefore(b, logo.nextSibling); else nav.appendChild(b);
    }
    document.addEventListener('keydown', function (e) { if (e.key === '/' && !/INPUT|TEXTAREA/.test((e.target || {}).tagName || '') && !document.querySelector('.rech-o')) { e.preventDefault(); ouvrir(); } });
    window.addEventListener('hashchange', aller); aller();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
