// node outils/votez.js a-ecrire : les votes de la page Votez les lois qui n'ont pas encore d'explication (une ligne JSON par vote :
//   clé à utiliser dans donnees/votez_explications.json, date, genre, intitulé officiel, dossier), votes à venir compris.
// node outils/votez.js verifier [--tout | <clé>] : chaque explication à valider (ou toutes avec --tout) est relue à la source : longueur,
//   aucun but prêté au texte, et chaque citation de « preuves » retrouvée dans le document de son lien (après normalisation des
//   espaces, apostrophes et tirets). Sort en erreur (code 1) si une citation est introuvable.
'use strict';
var fs = require('fs'), path = require('path'), cp = require('child_process');
var ROOT = path.join(__dirname, '..');
var J = JSON.parse(fs.readFileSync(path.join(ROOT, 'donnees', 'votes.json'), 'utf8'));
var FX = path.join(ROOT, 'donnees', 'votez_explications.json'), X = JSON.parse(fs.readFileSync(FX, 'utf8')).explications || {};

function questions() {
  // Même découpage que la page (commun/votez.js), sans filtre d'explication.
  global.window = {}; global.localStorage = { getItem: function () { return null; }, setItem: function () {} };
  var tout = {}; J.VOTES.forEach(function (v) { tout[v.n] = { e: 'x', url: 'x', valide: true }; });
  global.fetch = function (u) { return Promise.resolve({ ok: true, json: function () { return /votes\.json/.test(u) ? J : { explications: tout }; } }); };
  require(path.join(ROOT, 'commun', 'votez.js'));
  return window.ConcretVotez.charger();
}

function norm(s) {
  s = s.replace(/&nbsp;/g, ' ').replace(/&#x?([0-9a-f]+);/gi, function (m, n) { return String.fromCharCode(/^x/i.test(m.slice(2)) ? parseInt(n, 16) : parseInt(n, 10)); })
    .replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&rsquo;/g, '’').replace(/&laquo;/g, '«').replace(/&raquo;/g, '»');
  return s.normalize('NFC').replace(/[‐‑–]/g, '-').replace(/[   ]/g, ' ').replace(/[’‘]/g, '\'').replace(/œ/g, 'oe')
    .replace(/\b1\s*er\b/g, '1er').replace(/\bn\s+o(s?)\s*(?=\d)/g, 'no$1 ').replace(/\s+/g, ' ').replace(/ ?- ?/g, '-').replace(/ ([,.;:)])/g, '$1').replace(/([('«]) /g, '$1').replace(/ »/g, '»').trim().toLowerCase();
}
var cache = {};
function doc(u) {
  if (cache[u] != null) return cache[u];
  var t = '';
  try {
    var b = cp.execFileSync('curl', ['-sSL', '-m', '120', '-A', 'Mozilla/5.0', u], { maxBuffer: 1 << 28 });
    // Gros PDF coupé en route : on le relit par morceaux de 2 Mo.
    if (b.slice(0, 4).toString() === '%PDF' && b.slice(-1024).toString('latin1').indexOf('%%EOF') < 0) {
      var parts = [], debut = 0, m;
      do { m = cp.execFileSync('curl', ['-sSL', '-m', '120', '-A', 'Mozilla/5.0', '-r', debut + '-' + (debut + 2097151), u], { maxBuffer: 1 << 28 }); parts.push(m); debut += m.length; } while (m.length === 2097152 && parts.length < 40);
      b = Buffer.concat(parts);
    }
    if (b.slice(0, 4).toString() === '%PDF') t = cp.execFileSync('pdftotext', ['-layout', '-', '-'], { input: b, maxBuffer: 1 << 28 }).toString('utf8');
    else t = b.toString('utf8').replace(/<[^>]+>/g, ' ');
  } catch (e) { t = ''; }
  return (cache[u] = norm(t));
}
function retrouve(c, t) {
  c = norm(c); if (t.indexOf(c) >= 0) return true;
  var m = c.split(/\[\s*(?:\.\.\.|…)\s*\]|\.\.\.|…/).map(function (x) { return x.replace(/^[ .,;:]+|[ .,;:]+$/g, ''); }).filter(function (x) { return x.length > 8; });
  return m.length > 0 && m.every(function (x) { return t.indexOf(x) >= 0; });
}

var ordre = process.argv[2];
if (ordre === 'a-ecrire') {
  questions().then(function (D) {
    var n = 0;
    D.Q.forEach(function (q) {
      if (X[q.id] || (q.cav && X['avenir:' + q.cav])) return;
      n++; console.log(JSON.stringify({ cle: q.id, d: q.d, k: q.k, t: q.v.t, dos: q.v.dos || null, s: q.v.s, themes: q.pg }));
    });
    (J.AVENIR || []).forEach(function (a) {
      if (X['avenir:' + a.cle]) return;
      n++; console.log(JSON.stringify({ cle: 'avenir:' + a.cle, d: a.d, k: a.k, t: a.o, dos: a.dos, avenir: true }));
    });
    console.error(n ? n + ' vote(s) sans explication.' : 'Tous les votes ont leur explication.');
  });
} else if (ordre === 'verifier') {
  // « verifier 217 » : une seule explication, relue même si elle est validée.
  var tout = process.argv.indexOf('--tout') > 0, seule = /^[\w:-]+$/.test(process.argv[3] || '') && process.argv[3] !== '--tout' ? process.argv[3] : null, ko = 0, vus = 0;
  Object.keys(X).forEach(function (k) {
    var x = X[k]; if (seule ? k !== seule : x.valide && !tout) return;
    vus++;
    var pb = [];
    if (!x.e || x.e.length > 320) pb.push('explication absente ou trop longue');
    if (/\b(afin de|afin que|vis(e|ant) à|dans le but|pour que)\b/i.test(x.e || '')) pb.push('but prêté au texte');
    if (!(x.preuves || []).length) pb.push('aucune citation (« preuves ») à relire');
    (x.preuves || []).forEach(function (p) {
      var t = doc(p.url || x.url);
      if (!t) pb.push('document illisible : ' + (p.url || x.url));
      else if (!retrouve(p.citation || '', t)) pb.push('citation introuvable : « ' + (p.citation || '').slice(0, 90) + ' »');
    });
    if (pb.length) { ko++; console.log('✗ ' + k + ' : ' + pb.join(' ; ')); }
  });
  console.log(ko ? ko + ' explication(s) à corriger sur ' + vus + '.' : vus + ' explication(s) relue(s) à la source : tout est retrouvé.');
  process.exit(ko ? 1 : 0);
} else {
  console.log('Usage : node outils/votez.js a-ecrire | verifier [--tout | <clé>]');
}
