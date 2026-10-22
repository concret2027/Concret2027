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
    texte: 'Aucun président depuis 1995 n\'a la moyenne en économie',
    verifier: function (c) { var best = c.notes.finances.pres.slice().sort(function (a, b) { return b.v - a.v; })[0]; return { ok: best.v < 10, constat: 'meilleure note de président : ' + best.n + ', ' + fr(best.v, 1) + '/20' }; } },
  { id: 'fin_bilan_decrochage', page: 'finances', ou: 'résumé « Le bilan depuis 1995 »',
    texte: 'la dette, le chômage et la richesse décrochent face à la zone euro',
    verifier: function (c) {
      var D = c.fin.D, i = lastBoth(D.dette.fr, D.dette.ea), u = c.fin.X94, j = lastBoth(u.uFr, u.uEa), P = c.fin.PIB, k = lastBoth(P.fr, P.ea);
      var dette = D.dette.fr[i] - D.dette.ea[i] > D.dette.fr[0] - D.dette.ea[0], chom = u.uFr[j] > u.uEa[j], rich = P.fr[k] < P.ea[k];
      return { ok: dette && chom && rich, constat: 'écart de dette ' + fr(D.dette.fr[i] - D.dette.ea[i], 1) + ' pt, chômage ' + fr(u.uFr[j], 1) + ' % contre ' + fr(u.uEa[j], 1) + ' %, PIB/hab. ' + fr(100 * P.fr[k] / P.ea[k]) + ' % de la zone euro' }; } },
  { id: 'fin_c1', page: 'finances', ou: 'titre du graphique Dette', texte: 'De 14 points sous la zone euro à 28 points au-dessus',
    verifier: function (c) { var d = c.fin.D.dette, i = lastBoth(d.fr, d.ea), a = Math.round(d.fr[0] - d.ea[0]), b = Math.round(d.fr[i] - d.ea[i]); return { ok: a === -14 && b === 28, constat: 'écart 1995 : ' + a + ' pt, écart ' + (1995 + i) + ' : ' + b + ' pt' }; } },
  { id: 'fin_c2', page: 'finances', ou: 'titre du graphique Déficit', texte: 'Pire que la zone euro chaque année depuis 2002',
    verifier: function (c) { var d = c.fin.D.deficit, bad = []; for (var i = 2002 - 1995; i < Math.min(d.fr.length, d.ea.length); i++) if (d.fr[i] != null && d.ea[i] != null && !(d.fr[i] < d.ea[i])) bad.push(1995 + i); return { ok: !bad.length, constat: bad.length ? 'années où la France fait au moins aussi bien : ' + bad.join(', ') : 'vrai sur toutes les années' }; } },
  { id: 'fin_c3', page: 'finances', ou: 'titre du graphique Dépenses', texte: 'L\'écart est passé de 3 à 7 points',
    verifier: function (c) { var d = c.fin.D.dep, i = lastBoth(d.fr, d.ea), a = Math.round(d.fr[0] - d.ea[0]), b = Math.round(d.fr[i] - d.ea[i]); return { ok: a === 3 && b === 7, constat: 'écart 1995 : ' + a + ' pt, écart ' + (1995 + i) + ' : ' + b + ' pt' }; } },
  { id: 'fin_c4', page: 'finances', ou: 'titre du graphique Prélèvements', texte: 'Entre 3,7 et 7,1 points au-dessus depuis 1995',
    verifier: function (c) { var d = c.fin.D.po, g = []; for (var i = 0; i < d.fr.length; i++) if (d.fr[i] != null && d.ea[i] != null) g.push(r1(d.fr[i] - d.ea[i])); var lo = Math.min.apply(null, g), hi = Math.max.apply(null, g); return { ok: lo === 3.7 && hi === 7.1, constat: 'écart minimum ' + fr(lo, 1) + ' pt, maximum ' + fr(hi, 1) + ' pt' }; } },
  { id: 'fin_pib', page: 'finances', ou: 'titre « Richesse par habitant »', texte: 'La France est passée sous la moyenne de la zone euro en 2016',
    verifier: function (c) { var P = c.fin.PIB, cross = null; for (var i = 1; i < P.fr.length; i++) if (P.fr[i] < P.ea[i] && P.fr[i - 1] >= P.ea[i - 1]) cross = 1990 + i; var k = lastBoth(P.fr, P.ea); return { ok: cross === 2016 && P.fr[k] < P.ea[k], constat: 'passage sous la moyenne : ' + cross + ', dernière année ' + (P.fr[k] < P.ea[k] ? 'en dessous' : 'au-dessus') }; } },
  { id: 'fin_spread', page: 'finances', ou: 'titre « Politique et marchés »', texte: 'La France emprunte plus cher que l\'Italie',
    verifier: function (c) { var sp = c.pouls.filter(function (r) { return r.indicateur === 'ecart_allemagne'; }).sort(function (a, b) { return a.date < b.date ? -1 : 1; }).pop(), it = c.fin.P.spread_italie; return { ok: +sp.valeur > it.v, constat: 'écart France ' + fr(+sp.valeur) + ' pb (' + sp.date + '), Italie ' + fr(it.v) + ' pb (' + it.date + ')' }; } },
  // ===== Santé (brouillon : le récit reste une question tant que les données réelles ne le confirment pas) =====
  { id: 'sante_recit', page: 'sante', ou: 'titre de la page et meta og:description',
    texte: 'Un système généreux et accessible, mais qui vit à crédit et prévient mal ?',
    verifier: function (c) {
      if (!c.sante) return { ok: true, constat: 'page non publiée' };
      // « Prévient mal » : la France fait moins bien que son voisin sur au moins la moitié des indicateurs de la question Prévention.
      var C = c.sante.C, last = function (k, w) { var a = C[k][w] || []; for (var i = a.length - 1; i >= 0; i--) if (a[i] != null) return a[i]; return null; };
      var pire = function (k) { var x = C[k], r = x.ref || 'ue', i = x.y.length - 1; while (i >= 0 && (x.fr[i] == null || x[r][i] == null)) i--; return x.low ? x.fr[i] > x[r][i] : x.fr[i] < x[r][i]; };
      var prev = c.sante.THEMES.filter(function (t) { return t.k === 'prev'; })[0].crit, mal = prev.filter(pire);
      var genereux = last('rac', 'fr') < last('rac', 'ue'), accessible = last('ren', 'fr') <= last('ren', 'ue'), credit = last('secu', 'fr') < 0, previent = mal.length * 2 >= prev.length;
      return { ok: genereux && accessible && credit && previent, constat: 'reste à charge ' + last('rac', 'fr') + ' % contre ' + last('rac', 'ue') + ' %, renoncement ' + last('ren', 'fr') + ' % contre ' + last('ren', 'ue') + ' %, solde de la Sécu ' + last('secu', 'fr') + ' % du PIB, prévention : moins bien que le voisin sur ' + mal.length + ' indicateurs sur ' + prev.length + (mal.length ? ' (' + mal.join(', ') + ')' : '') }; } },
  // ===== Éducation =====
  { id: 'edu_bilan', page: 'education', ou: 'meta og:description et résumé « Le bilan »',
    texte: 'On diplôme plus que nos voisins, mais les élèves apprennent moins, et les jeunes trouvent moins vite un emploi',
    verifier: function (c) {
      var S = c.edu.S, t = lastBoth(S.te.fr, S.te.eu), y = lastBoth(S.yu.fr, S.yu.eu), m = c.edu.PI.m, r = c.edu.PI.r, im = m.fr.length - 1, ir = r.fr.length - 1;
      var ok = S.te.fr[t] > S.te.eu[t] && m.fr[im] < m.oe[im] && r.fr[ir] < r.oe[ir] && S.yu.fr[y] > S.yu.eu[y];
      return { ok: ok, constat: 'diplômés ' + fr(S.te.fr[t], 1) + ' % contre ' + fr(S.te.eu[t], 1) + ' %, PISA maths ' + m.fr[im] + ' contre ' + m.oe[im] + ', lecture ' + r.fr[ir] + ' contre ' + r.oe[ir] + ', chômage des jeunes ' + fr(S.yu.fr[y], 1) + ' % contre ' + fr(S.yu.eu[y], 1) + ' %' }; } },
  { id: 'edu_c1', page: 'education', ou: 'titre du graphique Décrochage', texte: 'Moins de décrocheurs que nos voisins',
    verifier: function (c) { var s = c.edu.S.el, i = lastBoth(s.fr, s.eu); return { ok: s.fr[i] < s.eu[i], constat: fr(s.fr[i], 1) + ' % contre ' + fr(s.eu[i], 1) + ' % dans l\'UE' }; } },
  { id: 'edu_c2', page: 'education', ou: 'titre du graphique Ni emploi ni études', texte: 'Plus de jeunes à l\'arrêt que nos voisins',
    verifier: function (c) { var s = c.edu.S.ne, i = lastBoth(s.fr, s.eu); return { ok: s.fr[i] > s.eu[i], constat: fr(s.fr[i], 1) + ' % contre ' + fr(s.eu[i], 1) + ' % dans l\'UE' }; } },
  { id: 'edu_c3', page: 'education', ou: 'titre du graphique Diplômés', texte: 'Plus de diplômés : 11 points d\'avance sur l\'UE',
    verifier: function (c) { var s = c.edu.S.te, i = lastBoth(s.fr, s.eu), g = Math.round(s.fr[i] - s.eu[i]); return { ok: g === 11, constat: 'avance de ' + g + ' points' }; } },
  { id: 'edu_c4', page: 'education', ou: 'titre du graphique Chômage des 15-24 ans', texte: 'Deux à trois fois plus qu\'en Allemagne',
    verifier: function (c) { var s = c.edu.S.yu, i = lastBoth(s.fr, s.de), q = s.fr[i] / s.de[i]; return { ok: q >= 2 && q <= 3, constat: 'rapport ' + fr(q, 1) }; } },
  { id: 'edu_depense', page: 'education', ou: 'titre « Ce que ça coûte »', texte: 'La France dépense plus que ses voisins, pour des résultats PISA inférieurs',
    verifier: function (c) { var s = c.edu.SP, i = lastBoth(s.fr, s.eu), m = c.edu.PI.m, im = m.fr.length - 1; return { ok: s.fr[i] > s.eu[i] && m.fr[im] < m.oe[im], constat: 'dépense ' + fr(s.fr[i], 1) + ' % contre ' + fr(s.eu[i], 1) + ' %, PISA maths ' + m.fr[im] + ' contre ' + m.oe[im] }; } },
  { id: 'edu_pisa', page: 'education', ou: 'titre « PISA »', texte: 'Vingt-cinq ans de recul, et sous la moyenne de l\'OCDE',
    verifier: function (c) { var m = c.edu.PI.m, r = c.edu.PI.r, im = m.fr.length - 1, ir = r.fr.length - 1; return { ok: m.fr[im] < m.fr[0] && r.fr[ir] < r.fr[0] && m.fr[im] < m.oe[im] && r.fr[ir] < r.oe[ir], constat: 'maths ' + m.fr[0] + ' → ' + m.fr[im] + ' (OCDE ' + m.oe[im] + '), lecture ' + r.fr[0] + ' → ' + r.fr[ir] + ' (OCDE ' + r.oe[ir] + ')' }; } },
  { id: 'edu_pisa_maths', page: 'education', ou: 'titre du graphique Mathématiques', texte: '−53 points depuis 2003',
    verifier: function (c) { var m = c.edu.PI.m, i = m.y.indexOf(2003), g = m.fr[m.fr.length - 1] - m.fr[i]; return { ok: g === -53, constat: 'évolution ' + g + ' points' }; } },
  { id: 'edu_pisa_lecture', page: 'education', ou: 'titre du graphique Lecture', texte: 'Le plus fort recul : −49 points depuis 2012',
    verifier: function (c) { var r = c.edu.PI.r, i = r.y.indexOf(2012), g = r.fr[r.fr.length - 1] - r.fr[i]; return { ok: g === -49, constat: 'évolution ' + g + ' points' }; } },
  { id: 'edu_pisa_sciences', page: 'education', ou: 'titre du graphique Sciences', texte: 'Le domaine qui résiste le mieux',
    verifier: function (c) { var gap = function (k) { var x = c.edu.PI[k], i = x.fr.length - 1; return x.fr[i] - x.oe[i]; }; return { ok: gap('s') >= gap('m') && gap('s') >= gap('r'), constat: 'écart à l\'OCDE : sciences ' + gap('s') + ', maths ' + gap('m') + ', lecture ' + gap('r') }; } },
  { id: 'edu_origine', page: 'education', ou: 'titre « Poids de l\'origine sociale »', texte: 'L\'école française corrige moins les inégalités que la moyenne de l\'OCDE',
    verifier: function (c) { var e = c.edu.EQ, i = e.fr.length - 1; return { ok: e.fr[i] > e.oe[i], constat: 'écart social ' + e.fr[i] + ' points contre ' + e.oe[i] + ' dans l\'OCDE' }; } },
  { id: 'edu_shanghai', page: 'education', ou: 'titre « Universités »', texte: 'Quatre universités dans le top 100 mondial, autant que l\'Allemagne',
    verifier: function (c) { var a = c.edu.ARWU, i = lastIdx(a.fr); return { ok: a.fr[i] === 4 && a.de[i] === 4, constat: 'France ' + a.fr[i] + ', Allemagne ' + a.de[i] + ' (' + a.y[i] + ')' }; } }
];
