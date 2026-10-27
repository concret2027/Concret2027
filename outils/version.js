// node outils/version.js : version du site, pour que les visiteurs (et la web app) sachent quand une nouvelle version est en ligne.
// La version est une empreinte des pages HTML et des scripts communs (commun/*.js) : elle ne change que si le site lui-même change,
// pas quand seules les données changent (data.json est déjà relu à chaque visite). Elle est écrite dans chaque page
// (<meta name="concret-version">) et dans donnees/version.json, que commun/menu.js compare à chaque ouverture.
'use strict';
var fs = require('fs'), path = require('path'), crypto = require('crypto');
var ROOT = path.join(__dirname, '..');
var META = /<meta name="concret-version" content="[^"]*">\n?/;

var pages = ['index.html'].concat(fs.readdirSync(ROOT).filter(function (d) {
  return fs.existsSync(path.join(ROOT, d, 'index.html')) && !/^(\.|node_modules)/.test(d);
}).sort().map(function (d) { return d + '/index.html'; }));
var communs = fs.readdirSync(path.join(ROOT, 'commun')).filter(function (f) { return /\.js$/.test(f); }).sort().map(function (f) { return 'commun/' + f; });

var h = crypto.createHash('sha256');
pages.concat(communs).forEach(function (f) { h.update(f + '\n'); h.update(fs.readFileSync(path.join(ROOT, f), 'utf8').replace(META, '')); });
var v = h.digest('hex').slice(0, 12);

var changees = 0;
pages.forEach(function (f) {
  var p = path.join(ROOT, f), s = fs.readFileSync(p, 'utf8'), m = '<meta name="concret-version" content="' + v + '">\n';
  var n = META.test(s) ? s.replace(META, m) : s.replace(/(<meta charset="utf-8">\n)/i, '$1' + m);
  if (n !== s) { fs.writeFileSync(p, n); changees++; }
});
var vf = path.join(ROOT, 'donnees', 'version.json'), avant = fs.existsSync(vf) ? fs.readFileSync(vf, 'utf8') : '';
var nv = JSON.stringify({ v: v }) + '\n';
if (avant !== nv) fs.writeFileSync(vf, nv);
console.log('Version du site : ' + v + (changees ? ' (' + changees + ' page(s) mise(s) à jour)' : ''));
