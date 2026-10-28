/* Partage de n'importe quel bloc de Concret en image.
   Ajoute un bouton « Partager » à chaque carte (chiffres clés, bulletin, courbes, encadrés, actualité) qui n'en a pas déjà un.
   L'image contient : le titre du bloc, son contenu (chiffre ou courbe, capturé tel qu'affiché), la source et l'adresse concret2027.fr.
   Source : attribut data-src du bloc s'il existe, sinon la phrase « Source… » du bloc, sinon les sources de la page (data-sources sur <body>).
   La capture utilise html2canvas, chargé seulement au premier partage. */
(function () {
  var H2C = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
  var SEL = '.card, .today .metric, .bx-card, .bx-hero, details.acc';
  var page = location.pathname.replace(/index\.html$/, '');
  var adresse = 'concret2027.fr' + (page === '/' ? '' : page.replace(/\/$/, '/'));
  var loading = null;
  function lib() {
    if (window.html2canvas) return Promise.resolve(window.html2canvas);
    if (!loading) loading = new Promise(function (ok, ko) { var s = document.createElement('script'); s.src = H2C; s.onload = function () { ok(window.html2canvas); }; s.onerror = ko; document.head.appendChild(s); });
    return loading;
  }
  var txt = function (el) { return el ? el.textContent.replace(/\s+/g, ' ').replace(/\bexemple\b/i, '').trim() : ''; };
  // Titre d'un h2 avec sur-titre : { sur: « Dette, % du PIB », main: la phrase }.
  function parties(card) {
    var h = card.querySelector('h1, h2, .acc-h, .lab, .eyebrow');
    if (!h) return { sur: '', main: document.title.replace(' · Concret', '') };
    var eb = h.querySelector('.eyebrow'), clone = h.cloneNode(true);
    Array.prototype.forEach.call(clone.querySelectorAll('.eyebrow, .ex'), function (e) { e.remove(); });
    return { sur: txt(eb), main: txt(clone) };
  }
  // En une ligne (texte du partage) : « Sur-titre : titre », sans les coller.
  function titre(card) { var p = parties(card); return p.main && p.sur ? p.sur + ' : ' + p.main : p.main || p.sur; }
  function source(card) {
    if (card.dataset.src) return card.dataset.src;
    var notes = card.querySelectorAll('.note, .bx-note, small, footer p');
    for (var i = 0; i < notes.length; i++) { var t = txt(notes[i]), m = t.match(/(Sources? ?:[^.]+\.)/); if (m) return m[1]; }
    return document.body.dataset.sources || 'Sources : voir la méthode sur ' + adresse;
  }
  function wrapLines(ctx, text, maxW) {
    var words = text.split(' '), lines = [], line = '';
    words.forEach(function (w) { var t = line ? line + ' ' + w : w; if (ctx.measureText(t).width > maxW && line) { lines.push(line); line = w; } else line = t; });
    if (line) lines.push(line); return lines;
  }
  function compose(shot, card) {
    var W = 1080, pad = 56, bg = getComputedStyle(document.body).backgroundColor || '#f6f5f1', fg = getComputedStyle(document.body).color || '#1a1a1a';
    var c = document.createElement('canvas'), x = c.getContext('2d');
    // Seul le titre est en gras ; la phrase qui le suit (quand il y a un sur-titre) est en maigre, dessous.
    var pt = parties(card), gras = pt.sur && pt.main ? pt.sur : (pt.main || pt.sur), suite = pt.sur && pt.main ? pt.main : '';
    x.font = '700 44px "Inter Tight", system-ui, sans-serif';
    var tl = wrapLines(x, gras, W - 2 * pad).slice(0, 2);
    x.font = '400 36px "Inter Tight", system-ui, sans-serif';
    var ml = suite ? wrapLines(x, suite, W - 2 * pad).slice(0, 3) : [];
    x.font = '400 26px "Inter Tight", system-ui, sans-serif';
    var sl = wrapLines(x, source(card), W - 2 * pad).slice(0, 4);
    var k = Math.min((W - 2 * pad) / shot.width, 2200 / shot.height), sw = shot.width * k, sh = shot.height * k;
    c.width = W; c.height = pad + 40 + tl.length * 54 + ml.length * 46 + 24 + sh + 30 + sl.length * 34 + 90;
    x.fillStyle = bg; x.fillRect(0, 0, c.width, c.height);
    var y = pad;
    x.fillStyle = '#2f5bd3'; x.font = '700 28px "Inter Tight", system-ui, sans-serif'; x.fillText('Concret', pad, y + 10); y += 50;
    x.fillStyle = fg; x.font = '700 44px "Inter Tight", system-ui, sans-serif'; tl.forEach(function (l) { x.fillText(l, pad, y + 30); y += 54; });
    x.font = '400 36px "Inter Tight", system-ui, sans-serif'; ml.forEach(function (l) { x.fillText(l, pad, y + 28); y += 46; }); y += 24;
    x.drawImage(shot, 0, 0, shot.width, shot.height, (W - sw) / 2, y, sw, sh); y += sh + 30;
    x.fillStyle = '#6b6b6b'; x.font = '400 26px "Inter Tight", system-ui, sans-serif'; sl.forEach(function (l) { x.fillText(l, pad, y + 20); y += 34; });
    x.fillStyle = '#2f5bd3'; x.font = '700 34px "Inter Tight", system-ui, sans-serif'; x.fillText(adresse, pad, c.height - pad + 6);
    return c;
  }
  // L'image prend quelques secondes à préparer : passé ce délai, l'iPhone refuse d'ouvrir le menu de partage.
  // On montre alors l'image avec un bouton « Partager » qui, touché, ouvre le menu tout de suite.
  function montrer(url, file, titreTxt) {
    var o = document.createElement('div'); o.className = 'pt-overlay';
    o.setAttribute('role', 'dialog'); o.setAttribute('aria-modal', 'true');
    o.style.cssText = 'position:fixed;inset:0;z-index:99;background:rgba(0,0,0,.6);display:grid;place-items:center;padding:16px';
    o.innerHTML = '<div style="background:#fff;color:#111;border-radius:14px;padding:14px;max-width:min(92vw,520px);max-height:92vh;overflow:auto;display:grid;gap:10px;font:14px system-ui,sans-serif"><img alt="Image à partager" style="width:100%;border-radius:8px"><button type="button" class="pt-go" hidden style="font:inherit;font-weight:600;padding:12px;border-radius:10px;border:0;background:#2f5bd3;color:#fff">Partager l\'image</button><a download="concret.png" style="font-weight:600">Enregistrer l\'image</a><span>Ou appui long sur l\'image pour la partager.</span><button type="button" class="pt-close" style="font:inherit;font-weight:600;padding:10px;border-radius:10px;border:0;background:#111;color:#fff">Fermer</button></div>';
    o.querySelector('img').src = url; o.querySelector('a').href = url;
    var go = o.querySelector('.pt-go');
    if (file && navigator.canShare && navigator.canShare({ files: [file] })) {
      go.hidden = false;
      go.onclick = function () { navigator.share({ files: [file], title: titreTxt, text: titreTxt + ' · ' + adresse }).then(function () { o.remove(); }, function () {}); };
    }
    o.querySelector('.pt-close').onclick = function () { o.remove(); };
    o.addEventListener('click', function (e) { if (e.target === o) o.remove(); });
    document.body.appendChild(o);
  }
  // Légende d'une courbe partagée seule : celle du bloc, sinon la légende commune placée juste avant le groupe de courbes
  // (Finances : « Les courbes » en tête des quatre graphiques).
  function legende(card) {
    if (!card.querySelector('svg') || card.querySelector('.key')) return null;
    for (var el = card, k = 0; el && k < 2; el = el.parentElement, k++) {
      var p = el.previousElementSibling, key = p && (p.matches('.key') ? p : p.querySelector('.key'));
      if (key) return key;
    }
    return null;
  }
  function partager(card, btn) {
    var label = btn.textContent; btn.textContent = 'Préparation…'; btn.disabled = true;
    var wasClosed = card.tagName === 'DETAILS' && !card.open; if (wasClosed) card.open = true;
    // Courbe repliée sous son titre (pages de mission) : ouverte le temps de la capture, puis refermée.
    var plis = Array.prototype.filter.call(card.querySelectorAll('details.pli-courbe'), function (d) { return !d.open; }); plis.forEach(function (d) { d.open = true; });
    lib().then(function (h2c) {
      // Le titre est déjà écrit en haut de l'image : on le retire de la capture pour ne pas le répéter.
      var h = card.querySelector('h1, h2, .acc-h, .lab, .eyebrow'); if (h) h.setAttribute('data-pt-titre', ''); card.setAttribute('data-pt-bloc', '');
      var lg = legende(card); if (lg) lg.setAttribute('data-pt-legende', '');
      return h2c(card, { backgroundColor: getComputedStyle(document.body).backgroundColor, scale: 2, useCORS: true, logging: false,
        ignoreElements: function (el) { return el.classList && (el.classList.contains('share') || el.classList.contains('pt-share') || el.classList.contains('nt-btn') || el.classList.contains('cp-bar')); },
        // La capture ne sait pas ce qu'est un bloc replié : elle dessinerait son contenu par-dessus le reste.
        // Dans la copie capturée, on ne garde que ce qui est visible à l'écran.
        onclone: function (doc) {
          // Courbe ouverte le temps de la capture : sans le bouton du dépliant dans l'image.
          Array.prototype.forEach.call(doc.querySelectorAll('details.pli-courbe'), function (d) { var su = d.querySelector('summary'); if (su) su.remove(); d.style.border = '0'; d.style.background = 'none'; var fi = d.querySelector('.fold-in'); if (fi) fi.style.padding = '0'; });
          Array.prototype.forEach.call(doc.querySelectorAll('details'), function (d) {
            if (!d.open) Array.prototype.forEach.call(d.children, function (c) { if (c.tagName !== 'SUMMARY') c.remove(); });
          });
          Array.prototype.forEach.call(doc.querySelectorAll('summary'), function (s) { s.style.listStyle = 'none'; s.style.display = 'block'; });
          Array.prototype.forEach.call(doc.querySelectorAll('[hidden], .pt-overlay, .nt-btn'), function (e) { e.remove(); });
          // Texte sous la courbe replié à l'écran (« Détail du graphe ») : en entier dans l'image.
          Array.prototype.forEach.call(doc.querySelectorAll('.nt-pli'), function (e) { e.classList.remove('nt-pli'); });
          // Ce qui n'est montré que dans l'image (la note du thème par président) : visible dans la copie.
          Array.prototype.forEach.call(doc.querySelectorAll('.pt-seul'), function (e) { e.classList.remove('pt-seul'); });
          // Dans l'image, seulement ce qui se lit : pas de bouton, pas de liste de détail à toucher, pas de bloc replié.
          var bl = doc.querySelector('[data-pt-bloc]');
          if (bl) {
            Array.prototype.forEach.call(bl.querySelectorAll('details:not([open]), button.more, .gov-list, .pt-hors'), function (e) { e.remove(); });
            Array.prototype.forEach.call(bl.querySelectorAll('.note'), function (n) {
              var w = doc.createTreeWalker(n, 4), x; while ((x = w.nextNode())) x.nodeValue = x.nodeValue.replace(/\s*Touchez[^.]*\./g, '');
            });
            // Légende commune recopiée au-dessus de la courbe.
            var lk = doc.querySelector('[data-pt-legende]'), ch = bl.querySelector('.chart, svg');
            if (lk && ch) { var cp = lk.cloneNode(true); cp.removeAttribute('data-pt-legende'); cp.style.margin = '4px 0 8px'; ch.parentNode.insertBefore(cp, ch); }
            // Trait pointillé de la légende (moyenne de l'UE) : la capture ne sait pas dessiner un dégradé répété, on le refait en bordure.
            Array.prototype.forEach.call(bl.querySelectorAll('.key i.dash'), function (i) {
              var c = i.getAttribute('data-c') || 'var(--ea)', h = i.closest('.mini') ? 2 : 3; i.style.setProperty('background', 'none', 'important'); i.style.display = 'inline-flex'; i.style.gap = '2px'; i.style.alignItems = 'center'; i.innerHTML = [0, 1, 2].map(function () { return '<b style="display:block;flex:1;height:' + h + 'px;background:' + c + '"></b>'; }).join('');
            });
          }
          var t = doc.querySelector('[data-pt-titre]'), bloc = doc.querySelector('[data-pt-bloc]');
          if (bloc && bloc.tagName === 'DETAILS') { var sm = bloc.querySelector(':scope > summary'); if (sm) sm.remove(); }
          else if (t) t.remove();
        } }).then(function (shot) { fin(); return shot; }, function (e) { fin(); throw e; });
      function fin() { if (h) h.removeAttribute('data-pt-titre'); card.removeAttribute('data-pt-bloc'); if (lg) lg.removeAttribute('data-pt-legende'); }
    }).then(function (shot) {
      var c = compose(shot, card);
      return new Promise(function (ok) { c.toBlob(function (b) { ok({ blob: b, url: c.toDataURL('image/png') }); }, 'image/png'); });
    }).then(function (r) {
      var file = new File([r.blob], 'concret.png', { type: 'image/png' });
      var t = titre(card);
      if (navigator.canShare && navigator.canShare({ files: [file] })) return navigator.share({ files: [file], title: t, text: t + ' · ' + adresse }).catch(function (e) { if (!e || e.name !== 'AbortError') montrer(r.url, file, t); });
      montrer(r.url, file, t);
    }).catch(function () { alert('Le partage n\'a pas pu être préparé.'); })
      .then(function () { if (wasClosed) card.open = false; plis.forEach(function (d) { d.open = false; }); btn.textContent = label; btn.disabled = false; });
  }
  function equiper(root) {
    Array.prototype.forEach.call((root || document).querySelectorAll(SEL), function (card) {
      if (card.dataset.partage || card.querySelector('.share, .pt-share')) return; // data-partage="non" : bloc d'en-tête, rien à partager
      // Un bloc dans un autre n'a pas son propre bouton, sauf une courbe d'un dépliant (« Voir les autres courbes ») ou la courbe principale
      // d'un thème (.courbe-p) : on peut la partager seule. data-partage-l : le libellé du bouton (« Partager la courbe », « Partager le thème »).
      if (card.parentElement && card.parentElement.closest(SEL) && !card.matches('.today .metric') && !card.parentElement.closest('.fold') && !card.classList.contains('courbe-p') && !card.classList.contains('courbe-s')) return;
      card.dataset.partage = '1';
      var b = document.createElement('button'); b.type = 'button'; b.className = 'share pt-share'; b.textContent = card.dataset.partageL || 'Partager';
      b.setAttribute('aria-label', 'Partager ce bloc en image');
      b.addEventListener('click', function (e) { e.preventDefault(); e.stopPropagation(); partager(card, b); });
      var target = card.tagName === 'DETAILS' ? (card.querySelector('.acc-body') || card) : card;
      target.appendChild(b);
    });
  }
  function init() {
    var st = document.createElement('style');
    st.textContent = '.pt-share{justify-self:start;align-self:start;margin-top:4px;font:inherit;font-size:12.5px;font-weight:600;padding:5px 12px;border-radius:999px;border:1px solid var(--line,#ddd);background:var(--panel,#fff);color:var(--fg,#111);cursor:pointer}.pt-share:disabled{opacity:.6}';
    document.head.appendChild(st);
    equiper();
    var pre = function () { lib().catch(function () { loading = null; }); };
    if (window.requestIdleCallback) requestIdleCallback(pre, { timeout: 4000 }); else setTimeout(pre, 2000);
    var t; new MutationObserver(function () { clearTimeout(t); t = setTimeout(equiper, 200); }).observe(document.body, { childList: true, subtree: true });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
