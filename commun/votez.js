/* Votez les lois : les votes importants de l'Assemblée nationale depuis le début de la législature (donnees/votes.json,
   écrit chaque jour par outils/parlement.py à partir des données ouvertes de l'Assemblée), à voter à son tour.
   Une question par texte (son dernier vote sur l'ensemble, sinon sur une partie, sinon la motion de rejet), et une par
   motion de censure, vote de confiance ou déclaration du Gouvernement suivie d'un vote.
   Le résultat (accord avec chaque groupe de députés) est calculé dans le navigateur. Les votes restent sur l'appareil
   (localStorage « concret-votez ») : rien n'est envoyé, ni au compteur du quiz ni ailleurs.
   Utilisé par la page /votez/ et par le bloc « Votez les lois » du quiz. */
(function () {
  var CLE = 'concret-votez', CLE_AV = 'concret-votez-avant', MIN = 5, SERIE = 10;
  var MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
  var dateFr = function (d) { var p = d.split('-'); return (+p[2] === 1 ? '1er' : +p[2]) + ' ' + MOIS[p[1] - 1] + ' ' + p[0]; };
  var moisFr = function (d) { var p = d.split('-'); return MOIS[p[1] - 1] + ' ' + p[0]; };
  // Espace insécable avant « : ; ? ! », dans les nombres et avant € et % (pas de ponctuation ni de chiffre seul en début de ligne).
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }).replace(/ ([:;?!])/g, '\u00a0$1').replace(/(\d) (?=\d{3}\b)/g, '$1\u202f').replace(/(\d) (€|%)/g, '$1\u00a0$2'); };
  var nf = function (n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' '); };
  var cap = function (s) { return s.charAt(0).toUpperCase() + s.slice(1); };
  // Les étapes d'un texte, dites sans jargon.
  var STADE = {
    'première lecture': 'premier examen à l\'Assemblée',
    'deuxième lecture': 'deuxième examen à l\'Assemblée',
    'nouvelle lecture': 'nouvel examen, après un désaccord avec le Sénat',
    'lecture définitive': 'dernier vote : l\'Assemblée a le dernier mot',
    'texte de la commission mixte paritaire': 'texte de compromis entre députés et sénateurs'
  };
  var CHOIX = { pour: 'Pour', contre: 'Contre', abstention: 'Abstention' };

  var css = '.vz{display:grid;gap:10px}' +
    '.vz-titre{font-family:var(--serif);font-weight:500;font-size:21px;line-height:1.25;margin:0;text-wrap:balance}' +
    '.vz-expl{margin:0;font-size:15px;line-height:1.5}' +
    '.vz-lu{margin:-4px 0 0;font-size:12px;color:var(--muted)}.vz-lu a{color:var(--muted)}' +
    '.vz-q{margin:4px 0 0;font-size:17px;font-weight:700}' +
    '.vz-aide{margin:-4px 0 0;font-size:13.5px;color:var(--muted)}' +
    '.vz-choix{display:grid;grid-template-columns:repeat(var(--n,3),minmax(0,1fr));gap:8px}' +
    '.vz-choix button{font:inherit;font-weight:700;font-size:15.5px;min-height:52px;border-radius:12px;border:1.5px solid var(--fg);background:var(--panel);color:var(--fg);cursor:pointer}' +
    '.vz-choix button[aria-pressed="true"]{background:var(--fg);color:var(--bg)}' +
    '.vz-choix button:disabled{cursor:default}.vz-choix button:disabled:not([aria-pressed="true"]){opacity:.45}' +
    '.vz-choix button:focus-visible,.vz-passe:focus-visible,.vz-suite:focus-visible{outline:2px solid var(--fr);outline-offset:2px}' +
    '.vz-passe{font:inherit;font-size:13px;color:var(--muted);background:none;border:0;padding:4px 0;cursor:pointer;text-decoration:underline;text-underline-offset:3px;justify-self:start}' +
    '.vz-off{font-size:12.5px;color:var(--muted)}.vz-off summary{cursor:pointer;font-weight:600}.vz-off p{margin:6px 0 0}.vz-off a{color:var(--fr)}' +
    '.vz-rev{display:grid;gap:10px;padding:12px;border-radius:12px;background:var(--band);border:1px solid var(--line)}' +
    '.vz-sort{margin:0;font-size:15px}.vz-sort b{font-weight:700}.vz-sort small{display:block;color:var(--muted);font-size:13px;font-variant-numeric:tabular-nums}' +
    '.vz-gr{display:grid;grid-template-columns:6.2em minmax(0,1fr);gap:6px 10px;align-items:start;font-size:13px}' +
    '.vz-gr>b{font-weight:700;padding-top:4px}' +
    '.vz-gr>div{display:flex;flex-wrap:wrap;gap:5px}' +
    '.vz-gr span{padding:3px 8px;border-radius:999px;border:1px solid var(--line);background:var(--panel);line-height:1.3}' +
    '.vz-gr span.moi{border-color:var(--fr);box-shadow:inset 0 0 0 1px var(--fr);font-weight:600}' +
    '.vz-gr i{font-style:normal;color:var(--muted)}' +
    '.vz-comme{margin:0;font-size:13.5px}' +
    '.vz-suite{font:inherit;font-weight:700;font-size:15px;min-height:48px;padding:0 20px;border-radius:999px;border:0;background:var(--fr);color:#fff;cursor:pointer;justify-self:start}' +
    '.vz-bars{list-style:none;margin:0;padding:0;display:grid;gap:8px}' +
    '.vz-bars li{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:3px 10px;font-size:14px;align-items:baseline}' +
    '.vz-bars .n{font-weight:600;line-height:1.3}.vz-bars .v{font-weight:700;font-variant-numeric:tabular-nums}' +
    '.vz-bars .b{grid-column:1/-1;height:8px;border-radius:4px;background:var(--line);overflow:hidden}.vz-bars .b i{display:block;height:100%;background:var(--fr);border-radius:4px}' +
    '.vz-bars .v small{font-weight:400;font-size:12px;color:var(--muted);margin-right:6px}' +
    '.vz-bars li.top .n{color:var(--fr)}';

  var donnees = null;
  function lireMes() { try { var o = JSON.parse(localStorage.getItem(CLE) || '{}'); return o && typeof o === 'object' ? o : {}; } catch (e) { return {}; } }
  function ecrireMes(o) { try { localStorage.setItem(CLE, JSON.stringify(o)); } catch (e) {} }
  // Votes faits avant le vote de l'Assemblée : { 'dossier:texte' ou 'dossier:partie:première': { c: choix, le: date } }.
  function lireAv() { try { var o = JSON.parse(localStorage.getItem(CLE_AV) || '{}'); return o && typeof o === 'object' ? o : {}; } catch (e) { return {}; } }
  function ecrireAv(o) { try { localStorage.setItem(CLE_AV, JSON.stringify(o)); } catch (e) {} }
  var aujourdhui = function () { var d = new Date(); return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2); };
  var nomPartie = function (t) { var m = t.match(/^la (première|deuxième|seconde) partie/i); return m ? m[1].toLowerCase() : ''; };

  // Le texte visé par un vote : « projet de loi … » ou « proposition de loi … », sans l'étape entre parenthèses.
  function sujet(t) {
    var i = t.search(/(projet|proposition) de (loi|résolution)/i); if (i < 0) return '';
    return t.slice(i).replace(/\s*\(([^()]*)\)\s*$/, '').trim();
  }
  function stade(t) { var m = t.match(/\(([^()]*)\)\s*$/); return m ? m[1] : ''; }
  // Position d'un groupe : celle de la majorité de ses députés qui ont voté (publiée par l'Assemblée). Pour une censure,
  // seuls les votes pour sont comptés : le groupe est compté pour si la majorité de ses membres l'a votée, contre sinon.
  function position(v, c) {
    var x = v.g[c]; if (!x) return null;
    if (v.k === 'censure') return x[1] > x[4] / 2 ? 'pour' : 'contre';
    return CHOIX[x[0]] ? x[0] : null;
  }
  function pm(J, d) { var n = ''; (J.PM || []).forEach(function (p) { if (p.d < d) n = p.n; }); return n; }

  function question(v, J) {
    var q = { id: String(v.n), v: v, k: v.k, d: v.d, choix: ['pour', 'contre', 'abstention'], pos: {} };
    var s = sujet(v.t), st = stade(v.t), par = (v.t.match(/\bpar ((M\.|Mme|MM\.|Mmes) .+?)(,? (du|de la|de l'|des) (projet|proposition)|$)/) || [])[1];
    var gouv = pm(J, v.d), dg = gouv ? 'le Gouvernement de ' + gouv : 'le Gouvernement';
    if (v.k === 'texte' || v.k === 'partie') {
      q.type = v.k === 'texte' ? 'Vote sur l\'ensemble du texte' : 'Vote sur une partie du texte';
      q.titre = v.dl || cap(s); q.stade = STADE[st] ? cap(STADE[st]) + '.' : (st ? cap(st) + '.' : '');
      q.q = v.k === 'texte' ? 'Adopter ce texte ?' : 'Adopter cette partie du texte ?';
      if (v.k === 'partie') q.aide = 'Le vote porte sur ' + v.t.replace(/\s*\([^()]*\)\s*$/, '') + '.';
      q.sort = (v.k === 'texte' ? 'Texte ' : 'Partie ') + (v.s === 'adopté' ? 'adopté' : 'rejeté') + (v.k === 'partie' ? 'e' : '');
    } else if (v.k === 'rejet') {
      q.type = 'Motion de rejet préalable';
      q.titre = v.dl || cap(s); q.stade = STADE[st] ? cap(STADE[st]) + '.' : '';
      q.q = 'Rejeter ce texte sans l\'examiner ?';
      q.aide = 'Voter pour la motion, c\'est rejeter le texte avant tout débat.' + (par ? ' Motion déposée par ' + par + '.' : '');
      q.sort = v.s === 'adopté' ? 'Motion adoptée : le texte est rejeté' : 'Motion rejetée : le texte est examiné';
    } else if (v.k === 'censure') {
      q.type = 'Motion de censure';
      q.titre = 'Censure contre ' + dg; q.choix = ['pour', 'contre'];
      q.q = 'Renverser le Gouvernement ?';
      q.aide = (/alinéa 3/.test(v.t) ? 'Le Gouvernement avait engagé sa responsabilité sur un texte (article 49, alinéa 3) : si la motion est rejetée, le texte est adopté sans vote. ' : '') +
        'Pour renverser le Gouvernement, la motion doit réunir la majorité absolue des députés (' + nf(v.req) + ' voix) ; seuls les votes pour sont comptés.' + (par ? ' Motion déposée par ' + par + '.' : '');
      q.sort = v.s === 'adopté' ? 'Motion adoptée : le Gouvernement est renversé' : 'Motion rejetée : le Gouvernement reste en place';
    } else if (v.k === 'confiance') {
      q.type = 'Vote de confiance';
      q.titre = 'Confiance à ' + dg;
      q.q = 'Accorder la confiance au Gouvernement ?';
      q.sort = v.s === 'adopté' ? 'Confiance accordée' : 'Confiance refusée : le Gouvernement doit démissionner';
    } else {
      q.type = 'Déclaration du Gouvernement suivie d\'un vote';
      q.titre = cap(v.t.replace(/\s*\([^()]*\)\s*$/, ''));
      q.q = 'Approuver cette déclaration ?';
      q.sort = 'Déclaration ' + (v.s === 'adopté' ? 'approuvée' : 'rejetée');
    }
    q.compte = v.k === 'censure' ? nf(v.p) + ' voix pour la censure ; il en fallait ' + nf(v.req) + '.'
      : nf(v.p) + ' pour, ' + nf(v.c) + ' contre, ' + nf(v.a) + (v.a > 1 ? ' abstentions.' : ' abstention.');
    q.majorite = v.s === 'adopté' ? 'pour' : 'contre';
    // Le même texte dans l'ordre du jour (votes à venir) : dossier, et partie du budget s'il y a lieu.
    if (v.dos && (v.k === 'texte' || v.k === 'partie')) q.cav = v.dos + ':' + (v.k === 'partie' ? 'partie:' + nomPartie(v.t) : 'texte');
    J.GROUPES.forEach(function (g) { if (g.c === 'NI') return; var p = position(v, g.c); if (p) q.pos[g.c] = p; });
    // Partage de l'Assemblée : sièges des groupes pour et contre les plus proches (sert à choisir les dix premiers votes).
    var S = { pour: 0, contre: 0, abstention: 0 };
    Object.keys(q.pos).forEach(function (c) { S[q.pos[c]] += v.g[c][4]; });
    var tot = S.pour + S.contre + S.abstention; q.partage = tot ? Math.min(S.pour, S.contre) / tot : 0;
    return q;
  }

  function construire(J, X) {
    var rang = { texte: 3, partie: 2, rejet: 1 }, par = {}, Q = [], dos = {};
    // Un même texte : même dossier de l'Assemblée, sinon même intitulé (le dossier n'est pas indiqué pour les votes les plus anciens).
    var cle = function (v) { return sujet(v.t).toLowerCase().replace(/[’']/g, '\'').replace(/\s+/g, ' '); };
    J.VOTES.forEach(function (v) { if (rang[v.k] && v.dos) dos[cle(v)] = v.dos; });
    J.VOTES.forEach(function (v) {
      if (rang[v.k]) {
        if (!sujet(v.t)) return;
        // Chaque partie d'un budget est une question à part.
        var k = (v.dos || dos[cle(v)] || cle(v)) + (v.k === 'partie' ? ':partie:' + nomPartie(v.t) : ''), x = par[k];
        if (!x || rang[v.k] > rang[x.k] || (rang[v.k] === rang[x.k] && (v.d > x.d || (v.d === x.d && v.n > x.n)))) par[k] = v;
      } else Q.push(v);
    });
    Object.keys(par).forEach(function (k) { Q.push(par[k]); });
    Q = Q.map(function (v) { return question(v, J); }).sort(function (a, b) { return a.d < b.d ? 1 : a.d > b.d ? -1 : b.v.n - a.v.n; });
    // Un vote n'est proposé qu'avec son explication, écrite à partir du texte voté et validée (donnees/votez_explications.json).
    var tous = Q.length;
    var ok = function (x) { return x && x.valide && x.e && x.url; };
    Q = Q.filter(function (q) {
      var x = X && X[q.id], xa = q.cav && X && X['avenir:' + q.cav];
      if (ok(x)) { q.expl = x; return true; }
      // Explication écrite avant le vote, sur le texte tel qu'il arrivait en séance.
      if (ok(xa)) { q.expl = xa; q.explAvant = true; return true; }
      return false;
    });
    // Votes faits avant celui de l'Assemblée : une fois le vote tenu, ils comptent comme les autres.
    var av = lireAv(), mes = lireMes(), change = false;
    Q.forEach(function (q) {
      var r = q.cav && av[q.cav]; if (!r || r.le > q.d) return;
      q.avant = r; if (!mes[q.id]) { mes[q.id] = r.c; change = true; }
    });
    if (change) ecrireMes(mes);
    // Votes à venir : les votes solennels déjà fixés à l'ordre du jour, s'ils ont leur explication.
    var A = (J.AVENIR || []).filter(function (a) { return ok(X && X['avenir:' + a.cle]) && !Q.some(function (q) { return q.cav === a.cle && q.d >= a.d; }); }).map(function (a) {
      return { id: 'av:' + a.cle, avenir: true, cle: a.cle, dos: a.dos, k: a.k, d: a.d, titre: a.o, type: 'Vote prévu à l\'Assemblée', expl: X['avenir:' + a.cle],
        q: a.k === 'partie' ? 'Adopter cette partie du texte ?' : 'Adopter ce texte ?', choix: ['pour', 'contre', 'abstention'] };
    });
    // Ordre de la page : les dix votes qui ont le plus partagé l'Assemblée (une seule motion de censure parmi eux), puis tous les
    // autres, du plus récent au plus ancien.
    var censure = 0, premiers = Q.slice().sort(function (a, b) { return b.partage - a.partage || (a.d < b.d ? 1 : -1); })
      .filter(function (q) { return q.k !== 'censure' || !censure++; }).slice(0, SERIE);
    var ordre = premiers.concat(Q.filter(function (q) { return premiers.indexOf(q) < 0; }));
    var G = {}; J.GROUPES.forEach(function (g) { G[g.c] = g; });
    // Carte des groupes : calculée sur tous les votes importants de la législature, expliqués ou non.
    var tousPos = J.VOTES.map(function (v) { var o = {}; J.GROUPES.forEach(function (g) { if (g.c !== 'NI') { var p = position(v, g.c); if (p) o[g.c] = p; } }); return o; });
    return { Q: Q, ordre: ordre, avenir: A, nbVotes: J.VOTES.length, plan: plan(J.GROUPES.filter(function (g) { return g.c !== 'NI'; }), tousPos), tous: tous, G: G, groupes: J.GROUPES.filter(function (g) { return g.c !== 'NI'; }), maj: J.maj, P: J.P, debut: J.VOTES.length ? J.VOTES[J.VOTES.length - 1].d : '' };
  }

  // Plan des groupes (positionnement multidimensionnel classique) : la distance entre deux groupes est 1 − leur accord moyen
  // sur les votes où les deux avaient une position ; on garde les deux directions qui expliquent le plus ces distances.
  function plan(groupes, tousPos) {
    var n = groupes.length, D2 = [], i, j;
    for (i = 0; i < n; i++) { D2.push([]); for (j = 0; j < n; j++) {
      var s = 0, k = 0; tousPos.forEach(function (o) { var a = o[groupes[i].c], b = o[groupes[j].c]; if (a && b) { k++; s += accord(a, b); } });
      var d = k ? 1 - s / k : 1; D2[i].push(d * d);
    } }
    var lig = D2.map(function (r) { return r.reduce(function (a, b) { return a + b; }, 0) / n; }), tot = lig.reduce(function (a, b) { return a + b; }, 0) / n;
    var B = D2.map(function (r, i) { return r.map(function (x, j) { return -0.5 * (x - lig[i] - lig[j] + tot); }); });
    var axes = [], M = B.map(function (r) { return r.slice(); });
    for (var a = 0; a < 2; a++) {
      var v = groupes.map(function (g, i) { return 1 + i / n; }), l = 0;
      for (var it = 0; it < 300; it++) {
        var w = M.map(function (r) { return r.reduce(function (s, x, j) { return s + x * v[j]; }, 0); });
        l = Math.sqrt(w.reduce(function (s, x) { return s + x * x; }, 0)); if (!l) break;
        v = w.map(function (x) { return x / l; });
      }
      axes.push({ l: l, v: v });
      M = M.map(function (r, i) { return r.map(function (x, j) { return x - l * v[i] * v[j]; }); });
    }
    // Sens des axes fixé une fois pour toutes : le plus grand groupe du côté positif (le sens n'a pas de signification).
    var grand = 0; groupes.forEach(function (g, i) { if ((g.m || 0) > (groupes[grand].m || 0)) grand = i; });
    axes.forEach(function (ax) { if (ax.v[grand] < 0) ax.v = ax.v.map(function (x) { return -x; }); });
    var X = groupes.map(function (g, i) { return axes.map(function (ax) { return ax.v[i] * Math.sqrt(Math.max(ax.l, 0)); }); });
    var tr = B.reduce(function (s, r, i) { return s + Math.max(r[i], 0); }, 0);
    return { groupes: groupes, X: X, axes: axes, lig: lig, part: axes.map(function (ax) { return tr ? ax.l / tr : 0; }) };
  }
  // Place la personne entre les groupes : moyenne de leurs positions, chacune pesée par son accord avec le groupe à la
  // puissance 8 (le groupe avec qui elle vote le plus souvent l'attire le plus ; voter toujours comme un groupe place sur lui).
  function placer(P, R) {
    var acc = {}; R.groupes.forEach(function (g) { acc[g.c] = g.pct / 100; });
    var w = P.groupes.map(function (g) { return Math.pow(acc[g.c] || 0, 8); }), t = w.reduce(function (a, b) { return a + b; }, 0);
    if (!t) return null;
    return [0, 1].map(function (a) { return P.X.reduce(function (s, x, i) { return s + w[i] * x[a]; }, 0) / t; });
  }

  var accord = function (a, b) { return a === b ? 1 : (a === 'abstention' || b === 'abstention') ? 0.5 : 0; };
  function resultat(D) {
    var mes = lireMes(), faits = D.Q.filter(function (q) { return CHOIX[mes[q.id]]; });
    var L = D.groupes.map(function (g) {
      var s = 0, n = 0;
      faits.forEach(function (q) { var p = q.pos[g.c]; if (p) { n++; s += accord(mes[q.id], p); } });
      return { c: g.c, n: g.n, nb: n, pct: n ? Math.round(100 * s / n) : null };
    }).filter(function (r) { return r.nb; }).sort(function (a, b) { return b.pct - a.pct || b.nb - a.nb; });
    var sa = 0; faits.forEach(function (q) { sa += accord(mes[q.id], q.majorite); });
    return { nb: faits.length, groupes: L, assemblee: faits.length ? Math.round(100 * sa / faits.length) : null };
  }

  function style() { if (!document.getElementById('vz-css')) { var st = document.createElement('style'); st.id = 'vz-css'; st.textContent = css; document.head.appendChild(st); } }

  // Une question : le vote, puis ce qu'a fait l'Assemblée et chaque groupe.
  function carte(el, q, D, o) {
    o = o || {}; style();
    if (q.avenir) return carteAvenir(el, q, D, o);
    var mes = lireMes(), deja = mes[q.id];
    var off = '<details class="vz-off"><summary>Intitulé officiel et sources</summary><p>« ' + esc(cap(q.v.t)) + ' » (Assemblée nationale, ' + dateFr(q.d) + ').' + (q.stade ? ' Étape : ' + esc(q.stade.replace(/\.$/, '').toLowerCase()) + '.' : '') + '</p><p>' +
      (q.v.dos ? '<a href="https://www.assemblee-nationale.fr/dyn/17/dossiers/' + esc(q.v.dos) + '">Le dossier du texte</a> · ' : '') +
      '<a href="https://www.assemblee-nationale.fr/dyn/17/scrutins/' + q.v.n + '">Le scrutin n° ' + q.v.n + '</a></p></details>';
    el.innerHTML = '<div class="vz">' + (o.entete || '') +
      '<span class="eyebrow">' + esc(q.type) + ' · ' + dateFr(q.d) + '</span>' +
      '<h2 class="vz-titre">' + esc(q.titre) + '</h2>' +
      expl(q) +
      '<p class="vz-q">' + esc(q.q) + '</p>' + (q.aide ? '<p class="vz-aide">' + esc(q.aide) + '</p>' : '') +
      '<div class="vz-choix" style="--n:' + q.choix.length + '">' + q.choix.map(function (c) { return '<button type="button" data-c="' + c + '" aria-pressed="false">' + CHOIX[c] + '</button>'; }).join('') + '</div>' +
      '<button type="button" class="vz-passe">Je ne sais pas : passer</button>' + off + '<div class="vz-rev" hidden></div></div>';
    var rev = el.querySelector('.vz-rev'), bs = el.querySelectorAll('.vz-choix button');
    function montrer(c) {
      Array.prototype.forEach.call(bs, function (b) { b.disabled = true; b.setAttribute('aria-pressed', b.dataset.c === c ? 'true' : 'false'); });
      el.querySelector('.vz-passe').hidden = true;
      var par = { pour: [], contre: [], abstention: [] }, comme = 0, n = 0;
      D.groupes.forEach(function (g) { var p = q.pos[g.c]; if (!p) return; n++; if (p === c) comme++; par[p].push('<span' + (p === c ? ' class="moi"' : '') + '>' + esc(g.n) + '</span>'); });
      rev.innerHTML = '<p class="vz-sort">À l\'Assemblée : <b>' + esc(q.sort) + '</b><small>' + q.compte + '</small></p>' +
        '<div class="vz-gr">' + ['pour', 'contre', 'abstention'].filter(function (p) { return par[p].length; }).map(function (p) { return '<b>' + CHOIX[p] + '</b><div>' + par[p].join('') + '</div>'; }).join('') + '</div>' +
        (q.avant ? '<p class="vz-comme">Vous aviez voté le ' + dateFr(q.avant.le) + ', avant l\'Assemblée. Les députés ont pu modifier le texte pendant le débat.</p>' : '') +
        '<p class="vz-comme">Vous avez voté comme <b>' + comme + ' groupe' + (comme > 1 ? 's' : '') + ' sur ' + n + '</b> (encadrés).' + (q.k === 'censure' ? ' Un groupe est compté pour si la majorité de ses membres a voté la censure.' : '') + '</p>' +
        (o.suivant ? '<button type="button" class="vz-suite">' + esc(o.suivantLabel || 'Vote suivant →') + '</button>' : '');
      rev.hidden = false;
      var s = rev.querySelector('.vz-suite'); if (s) s.addEventListener('click', o.suivant);
    }
    Array.prototype.forEach.call(bs, function (b) {
      b.addEventListener('click', function () { var m = lireMes(); m[q.id] = b.dataset.c; ecrireMes(m); montrer(b.dataset.c); if (o.apres) o.apres(q, b.dataset.c); });
    });
    el.querySelector('.vz-passe').addEventListener('click', function () { var m = lireMes(); m[q.id] = 'passe'; ecrireMes(m); if (o.apres) o.apres(q, 'passe'); if (o.suivant) o.suivant(); });
    if (CHOIX[deja]) montrer(deja);
  }

  function expl(q) {
    return q.expl ? '<p class="vz-expl">' + esc(q.expl.e) + '</p><p class="vz-lu">Lu dans : <a href="' + esc(q.expl.url) + '">' + esc(q.expl.src) + '</a>' +
      (q.explAvant || q.avenir ? ' (le texte tel qu\'il arrivait en séance : les députés peuvent le modifier pendant le débat)' : '') + '</p>' : '';
  }
  // Un vote à venir : on vote avant l'Assemblée ; le jour du vote, la carte montre ce qu'ont fait les groupes.
  function carteAvenir(el, q, D, o) {
    var deja = lireAv()[q.cle];
    el.innerHTML = '<div class="vz">' + (o.entete || '') + '<span class="eyebrow">' + esc(q.type) + ' · ' + dateFr(q.d) + '</span>' +
      '<h2 class="vz-titre">' + esc(q.titre) + '</h2>' + expl(q) + '<p class="vz-q">' + esc(q.q) + '</p>' +
      '<div class="vz-choix" style="--n:3">' + q.choix.map(function (c) { return '<button type="button" data-c="' + c + '" aria-pressed="false">' + CHOIX[c] + '</button>'; }).join('') + '</div>' +
      '<details class="vz-off"><summary>Sources</summary><p><a href="https://www.assemblee-nationale.fr/dyn/17/dossiers/' + esc(q.dos) + '">Le dossier du texte</a> · ordre du jour de l\'Assemblée nationale</p></details>' +
      '<div class="vz-rev" hidden></div></div>';
    var rev = el.querySelector('.vz-rev'), bs = el.querySelectorAll('.vz-choix button');
    function montrer(c, le) {
      Array.prototype.forEach.call(bs, function (b) { b.disabled = true; b.setAttribute('aria-pressed', b.dataset.c === c ? 'true' : 'false'); });
      rev.innerHTML = '<p class="vz-sort">Vote de l\'Assemblée prévu le <b>' + dateFr(q.d) + '</b><small>Votre vote du ' + dateFr(le) + ' est gardé sur cet appareil. Revenez après le vote : vous verrez comment chaque groupe a voté, et ce vote comptera dans votre résultat.</small></p>' +
        (o.suivant ? '<button type="button" class="vz-suite">' + esc(o.suivantLabel || 'Vote suivant →') + '</button>' : '');
      rev.hidden = false;
      var s = rev.querySelector('.vz-suite'); if (s) s.addEventListener('click', o.suivant);
    }
    Array.prototype.forEach.call(bs, function (b) {
      b.addEventListener('click', function () { var a = lireAv(), le = aujourdhui(); a[q.cle] = { c: b.dataset.c, le: le }; ecrireAv(a); montrer(b.dataset.c, le); if (o.apres) o.apres(q, b.dataset.c); });
    });
    if (deja && CHOIX[deja.c]) montrer(deja.c, deja.le);
  }

  // Le résultat : de quels groupes les votes de la personne sont le plus proches.
  function bilan(el, D) {
    style();
    var R = resultat(D);
    if (R.nb < MIN) {
      el.innerHTML = '<span class="eyebrow">Votre résultat</span><h2>Votre résultat s\'affiche à partir de ' + MIN + ' votes</h2><p class="note">Encore ' + (MIN - R.nb) + ' vote' + (MIN - R.nb > 1 ? 's' : '') + '. Avant, il dépendrait d\'un ou deux textes seulement.</p>';
      return R;
    }
    var top = R.groupes.filter(function (g) { return g.pct === R.groupes[0].pct; });
    el.innerHTML = '<span class="eyebrow">Votre résultat · ' + R.nb + ' votes</span>' +
      '<h2>Vos votes ressemblent le plus à ceux ' + (top.length > 1 ? 'des groupes ' + top.map(function (g) { return esc(g.n); }).join(' et ') + ' (à égalité)' : 'du groupe ' + esc(top[0].n)) + '</h2>' +
      '<ul class="vz-bars">' + R.groupes.map(function (g) {
        return '<li' + (g.pct === R.groupes[0].pct ? ' class="top"' : '') + '><span class="n">' + esc(g.n) + '</span><span class="v">' + (g.nb < R.nb ? '<small>sur ' + g.nb + ' votes</small>' : '') + g.pct + ' %</span><span class="b"><i style="width:' + g.pct + '%"></i></span></li>';
      }).join('') + '</ul>' +
      '<p class="note">Accord avec le résultat de l\'Assemblée : <b>' + R.assemblee + ' %</b> de vos votes. Accord : 1 si vous avez voté comme la majorité du groupe, ½ si l\'un des deux s\'est abstenu et pas l\'autre, 0 sinon.' +
      (R.groupes.some(function (g) { return g.nb < R.nb; }) ? ' « Sur … votes » : le groupe n\'avait pas de position sur vos autres votes (aucun de ses députés n\'a voté, ou il n\'existait pas encore) ; ils ne comptent pas pour lui.' : '') +
      ' Source : Assemblée nationale, scrutins de la 17e législature ; calcul de Concret à partir de vos votes, faits sur cet appareil.</p>';
    return R;
  }

  // La carte : les groupes placés selon leurs votes, et la personne selon les siens (à partir de MIN_PLAN votes).
  var MIN_PLAN = 10;
  function dessinerPlan(el, D) {
    style();
    var P = D.plan, R = resultat(D), moi = R.nb >= MIN_PLAN ? placer(P, R) : null;
    var pts = P.X.map(function (x, i) { return { x: x[0], y: x[1], c: P.groupes[i].c, n: P.groupes[i].n }; });
    if (moi) pts.push({ x: moi[0], y: moi[1], c: 'Vous', moi: 1 });
    var xs = pts.map(function (p) { return p.x; }), ys = pts.map(function (p) { return p.y; });
    var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs), y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
    var W = 340, H = 260, m = 34;
    var sx = function (x) { return m + (x - x0) / ((x1 - x0) || 1) * (W - 2 * m); }, sy = function (y) { return H - m - (y - y0) / ((y1 - y0) || 1) * (H - 2 * m); };
    // Étiquettes : au-dessus du point, sinon dessous, à droite ou à gauche, la première place libre (ni étiquette ni point).
    var pris = [], larg = function (t) { return t.length * 7 + 4; };
    var libre = function (x, y, w) { return !pris.some(function (q) { return Math.abs(q.x - x) < (q.w + w) / 2 && Math.abs(q.y - y) < 12; }) && !pts.some(function (p) { return Math.abs(sx(p.x) - x) < w / 2 && y - 10 < sy(p.y) + 5 && sy(p.y) - 5 < y + 2; }); };
    var svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Carte des groupes de l\'Assemblée selon leurs votes" style="display:block;width:100%;height:auto;font-family:var(--sans)">' +
      '<line x1="' + m / 2 + '" y1="' + H / 2 + '" x2="' + (W - m / 2) + '" y2="' + H / 2 + '" stroke="var(--line)" stroke-dasharray="3 3"/><line x1="' + W / 2 + '" y1="' + m / 2 + '" x2="' + W / 2 + '" y2="' + (H - m / 2) + '" stroke="var(--line)" stroke-dasharray="3 3"/>' +
      // « Vous » choisit sa place en premier et se dessine en dernier (au-dessus des groupes).
      (pts.slice().sort(function (p, q) { return (q.moi || 0) - (p.moi || 0); }).forEach(function (p) {
        var X = sx(p.x), Y = sy(p.y), w = larg(p.c); p.lx = X; p.ly = Y - 9;
        var essais = [[0, -9], [0, 17], [w / 2 + 8, 4], [-w / 2 - 8, 4], [0, -21], [0, 29], [w / 2 + 8, -8], [-w / 2 - 8, -8]];
        for (var t = 0; t < essais.length; t++) { if (libre(X + essais[t][0], Y + essais[t][1], w)) { p.lx = X + essais[t][0]; p.ly = Y + essais[t][1]; break; } }
        pris.push({ x: p.lx, y: p.ly, w: w });
      }), '') +
      pts.map(function (p) {
        var X = sx(p.x), Y = sy(p.y), lx = p.lx, ly = p.ly;
        return '<circle cx="' + X.toFixed(1) + '" cy="' + Y.toFixed(1) + '" r="' + (p.moi ? 7 : 5) + '" fill="' + (p.moi ? 'var(--fr)' : 'var(--muted)') + '"' + (p.moi ? ' stroke="var(--panel)" stroke-width="2"' : '') + '><title>' + esc(p.n || 'Vous') + '</title></circle>' +
          '<text x="' + lx.toFixed(1) + '" y="' + ly.toFixed(1) + '" text-anchor="middle" font-size="' + (p.moi ? 13 : 11) + '" font-weight="' + (p.moi ? 700 : 600) + '" fill="' + (p.moi ? 'var(--fr)' : 'var(--fg)') + '">' + esc(p.c) + '</text>';
      }).join('') + '</svg>';
    var bouts = function (a) { var o = P.groupes.map(function (g, i) { return { c: g.c, v: P.X[i][a] }; }).sort(function (p, q) { return p.v - q.v; }); return [o.slice(0, 2), o.slice(-2).reverse()].map(function (l) { return l.map(function (g) { return g.c; }).join(', '); }); };
    var bx = bouts(0), by = bouts(1), part = Math.round(100 * (P.part[0] + P.part[1]));
    el.innerHTML = '<span class="eyebrow">La carte des votes</span><h2>' + (moi ? 'Où vous placent vos votes' : 'Les groupes de l\'Assemblée selon leurs votes') + '</h2>' + svg +
      '<p class="note">Deux groupes sont d\'autant plus proches qu\'ils ont souvent voté pareil sur les ' + D.nbVotes + ' votes importants depuis ' + moisFr(D.debut) + '. Les axes n\'ont pas de nom : à gauche du dessin, ' + bx[0] + ' ; à droite, ' + bx[1] + ' ; en bas, ' + by[0] + ' ; en haut, ' + by[1] + '. Ces deux directions résument ' + part + ' % des écarts entre groupes. ' +
      (moi ? 'Votre point se place entre les groupes, d\'autant plus près de chacun que vous votez souvent comme lui (sur vos ' + R.nb + ' votes).' : 'Votre point apparaît à partir de ' + MIN_PLAN + ' votes (vous en avez ' + R.nb + ').') + '</p>' +
      '<p class="note">' + P.groupes.map(function (g) { return '<b>' + esc(g.c) + '</b> ' + esc(g.n); }).join(' · ') + '</p>';
  }

  window.ConcretVotez = {
    MIN: MIN, SERIE: SERIE, dateFr: dateFr, moisFr: moisFr, nf: nf, esc: esc, CHOIX: CHOIX,
    charger: function () {
      var lire = function (u) { return fetch(u, { cache: 'no-cache' }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }); };
      if (!donnees) donnees = Promise.all([lire('/donnees/votes.json'), lire('/donnees/votez_explications.json')]).then(function (r) { return construire(r[0], r[1].explications || {}); });
      return donnees;
    },
    mes: lireMes,
    oublier: function (id) { var m = lireMes(); delete m[id]; ecrireMes(m); },
    effacer: function () { try { localStorage.removeItem(CLE); localStorage.removeItem(CLE_AV); } catch (e) {} },
    avant: lireAv,
    resultat: resultat, carte: carte, bilan: bilan, dessinerPlan: dessinerPlan,
    // Bloc du quiz : un vote pas encore voté sur cet appareil.
    duJour: function (el) {
      if (!el || !window.fetch) return;
      this.charger().then(function (D) {
        // D'abord un vote à venir pas encore voté ; sinon le plus récent pas encore voté, de préférence un vote où les groupes ne sont pas tous du même avis.
        var mes = lireMes(), av = lireAv(), reste = D.Q.filter(function (x) { return !mes[x.id]; }),
          q = D.avenir.filter(function (x) { return !av[x.cle]; })[0] || reste.filter(function (x) { return x.partage >= 0.1; })[0] || reste[0], lien = '<p class="note" style="font-size:14px"><a href="/votez/" style="color:var(--fr);font-weight:600">Voir votre résultat et voter les autres textes →</a></p>';
        var ent = '<div><span class="eyebrow">Votez les lois</span><h2 style="font-family:var(--serif);font-weight:400;font-size:24px;margin:0">Et vous, qu\'auriez-vous voté ?</h2><p class="note">Un vrai vote de l\'Assemblée nationale. Votre vote reste sur cet appareil.</p></div>';
        el.hidden = false;
        if (!q) { el.innerHTML = ent + '<p class="note" style="font-size:14px">Vous avez voté tous les textes. Le prochain arrive dès que l\'Assemblée en vote un.</p>' + lien; return; }
        var zone = document.createElement('div'); el.innerHTML = ent; el.appendChild(zone);
        var pied = document.createElement('div'); el.appendChild(pied);
        carte(zone, q, D, { apres: function () { var R = resultat(D); pied.innerHTML = (R.nb >= MIN && R.groupes.length ? '<p class="note" style="font-size:14px">Sur vos ' + R.nb + ' votes, vous êtes le plus proche du groupe <b>' + esc(R.groupes[0].n) + '</b> (' + R.groupes[0].pct + ' %).</p>' : '') + lien; } });
      }).catch(function () {});
    }
  };
})();
