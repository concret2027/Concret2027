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
      var sujet = qui === 'fr' ? 'la France a changé sa façon de mesurer ce chiffre' : qui === 'fr_ue' ? 'la France et la moyenne européenne ont changé leur façon de mesurer ce chiffre' : 'la moyenne européenne a changé sa façon de mesurer ce chiffre';
      return 'Non compté : en ' + y + ', ' + sujet + ', il n\'est pas comparable à ' + (y - 1) + '.';
    },
    pasPublie: function (y, source) { return 'Non compté : le chiffre ' + y + ' n\'est pas encore publié' + (source ? ' par ' + source : '') + '.'; },
    debut: function (y, source) { return 'Non compté : les séries ' + (source ? source + ' ' : '') + 'commencent en ' + y + ', il n\'y a pas d\'année précédente pour mesurer l\'évolution.'; },
    absent: function (y) { return 'Non compté : pas de chiffre disponible pour ' + y + '.'; },
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
    // Ce que l'on compare, année par année : f / e = évolution France / zone euro, lf / le = niveau de l'année (pour le détail affiché).
    var CMP = {
      dette: function (y) { return { f: chg('dette', 'fr', y), e: chg('dette', 'ea', y), low: true, lf: lvl('dette', 'fr', y), le: lvl('dette', 'ea', y) }; },
      deficit: function (y) { return { f: chg('deficit', 'fr', y), e: chg('deficit', 'ea', y), low: false, lf: lvl('deficit', 'fr', y), le: lvl('deficit', 'ea', y) }; },
      dep: function (y) { return { f: chg('dep', 'fr', y), e: chg('dep', 'ea', y), low: true, lf: lvl('dep', 'fr', y), le: lvl('dep', 'ea', y) }; },
      po: function (y) { return { f: chg('po', 'fr', y), e: chg('po', 'ea', y), low: true, lf: lvl('po', 'fr', y), le: lvl('po', 'ea', y) }; },
      pib: function (y) { return { f: pibAt('fr', y) / pibAt('fr', y - 1), e: pibAt('ea', y) / pibAt('ea', y - 1), low: false }; },
      emploi: function (y) { return { f: x94('uFr', y) - x94('uFr', y - 1), e: x94('uEa', y) - x94('uEa', y - 1), low: true, lf: x94('uFr', y), le: x94('uEa', y) }; },
      com: function (y) { return y > 1995 ? { f: cov('Fr', y) - cov('Fr', y - 1), e: cov('Ea', y) - cov('Ea', y - 1), low: false, lf: 100 * cov('Fr', y), le: 100 * cov('Ea', y) } : null; },
      int: function (y) { return y > 1995 ? { f: X95.iFr[y - 1995] - X95.iFr[y - 1996], e: X95.iEa[y - 1995] - X95.iEa[y - 1996], low: true, lf: X95.iFr[y - 1995], le: X95.iEa[y - 1995] } : null; }
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

  // ===== Éducation : 6 critères, France face à l'UE (OCDE pour PISA), depuis 2002 ; PISA compte triple =====
  function education(S, opts) {
    var LONG = !opts || opts.long !== false;
    var Y0 = 2002, C = S.S, PI = S.PI, WAVES = S.WAVES, EQ = S.EQ;
    var KEYS = ['el', 'ne', 'te', 'yu', 'pi', 'eq'], WT = { el: 1, ne: 1, te: 1, yu: 1, pi: 3, eq: 1 }, MIN_N = 6;
    var at = function (arr, y) { return arr[y - Y0]; };
    function pisaGap(w0, w1) {
      var d = [];
      ['m', 'r', 's'].forEach(function (k) { var c = PI[k], i0 = c.y.indexOf(w0), i1 = c.y.indexOf(w1); if (i0 >= 0 && i1 >= 0) d.push((c.fr[i1] - c.fr[i0]) - (c.oe[i1] - c.oe[i0])); });
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
    return { KEYS: KEYS, WT: WT, MIN_N: MIN_N, Y0: Y0, evaluate: evaluate, note: note, count: count, score: score, waveRes: waveRes, waveOf: waveOf, pisaGap: pisaGap, at: at };
  }

  // ===== Santé : 10 critères, France face à l'UE ; déficit de la Sécu jugé sur lui-même (poids 3) =====
  // Chaque critère de S.C a ses propres années (y) et valeurs (fr, ue, de, us), et une règle :
  //  - 'propre' : 1 point si équilibre ou excédent, ½ si le déficit se réduit, 0 s'il se creuse ou stagne ;
  //  - 'niveau' : par édition (W.A.I.T.), 1 point si la France fait mieux que la moyenne UE cette année-là ;
  //  - 'vagues' : enquête tous les 5-6 ans (tabac, EHIS), l'évolution entre deux vagues compte pour les années qui les séparent ;
  //  - sinon : chaque année, 1 point si la France évolue mieux que l'UE (comme Éducation).
  function sante(S) {
    var C = S.C, KEYS = Object.keys(C), WT = {}, MIN_N = 6;
    KEYS.forEach(function (k) { WT[k] = C[k].poids || 1; });
    var val = function (c, w, y) { var i = c.y.indexOf(y); return i < 0 || !c[w] ? null : c[w][i]; };
    function score(k, y) {
      var c = C[k], i = c.y.indexOf(y);
      if ((c.br || {})[y]) return null;
      if (c.regle === 'propre') { var v = val(c, 'fr', y), p = val(c, 'fr', y - 1); if (v == null) return null; if (v >= 0) return 1; if (p == null) return null; return v > p ? 0.5 : 0; }
      if (c.regle === 'niveau') return i < 0 ? null : match(val(c, 'fr', y), val(c, 'ue', y), c.low);
      if (c.regle === 'vagues') {
        for (var j = 1; j < c.y.length; j++) if (y > c.y[j - 1] && y <= c.y[j]) return match(c.fr[j] - c.fr[j - 1], c.ue[j] - c.ue[j - 1], c.low);
        return null;
      }
      var a = val(c, 'fr', y), b = val(c, 'fr', y - 1), e = val(c, 'ue', y), f = val(c, 'ue', y - 1);
      return a == null || b == null || e == null || f == null ? null : match(a - b, e - f, c.low);
    }
    function evaluate(g) {
      g.w = {}; g.y = {};
      KEYS.forEach(function (k) { g.w[k] = []; g.y[k] = []; for (var y = g.y0; y <= g.y1; y++) { var m = score(k, y); if (m != null) g.w[k].push(m); g.y[k].push({ y: y, pt: m }); } });
      return g;
    }
    var count = function (g, on) { return sum(KEYS.filter(function (k) { return !on || on[k]; }).map(function (k) { return g.w[k].length; })); };
    function note(g, on) {
      var r = KEYS.filter(function (k) { return (!on || on[k]) && g.w[k].length; }).map(function (k) { return [mean(g.w[k]), WT[k]]; });
      var sw = sum(r.map(function (p) { return p[1]; }));
      return sw ? 20 * sum(r.map(function (p) { return p[0] * p[1]; })) / sw : null;
    }
    // Pourquoi une année n'est pas comptée pour un critère (phrase affichée sous le détail).
    function raison(k, y) {
      var c = C[k], first = c.y[0], last = c.y[c.y.length - 1];
      if ((c.br || {})[y]) return POURQUOI.methode(y, c.br[y]);
      if (c.regle === 'niveau') return y > last ? POURQUOI.pasPublie(y) : y < first ? 'Non compté : l\'étude n\'existait pas encore en ' + y + '.' : 'Non compté : pas d\'édition de l\'étude pour ' + y + '.';
      if (c.regle === 'vagues') return y > last ? 'Non compté : la prochaine vague de l\'enquête, après ' + last + ', n\'est pas encore publiée.' : 'Non compté : l\'enquête a commencé en ' + first + ', il n\'y a pas de vague précédente.';
      if (y > last) return POURQUOI.pasPublie(y);
      if (y <= first) return POURQUOI.debut(first);
      return POURQUOI.absent(y);
    }
    return { KEYS: KEYS, WT: WT, MIN_N: MIN_N, evaluate: evaluate, note: note, count: count, score: score, raison: raison, val: val };
  }

  // ===== Classement général de l'accueil : moyenne des notes par mission, réglages par défaut de chaque page =====
  var MISSIONS = [
    { k: 'f', l: 'Finances', url: '/finances/#bulletin', debut: 'les séries des finances publiques commencent en 1995', calc: function (S) { return finances(S.finances); }, ser: 'finances' },
    { k: 'e', l: 'Éducation', url: '/education/#bulletin', debut: 'les chiffres de l\'éducation commencent en 2002, la première évolution mesurable est celle de 2003', calc: function (S) { return education(S.education, { long: true }); }, ser: 'education' }
  ];
  var r1 = function (v) { return v == null ? null : Math.round(v * 10) / 10; };
  function classement(series) {
    var out = { pres: [], gov: [] };
    ['pres', 'gov'].forEach(function (kind) {
      var rows = {}, order = [];
      MISSIONS.forEach(function (m) {
        var calc = m.calc(series), list = series[m.ser][kind === 'pres' ? 'PRES' : 'GOVS'];
        list.forEach(function (g0) {
          var g = calc.evaluate({ n: g0.n, y0: g0.y0, y1: g0.y1 });
          if (!rows[g0.n]) { rows[g0.n] = { n: g0.n, y0: g0.y0, y1: g0.y1 }; order.push(g0.n); }
          var r = rows[g0.n]; r.y0 = Math.min(r.y0, g0.y0); r.y1 = Math.max(r.y1, g0.y1);
          r[m.k] = r1(calc.note(g));
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

  var api = { match: match, POURQUOI: POURQUOI, finances: finances, education: education, sante: sante, classement: classement, MISSIONS: MISSIONS.map(function (m) { return { k: m.k, l: m.l, url: m.url, debut: m.debut }; }) };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.ConcretNotes = api;
})(this);
