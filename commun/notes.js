/* Règles de notation de Concret : la méthode affichée sur chaque page, sous forme de code.
   Un seul fichier, utilisé par les pages Finances et Éducation, par l'accueil (classement général)
   et par le contrôle de la mise à jour automatique (outils/controle.js). Les notes ne sont jamais
   saisies à la main : elles se recalculent à partir des séries de data.json.
   Aucune dépendance (ni d3, ni DOM) pour tourner aussi bien dans le navigateur que sous Node. */
(function (root) {
  var mean = function (a) { return a.length ? a.reduce(function (s, v) { return s + v; }, 0) / a.length : null; };
  var sum = function (a) { return a.reduce(function (s, v) { return s + v; }, 0); };

  // Phrases d'explication, à afficher là où le lecteur voit la donnée non comptée ou absente (règle de CLAUDE.md) :
  // ce qui se passe et pourquoi ça ne compte pas, en une phrase courte, sans jargon.
  var POURQUOI = {
    // qui : 'fr' (la France), 'ue' (la moyenne européenne), 'fr_ue' (les deux)
    methode: function (y, qui) {
      if (qui === 'serie') return 'Non compté : en ' + y + ', Eurostat passe d\'une table à une autre (chiffres jusqu\'en ' + (y - 1) + ', puis depuis ' + y + '), qu\'il ne raccorde pas : l\'évolution entre les deux n\'est pas comptée.';
      var sujet = qui === 'fr' ? 'la France a changé sa façon de mesurer ce chiffre' : qui === 'fr_ue' ? 'la France et la moyenne européenne ont changé leur façon de mesurer ce chiffre' : 'la moyenne européenne a changé sa façon de mesurer ce chiffre';
      return 'Non compté : en ' + y + ', ' + sujet + ', il n\'est pas comparable à ' + (y - 1) + '.';
    },
    pasPublie: function (y, source) { return 'Non compté : le chiffre ' + y + ' n\'est pas encore publié' + (source ? ' par ' + source : '') + '.'; },
    debut: function (y, source) { return 'Non compté : les séries ' + (source ? source + ' ' : '') + 'commencent en ' + y + ', il n\'y a pas d\'année précédente pour mesurer l\'évolution.'; },
    ueDebut: function (y, y0, source) { return 'Non compté : ' + (source || 'Eurostat') + ' ne publie la moyenne de l\'UE qu\'à partir de ' + y0 + (y === y0 ? ', il n\'y a pas d\'année précédente pour mesurer son évolution' : '') + '.'; },
    absent: function (y) { return 'Non compté : pas de chiffre disponible pour ' + y + '.'; },
    // Moyenne de l'UE calculée par Concret (outils/ue_calc.py) : il faut des pays qui font au moins 70 % de la population de l'UE.
    provisoire: function (y) { return 'Non compté : le chiffre ' + y + ' est provisoire (statistiques nationales) ; la moyenne de l\'UE de ' + y + ' se calcule quand Eurostat publie les chiffres des pays de l\'UE.'; },
    couverture: function (y) { return 'Non compté : les pays de l\'UE qui publient ce chiffre en ' + (y - 1) + ' et en ' + y + ' font moins de 70 % de sa population, sa moyenne ne peut pas être calculée.'; },
    egalite: function (y, voisin) { return 'Demi-point : en ' + y + ', la France et ' + voisin + ' ont évolué exactement autant.'; }
  };

  // Chaque année : 1 si la France fait mieux que ses voisins, 0 sinon, 0,5 en cas d'égalité.
  function match(fr, ref, lowerIsBetter) {
    if (fr == null || ref == null || isNaN(fr) || isNaN(ref)) return null;
    if (Math.abs(fr - ref) < 1e-9) return 0.5;
    return (lowerIsBetter ? fr < ref : fr > ref) ? 1 : 0;
  }

  // ===== Finances publiques : 8 critères, France face à la zone euro, depuis 1995 =====
  function finances(S) {
    var Y0 = 1995, D = S.D, X94 = S.X94, X95 = S.X95;
    var at = function (arr, y) { return arr[y - Y0]; };
    var pibAt = function (k, y) { return S.PIB[k][y - 1990]; };
    var x94 = function (k, y) { return X94[k][y - 1994]; };
    var chg = function (k, w, y) { var a = at(D[k][w], y), b = y > Y0 ? at(D[k][w], y - 1) : null; return a == null || b == null ? null : a - b; };
    var cov = function (w, y) { return X95['x' + w][y - 1995] / X95['m' + w][y - 1995]; };
    var lvl = function (k, w, y) { return at(D[k][w], y); };
    var CRIT = [
      { k: 'dette', l: 'Dette' }, { k: 'deficit', l: 'Déficit' }, { k: 'dep', l: 'Dépenses' }, { k: 'po', l: 'Prélèvements' },
      { k: 'pib', l: 'Croissance/hab.' }, { k: 'emploi', l: 'Emploi' }, { k: 'com', l: 'Commerce' }, { k: 'int', l: 'Coût de la dette' }
    ];
    // Ce que l'on compare, année par année : f / e = évolution France / moyenne de l'UE (Eurostat EU27_2020, Banque mondiale EUU ; la zone euro reste affichée comme repère), lf / le = niveau de l'année (pour le détail affiché).
    var CMP = {
      dette: function (y) { return { f: chg('dette', 'fr', y), e: chg('dette', 'eu', y), low: true, lf: lvl('dette', 'fr', y), le: lvl('dette', 'eu', y) }; },
      deficit: function (y) { return { f: chg('deficit', 'fr', y), e: chg('deficit', 'eu', y), low: false, lf: lvl('deficit', 'fr', y), le: lvl('deficit', 'eu', y) }; },
      dep: function (y) { return { f: chg('dep', 'fr', y), e: chg('dep', 'eu', y), low: true, lf: lvl('dep', 'fr', y), le: lvl('dep', 'eu', y) }; },
      po: function (y) { return { f: chg('po', 'fr', y), e: chg('po', 'eu', y), low: true, lf: lvl('po', 'fr', y), le: lvl('po', 'eu', y) }; },
      pib: function (y) { return { f: pibAt('fr', y) / pibAt('fr', y - 1), e: pibAt('eu', y) / pibAt('eu', y - 1), low: false }; },
      emploi: function (y) { return { f: x94('uFr', y) - x94('uFr', y - 1), e: x94('uEu', y) - x94('uEu', y - 1), low: true, lf: x94('uFr', y), le: x94('uEu', y) }; },
      com: function (y) { return y > 1995 ? { f: cov('Fr', y) - cov('Fr', y - 1), e: cov('Eu', y) - cov('Eu', y - 1), low: false, lf: 100 * cov('Fr', y), le: 100 * cov('Eu', y) } : null; },
      int: function (y) { return y > 1995 ? { f: X95.iFr[y - 1995] - X95.iFr[y - 1996], e: X95.iEu[y - 1995] - X95.iEu[y - 1996], low: true, lf: X95.iFr[y - 1995], le: X95.iEu[y - 1995] } : null; }
    };
    function evaluate(g) {
      g.w = {}; g.y = {}; g.r = {};
      CRIT.forEach(function (c) { g.w[c.k] = []; g.y[c.k] = []; });
      for (var y = g.y0; y <= g.y1; y++) {
        CRIT.forEach(function (c) {
          var d = CMP[c.k](y), m = d ? match(d.f, d.e, d.low) : null;
          if (m != null) g.w[c.k].push(m);
          if (!d) d = { f: null, e: null };
          d.y = y; d.pt = m; g.y[c.k].push(d);
        });
      }
      CRIT.forEach(function (c) { g.r[c.k] = mean(g.w[c.k]); });
      return g;
    }
    // Note sur 20 : moyenne des critères retenus (tous par défaut).
    function note(g, on) {
      var r = CRIT.filter(function (c) { return (!on || on[c.k]) && g.r[c.k] != null; }).map(function (c) { return g.r[c.k]; });
      return r.length ? 20 * mean(r) : null;
    }
    return { CRIT: CRIT, evaluate: evaluate, note: note, match: match, pibAt: pibAt, at: at };
  }

  // ===== Éducation : 6 critères, France face à l'UE (PISA : moyenne de l'UE calculée ; origine sociale : OCDE), depuis 2002 ; PISA compte triple =====
  function education(S, opts) {
    var LONG = !opts || opts.long !== false;
    var Y0 = 2002, C = S.S, PI = S.PI, WAVES = S.WAVES, EQ = S.EQ;
    var KEYS = ['el', 'ne', 'te', 'yu', 'pi', 'eq'], WT = { el: 1, ne: 1, te: 1, yu: 1, pi: 3, eq: 1 }, MIN_N = 6;
    var at = function (arr, y) { return arr[y - Y0]; };
    var pisaRef = function (c, i0, i1) { var e = c.ue_calc_ev && i1 === i0 + 1 ? c.ue_calc_ev[i1] : null; return e != null ? e : c.oe[i1] - c.oe[i0]; };
    function pisaGap(w0, w1) {
      var d = [];
      // Référence : la moyenne de l'UE calculée par outils/ue_calc.py (ue_calc_ev : évolution entre deux vagues, sur les pays
      // qui ont passé les deux) ; si elle manque (moins de 70 % de la population de l'UE), la moyenne de l'OCDE comme avant.
      ['m', 'r', 's'].forEach(function (k) { var c = PI[k], i0 = c.y.indexOf(w0), i1 = c.y.indexOf(w1); if (i0 >= 0 && i1 >= 0) d.push((c.fr[i1] - c.fr[i0]) - pisaRef(c, i0, i1)); });
      return d.length ? mean(d) : null;
    }
    function waveOf(ws, y) { for (var i = 1; i < ws.length; i++) if (y > ws[i - 1] && y <= ws[i]) return [ws[i - 1], ws[i]]; return null; }
    function waveRes(k, W) {
      if (k === 'pi') { var i = WAVES.indexOf(W); if (i < 1) return null; var g = pisaGap(WAVES[i - 1], W); return g == null ? null : Math.abs(g) < 0.5 ? 0.5 : g > 0 ? 1 : 0; }
      var j = EQ.y.indexOf(W); if (j < 1) return null; var e = (EQ.fr[j] - EQ.fr[j - 1]) - (EQ.oe[j] - EQ.oe[j - 1]); return e === 0 ? 0.5 : e < 0 ? 1 : 0;
    }
    function score(k, y) {
      if (y <= Y0) return null;
      if (LONG && (k === 'pi' || k === 'eq')) {
        // Temps long : chaque vague est répartie sur les dix années de scolarité des élèves testés (de 6 à 15 ans)
        var r = (k === 'pi' ? WAVES : EQ.y).filter(function (W) { return y >= W - 9 && y <= W; }).map(function (W) { return waveRes(k, W); }).filter(function (v) { return v != null; });
        return r.length ? mean(r) : null;
      }
      if (k === 'pi') { var w = waveOf(WAVES, y); if (!w) return null; var g = pisaGap(w[0], w[1]); return g == null ? null : Math.abs(g) < 0.5 ? 0.5 : g > 0 ? 1 : 0; }
      if (k === 'eq') { var v = waveOf(EQ.y, y); if (!v) return null; var i1 = EQ.y.indexOf(v[1]), e = (EQ.fr[i1] - EQ.fr[i1 - 1]) - (EQ.oe[i1] - EQ.oe[i1 - 1]); return e === 0 ? 0.5 : e < 0 ? 1 : 0; }
      var c = C[k];
      if (c.br.indexOf(y) >= 0) return null;
      var df = at(c.fr, y) - at(c.fr, y - 1), de = at(c.eu, y) - at(c.eu, y - 1);
      if (Math.abs(df - de) < 1e-9) return 0.5;
      return (c.low ? df < de : df > de) ? 1 : 0;
    }
    function evaluate(g) {
      g.w = {}; g.y = {};
      KEYS.forEach(function (k) { g.w[k] = []; g.y[k] = []; for (var y = g.y0; y <= g.y1; y++) { var m = score(k, y); if (m != null) g.w[k].push(m); g.y[k].push({ y: y, pt: m }); } });
      return g;
    }
    var count = function (g, on) { return sum(KEYS.filter(function (k) { return !on || on[k]; }).map(function (k) { return g.w[k].length; })); };
    // Note sur 20 : moyenne pondérée des critères mesurés (PISA × 3).
    function note(g, on) {
      var r = KEYS.filter(function (k) { return (!on || on[k]) && g.w[k].length; }).map(function (k) { return [mean(g.w[k]), WT[k]]; });
      var sw = sum(r.map(function (p) { return p[1]; }));
      return sw ? 20 * sum(r.map(function (p) { return p[0] * p[1]; })) / sw : null;
    }
    return { KEYS: KEYS, WT: WT, MIN_N: MIN_N, Y0: Y0, evaluate: evaluate, note: note, count: count, score: score, waveRes: waveRes, waveOf: waveOf, pisaGap: pisaGap, pisaRef: pisaRef, at: at };
  }

  // ===== Santé : cinq questions, une note par question ; la note de la page est la moyenne des cinq =====
  // S.THEMES : [{ k, q (la question), court, crit: [clés de S.C] }]. Chaque critère compare la France à la moyenne de l'UE :
  // celle de la source ('ue'), ou, si la source n'en publie pas, celle calculée par outils/ue_calc.py (champ ref 'ue_calc' ;
  // son évolution, ue_calc_ev, porte sur les pays qui publient les deux années). Jamais un pays seul. Règles (S.C[k].regle) :
  //  - sinon : chaque année, 1 point si la France évolue mieux que la référence, 0 sinon, ½ en cas d'égalité ;
  //  - 'long' : résultats de santé (espérance de vie, mortalité) : les effets d'une politique de santé mettent des années
  //    à se voir, l'année t vaut donc la moyenne des points d'évolution de t à t+4 (années déjà publiées seulement) ;
  //  - 'ecart' : équité, 1 point si l'écart français est plus faible que celui de la référence ou se réduit plus vite ;
  //  - 'composite' : un programme entier (vaccins, dépistages) : le point de l'année est la part des éléments où la France
  //    progresse mieux que sa référence (chaque élément a la sienne) ;
  //  - 'niveau' : par édition d'une étude (W.A.I.T.), 1 point si la France fait mieux que la référence l'année jugée ;
  //  - 'propre' : déficit de l'Assurance maladie, jugé sur la France seule faute de comparaison possible : 1 point si
  //    équilibre ou excédent, ½ si le déficit se réduit d'au moins 0,1 point de PIB, 0 s'il se creuse ou reste stable.
  function sante(S) {
    // Note fragile en dessous d'une année complète de comparaisons (un point par indicateur), comme en Éducation.
    var C = S.C, THEMES = S.THEMES, KEYS = Object.keys(C), WT = {}, MIN_N = KEYS.length, SEUIL_STABLE = 0.1, LONG = 5;
    KEYS.forEach(function (k) { WT[k] = C[k].poids || 1; });
    var val = function (c, w, y) { var i = c.y.indexOf(y); return i < 0 || !c[w] ? null : c[w][i]; };
    var ref = function (c) { return c.ref || 'ue'; };
    // Évolution de la référence entre y - 1 et y.
    var refEv = function (c, y) {
      if (ref(c) === 'ue_calc' && c.ue_calc_ev) return val(c, 'ue_calc_ev', y);
      var e = val(c, ref(c), y), f = val(c, ref(c), y - 1);
      return e == null || f == null ? null : e - f;
    };
    function evol(c, y) {
      var a = val(c, 'fr', y), b = val(c, 'fr', y - 1), d = refEv(c, y);
      if ((c.br || {})[y]) return null;
      return a == null || b == null || d == null ? null : match(a - b, d, c.low);
    }
    // Années d'évolution prises en compte pour l'année y (règle 'long').
    var fenetre = function (y) { var a = []; for (var t = y; t < y + LONG; t++) a.push(t); return a; };
    function score(k, y) {
      var c = C[k];
      if (c.regle === 'long') { var pts = fenetre(y).map(function (t) { return evol(c, t); }).filter(function (x) { return x != null; }); return pts.length ? mean(pts) : null; }
      if ((c.br || {})[y]) return null;
      if (c.regle === 'composite') { var q = Object.keys(c.sous).map(function (j) { return evol(c.sous[j], y); }).filter(function (x) { return x != null; }); return q.length ? mean(q) : null; }
      if (c.regle === 'niveau') return c.y.indexOf(y) < 0 ? null : match(val(c, 'fr', y), val(c, ref(c), y), c.low);
      if (c.regle === 'propre') { var v = val(c, 'fr', y), p = val(c, 'fr', y - 1); if (v == null) return null; if (v >= 0) return 1; if (p == null) return null; return v - p >= SEUIL_STABLE - 1e-9 ? 0.5 : 0; }
      if (c.regle === 'ecart') {
        var a = val(c, 'fr', y), e = val(c, ref(c), y), pa = val(c, 'fr', y - 1), pe = val(c, ref(c), y - 1);
        if (a == null || e == null) return null;
        if (a < e - 1e-9) return 1;
        if (pa != null && pe != null && (a - pa) < (e - pe) - 1e-9) return 1;
        return Math.abs(a - e) < 1e-9 ? 0.5 : 0;
      }
      return evol(c, y);
    }
    function evaluate(g) {
      g.w = {}; g.y = {};
      KEYS.forEach(function (k) { g.w[k] = []; g.y[k] = []; for (var y = g.y0; y <= g.y1; y++) { var m = score(k, y); if (m != null) g.w[k].push(m); g.y[k].push({ y: y, pt: m }); } });
      return g;
    }
    var themeOf = function (t) { return typeof t === 'string' ? THEMES.filter(function (x) { return x.k === t; })[0] : t; };
    var count = function (g, t) { var ks = t ? themeOf(t).crit : KEYS; return sum(ks.map(function (k) { return g.w[k].length; })); };
    // Note d'une question : part des points marqués, critères pondérés (le déficit de la Sécu compte triple).
    function noteTheme(g, t) {
      var r = themeOf(t).crit.filter(function (k) { return g.w[k].length; }).map(function (k) { return [mean(g.w[k]), WT[k]]; });
      var sw = sum(r.map(function (p) { return p[1]; }));
      return sw ? 20 * sum(r.map(function (p) { return p[0] * p[1]; })) / sw : null;
    }
    // Note de la page : moyenne des questions notées pour ce mandat.
    function note(g) {
      var n = THEMES.map(function (t) { return noteTheme(g, t); }).filter(function (v) { return v != null; });
      return n.length ? mean(n) : null;
    }
    // Pourquoi une année n'est pas comptée pour un critère (phrase affichée sous le détail).
    function raisonSerie(c, y) {
      var first = c.y[0], last = c.y[c.y.length - 1], r = ref(c), nomRef = r === 'ue_calc' ? 'la moyenne de l\'UE calculée par Concret' : 'la moyenne de l\'UE';
      if ((c.br || {})[y]) return POURQUOI.methode(y, c.br[y]);
      if ((c.manque || {})[y]) return c.manque[y];
      if (y > last) return POURQUOI.pasPublie(y);
      if (y < first) return 'Non compté : pas de chiffre avant ' + first + '.';
      if (y === first) return POURQUOI.debut(first);
      if (val(c, 'fr', y) == null || val(c, 'fr', y - 1) == null) return POURQUOI.absent(val(c, 'fr', y) == null ? y : y - 1);
      if (r === 'ue_calc' && refEv(c, y) == null) return (c.prov || {})[y] ? POURQUOI.provisoire(y) : POURQUOI.couverture(y);
      if (val(c, r, y) == null || val(c, r, y - 1) == null) return 'Non compté : pas de chiffre pour ' + nomRef + ' en ' + (val(c, r, y) == null ? y : y - 1) + '.';
      return POURQUOI.absent(y);
    }
    function raison(k, y) {
      var c = C[k];
      if (c.regle === 'composite') return 'Non compté : aucun élément du critère n\'a de chiffre comparable pour ' + y + ' et l\'année précédente.';
      if (c.regle === 'niveau') return y < c.y[0] ? 'Non compté : l\'étude ne couvre pas encore ' + y + ' (première année jugée : ' + c.y[0] + ').' : POURQUOI.pasPublie(y);
      if (c.regle === 'long') return y > c.y[c.y.length - 1] ? POURQUOI.pasPublie(y) : 'Non compté : aucune évolution comparable publiée entre ' + y + ' et ' + (y + LONG - 1) + '.';
      return raisonSerie(c, y);
    }
    return { KEYS: KEYS, THEMES: THEMES, WT: WT, MIN_N: MIN_N, SEUIL_STABLE: SEUIL_STABLE, LONG: LONG, evaluate: evaluate, note: note, noteTheme: noteTheme, count: count, score: score, evol: evol, fenetre: fenetre, raison: raison, raisonSerie: raisonSerie, val: val, ref: ref, refEv: refEv };
  }

  // ===== Classement général de l'accueil : moyenne des notes par mission, réglages par défaut de chaque page =====
  var MISSIONS = [
    { k: 'f', l: 'Finances', url: '/finances/#bulletin', debut: 'les séries des finances publiques commencent en 1995', calc: function (S) { return finances(S.finances); }, ser: 'finances' },
    { k: 'e', l: 'Éducation', url: '/education/#bulletin', debut: 'les chiffres de l\'éducation commencent en 2002, la première évolution mesurable est celle de 2003', calc: function (S) { return education(S.education, { long: true }); }, ser: 'education' },
    { k: 's', l: 'Santé', url: '/sante/#bulletin', debut: 'la plupart des chiffres européens de la santé commencent entre 2000 et 2011', calc: function (S) { return sante(S.sante); }, ser: 'sante' },
    { k: 'j', l: 'Sécurité et justice', url: '/securite/#bulletin', debut: 'les chiffres européens de la délinquance commencent en 1995', calc: function (S) { return securite(S.securite); }, ser: 'securite' }
  ];
  var r1 = function (v) { return v == null ? null : Math.round(v * 10) / 10; };
  function classement(series) {
    var out = { pres: [], gov: [] };
    ['pres', 'gov'].forEach(function (kind) {
      var rows = {}, order = [];
      MISSIONS.forEach(function (m) {
        if (!series[m.ser]) return;
        var calc = m.calc(series), list = series[m.ser][kind === 'pres' ? 'PRES' : 'GOVS'];
        list.forEach(function (g0) {
          var g = calc.evaluate({ n: g0.n, y0: g0.y0, y1: g0.y1 });
          if (!rows[g0.n]) { rows[g0.n] = { n: g0.n, y0: g0.y0, y1: g0.y1 }; order.push(g0.n); }
          var r = rows[g0.n]; r.y0 = Math.min(r.y0, g0.y0); r.y1 = Math.max(r.y1, g0.y1);
          r[m.k] = r1(calc.note(g));
          // Note provisoire : moins d'une année complète de comparaisons (mandat court, ou chiffres pas encore publiés).
          var nb = calc.count ? calc.count(g) : null;
          r[m.k + '_n'] = nb; r[m.k + '_prov'] = r[m.k] != null && nb != null && calc.MIN_N != null && nb < calc.MIN_N;
          var ys = []; Object.keys(g.y).forEach(function (k) { g.y[k].forEach(function (d) { if (d.pt != null) ys.push(d.y); }); });
          r[m.k + '_ans'] = ys.length ? [Math.min.apply(null, ys), Math.max.apply(null, ys)] : null;
        });
      });
      out[kind] = order.map(function (n) {
        var r = rows[n], v = MISSIONS.map(function (m) { return r[m.k]; }).filter(function (x) { return x != null; });
        r.m = v.length ? r1(sum(v) / v.length) : null; r.k = v.length; return r;
      }).sort(function (a, b) { return b.m - a.m; });
    });
    return out;
  }

  // Sécurité et justice : même méthode que la Santé (thèmes, évolution comparée à la moyenne de l'UE, résultats jugés sur le long terme).
  var securite = function (S) { return sante(S); };
  var api = { match: match, POURQUOI: POURQUOI, finances: finances, education: education, sante: sante, securite: securite, classement: classement, MISSIONS: MISSIONS.map(function (m) { return { k: m.k, l: m.l, url: m.url, debut: m.debut }; }) };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.ConcretNotes = api;
})(this);
