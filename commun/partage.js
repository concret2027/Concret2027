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
  function titre(card) {
    var h = card.querySelector('h1, h2, .acc-h, .lab, .eyebrow');
    if (!h) return document.title.replace(' · Concret', '');
    // Titre d'un h2 avec sur-titre : « Sur-titre : titre », sans les coller.
    var eb = h.querySelector('.eyebrow'), clone = h.cloneNode(true);
    Array.prototype.forEach.call(clone.querySelectorAll('.eyebrow, .ex'), function (e) { e.remove(); });
    var main = txt(clone), sur = txt(eb);
    return main && sur ? sur + ' : ' + main : main || sur;
  }
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
    x.font = '700 44px "Inter Tight", system-ui, sans-serif';
    var tl = wrapLines(x, titre(card), W - 2 * pad).slice(0, 3);
    x.font = '400 26px "Inter Tight", system-ui, sans-serif';
    var sl = wrapLines(x, source(card), W - 2 * pad).slice(0, 4);
    var k = Math.min((W - 2 * pad) / shot.width, 2200 / shot.height), sw = shot.width * k, sh = shot.height * k;
    c.width = W; c.height = pad + 40 + tl.length * 54 + 24 + sh + 30 + sl.length * 34 + 90;
    x.fillStyle = bg; x.fillRect(0, 0, c.width, c.height);
    var y = pad;
    x.fillStyle = '#2f5bd3'; x.font = '700 28px "Inter Tight", system-ui, sans-serif'; x.fillText('Concret', pad, y + 10); y += 50;
    x.fillStyle = fg; x.font = '700 44px "Inter Tight", system-ui, sans-serif'; tl.forEach(function (l) { x.fillText(l, pad, y + 30); y += 54; }); y += 24;
    x.drawImage(shot, 0, 0, shot.width, shot.height, (W - sw) / 2, y, sw, sh); y += sh + 30;
    x.fillStyle = '#6b6b6b'; x.font = '400 26px "Inter Tight", system-ui, sans-serif'; sl.forEach(function (l) { x.fillText(l, pad, y + 20); y += 34; });
    x.fillStyle = '#2f5bd3'; x.font = '700 34px "Inter Tight", system-ui, sans-serif'; x.fillText(adresse, pad, c.height - pad + 6);
    return c;
  }
  function montrer(url) {
    var o = document.createElement('div'); o.className = 'pt-overlay';
    o.setAttribute('role', 'dialog'); o.setAttribute('aria-modal', 'true');
    o.style.cssText = 'position:fixed;inset:0;z-index:99;background:rgba(0,0,0,.6);display:grid;place-items:center;padding:16px';
    o.innerHTML = '<div style="background:#fff;color:#111;border-radius:14px;padding:14px;max-width:min(92vw,520px);max-height:92vh;overflow:auto;display:grid;gap:10px;font:14px system-ui,sans-serif"><img alt="Image à partager" style="width:100%;border-radius:8px"><a download="concret.png" style="font-weight:600">Enregistrer l\'image</a><span>Ou appui long sur l\'image pour la partager.</span><button type="button" style="font:inherit;font-weight:600;padding:10px;border-radius:10px;border:0;background:#111;color:#fff">Fermer</button></div>';
    o.querySelector('img').src = url; o.querySelector('a').href = url;
    o.querySelector('button').onclick = function () { o.remove(); };
    o.addEventListener('click', function (e) { if (e.target === o) o.remove(); });
    document.body.appendChild(o);
  }
  function partager(card, btn) {
    var label = btn.textContent; btn.textContent = 'Préparation…'; btn.disabled = true;
    var wasClosed = card.tagName === 'DETAILS' && !card.open; if (wasClosed) card.open = true;
    lib().then(function (h2c) {
      return h2c(card, { backgroundColor: getComputedStyle(document.body).backgroundColor, scale: 2, useCORS: true, logging: false, ignoreElements: function (el) { return el.classList && (el.classList.contains('share') || el.classList.contains('pt-share')); } });
    }).then(function (shot) {
      var c = compose(shot, card);
      return new Promise(function (ok) { c.toBlob(function (b) { ok({ blob: b, url: c.toDataURL('image/png') }); }, 'image/png'); });
    }).then(function (r) {
      var file = new File([r.blob], 'concret.png', { type: 'image/png' });
      if (navigator.canShare && navigator.canShare({ files: [file] })) return navigator.share({ files: [file], title: titre(card), text: titre(card) + ' · ' + adresse }).catch(function () {});
      montrer(r.url);
    }).catch(function () { alert('Le partage n\'a pas pu être préparé.'); })
      .then(function () { if (wasClosed) card.open = false; btn.textContent = label; btn.disabled = false; });
  }
  function equiper(root) {
    Array.prototype.forEach.call((root || document).querySelectorAll(SEL), function (card) {
      if (card.dataset.partage || card.querySelector('.share, .pt-share')) return;
      if (card.parentElement && card.parentElement.closest(SEL) && !card.matches('.today .metric')) return;
      card.dataset.partage = '1';
      var b = document.createElement('button'); b.type = 'button'; b.className = 'share pt-share'; b.textContent = 'Partager';
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
    var t; new MutationObserver(function () { clearTimeout(t); t = setTimeout(equiper, 200); }).observe(document.body, { childList: true, subtree: true });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
