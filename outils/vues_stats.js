#!/usr/bin/env node
// Ce que les visiteurs ouvrent, page par page, pour l'éditeur seulement (rien n'est affiché sur le site ni écrit dans le dépôt).
// Lit le compteur de Concret (outils/compteur_worker.js), qui ne connaît que des totaux : pages vues, puis, une fois par visite de la
// page, petites courbes agrandies, « Voir les chiffres », « Définitions et sources », dépliants de courbes, « Détail du graphe »
// (comptés par commun/menu.js, seulement sur concret2027.fr). Jamais rien qui identifie la personne.
// Et, depuis le 30 octobre 2026 : appareils différents, passages d'une page à l'autre, temps passé par page (tranches), durée et
// nombre de pages des visites, toujours en totaux. Les appareils de l'éditeur (concret2027.fr/?moi=1) ne sont pas comptés.
//   node outils/vues_stats.js   → quelques lignes à mettre dans la notification de la tâche quotidienne
var cp = require('child_process');
var API = 'https://compteur.square-brook-9d65.workers.dev/';
var PAGES = ['accueil', 'finances', 'education', 'sante', 'securite', 'defense', 'vie', 'demographie', 'politique', 'barometre', 'quiz', 'votez'];
var QUOI = [['courbe', 'petite courbe agrandie'], ['chiffres', '« Voir les chiffres »'], ['replis', 'courbes dépliées'], ['detail', '« Détail du graphe »'], ['defs', '« Définitions et sources »']];
// Par curl, comme outils/votez_stats.js (il passe par le proxy de l'environnement).
function lire(k, n) {
  return new Promise(function (ok) {
    cp.execFile('curl', ['-sS', '-m', '30', '-H', 'Origin: https://concret2027.fr', API + 'get?k=' + encodeURIComponent('quiz-vue-' + k) + '&n=' + (n || 1)], function (e, out) {
      if (e) return ok(null); try { var v = JSON.parse(out).v; ok(n ? v : v[0]); } catch (x) { ok(null); }
    });
  });
}
// Par paquets, pour ne pas lancer des centaines de curl à la fois.
async function lireTout(cles, n) {
  var out = [];
  for (var i = 0; i < cles.length; i += 24) out = out.concat(await Promise.all(cles.slice(i, i + 24).map(function (k) { return lire(k, n); })));
  return out;
}
var pc = function (n, d) { return d ? Math.round(100 * n / d) + ' %' : '—'; };

(async function () {
  var lignes = ['Ce que les visiteurs ouvrent (pour l\'éditeur, pas affiché sur le site ; une fois par visite de la page) :'];
  for (var i = 0; i < PAGES.length; i++) {
    var p = PAGES[i], v = await Promise.all([p].concat(QUOI.map(function (q) { return p + '-' + q[0]; })).map(function (k) { return lire(k); }));
    if (v[0] == null) { lignes.push('  ' + p + ' : compteur illisible'); continue; }
    if (!v[0]) continue;
    var det = QUOI.map(function (q, j) { return v[j + 1] ? q[1] + ' ' + pc(v[j + 1], v[0]) : ''; }).filter(Boolean);
    lignes.push('  ' + p + ' : ' + v[0] + ' visite' + (v[0] > 1 ? 's' : '') + (det.length ? ' ; ' + det.join(', ') : ' ; rien ouvert'));
  }
  if (lignes.length === 1) lignes.push('  aucune visite comptée pour l\'instant.');
  // Appareils (commun/menu.js) : depuis le début, aujourd'hui, hier et les sept derniers jours (heure de Paris).
  var j = function (n) { return new Date(Date.now() - n * 864e5).toLocaleDateString('sv-SE', { timeZone: 'Europe/Paris' }); };
  var a = await Promise.all(['appareils'].concat([0, 1, 2, 3, 4, 5, 6].map(function (n) { return 'appareils-' + j(n); })).map(function (k) { return lire(k); }));
  if (a[0] != null) {
    var sept = a.slice(1).reduce(function (t, v) { return t + (v || 0); }, 0);
    lignes.unshift('Appareils différents sur le site (pour l\'éditeur ; comptés depuis le 30 octobre 2026) : ' + a[0] + ' depuis le début · aujourd\'hui ' + (a[1] || 0) + ' · hier ' + (a[2] || 0) + ' · 7 derniers jours, total des appareils de chaque jour ' + sept + '.');
  }
  // Quiz : nouveaux joueurs et joueurs revenus (quiz/index.html, depuis le 31 octobre 2026 ; appareils de l'éditeur exclus).
  var jq = await Promise.all([0, 1].map(function (n) { return Promise.all([lire('joueurs-nouveaux-' + j(n)), lire('joueurs-revenus-' + j(n))]); }));
  if (jq[0][0] != null) lignes.push('Quiz terminé (appareils, éditeur exclu) : aujourd\'hui ' + (jq[0][0] || 0) + ' nouveau' + ((jq[0][0] || 0) > 1 ? 'x' : '') + ' joueur' + ((jq[0][0] || 0) > 1 ? 's' : '') + ', ' + (jq[0][1] || 0) + ' revenu' + ((jq[0][1] || 0) > 1 ? 's' : '') + ' · hier ' + (jq[1][0] || 0) + ' et ' + (jq[1][1] || 0) + ' (comptés depuis le 31 octobre 2026).');
  // Parcours (commun/menu.js, depuis le 30 octobre 2026) : passages d'une page à l'autre, temps passé, durée et longueur des visites.
  var TOUTES = PAGES.concat(['contact', 'mentions-legales', 'application']);
  var nomP = function (p) { return p === 'entree' ? 'arrivée sur le site' : p; };
  var paires = []; ['entree'].concat(TOUTES).forEach(function (de) { TOUTES.forEach(function (a) { if (de !== a) paires.push([de, a]); }); });
  var pv = await lireTout(paires.map(function (x) { return 'chemin-' + x[0] + '-' + x[1]; }));
  var ch = paires.map(function (x, i) { return { de: x[0], a: x[1], n: pv[i] || 0 }; }).filter(function (x) { return x.n; });
  var entrees = ch.filter(function (x) { return x.de === 'entree'; }), nEntrees = entrees.reduce(function (t, x) { return t + x.n; }, 0);
  if (nEntrees) {
    lignes.push('Parcours (en totaux, sans suivre personne ; depuis le 30 octobre 2026) :');
    lignes.push('  ' + nEntrees + ' visites. Pages d\'arrivée : ' + entrees.sort(function (x, y) { return y.n - x.n; }).map(function (x) { return x.a + ' ' + x.n; }).join(', ') + '.');
    var internes = ch.filter(function (x) { return x.de !== 'entree'; }).sort(function (x, y) { return y.n - x.n; });
    if (internes.length) lignes.push('  Passages les plus suivis : ' + internes.slice(0, 10).map(function (x) { return x.de + ' → ' + x.a + ' ' + x.n; }).join(', ') + '.');
    // Départ du site depuis une page : passages vers elle moins passages qui en repartent vers une autre page (à peu près).
    var dep = TOUTES.map(function (p) {
      var vers = ch.filter(function (x) { return x.a === p; }).reduce(function (t, x) { return t + x.n; }, 0), hors = ch.filter(function (x) { return x.de === p; }).reduce(function (t, x) { return t + x.n; }, 0);
      return { p: p, vers: vers, part: vers ? Math.max(0, vers - hors) / vers : 0 };
    }).filter(function (x) { return x.vers >= 5; }).sort(function (x, y) { return y.vers - x.vers; });
    if (dep.length) lignes.push('  Quittent le site après cette page (environ) : ' + dep.map(function (x) { return x.p + ' ' + Math.round(100 * x.part) + ' %'; }).join(', ') + '.');
    var vs = await lireTout(['visite-10s', 'visite-30s', 'visite-60s', 'visite-180s', 'visite-600s', 'visite-pages-2', 'visite-pages-3', 'visite-pages-5', 'visite-pages-10']);
    lignes.push('  Durée des visites : au moins 10 s ' + pc(vs[0] || 0, nEntrees) + ', 30 s ' + pc(vs[1] || 0, nEntrees) + ', 1 min ' + pc(vs[2] || 0, nEntrees) + ', 3 min ' + pc(vs[3] || 0, nEntrees) + ', 10 min ' + pc(vs[4] || 0, nEntrees) + '.');
    lignes.push('  Pages vues par visite : au moins 2 ' + pc(vs[5] || 0, nEntrees) + ', 3 ' + pc(vs[6] || 0, nEntrees) + ', 5 ' + pc(vs[7] || 0, nEntrees) + ', 10 ' + pc(vs[8] || 0, nEntrees) + '.');
    var TR = ['< 10 s', '10-30 s', '30 s-1 min', '1-3 min', '3-10 min', '> 10 min'];
    var tp = await lireTout(TOUTES.map(function (p) { return 'temps-' + p; }), 6);
    var tl = TOUTES.map(function (p, i) { var v = tp[i] || [], t = v.reduce(function (a, b) { return a + b; }, 0); return t ? p + ' (' + t + ') : ' + v.map(function (n, j) { return n ? TR[j] + ' ' + pc(n, t) : ''; }).filter(Boolean).join(', ') : ''; }).filter(Boolean);
    if (tl.length) { lignes.push('  Temps passé sur chaque page :'); tl.forEach(function (l) { lignes.push('    ' + l); }); }
  }
  console.log(lignes.join('\n'));
})();
