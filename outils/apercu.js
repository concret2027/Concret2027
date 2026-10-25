/* Cartes d'aperçu des liens (og:image) : l'image qu'affichent WhatsApp, X, LinkedIn ou un e-mail quand on colle un lien
   vers une page de Concret. Une image par page, 1200 × 630, dans donnees/apercu/<page>.png, refaite à partir des chiffres
   affichés (bloc « En bref » de chaque mission, classement général pour l'accueil) : jamais de chiffre saisi à la main.
   Lancée par outils/controle.js verifier à chaque mise à jour ; à la main : node outils/apercu.js */
var fs = require('fs'), path = require('path'), http = require('http'), crypto = require('crypto');
var ROOT = path.join(__dirname, '..'), OUT = path.join(ROOT, 'donnees', 'apercu');
var NOTES = require('../commun/notes.js');
var MIME = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.json': 'application/json', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png' };
// Pages de mission : le chiffre et les notes viennent du bloc « En bref » de la page affichée.
var MISSIONS = [['finances', 'Finances publiques'], ['education', 'Éducation'], ['sante', 'Santé'], ['securite', 'Sécurité et justice'], ['defense', 'Défense'], ['vie', 'Vie des Français']];

function serveur() {
  return new Promise(function (ok) {
    var s = http.createServer(function (req, res) {
      var u = decodeURIComponent(req.url.split('?')[0]), f = path.join(ROOT, u.endsWith('/') ? u + 'index.html' : u);
      if (!f.startsWith(ROOT) || !fs.existsSync(f)) { res.writeHead(404); return res.end(); }
      res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' }); fs.createReadStream(f).pipe(res);
    }).listen(0, function () { ok(s); });
  });
}
var esc = function (t) { return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;'); };
var nf = function (v) { return v == null ? '—' : (Math.round(v * 10) / 10).toFixed(1).replace('.', ','); };
var cl = function (v) { return v == null ? '' : v >= 10 ? 'g' : v >= 6 ? 'm' : 'b'; };

// La carte : le nom de la page, ce qui est mesuré, un grand chiffre, la note des quatre présidents, l'adresse.
// Mise en page qui remplit les 1200 × 630 : en-tête, titre, puis le bloc chiffré au centre (flex 1), légende en pied.
function carte(o) {
  var large = !o.n; // sans grand chiffre (accueil) : les cartes des présidents prennent toute la largeur
  return '<!doctype html><html lang="fr"><head><meta charset="utf-8">' +
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap">' +
    '<style>*{box-sizing:border-box}body{margin:0;width:1200px;height:630px;background:#f6f6f3;color:#1c1d22;font-family:"Inter Tight",system-ui,sans-serif;padding:44px 60px 40px;display:flex;flex-direction:column}' +
    '.top{display:flex;justify-content:space-between;align-items:baseline}.brand{font-family:Newsreader,serif;font-size:40px;color:#2f5bd3}.adr{font-size:26px;font-weight:700;color:#2f5bd3}' +
    '.t{font-size:' + (o.titre.length > 30 ? 60 : 78) + 'px;font-weight:700;letter-spacing:-.015em;margin:6px 0 0;line-height:1.02}.s{font-size:28px;color:#62646d;margin-top:10px;line-height:1.25}' +
    '.mid{flex:1;display:flex;align-items:center;gap:44px}.gauche{display:flex;flex-direction:column;gap:6px}.n{font-family:Newsreader,serif;font-size:200px;line-height:.8;white-space:nowrap;letter-spacing:-.02em}.n small{font-size:72px;color:#62646d;letter-spacing:0}' +
    '.nt{font-size:25px;color:#62646d;max-width:360px;line-height:1.3}.pres{display:flex;gap:16px;margin-left:auto}' + (large ? '.pres{margin:0;width:100%}.p{flex:1}' : '') +
    '.p{width:' + (large ? 'auto' : '164px') + ';background:#fff;border:2px solid #e2e2dc;border-radius:22px;padding:' + (large ? '22px 8px 30px' : '18px 8px 26px') + ';text-align:center;position:relative;overflow:hidden}' +
    '.p span{display:block;font-size:' + (large ? 30 : 24) + 'px;color:#62646d;font-weight:600}.p b{display:block;font-family:Newsreader,serif;font-size:' + (large ? 104 : 58) + 'px;font-weight:500;line-height:1.05}' +
    '.p i{position:absolute;left:0;bottom:0;height:9px}.g b{color:#1f8a4c}.g i{background:#1f8a4c}.m b{color:#b0812a}.m i{background:#b0812a}.b b{color:#c43d3d}.b i{background:#c43d3d}' +
    '.dates{display:flex;flex-direction:column;gap:14px;margin-left:auto}.d{background:#fff;border:2px solid #e2e2dc;border-radius:22px;padding:18px 28px}.d span{display:block;font-size:24px;color:#62646d;font-weight:600}.d b{font-family:Newsreader,serif;font-size:52px;font-weight:500}' +
    '.f{font-size:23px;color:#62646d}</style></head><body>' +
    '<div class="top"><span class="brand">Concret</span><span class="adr">' + esc(o.adresse) + '</span></div>' +
    '<div class="t">' + esc(o.titre) + '</div><div class="s">' + esc(o.sous) + '</div>' +
    '<div class="mid">' + (o.n ? '<div class="gauche"><div class="n">' + esc(o.n[0]) + '<small>' + esc(o.n[1]) + '</small></div><div class="nt">' + esc(o.nt) + '</div></div>' : '') +
    (o.pres ? '<div class="pres">' + o.pres.map(function (p) { return '<div class="p ' + cl(p.v) + '"><span>' + esc(p.n) + '</span><b>' + nf(p.v) + '</b><i style="width:' + (p.v == null ? 0 : 5 * p.v) + '%"></i></div>'; }).join('') + '</div>' : '') +
    (o.dates ? '<div class="dates">' + o.dates.map(function (d) { return '<div class="d"><span>' + esc(d[0]) + '</span><b>' + esc(d[1]) + '</b></div>'; }).join('') + '</div>' : '') + '</div>' +
    '<div class="f">' + esc(o.pied) + '</div></body></html>';
}

(async function () {
  if (!fs.existsSync(OUT)) fs.mkdirSync(OUT, { recursive: true });
  var srv = await serveur(), base = 'http://localhost:' + srv.address().port;
  var { chromium } = require('playwright'), b = await chromium.launch(), cartes = [];
  var court = function (n) { return n.split(' ').slice(-1)[0]; };
  // Missions : on lit le bloc « En bref » tel que la page l'affiche.
  for (var i = 0; i < MISSIONS.length; i++) {
    var p = await b.newPage({ viewport: { width: 1280, height: 900 } });
    await p.goto(base + '/' + MISSIONS[i][0] + '/', { waitUntil: 'networkidle' }); await p.waitForTimeout(1200);
    var r = await p.evaluate(function () {
      var box = document.getElementById('reponse'); if (!box || !box.querySelector('.bref-n')) return null;
      var n = box.querySelector('.bref-n').textContent.split('/');
      return { n: n, pres: Array.prototype.map.call(box.querySelectorAll('.bref-pres a'), function (a) { var t = a.querySelector('b').textContent.replace(',', '.'); return { n: a.querySelector('span').textContent, v: isNaN(+t) ? null : +t }; }) };
    });
    await p.close();
    if (!r) throw new Error('bloc « En bref » introuvable sur la page ' + MISSIONS[i][0]);
    cartes.push({ f: MISSIONS[i][0], titre: MISSIONS[i][1], sous: 'La France face à la moyenne de l\'Union européenne', n: [r.n[0], '/' + r.n[1]], nt: 'indicateurs où la France fait mieux, au dernier chiffre connu', pres: r.pres, pied: 'La note des présidents sur 20 · 10 = aussi bien que la moyenne de l\'UE', adresse: 'concret2027.fr/' + MISSIONS[i][0] });
  }
  // Accueil (et mentions légales) : le classement général, toutes missions confondues (même calcul que la page).
  var S = JSON.parse(fs.readFileSync(path.join(ROOT, 'data.json'), 'utf8')).series, cg = NOTES.classement(S).pres.slice().sort(function (a, c) { return a.y0 - c.y0; });
  var gen = { titre: 'Les présidents notés, mission par mission', sous: 'Finances, éducation, santé, sécurité et justice, défense, vie des Français : face à la moyenne de l\'UE, depuis 1995', pres: cg.map(function (x) { return { n: court(x.n), v: x.m }; }), pied: 'Classement général sur 20 · ' + NOTES.MISSIONS.length + ' missions', adresse: 'concret2027.fr' };
  cartes.push(Object.assign({ f: 'accueil' }, gen));
  // Baromètre : le nombre de jours avant le premier tour (date lue dans l'agenda du baromètre), refait chaque jour.
  var D = JSON.parse(fs.readFileSync(path.join(ROOT, 'data.json'), 'utf8')).datasets, t1 = (D.agenda_barometre || []).filter(function (a) { return /premier tour/i.test(a.evenement); })[0];
  var t2 = (D.agenda_barometre || []).filter(function (a) { return /second tour/i.test(a.evenement); })[0], jour = function (a) { return new Date(a.date + 'T12:00:00').toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' }); };
  var jours = t1 ? Math.ceil((new Date(t1.date + 'T00:00:00+02:00') - new Date()) / 864e5) : null;
  cartes.push({ f: 'barometre', titre: 'Baromètre 2027', sous: 'Sondages et parieurs de la présidentielle, mis à jour chaque jour', n: jours > 0 ? [String(jours), ' jours'] : null, nt: 'avant le premier tour de l\'élection présidentielle', dates: [t1, t2].filter(Boolean).map(function (a) { return [/premier/i.test(a.evenement) ? 'Premier tour' : 'Second tour', jour(a) + ' ' + a.date.slice(0, 4)]; }), pied: 'Sources : Commission des sondages, instituts, Polymarket', adresse: 'concret2027.fr/barometre' });
  // Une image n'est refaite que si son contenu a changé (empreinte du texte de la carte) : le dépôt ne grossit pas chaque jour.
  var EMP = path.join(OUT, 'empreintes.json'), emp = fs.existsSync(EMP) ? JSON.parse(fs.readFileSync(EMP, 'utf8')) : {}, faites = [];
  for (var j = 0; j < cartes.length; j++) {
    var h = carte(cartes[j]), e = crypto.createHash('sha1').update(h).digest('hex').slice(0, 16), f = path.join(OUT, cartes[j].f + '.png');
    if (emp[cartes[j].f] === e && fs.existsSync(f)) continue;
    var q = await b.newPage({ viewport: { width: 1200, height: 630 } });
    await q.setContent(h, { waitUntil: 'networkidle' }); await q.waitForTimeout(300);
    await q.screenshot({ path: f });
    await q.close(); emp[cartes[j].f] = e; faites.push(cartes[j].f);
  }
  fs.writeFileSync(EMP, JSON.stringify(emp, null, 1) + '\n');
  await b.close(); srv.close();
  console.log('donnees/apercu : ' + (faites.length ? 'refaites : ' + faites.join(', ') : 'aucune carte modifiée'));
})().catch(function (e) { console.error(e.message); process.exit(1); });
