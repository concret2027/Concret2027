#!/usr/bin/env node
// Ce que les visiteurs ouvrent, page par page, pour l'éditeur seulement (rien n'est affiché sur le site ni écrit dans le dépôt).
// Lit le compteur de Concret (outils/compteur_worker.js), qui ne connaît que des totaux : pages vues, puis, une fois par visite de la
// page, petites courbes agrandies, « Voir les chiffres », « Définitions et sources », dépliants de courbes, « Détail du graphe »
// (comptés par commun/menu.js, seulement sur concret2027.fr). Jamais rien qui identifie la personne.
//   node outils/vues_stats.js   → quelques lignes à mettre dans la notification de la tâche quotidienne
var cp = require('child_process');
var API = 'https://compteur.square-brook-9d65.workers.dev/';
var PAGES = ['accueil', 'finances', 'education', 'sante', 'securite', 'defense', 'vie', 'demographie', 'politique', 'barometre', 'quiz', 'votez'];
var QUOI = [['courbe', 'petite courbe agrandie'], ['chiffres', '« Voir les chiffres »'], ['replis', 'courbes dépliées'], ['detail', '« Détail du graphe »'], ['defs', '« Définitions et sources »']];
// Par curl, comme outils/votez_stats.js (il passe par le proxy de l'environnement).
function lire(k) {
  return new Promise(function (ok) {
    cp.execFile('curl', ['-sS', '-m', '30', '-H', 'Origin: https://concret2027.fr', API + 'get?k=' + encodeURIComponent('quiz-vue-' + k) + '&n=1'], function (e, out) {
      if (e) return ok(null); try { ok(JSON.parse(out).v[0]); } catch (x) { ok(null); }
    });
  });
}
var pc = function (n, d) { return d ? Math.round(100 * n / d) + ' %' : '—'; };

(async function () {
  var lignes = ['Ce que les visiteurs ouvrent (pour l\'éditeur, pas affiché sur le site ; une fois par visite de la page) :'];
  for (var i = 0; i < PAGES.length; i++) {
    var p = PAGES[i], v = await Promise.all([p].concat(QUOI.map(function (q) { return p + '-' + q[0]; })).map(lire));
    if (v[0] == null) { lignes.push('  ' + p + ' : compteur illisible'); continue; }
    if (!v[0]) continue;
    var det = QUOI.map(function (q, j) { return v[j + 1] ? q[1] + ' ' + pc(v[j + 1], v[0]) : ''; }).filter(Boolean);
    lignes.push('  ' + p + ' : ' + v[0] + ' visite' + (v[0] > 1 ? 's' : '') + (det.length ? ' ; ' + det.join(', ') : ' ; rien ouvert'));
  }
  if (lignes.length === 1) lignes.push('  aucune visite comptée pour l\'instant.');
  // Appareils (commun/menu.js) : depuis le début, aujourd'hui, hier et les sept derniers jours (heure de Paris).
  var j = function (n) { return new Date(Date.now() - n * 864e5).toLocaleDateString('sv-SE', { timeZone: 'Europe/Paris' }); };
  var a = await Promise.all(['appareils'].concat([0, 1, 2, 3, 4, 5, 6].map(function (n) { return 'appareils-' + j(n); })).map(lire));
  if (a[0] != null) {
    var sept = a.slice(1).reduce(function (t, v) { return t + (v || 0); }, 0);
    lignes.unshift('Appareils différents sur le site (pour l\'éditeur ; comptés depuis le 30 octobre 2026) : ' + a[0] + ' depuis le début · aujourd\'hui ' + (a[1] || 0) + ' · hier ' + (a[2] || 0) + ' · 7 derniers jours, total des appareils de chaque jour ' + sept + '.');
  }
  console.log(lignes.join('\n'));
})();
