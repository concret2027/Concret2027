#!/usr/bin/env node
// La place de la France parmi les pays de l'UE, pour la phrase sous le titre de chaque courbe des pages de mission.
// Calculée, jamais saisie : le dernier chiffre définitif de la France (data.json, sans année estimée ni provisoire), comparé
// aux autres pays de l'UE la même année (donnees/pays.json, lus aux mêmes sources par outils/pays.py), seulement si au moins
// 20 des 27 pays ont un chiffre. Écrit dans donnees/pays_index.json (« rangs »), le petit index que chaque page charge déjà.
// Lancé par outils/controle.js verifier, pour suivre chaque mise à jour des données.
//   node outils/rangs.js
var fs = require('fs'), path = require('path');
var ROOT = path.join(__dirname, '..');
var lire = function (f) { return JSON.parse(fs.readFileSync(path.join(ROOT, f), 'utf8')); };
var S = lire('data.json').series, P = lire('donnees/pays.json'), fIdx = path.join(ROOT, 'donnees', 'pays_index.json'), I = JSON.parse(fs.readFileSync(fIdx, 'utf8'));
var UE = ['BE', 'BG', 'CZ', 'DK', 'DE', 'EE', 'IE', 'EL', 'ES', 'FR', 'HR', 'IT', 'CY', 'LV', 'LT', 'LU', 'HU', 'MT', 'NL', 'AT', 'PL', 'PT', 'RO', 'SI', 'SK', 'FI', 'SE'];
var AFFN = { dep: 'depense', det: 'detenus', jug: 'juges', pol: 'police' };
var NOM = Object.assign({ FR: 'France', DE: 'Allemagne', ES: 'Espagne' }, P.noms || {});
var MIN = 20, rangs = {};
// Les pays à égalité au plus haut ou au plus bas sont tous nommés (« Roumanie et Bulgarie »), sans la France, déjà dans la phrase.
var noms = function (L, v) { var n = L.filter(function (x) { return x.v === v && x.g !== 'FR'; }).map(function (x) { return NOM[x.g]; }); return n.length > 1 ? n.slice(0, -1).join(', ') + ' et ' + n[n.length - 1] : n[0] || 'France'; };

Object.keys(P.series).forEach(function (cle) {
  var p = cle.split('.'), pg = p[0], k = p[1];
  if (['sante', 'securite', 'defense', 'vie'].indexOf(pg) < 0 || p.length !== 2) return;
  var c = /^a-/.test(k) ? ((S[pg] || {}).AFF || {})[AFFN[k.slice(2)] || k.slice(2)] : ((S[pg] || {}).C || {})[k];
  var s = P.series[cle];
  // Un indice (100 en 2008, règle « croissance ») n'est pas un niveau qu'on peut classer.
  if (!c || !c.y || !c.fr || !s || !s.y || c.regle === 'croissance') return;
  var est = c.est || {}, prov = c.prov || {};
  for (var i = c.y.length - 1; i >= 0; i--) {
    var y = c.y[i], j = s.y.indexOf(y);
    if (c.fr[i] == null || est[y] || prov[y] || j < 0) continue;
    var L = UE.map(function (g) {
      var v = g === 'FR' ? c.fr[i] : g === 'DE' ? (c.de || [])[i] : g === 'ES' ? (c.es || [])[i] : (s[g] || [])[j];
      return v == null ? null : { g: g, v: v };
    }).filter(Boolean);
    if (L.length < MIN) continue;
    L.sort(function (a, b) { return b.v - a.v; });
    // Rang compté depuis le haut et depuis le bas : 1 + le nombre de pays strictement au-dessus (ou au-dessous).
    var f = c.fr[i], rh = 1 + L.filter(function (x) { return x.v > f; }).length, rb = 1 + L.filter(function (x) { return x.v < f; }).length;
    rangs[cle] = { y: y, rh: rh, rb: rb, n: L.length, dec: c.dec != null ? c.dec : 1, haut: [noms(L, L[0].v), L[0].v], bas: [noms(L, L[L.length - 1].v), L[L.length - 1].v] };
    break;
  }
});
I.rangs = rangs;
fs.writeFileSync(fIdx, JSON.stringify(I));
console.log(Object.keys(rangs).length + ' rangs écrits dans donnees/pays_index.json');
