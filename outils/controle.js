#!/usr/bin/env node
/* Contrôle de la mise à jour automatique de Concret.
   node outils/controle.js a-faire [AAAA-MM-JJ]
       Liste les indicateurs du calendrier à vérifier aujourd'hui.
   node outils/controle.js verifier [AAAA-MM-JJ] [--compte-rendu fichier.md]
       Valide data.json, recalcule toutes les notes (commun/notes.js), les compare à la dernière publication,
       vérifie les récits (outils/recits.js), contrôle le calendrier, met à jour donnees/notes.json et
       donnees/a_valider.json, écrit le journal du mois (journal/AAAA-MM.md) et imprime la notification.
       Code de sortie 1 si data.json ne doit pas être publié. */
var fs = require('fs'), path = require('path'), cp = require('child_process');
var ROOT = path.join(__dirname, '..');
var rd = function (f) { return JSON.parse(fs.readFileSync(path.join(ROOT, f), 'utf8')); };
var wr = function (f, o) { fs.writeFileSync(path.join(ROOT, f), JSON.stringify(o, null, 1) + '\n'); };
var NOTES = require('../commun/notes.js'), RECITS = require('./recits.js');

var args = process.argv.slice(2), cmd = args[0];
var today = (args[1] && /^\d{4}-\d{2}-\d{2}$/.test(args[1])) ? args[1] : new Date().toLocaleDateString('sv-SE', { timeZone: 'Europe/Paris' });
var crIdx = args.indexOf('--compte-rendu'), compteRendu = crIdx > 0 ? fs.readFileSync(args[crIdx + 1], 'utf8').trim() : '';
var MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
var dateFr = function (iso) { var p = iso.split('-'); return (+p[2] === 1 ? '1er' : +p[2]) + ' ' + MOIS[+p[1] - 1] + ' ' + p[0]; };
var nf = function (v) { return v == null ? 'non noté' : String(Math.round(v * 10) / 10).replace('.', ','); };

var cal = rd('donnees/calendrier.json');

if (cmd === 'a-faire') {
  var due = cal.indicateurs.filter(function (i) { return i.prochaine_verification && i.prochaine_verification <= today; });
  console.log(due.length + ' indicateur(s) à vérifier le ' + dateFr(today) + ' :');
  due.forEach(function (i) {
    console.log('- ' + i.id + ' [' + i.statut + (i.tentatives ? ', tentative ' + (i.tentatives + 1) : '') + '] ' + i.libelle + '\n    source : ' + i.source + (i.url ? '\n    url : ' + i.url : '') + '\n    cible : ' + i.cible + '\n    dernière donnée : ' + (i.derniere_donnee || 'aucune') + (i.publication_attendue ? ' · publication attendue : ' + i.publication_attendue : '') + (i.note ? '\n    note : ' + i.note : '') + (i.textes_lies.length ? '\n    textes liés : ' + i.textes_lies.join(', ') : ''));
  });
  process.exit(0);
}
if (cmd !== 'verifier') { console.error('Usage : node outils/controle.js a-faire|verifier [AAAA-MM-JJ] [--compte-rendu fichier.md]'); process.exit(2); }

// ===== 1. Validation de data.json =====
var bloquant = [], alertes = [];
var d;
try { d = rd('data.json'); } catch (e) { console.log('Concret ✗ ' + dateFr(today) + ' : data.json illisible (' + e.message + '), rien publié.'); process.exit(1); }
var err = function (m) { bloquant.push(m); };
if (!d.updated || !d.updated_iso || isNaN(Date.parse(d.updated_iso))) err('updated / updated_iso absents ou invalides');
var DATASETS = ['sondages_t1', 'sondages_t2', 'polymarket', 'polymarket_hist', 'evenements', 'agenda_barometre', 'pouls', 'finances_mois', 'actu_finances', 'agenda_finances', 'education_mois', 'actu_education', 'agenda_education'];
DATASETS.forEach(function (k) { if (!Array.isArray((d.datasets || {})[k])) err('jeu de données manquant : ' + k); });
Object.keys(d.datasets || {}).forEach(function (k) {
  (d.datasets[k] || []).forEach(function (r, i) { Object.keys(r).forEach(function (f) { if (typeof r[f] !== 'string') err(k + '[' + i + '].' + f + ' n\'est pas une chaîne'); }); });
});
var S = d.series || {};
if (!S.finances || !S.education) err('series.finances ou series.education manquant');
function serie(nom, arr, lo, hi) {
  if (!Array.isArray(arr)) return err(nom + ' manquant');
  arr.forEach(function (v, i) { if (v == null) return; if (typeof v !== 'number' || !isFinite(v)) err(nom + '[' + i + '] n\'est pas un nombre'); else if (v < lo || v > hi) err(nom + '[' + i + '] = ' + v + ' hors de [' + lo + ', ' + hi + ']'); });
}
if (S.finances) {
  var F = S.finances, R = { dette: [0, 250], deficit: [-25, 10], dep: [20, 80], po: [10, 60] };
  Object.keys(R).forEach(function (k) { ['fr', 'ea', 'de', 'us'].forEach(function (w) { serie('finances.D.' + k + '.' + w, (F.D[k] || {})[w], R[k][0], R[k][1]); }); });
  ['fr', 'ea', 'de', 'us'].forEach(function (w) { serie('finances.PIB.' + w, F.PIB[w], 5000, 200000); });
  ['uFr', 'uEa'].forEach(function (w) { serie('finances.X94.' + w, F.X94[w], 0, 40); });
  ['xFr', 'xEa', 'mFr', 'mEa'].forEach(function (w) { serie('finances.X95.' + w, F.X95[w], 5, 120); });
  ['iFr', 'iEa'].forEach(function (w) { serie('finances.X95.' + w, F.X95[w], 0, 15); });
  var ret = F.retraites || {};
  ['fr', 'eu', 'de', 'us'].forEach(function (w) { serie('finances.retraites.' + w, ret[w], 0, 25); if ((ret[w] || []).length !== (ret.annees || []).length) err('finances.retraites.' + w + ' : longueur différente de annees'); });
}
if (S.education) {
  var E = S.education;
  ['el', 'ne', 'te', 'yu'].forEach(function (k) { ['fr', 'eu', 'de'].forEach(function (w) { serie('education.S.' + k + '.' + w, E.S[k][w], 0, 80); }); });
  ['m', 'r', 's'].forEach(function (k) { ['fr', 'oe'].forEach(function (w) { serie('education.PI.' + k + '.' + w, E.PI[k][w], 300, 650); if (E.PI[k][w].length !== E.PI[k].y.length) err('education.PI.' + k + '.' + w + ' : longueur différente de y'); }); });
  serie('education.SP.fr', E.SP.fr, 2, 10);
}
['finances', 'education'].forEach(function (pg) {
  var P = (S[pg] || {}).P || {};
  Object.keys(P).forEach(function (k) { var p = P[k]; if (typeof p.v !== 'number' || !isFinite(p.v)) err(pg + '.P.' + k + ' : valeur invalide'); if (!p.source) err(pg + '.P.' + k + ' : source manquante'); });
  var T = (d.textes || {})[pg] || {};
  Object.keys(T).forEach(function (k) { if (!T[k].html || typeof T[k].html !== 'string') err('textes.' + pg + '.' + k + ' vide'); });
});
// Règle de CLAUDE.md : une donnée non comptée s'explique en clair, sans jargon.
(function () { var JARGON = /\b(n\.d\.|n\.c\.)|rupture de série|\brupture\b|non comparable/i, vus = [];
  ['finances', 'education'].forEach(function (pg) {
    Object.keys((d.textes || {})[pg] || {}).forEach(function (k) { if (JARGON.test(d.textes[pg][k].html)) vus.push('textes.' + pg + '.' + k); });
    ['FACTS', 'QUIZ'].forEach(function (k) { if (JARGON.test(JSON.stringify((S[pg] || {})[k] || []))) vus.push(pg + '.' + k); });
  });
  vus.forEach(function (v) { alertes.push('jargon à remplacer par une phrase claire dans ' + v + ' (règle de CLAUDE.md)'); });
})();
// Valeurs d'exemple (page en brouillon) : jamais publiées.
Object.keys(S).forEach(function (pg) { if (S[pg] && S[pg].exemple) err('series.' + pg + ' contient des valeurs d\'exemple (brouillon) : à remplacer par des données sourcées avant publication'); });
Object.keys(d.datasets || {}).forEach(function (k) { if ((d.datasets[k] || []).some(function (r) { return r.exemple; })) err('datasets.' + k + ' contient des lignes d\'exemple (brouillon)'); });
if (S.sante) ['C', 'AFF'].forEach(function (bloc) { Object.keys(S.sante[bloc] || {}).forEach(function (k) {
  var c = S.sante[bloc][k]; if (!c || !c.y) return;
  ['fr', 'ue', 'de', 'es', 'us', 'ue_calc'].forEach(function (w) { if (c[w] && c[w].length !== c.y.length) err('sante.' + bloc + '.' + k + '.' + w + ' : longueur différente de y'); });
}); });
// Chaque critère noté de la Santé appartient à une et une seule des questions (au plus 5 indicateurs par question).
if (S.sante && S.sante.THEMES) {
  var vusT = {}; S.sante.THEMES.forEach(function (t) {
    if (t.crit.length > 5) err('sante : le thème « ' + t.q + ' » a plus de 5 indicateurs notés');
    t.crit.forEach(function (k) { if (!S.sante.C[k]) err('sante : critère inconnu ' + k + ' dans « ' + t.q + ' »'); if (vusT[k]) err('sante : critère ' + k + ' dans deux thèmes'); vusT[k] = 1; });
  });
  Object.keys(S.sante.C).forEach(function (k) { if (!vusT[k]) err('sante : critère ' + k + ' rattaché à aucun thème'); });
  if (S.sante.THEMES.length > 5) err('sante : plus de 5 thèmes notés');
}
var ids = {};
cal.indicateurs.forEach(function (i) { if (ids[i.id]) err('calendrier : id en double ' + i.id); ids[i.id] = 1; if (!/^\d{4}-\d{2}-\d{2}$/.test(i.prochaine_verification || '')) err('calendrier : ' + i.id + ' sans prochaine_verification valide'); });

// ===== 2. Notes recalculées par la règle fixe =====
var notes = null;
if (!bloquant.length) {
  try {
    var fin = NOTES.finances(S.finances), edu = NOTES.education(S.education, { long: true });
    var lst = function (calc, list) { return list.map(function (g) { return { n: g.n, v: calc.note(calc.evaluate({ n: g.n, y0: g.y0, y1: g.y1 })) }; }); };
    var cl = NOTES.classement(S);
    notes = {
      finances: { pres: lst(fin, S.finances.PRES), gov: lst(fin, S.finances.GOVS) },
      education: { pres: lst(edu, S.education.PRES), gov: lst(edu, S.education.GOVS) },
      sante: S.sante ? { pres: lst(NOTES.sante(S.sante), S.sante.PRES), gov: lst(NOTES.sante(S.sante), S.sante.GOVS) } : { pres: [], gov: [] },
      accueil: { pres: cl.pres.map(function (r) { return { n: r.n, v: r.m }; }), gov: cl.gov.map(function (r) { return { n: r.n, v: r.m }; }) }
    };
    ['finances', 'education', 'sante', 'accueil'].forEach(function (m) { ['pres', 'gov'].forEach(function (k) { notes[m][k].forEach(function (r) { if (r.v != null && (r.v < 0 || r.v > 20 || isNaN(r.v))) err('note hors échelle : ' + m + ' ' + r.n + ' ' + r.v); }); }); });
  } catch (e) { err('calcul des notes impossible : ' + e.message); }
}
var avant = fs.existsSync(path.join(ROOT, 'donnees/notes.json')) ? rd('donnees/notes.json') : null;
var chgNotes = [];
if (notes && avant) {
  var LAB = { finances: 'Finances', education: 'Éducation', sante: 'Santé', accueil: 'Classement général' };
  ['finances', 'education', 'sante', 'accueil'].forEach(function (m) { ['pres', 'gov'].forEach(function (k) {
    var old = {}; ((avant[m] || {})[k] || []).forEach(function (r) { old[r.n] = r.v; });
    notes[m][k].forEach(function (r) { var a = old[r.n] == null ? null : Math.round(old[r.n] * 10) / 10, b = r.v == null ? null : Math.round(r.v * 10) / 10; if (a !== b) chgNotes.push(LAB[m] + ' · ' + r.n + ' ' + nf(a) + ' → ' + nf(b)); });
  }); });
}

// ===== 3. Récits (titres et conclusions) =====
var aValider = fs.existsSync(path.join(ROOT, 'donnees/a_valider.json')) ? rd('donnees/a_valider.json') : [];
var recits = [];
if (!bloquant.length) {
  var ctx = { fin: S.finances, edu: S.education, sante: S.sante, notes: notes, pouls: d.datasets.pouls };
  RECITS.forEach(function (r) {
    var res; try { res = r.verifier(ctx); } catch (e) { res = { ok: false, constat: 'vérification impossible : ' + e.message }; }
    recits.push({ id: r.id, page: r.page, ou: r.ou, texte: r.texte, ok: res.ok, constat: res.constat });
  });
  var deja = {}; aValider.forEach(function (a) { deja[a.id] = a; });
  aValider = recits.filter(function (r) { return !r.ok; }).map(function (r) {
    return { id: r.id, page: r.page, ou: r.ou, texte_actuel: r.texte, constat: r.constat, depuis: deja[r.id] ? deja[r.id].depuis : today, proposition: deja[r.id] ? deja[r.id].proposition || '' : '' };
  });
}

// ===== 4. Calendrier =====
var problemes = [];
cal.indicateurs.forEach(function (i) {
  if (i.statut === 'en_retard') problemes.push(i.libelle + ' : publication attendue' + (i.publication_attendue ? ' le ' + i.publication_attendue : '') + ' introuvable (tentative ' + i.tentatives + ')');
  else if (i.prochaine_verification <= today && i.derniere_verification !== today) problemes.push(i.libelle + ' : vérification prévue le ' + i.prochaine_verification + ' non faite');
});
var fait = cal.indicateurs.filter(function (i) { return i.derniere_verification === today; });

// ===== 5. Ce qui a changé dans data.json depuis la dernière publication =====
var changements = [];
try {
  var prev = JSON.parse(cp.execSync('git show HEAD:data.json', { cwd: ROOT, encoding: 'utf8', maxBuffer: 1 << 26, stdio: ['ignore', 'pipe', 'ignore'] }));
  Object.keys(d.datasets).forEach(function (k) {
    var a = JSON.stringify(((prev.datasets || {})[k]) || []), b = JSON.stringify(d.datasets[k]);
    if (a !== b) { var n = d.datasets[k].length - ((prev.datasets || {})[k] || []).length; changements.push(k + (n > 0 ? ' +' + n : n < 0 ? ' ' + n : ' (modifié)')); }
  });
  ['finances', 'education'].forEach(function (pg) {
    var a = ((prev.series || {})[pg]) || {}, b = S[pg] || {};
    Object.keys(b).forEach(function (k) {
      if (k === 'P') Object.keys(b.P).forEach(function (q) { var o = (a.P || {})[q]; if (!o || o.v !== b.P[q].v) changements.push(pg + '.' + q + ' ' + (o ? o.v : '∅') + ' → ' + b.P[q].v); });
      else if (JSON.stringify(a[k]) !== JSON.stringify(b[k])) changements.push(pg + '.' + k + ' (série modifiée)');
    });
  });
  ['finances', 'education'].forEach(function (pg) { var a = ((prev.textes || {})[pg]) || {}, b = (d.textes || {})[pg] || {}; Object.keys(b).forEach(function (k) { if (!a[k] || a[k].html !== b[k].html) changements.push('texte ' + pg + '.' + k); }); });
} catch (e) { alertes.push('comparaison avec la version publiée impossible : ' + e.message.split('\n')[0]); }

// ===== 6. Écritures =====
if (!bloquant.length && notes) { wr('donnees/notes.json', { date: today, finances: notes.finances, education: notes.education, accueil: notes.accueil }); wr('donnees/a_valider.json', aValider); }
var J = [];
J.push('## ' + dateFr(today), '');
J.push('**Statut :** ' + (bloquant.length ? 'données refusées, rien publié' : problemes.length ? 'publié, avec ' + problemes.length + ' problème(s)' : 'publié, tout est à jour'), '');
if (compteRendu) J.push('### Compte rendu de la mise à jour', '', compteRendu, '');
J.push('### Indicateurs vérifiés aujourd\'hui (' + fait.length + ')', '');
fait.forEach(function (i) { J.push('- ' + i.libelle + ' : dernière donnée ' + (i.derniere_donnee || '—') + ', prochaine vérification ' + i.prochaine_verification + (i.statut !== 'a_jour' ? ' (' + i.statut + ')' : '')); });
if (!fait.length) J.push('- aucun');
J.push('', '### Changements dans data.json', '');
(changements.length ? changements : ['aucun']).forEach(function (c) { J.push('- ' + c); });
J.push('', '### Notes', '');
(chgNotes.length ? chgNotes : ['aucune note modifiée']).forEach(function (c) { J.push('- ' + c); });
J.push('', '### Récits', '');
recits.forEach(function (r) { J.push('- ' + (r.ok ? '✓' : '✗ à valider') + ' ' + r.page + ', ' + r.ou + ' : « ' + r.texte + ' » (' + r.constat + ')'); });
if (bloquant.length || problemes.length || alertes.length) { J.push('', '### Problèmes', ''); bloquant.concat(problemes, alertes).forEach(function (p) { J.push('- ' + p); }); }
J.push('', '');
var jf = path.join(ROOT, 'journal', today.slice(0, 7) + '.md');
if (!fs.existsSync(jf)) fs.writeFileSync(jf, '# Journal des mises à jour · ' + MOIS[+today.slice(5, 7) - 1] + ' ' + today.slice(0, 4) + '\n\n');
fs.appendFileSync(jf, J.join('\n'));

// ===== 7. Notification =====
var out = [];
if (bloquant.length) {
  out.push('Concret ✗ ' + dateFr(today) + ' : données refusées, rien publié (' + bloquant.length + ' erreur(s)).');
  bloquant.slice(0, 5).forEach(function (b) { out.push('⚠ ' + b); });
} else {
  var principaux = chgNotes.slice(0, 3).concat(changements.filter(function (c) { return !/^texte /.test(c); }).slice(0, chgNotes.length ? 2 : 4));
  out.push('Concret ✓ ' + dateFr(today) + ' : ' + fait.length + ' indicateur(s) vérifié(s)' + (principaux.length ? ' · ' + principaux.join(' · ') : ' · aucun chiffre nouveau') + '.');
  problemes.concat(alertes).forEach(function (p) { out.push('⚠ ' + p); });
}
aValider.forEach(function (a) { out.push('À valider : « ' + a.texte_actuel + ' » (' + a.page + ') ne tient plus : ' + a.constat + '.'); });
console.log(out.join('\n'));
process.exit(bloquant.length ? 1 : 0);
