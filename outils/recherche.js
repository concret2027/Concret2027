/* Index du moteur de recherche du site : donnees/recherche.json.
   Chaque page est affichée comme dans un navigateur (les courbes et les thèmes sont construits à l'affichage),
   tous les blocs dépliés ; on relève chaque bloc qui a un identifiant et un titre, et chaque mot du lexique.
   À relancer après une modification des pages (pas besoin après une mise à jour des chiffres) :
     node outils/recherche.js            (lance un petit serveur local sur le dossier du site) */
var fs = require('fs'), path = require('path'), http = require('http');
var ROOT = path.join(__dirname, '..');
var PAGES = [['/', 'Accueil'], ['/finances/', 'Finances'], ['/education/', 'Éducation'], ['/sante/', 'Santé'], ['/securite/', 'Sécurité et justice'], ['/barometre/', 'Baromètre 2027']];
// Mots que les lecteurs cherchent et qui ne sont pas écrits tels quels sur la page.
var SYN = { inflation: 'prix ipch hausse des prix', chomage: 'emploi travail', dette: 'endettement dette publique', deficit: 'solde budget', homicide: 'meurtre crime',
  prison: 'détenus incarcération surpopulation', oqtf: 'expulsion éloignement immigration', pisa: 'école élèves niveau', vaccination: 'vaccin', sondage: 'présidentielle élection candidats' };
var MIME = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.json': 'application/json', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png' };

function serveur() {
  return new Promise(function (ok) {
    var s = http.createServer(function (req, res) {
      var u = decodeURIComponent(req.url.split('?')[0]), f = path.join(ROOT, u.endsWith('/') ? u + 'index.html' : u);
      if (!f.startsWith(ROOT) || !fs.existsSync(f)) { res.writeHead(404); return res.end(); }
      res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' }); fs.createReadStream(f).pipe(res);
    }).listen(0, function () { ok(s); });
  });
}

(async function () {
  var srv = await serveur(), base = 'http://localhost:' + srv.address().port;
  var { chromium } = require('playwright'), b = await chromium.launch(), out = [];
  for (var i = 0; i < PAGES.length; i++) {
    var u = PAGES[i][0], nom = PAGES[i][1], p = await b.newPage({ viewport: { width: 1280, height: 900 } });
    await p.goto(base + u, { waitUntil: 'networkidle' }); await p.waitForTimeout(1500);
    await p.evaluate(function () { document.querySelectorAll('details').forEach(function (d) { d.open = true; d.dispatchEvent(new Event('toggle')); }); });
    await p.waitForTimeout(1500);
    var items = await p.evaluate(function () {
      var net = function (t) { return (t || '').replace(/\s+/g, ' ').trim(); }, res = [], vus = {};
      var titreDe = function (el) {
        var h = el.querySelector(':scope > h2, :scope > summary .acc-h, :scope > .mo-lab, :scope > h3, :scope > .eyebrow, :scope > span.eyebrow, :scope > .lab, h2');
        var e = el.querySelector('.eyebrow'), t = net(h && h.textContent);
        if (e && h && h !== e) { var et = net(e.textContent), reste = net(h.textContent.replace(e.textContent, '')); t = reste && reste !== et ? et + ' : ' + reste : et; }
        return t;
      };
      document.querySelectorAll('section[id], details[id], .card[id], .mo, .metric, .chart[id]').forEach(function (el) {
        var id = el.id, cible = el;
        if (!id) { var a = el.querySelector('[id]'); if (!a) return; id = a.id; cible = a; }
        if (vus[id] || /^(rank|radar|gov-list|sum-list|crit|regles|quiz)/.test(id)) return;
        var bloc = el.classList.contains('chart') ? el.closest('section, .card, .mo') || el : el, t = titreDe(bloc);
        if (!t || t.length < 3) return;
        vus[id] = 1;
        res.push({ id: id, t: t.slice(0, 140), k: net(bloc.textContent).slice(0, 400) });
      });
      // Lexique : chaque mot défini mène au lexique de la page.
      document.querySelectorAll('dl dt').forEach(function (dt) {
        var sec = dt.closest('section[id], details[id], [id]'); if (!sec) return;
        var dd = dt.nextElementSibling;
        res.push({ id: sec.id, t: 'Lexique : ' + net(dt.textContent), k: net(dd && dd.textContent).slice(0, 300) });
      });
      return res;
    });
    items.forEach(function (x) { out.push({ p: nom, u: u + '#' + x.id, t: x.t, k: x.k }); });
    console.log(nom + ' : ' + items.length + ' entrées');
    await p.close();
  }
  await b.close(); srv.close();
  // Titres sans la partie qui change (mois, « noté, dans… ») ; un même titre n'apparaît qu'une fois par page.
  var deja = {};
  out = out.filter(function (x) { x.t = x.t.split(' · ')[0].replace(/ du \d{1,2}(er)? (janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)( \d{4})?/g, '').replace(/^\s*:\s*|\s*:\s*$/g, '').replace(/^Le dernier sondage : .*/, 'Le dernier sondage'); var c = x.p + '|' + x.t; if (deja[c]) return false; deja[c] = 1; return true; });
  out.forEach(function (x) {
    var n = (x.t + ' ' + x.k).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
    Object.keys(SYN).forEach(function (s) { if (n.indexOf(s) >= 0) x.k += ' ' + SYN[s]; });
  });
  fs.writeFileSync(path.join(ROOT, 'donnees/recherche.json'), JSON.stringify(out));
  console.log('donnees/recherche.json : ' + out.length + ' entrées');
})().catch(function (e) { console.error('Index de recherche impossible : ' + e.message); process.exit(1); });
