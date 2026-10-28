#!/usr/bin/env node
// Compte rendu de participation de Votez les lois, pour l'éditeur seulement (rien n'est affiché sur le site ni écrit dans le dépôt).
// Lit le compteur de Concret (outils/compteur_worker.js), qui ne connaît que des nombres : personnes (une par appareil, au premier
// vote), votes au total et par jour, votes par texte. Jamais le sens d'un vote.
//   node outils/votez_stats.js            → quelques lignes à mettre dans la notification de la tâche quotidienne
//   node outils/votez_stats.js --textes   → aussi le nombre de votes de chaque texte
var fs = require('fs'), path = require('path'), cp = require('child_process');
var API = 'https://compteur.square-brook-9d65.workers.dev/';
var cle = function (id) { return 'quiz-votez-' + String(id).toLowerCase().replace(/[^a-z0-9-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 69); };
// Par curl, comme outils/votez.js (il passe par le proxy de l'environnement).
function lire(id) {
  return new Promise(function (ok, ko) {
    cp.execFile('curl', ['-sS', '-m', '30', '-H', 'Origin: https://concret2027.fr', API + 'get?k=' + encodeURIComponent(cle(id)) + '&n=1'], function (e, out) {
      if (e) return ko(e); try { ok(JSON.parse(out).v[0]); } catch (x) { ko(new Error('réponse illisible')); }
    });
  });
}
// Jour à Paris, décalé de d jours.
function jour(d) { var t = new Date(Date.now() + d * 864e5); return new Intl.DateTimeFormat('fr-CA', { timeZone: 'Europe/Paris' }).format(t); }
var nf = function (n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' '); };

(async function () {
  var J = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'donnees', 'votes.json'), 'utf8'));
  var hier = jour(-1), auj = jour(0);
  var v = await Promise.all(['personnes', 'personnes-' + hier, 'personnes-' + auj, 'total', 'jour-' + hier, 'jour-' + auj].map(lire));
  var lignes = ['Votez les lois (pour l\'éditeur, pas affiché sur le site) : ' + nf(v[0]) + ' personnes ont voté au moins un texte (' + nf(v[1]) + ' nouvelles hier, ' + nf(v[2]) + ' aujourd\'hui) ; ' + nf(v[3]) + ' votes au total (' + nf(v[4]) + ' hier, ' + nf(v[5]) + ' aujourd\'hui).'];
  // Votes par texte, quelques requêtes à la fois.
  var T = J.VOTES.map(function (x) { return { id: String(x.n), t: x.dl || x.t }; }).concat((J.AVENIR || []).map(function (a) { return { id: 'avenir-' + a.cle, t: 'À venir, ' + a.d + ' : ' + a.o }; }));
  var vus = {}; T = T.filter(function (x) { if (vus[x.id]) return false; vus[x.id] = 1; return true; });
  // Sans aucun vote, pas besoin de lire chaque texte.
  for (var i = 0; v[3] && i < T.length; i += 40) {
    var lot = T.slice(i, i + 40), n = await Promise.all(lot.map(function (x) { return lire(x.id).catch(function () { return null; }); }));
    lot.forEach(function (x, k) { x.n = n[k]; });
  }
  var L = T.filter(function (x) { return x.n; }).sort(function (a, b) { return b.n - a.n; });
  if (L.length) lignes.push('Textes les plus votés : ' + L.slice(0, 5).map(function (x) { return String(x.t).slice(0, 70) + ' (' + nf(x.n) + ')'; }).join(' ; ') + '.');
  if (process.argv.indexOf('--textes') > 0) L.forEach(function (x) { lignes.push('  ' + nf(x.n) + '  ' + x.t); });
  console.log(lignes.join('\n'));
})().catch(function (e) { console.log('Votez les lois : compteur illisible (' + e.message + ').'); process.exit(1); });
