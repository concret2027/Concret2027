#!/usr/bin/env node
// Audience de Concret pour le tableau de bord de l'éditeur (artifact « Concret, audience »), jamais dans le dépôt :
// lit les totaux du compteur (comme outils/vues_stats.js) et écrit des fichiers JSON dans un dossier HORS du dépôt.
//   node outils/audience.js <dossier> [<historique précédent .json>]
// Écrit : d_jours, d_pages, d_temps, d_chemins, d_visites, d_resume, d_hist (.json). d_hist garde une ligne par jour
// (totaux cumulés du jour) : on la reprend de la veille (2e argument) pour en tirer les visites par jour.
var cp = require('child_process'), fs = require('fs'), path = require('path');
var API = 'https://compteur.square-brook-9d65.workers.dev/';
var out = process.argv[2], prev = process.argv[3];
if (!out) { console.error('usage : node outils/audience.js <dossier hors dépôt> [historique.json]'); process.exit(2); }
if (path.resolve(out).indexOf(path.resolve(__dirname, '..') + path.sep) === 0) { console.error('Le dossier doit être hors du dépôt.'); process.exit(2); }
fs.mkdirSync(out, { recursive: true });
function lire(k, n) {
  return new Promise(function (ok) {
    cp.execFile('curl', ['-sS', '-m', '30', '-H', 'Origin: https://concret2027.fr', API + 'get?k=' + encodeURIComponent('quiz-' + k) + '&n=' + (n || 1)], function (e, o) {
      if (e) return ok(n ? [] : null); try { var v = JSON.parse(o).v; ok(n ? v : (v[0] || 0)); } catch (x) { ok(n ? [] : null); }
    });
  });
}
async function tout(ks, n) { var o = []; for (var i = 0; i < ks.length; i += 24) o = o.concat(await Promise.all(ks.slice(i, i + 24).map(function (k) { return lire(k, n); }))); return o; }
var jour = function (n) { return new Date(Date.now() - n * 864e5).toLocaleDateString('sv-SE', { timeZone: 'Europe/Paris' }); };
var PAGES = ['accueil', 'finances', 'education', 'sante', 'securite', 'defense', 'vie', 'demographie', 'politique', 'barometre', 'quiz', 'votez', 'contact', 'mentions-legales', 'application'];
var Q = ['courbe', 'chiffres', 'replis', 'detail', 'defs'];
var ecrire = function (n, v) { fs.writeFileSync(path.join(out, n + '.json'), JSON.stringify(v)); };
(async function () {
  var ds = []; for (var n = 13; n >= 0; n--) ds.push(jour(n));
  var cles = []; ds.forEach(function (d) { cles.push('vue-appareils-' + d, 'vue-joueurs-nouveaux-' + d, 'vue-joueurs-revenus-' + d, 'votez-jour-' + d, 'votez-personnes-' + d); });
  var v = await tout(cles);
  var jours = ds.map(function (d, i) {
    var r = { jour: d, appareils: v[i * 5], joueurs_nouveaux: v[i * 5 + 1], joueurs_revenus: v[i * 5 + 2], votes: v[i * 5 + 3], votants: v[i * 5 + 4] };
    if (d < '2026-10-30') r.appareils = null;                                  // comptés depuis le 30 octobre 2026
    if (d < '2026-10-31') { r.joueurs_nouveaux = null; r.joueurs_revenus = null; } // depuis le 31 octobre 2026
    return r;
  });
  ecrire('d_jours', jours);
  var pk = []; PAGES.forEach(function (p) { pk.push('vue-' + p); Q.forEach(function (q) { pk.push('vue-' + p + '-' + q); }); });
  var pv = await tout(pk), k = 0, pages = [];
  PAGES.forEach(function (p) { var r = { page: p, visites: pv[k++] }; Q.forEach(function (q) { r[q] = pv[k++]; }); pages.push(r); });
  pages = pages.filter(function (r) { return r.visites; }); ecrire('d_pages', pages);
  var TR = ['moins de 10 s', '10 à 30 s', '30 s à 1 min', '1 à 3 min', '3 à 10 min', 'plus de 10 min'], t = [];
  var tv = await tout(PAGES.map(function (p) { return 'vue-temps-' + p; }), 6);
  PAGES.forEach(function (p, i) { (tv[i] || []).forEach(function (n, j) { if (n) t.push({ page: p, tranche: TR[j], ordre: j, n: n }); }); });
  ecrire('d_temps', t);
  var vs = await tout(['vue-visite-10s', 'vue-visite-30s', 'vue-visite-60s', 'vue-visite-180s', 'vue-visite-600s', 'vue-visite-pages-2', 'vue-visite-pages-3', 'vue-visite-pages-5', 'vue-visite-pages-10', 'vue-appareils']);
  var pairs = []; ['entree'].concat(PAGES).forEach(function (a) { PAGES.forEach(function (b) { if (a !== b) pairs.push([a, b]); }); });
  var cv = await tout(pairs.map(function (x) { return 'vue-chemin-' + x[0] + '-' + x[1]; }));
  var chem = pairs.map(function (x, i) { return { de: x[0], vers: x[1], n: cv[i] }; }).filter(function (x) { return x.n; });
  ecrire('d_chemins', chem);
  var ent = chem.filter(function (x) { return x.de === 'entree'; }).reduce(function (s, x) { return s + x.n; }, 0);
  var noms = [['au moins 10 s', 'duree'], ['au moins 30 s', 'duree'], ['au moins 1 min', 'duree'], ['au moins 3 min', 'duree'], ['au moins 10 min', 'duree'], ['au moins 2 pages', 'pages'], ['au moins 3 pages', 'pages'], ['au moins 5 pages', 'pages'], ['au moins 10 pages', 'pages']];
  ecrire('d_visites', noms.map(function (x, i) { return { critere: x[0], genre: x[1], n: vs[i] || 0, visites: ent }; }));
  var auj = jour(0);
  ecrire('d_resume', [{ releve: auj, appareils_total: vs[9] || 0, visites_suivies: ent }]);
  // Historique : une ligne par jour, totaux cumulés (reprise de la veille).
  var hist = []; try { if (prev) hist = JSON.parse(fs.readFileSync(prev, 'utf8')); } catch (e) {}
  hist = hist.filter(function (r) { return r.jour !== auj; });
  hist.push({ jour: auj, pages_vues: pages.reduce(function (s, r) { return s + r.visites; }, 0), arrivees: ent, appareils_total: vs[9] || 0 });
  ecrire('d_hist', hist.slice(-120));
  console.log('Audience écrite dans ' + out + ' (' + auj + ') : ' + pages.length + ' pages, ' + chem.length + ' passages, ' + hist.length + ' jours d\'historique.');
})();
