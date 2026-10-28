/* Récits de Concret : les titres et conclusions des pages, qui ne changent jamais sans validation.
   Chaque récit a une vérification chiffrée, calculée sur data.json. Si elle échoue, outils/controle.js
   ne touche pas au texte : il l'inscrit dans donnees/a_valider.json et le signale dans la notification.
   Toute nouvelle conclusion chiffrée ajoutée à une page doit être inscrite ici. */
var r1 = function (v) { return Math.round(v * 10) / 10; };
var lastIdx = function (a) { var i = a.length - 1; while (i > 0 && (a[i] == null || isNaN(a[i]))) i--; return i; };
var lastBoth = function (a, b) { var i = Math.min(a.length, b.length) - 1; while (i > 0 && (a[i] == null || b[i] == null)) i--; return i; };
var fr = function (v, d) { return String(d ? r1(v) : Math.round(v)).replace('.', ','); };

module.exports = [
  // ===== Finances publiques =====
  { id: 'fin_bilan', page: 'finances', ou: 'meta og:description et résumé « Le bilan depuis 1995 »',
    texte: 'Depuis 1995, aucune note de président n\'atteint 10/20 en finances publiques',
    verifier: function (c) { var best = c.notes.finances.pres.slice().sort(function (a, b) { return b.v - a.v; })[0]; return { ok: best.v < 10, constat: 'meilleure note de président : ' + best.n + ', ' + fr(best.v, 1) + '/20' }; } },
  { id: 'fin_bilan_ue', page: 'finances', ou: 'résumé « Le bilan depuis 1995 »',
    texte: 'dette, dépenses et impôts au-dessus de la moyenne de l\'UE',
    verifier: function (c) {
      var D = c.fin.D, k = ['dette', 'dep', 'po'].map(function (x) { var i = lastBoth(D[x].fr, D[x].eu); return [x, D[x].fr[i] - D[x].eu[i], 1995 + i]; });
      return { ok: k.every(function (x) { return x[1] > 0; }), constat: k.map(function (x) { return x[0] + ' ' + fr(x[1], 1) + ' pt (' + x[2] + ')'; }).join(', ') }; } },
  { id: 'fin_c1', page: 'finances', ou: 'titre du graphique Dette', texte: 'De 7 points sous la moyenne de l\'UE en 2000 à 34 points au-dessus',
    verifier: function (c) { var d = c.fin.D.dette, i0 = 2000 - 1995, i = lastBoth(d.fr, d.eu), a = Math.round(d.fr[i0] - d.eu[i0]), b = Math.round(d.fr[i] - d.eu[i]); return { ok: d.eu.findIndex(function (v) { return v != null; }) === i0 && a === -7 && b === 34, constat: 'écart 2000 : ' + a + ' pt, écart ' + (1995 + i) + ' : ' + b + ' pt' }; } },
  { id: 'fin_c2', page: 'finances', ou: 'titre du graphique Déficit', texte: 'Un déficit plus élevé que la moyenne de l\'UE chaque année depuis 2002',
    verifier: function (c) { var d = c.fin.D.deficit, bad = []; for (var i = 2002 - 1995; i < Math.min(d.fr.length, d.eu.length); i++) if (d.fr[i] != null && d.eu[i] != null && !(d.fr[i] < d.eu[i])) bad.push(1995 + i); return { ok: !bad.length, constat: bad.length ? 'années où le déficit français n\'est pas plus élevé : ' + bad.join(', ') : 'vrai sur toutes les années' }; } },
  { id: 'fin_c3', page: 'finances', ou: 'titre du graphique Dépenses', texte: 'L\'écart avec l\'UE est passé de 2,6 à 7,9 points',
    verifier: function (c) { var d = c.fin.D.dep, i = lastBoth(d.fr, d.eu), a = r1(d.fr[0] - d.eu[0]), b = r1(d.fr[i] - d.eu[i]); return { ok: a === 2.6 && b === 7.9, constat: 'écart 1995 : ' + fr(a, 1) + ' pt, écart ' + (1995 + i) + ' : ' + fr(b, 1) + ' pt' }; } },
  { id: 'fin_c4', page: 'finances', ou: 'titre du graphique Prélèvements', texte: 'Entre 3,5 et 7,5 points au-dessus de l\'UE depuis 1995',
    verifier: function (c) { var d = c.fin.D.po, g = []; for (var i = 0; i < d.fr.length; i++) if (d.fr[i] != null && d.eu[i] != null) g.push(r1(d.fr[i] - d.eu[i])); var lo = Math.min.apply(null, g), hi = Math.max.apply(null, g); return { ok: lo === 3.5 && hi === 7.5, constat: 'écart minimum ' + fr(lo, 1) + ' pt, maximum ' + fr(hi, 1) + ' pt' }; } },
  { id: 'fin_pib', page: 'finances', ou: 'titre « Richesse par habitant »', texte: '16 % au-dessus de la moyenne de l\'UE en 1990, au même niveau en 2025',
    verifier: function (c) { var P = c.fin.PIB, k = lastBoth(P.fr, P.eu), a = Math.round(100 * (P.fr[0] / P.eu[0] - 1)), b = Math.round(100 * (P.fr[k] / P.eu[k] - 1)); return { ok: a === 16 && b === 0 && 1990 + k === 2025, constat: '1990 : ' + (a >= 0 ? '+' : '') + a + ' %, ' + (1990 + k) + ' : ' + (b >= 0 ? '+' : '') + b + ' %' }; } },
  { id: 'fin_spread', page: 'finances', ou: 'titre « Politique et marchés »', texte: 'La France emprunte plus cher que l\'Italie',
    // Le même mois pour les deux pays : dernières moyennes mensuelles (taux à 10 ans moins le taux allemand).
    verifier: function (c) { var F = c.fin.FR, I = c.fin.IT, D = c.fin.DE, i = Math.min(F.length, I.length, D.length) - 1, f = Math.round((F[i] - D[i]) * 100), t = Math.round((I[i] - D[i]) * 100), mois = new Date(2017, i, 15).toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' }); return { ok: f > t, constat: 'écart avec l\'Allemagne, moyenne de ' + mois + ' : France ' + fr(f) + ' pb, Italie ' + fr(t) + ' pb' }; } },
  // ===== Éducation =====
  { id: 'edu_bilan', page: 'education', ou: 'meta og:description et résumé « Le bilan »',
    texte: 'Plus de diplômés que la moyenne de l\'UE, mais des scores PISA plus bas et plus de jeunes au chômage',
    verifier: function (c) {
      var S = c.edu.S, t = lastBoth(S.te.fr, S.te.eu), y = lastBoth(S.yu.fr, S.yu.eu), m = c.edu.PI.m, r = c.edu.PI.r, im = m.fr.length - 1, ir = r.fr.length - 1;
      var ok = S.te.fr[t] > S.te.eu[t] && m.fr[im] < m.oe[im] && r.fr[ir] < r.oe[ir] && S.yu.fr[y] > S.yu.eu[y];
      return { ok: ok, constat: 'diplômés ' + fr(S.te.fr[t], 1) + ' % contre ' + fr(S.te.eu[t], 1) + ' %, PISA maths ' + m.fr[im] + ' contre ' + m.oe[im] + ', lecture ' + r.fr[ir] + ' contre ' + r.oe[ir] + ', chômage des jeunes ' + fr(S.yu.fr[y], 1) + ' % contre ' + fr(S.yu.eu[y], 1) + ' %' }; } },
  { id: 'edu_c1', page: 'education', ou: 'titre du graphique Décrochage', texte: 'Moins de décrocheurs que nos voisins',
    verifier: function (c) { var s = c.edu.S.el, i = lastBoth(s.fr, s.eu); return { ok: s.fr[i] < s.eu[i], constat: fr(s.fr[i], 1) + ' % contre ' + fr(s.eu[i], 1) + ' % dans l\'UE' }; } },
  { id: 'edu_c2', page: 'education', ou: 'titre du graphique Ni emploi ni études', texte: 'Plus de jeunes ni en emploi ni en études que la moyenne de l\'UE',
    verifier: function (c) { var s = c.edu.S.ne, i = lastBoth(s.fr, s.eu); return { ok: s.fr[i] > s.eu[i], constat: fr(s.fr[i], 1) + ' % contre ' + fr(s.eu[i], 1) + ' % dans l\'UE' }; } },
  { id: 'edu_c3', page: 'education', ou: 'titre du graphique Diplômés', texte: 'Plus de diplômés : 11 points d\'avance sur l\'UE',
    verifier: function (c) { var s = c.edu.S.te, i = lastBoth(s.fr, s.eu), g = Math.round(s.fr[i] - s.eu[i]); return { ok: g === 11, constat: 'avance de ' + g + ' points' }; } },
  { id: 'edu_c4', page: 'education', ou: 'titre du graphique Chômage des 15-24 ans', texte: 'Deux à trois fois plus qu\'en Allemagne',
    verifier: function (c) { var s = c.edu.S.yu, i = lastBoth(s.fr, s.de), q = s.fr[i] / s.de[i]; return { ok: q >= 2 && q <= 3, constat: 'rapport ' + fr(q, 1) }; } },
  { id: 'edu_depense', page: 'education', ou: 'titre « Ce que ça coûte »', texte: 'Dépense d\'éducation : 5,1 % du PIB en France, 4,7 % dans l\'UE',
    verifier: function (c) { var s = c.edu.SP, i = lastBoth(s.fr, s.eu); return { ok: fr(s.fr[i], 1) === '5,1' && fr(s.eu[i], 1) === '4,7', constat: 'dépense ' + fr(s.fr[i], 1) + ' % contre ' + fr(s.eu[i], 1) + ' % (' + (c.edu.SP.y ? c.edu.SP.y[i] : 'dernière année commune') + ')' }; } },
  { id: 'edu_pisa', page: 'education', ou: 'titre « PISA »', texte: 'Vingt-cinq ans de recul, et sous la moyenne de l\'OCDE',
    verifier: function (c) { var m = c.edu.PI.m, r = c.edu.PI.r, im = m.fr.length - 1, ir = r.fr.length - 1; return { ok: m.fr[im] < m.fr[0] && r.fr[ir] < r.fr[0] && m.fr[im] < m.oe[im] && r.fr[ir] < r.oe[ir], constat: 'maths ' + m.fr[0] + ' → ' + m.fr[im] + ' (OCDE ' + m.oe[im] + '), lecture ' + r.fr[0] + ' → ' + r.fr[ir] + ' (OCDE ' + r.oe[ir] + ')' }; } },
  { id: 'edu_pisa_maths', page: 'education', ou: 'titre du graphique Mathématiques', texte: '−53 points depuis 2003',
    verifier: function (c) { var m = c.edu.PI.m, i = m.y.indexOf(2003), g = m.fr[m.fr.length - 1] - m.fr[i]; return { ok: g === -53, constat: 'évolution ' + g + ' points' }; } },
  { id: 'edu_pisa_lecture', page: 'education', ou: 'titre du graphique Lecture', texte: 'Le plus fort recul : −49 points depuis 2012',
    verifier: function (c) { var r = c.edu.PI.r, i = r.y.indexOf(2012), g = r.fr[r.fr.length - 1] - r.fr[i]; return { ok: g === -49, constat: 'évolution ' + g + ' points' }; } },
  { id: 'edu_pisa_sciences', page: 'education', ou: 'titre du graphique Sciences', texte: 'Sciences : au niveau de la moyenne de l\'OCDE',
    verifier: function (c) { var gap = function (k) { var x = c.edu.PI[k], i = x.fr.length - 1; return x.fr[i] - x.oe[i]; }; return { ok: Math.abs(gap('s')) <= 3, constat: 'écart à l\'OCDE : sciences ' + gap('s') + ', maths ' + gap('m') + ', lecture ' + gap('r') }; } },
  { id: 'edu_origine', page: 'education', ou: 'titre « Poids de l\'origine sociale »', texte: 'Écart de score selon l\'origine sociale : 95 points en France, 83 dans l\'OCDE',
    verifier: function (c) { var e = c.edu.EQ, i = e.fr.length - 1; return { ok: e.fr[i] === 95 && e.oe[i] === 83, constat: 'écart social ' + e.fr[i] + ' points contre ' + e.oe[i] + ' dans l\'OCDE' }; } },
  { id: 'edu_shanghai', page: 'education', ou: 'titre « Universités »', texte: 'Quatre universités dans le top 100 mondial, autant que l\'Allemagne',
    verifier: function (c) { var a = c.edu.ARWU, i = lastIdx(a.fr); return { ok: a.fr[i] === 4 && a.de[i] === 4, constat: 'France ' + a.fr[i] + ', Allemagne ' + a.de[i] + ' (' + a.y[i] + ')' }; } }
];
