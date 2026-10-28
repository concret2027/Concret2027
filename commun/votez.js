/* Votez les lois : les votes importants de l'Assemblée nationale depuis le début de la législature (donnees/votes.json,
   écrit chaque jour par outils/parlement.py à partir des données ouvertes de l'Assemblée), à voter à son tour.
   Une question par texte (son dernier vote sur l'ensemble, sinon sur une partie, sinon la motion de rejet), et une par
   motion de censure, vote de confiance ou déclaration du Gouvernement suivie d'un vote.
   Le résultat (accord avec chaque groupe de députés) est calculé dans le navigateur. Les votes restent sur l'appareil
   (localStorage « concret-votez ») : le sens du vote n'est jamais envoyé. Seule la participation est comptée par le compteur
   de Concret (outils/compteur_worker.js) : « un vote de plus sur ce texte » au premier vote d'un texte, et « une personne de
   plus » au tout premier vote sur l'appareil ; ni pour, ni contre, ni rien qui identifie la personne.
   Utilisé par la page /votez/ et par le bloc « Votez les lois » du quiz. */
(function () {
  var CLE = 'concret-votez', CLE_AV = 'concret-votez-avant', MIN = 5, SERIE = 10;
  // Participation (jamais le sens du vote) : une clé du compteur par texte, une option unique.
  var API = 'https://compteur.square-brook-9d65.workers.dev/', CLE_VU = 'concret-votez-compte';
  var cleNb = function (id) { return 'quiz-votez-' + String(id).toLowerCase().replace(/[^a-z0-9-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 69); };
  function nb(id, ajouter) {
    var u = API + (ajouter ? 'hit' : 'get') + '?k=' + encodeURIComponent(cleNb(id)) + '&n=1' + (ajouter ? '&i=0' : '');
    return fetch(u, { method: ajouter ? 'POST' : 'GET', cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) { return j && j.v ? j.v[0] : null; }, function () { return null; });
  }
  // Au tout premier vote sur cet appareil : une personne de plus (une fois par appareil, et dans le total du jour).
  function personne() { var f = null; try { f = localStorage.getItem(CLE_VU); } catch (e) { return; } if (f) return; try { localStorage.setItem(CLE_VU, '1'); } catch (e) {} nb('personnes', true); nb('personnes-' + aujourdhui(), true); }
  // Un vote de plus : sur ce texte, au total et dans le total du jour. Ces nombres ne sont pas affichés sur le site :
  // ils servent au compte rendu quotidien de l'éditeur (outils/votez_stats.js).
  function compter(id) { personne(); nb(id, true); nb('total', true); nb('jour-' + aujourdhui(), true); }
  var MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
  var dateFr = function (d) { var p = d.split('-'); return (+p[2] === 1 ? '1er' : +p[2]) + ' ' + MOIS[p[1] - 1] + ' ' + p[0]; };
  var moisFr = function (d) { var p = d.split('-'); return MOIS[p[1] - 1] + ' ' + p[0]; };
  // Espace insécable avant « : ; ? ! », dans les nombres et avant € et % (pas de ponctuation ni de chiffre seul en début de ligne).
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }).replace(/ ([:;?!»])/g, '\u00a0$1').replace(/« /g, '«\u00a0').replace(/(\d) (?=\d{3}\b)/g, '$1\u202f').replace(/(\d) (€|%)/g, '$1\u00a0$2'); };
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

  var css = '.vz{display:grid;gap:12px}' +
    '.vz-titre{font-family:var(--serif);font-weight:500;font-size:21px;line-height:1.25;margin:0;text-wrap:balance}' +
    '.vz-tete{display:flex;flex-wrap:wrap;gap:6px;align-items:center}' +
    '.vz-chip{font-size:11.5px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--fr);background:var(--band);border-radius:999px;padding:4px 10px}' +
    '.vz-date{font-size:12.5px;font-weight:600;color:var(--muted)}' +
    '.vz-neuf{background:var(--fr);color:#fff}' +
    '.vz-boite{display:grid;gap:6px;padding:12px 14px;border-radius:12px;background:var(--bg);border:1px solid var(--line)}.vz-boite .eyebrow{margin:0}' +
    '.vz-expl{margin:0;font-size:15px;line-height:1.5}' +
    '.vz-pts{margin:0;padding-left:20px;display:grid;gap:4px;font-size:15px;line-height:1.45}' +
    '.vz-lu{margin:0;font-size:12px;color:var(--muted)}.vz-lu a{color:var(--muted)}' +
    '.vz-q{margin:4px 0 0;font-size:17px;font-weight:700}' +
    '.vz-aide{margin:-4px 0 0;font-size:13.5px;color:var(--muted)}' +
    '.vz-choix{display:grid;grid-template-columns:repeat(var(--n,3),minmax(0,1fr));gap:8px}' +
    '.vz-choix button{font:inherit;font-weight:700;font-size:15.5px;min-height:52px;border-radius:12px;border:1.5px solid var(--fg);background:var(--panel);color:var(--fg);cursor:pointer}' +
    '.vz-choix button[aria-pressed="true"]{background:var(--fg);color:var(--bg)}' +
    '.vz-choix button:disabled{cursor:default}.vz-choix.fait button:not([aria-pressed="true"]){opacity:.6}' +
    '.vz-change{margin:0;font-size:12.5px;color:var(--muted)}' +
    '.vz-choix button:focus-visible,.vz-passe:focus-visible,.vz-suite:focus-visible{outline:2px solid var(--fr);outline-offset:2px}' +
    '.vz-passe{font:inherit;font-size:13.5px;color:var(--muted);background:none;border:0;padding:4px 0;min-height:40px;cursor:pointer;text-decoration:underline;text-underline-offset:3px;justify-self:start}' +
    '.vz-off{font-size:12.5px;color:var(--muted)}.vz-off summary{cursor:pointer;font-weight:600;min-height:40px;display:flex;align-items:center}.vz-off p{margin:6px 0 0}.vz-off a{color:var(--fr)}' +
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
    '.vz-bars>li>i{width:10px;height:10px;border-radius:3px;grid-row:1;align-self:center}.vz-bars li{grid-template-columns:10px minmax(0,1fr) auto!important}.vz-bars .n small{color:var(--muted);font-weight:500;font-size:11.5px}.vz-bars .b{grid-column:2/-1!important}' +
    '.vz-hemi{position:relative}.vz-hemi svg{display:block;width:100%;height:auto;font-family:var(--sans)}.vz-hs{cursor:pointer;outline:none}.vz-hs:hover path,.vz-hs:focus path{filter:brightness(1.08)}' +
    '.vz-tip{position:absolute;top:0;z-index:3;max-width:260px;padding:7px 10px;border-radius:9px;background:var(--fg);color:var(--bg);font-size:12.5px;line-height:1.35;pointer-events:none;box-shadow:0 4px 14px rgba(0,0,0,.18)}' +
    '.vz-lire{margin:0;font-size:13.5px;color:var(--muted)}' +
    '.vz-avis{display:grid;gap:8px;padding:12px 14px;border-radius:12px;border:1.5px solid var(--fr);background:var(--band,var(--panel));font-size:14.5px}' +
    '.vz-avis p{margin:0}.vz-avis-ok{justify-self:start;font:inherit;font-weight:700;min-height:44px;padding:0 18px;border-radius:999px;border:1.5px solid var(--fr);background:var(--panel);color:var(--fr);cursor:pointer}' +
    '.vz-th{display:grid;gap:8px;border:1px solid var(--line);border-radius:12px;padding:0 12px}.vz-th[open]{padding-bottom:12px}' +
    '.vz-th>summary{cursor:pointer;list-style:none;display:flex;align-items:center;gap:10px;padding:12px 0;font-size:16px;font-weight:700}.vz-th>summary::-webkit-details-marker{display:none}' +
    '.vz-th>summary small{display:block;font-size:13px;font-weight:500;color:var(--muted)}.vz-th>summary::after{content:"Voir ▾";margin-left:auto;color:var(--fr);font-size:14px;white-space:nowrap}.vz-th[open]>summary::after{content:"Masquer ▴"}' +
    '.vz-th ul{list-style:none;margin:0;padding:0;display:grid}' +
    '.vz-th li{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:4px 10px;padding:10px 12px 12px;margin-top:8px;border:1px solid var(--line);border-radius:12px;font-size:14px;align-items:center}' +
    '.vz-th .t{font-weight:700;margin-bottom:2px;display:flex;align-items:center;gap:8px;color:var(--fg);text-decoration:none}.vz-th a.t:hover{color:var(--fr)}' +
    '.vz-th .t i{display:grid;place-items:center;width:30px;height:30px;border-radius:50%;background:color-mix(in srgb,var(--line) 70%,transparent);color:var(--fg);flex:none}.vz-th .n{color:var(--muted);font-size:12.5px;font-variant-numeric:tabular-nums}' +
    '.vz-th .b{grid-column:1/-1;height:10px;border-radius:5px;background:var(--line);overflow:hidden;margin-top:2px}.vz-th .b i{display:block;height:100%;border-radius:5px}.vz-th .b.vide i{background:var(--muted);opacity:.45}' +
    '.vz-th .bb{grid-column:1/-1;position:relative;display:block;height:30px;border-radius:8px;background:color-mix(in srgb,var(--line) 45%,transparent);overflow:hidden}' +
    '.vz-th .fi{position:absolute;inset:0 auto 0 0;border-radius:8px;background:color-mix(in srgb,var(--c) 38%,var(--bg))}' +
    '@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .vz-th .fi{background:color-mix(in srgb,var(--c) 50%,#5d6372)}}:root[data-theme="dark"] .vz-th .fi{background:color-mix(in srgb,var(--c) 50%,#5d6372)}' +
    '.vz-th .lb{position:relative;height:100%;display:flex;align-items:center;gap:8px;padding:0 10px;font-size:13.5px;color:var(--fg);white-space:nowrap}' +
    '.vz-th .lb .nm{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis}.vz-th .lb b{font-variant-numeric:tabular-nums}' +
    '.vz-th .g{font-size:13.5px;line-height:1.3}.vz-th .g.att{grid-column:1/-1;color:var(--muted)}' +
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
    var q = { id: String(v.n), v: v, k: v.k, d: v.d, choix: ['pour', 'contre', 'abstention'], pos: {}, pg: v.pg || [] };
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
    // Tous les groupes du même avis : le vote ne dit pas de qui l'on est proche (il ne compte pas dans l'accord avec chaque groupe).
    var avis = {}; Object.keys(q.pos).forEach(function (c) { avis[q.pos[c]] = 1; }); q.unanime = Object.keys(avis).length === 1 ? Object.keys(avis)[0] : '';
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
    // Ordre de la page : d'abord dix votes variés (pour la censure et pour chaque thème, le vote qui a le plus partagé l'Assemblée,
    // complétés par les plus partagés des textes sans thème), du plus partagé au moins partagé ; puis de quoi donner un résultat à
    // chaque thème (trois votes par thème, les plus partagés d'abord, un thème après l'autre) ; puis tous les autres, du plus
    // récent au plus ancien ; le tout mélangé (voir melanger).
    var parPartage = Q.slice().sort(function (a, b) { return b.partage - a.partage || (a.d < b.d ? 1 : -1); });
    var premiers = [], libre = function (q) { return premiers.indexOf(q) < 0; };
    var censure = parPartage.filter(function (q) { return q.k === 'censure'; })[0]; if (censure) premiers.push(censure);
    THEMES.forEach(function (t) {
      // Un thème déjà présent n'en reprend pas ; de préférence un texte de ce seul thème.
      if (premiers.some(function (p) { return p.pg.indexOf(t[0]) >= 0; })) return;
      var L = parPartage.filter(function (x) { return libre(x) && x.pg.indexOf(t[0]) >= 0; });
      var q = L.filter(function (x) { return x.pg.length === 1; })[0] || L[0];
      if (q) premiers.push(q);
    });
    parPartage.forEach(function (q) { if (premiers.length < SERIE && libre(q) && q.k !== 'censure' && !q.pg.length) premiers.push(q); });
    parPartage.forEach(function (q) { if (premiers.length < SERIE && libre(q) && q.k !== 'censure') premiers.push(q); });
    premiers = premiers.slice(0, SERIE).sort(function (a, b) { return b.partage - a.partage; });
    var pris = premiers.slice(), nbTh = {};
    var compter = function (q) { q.pg.forEach(function (t) { nbTh[t] = (nbTh[t] || 0) + 1; }); };
    premiers.forEach(compter);
    for (var tour = 0; tour < MIN_THEME; tour++) THEMES.forEach(function (t) {
      if ((nbTh[t[0]] || 0) >= MIN_THEME) return;
      var q = parPartage.filter(function (x) { return pris.indexOf(x) < 0 && x.pg.indexOf(t[0]) >= 0; })[0];
      if (q) { pris.push(q); compter(q); }
    });
    // Mélange : jamais deux votes budgétaires de suite (budget de l'État, de la Sécurité sociale, approbation des comptes), ni deux
    // votes du même thème de suite ; à chaque place, le premier vote de la liste qui respecte ces deux règles (sinon le premier).
    var budget = function (q) { return /loi de finances|financement de la sécurité sociale|résultats de la gestion|approbation des comptes|programmation des finances/i.test(q.titre || ''); };
    var voisins = function (a, b) { return !!a && ((budget(a) && budget(b)) || a.pg.some(function (t) { return b.pg.indexOf(t) >= 0; })); };
    var melanger = function (L, prec) {
      var R = [], reste = L.slice();
      while (reste.length) { var i = 0; for (var j = 0; j < reste.length; j++) if (!voisins(prec, reste[j])) { i = j; break; } prec = reste.splice(i, 1)[0]; R.push(prec); }
      return R;
    };
    var ordre = melanger(pris.concat(Q.filter(function (q) { return pris.indexOf(q) < 0; })), null);
    var finThemes = 1 + Math.max.apply(null, pris.map(function (q) { return ordre.indexOf(q); }));
    var G = {}; J.GROUPES.forEach(function (g) { G[g.c] = g; });
    return { Q: Q, ordre: ordre, finThemes: finThemes, avenir: A, nbVotes: J.VOTES.length,  tous: tous, G: G, groupes: J.GROUPES.filter(function (g) { return g.c !== 'NI'; }), maj: J.maj, P: J.P, debut: J.VOTES.length ? J.VOTES[J.VOTES.length - 1].d : '' };
  }

  // L'accord avec un groupe sur un texte (calcul du 28 octobre 2026) : la part des députés du groupe qui ont voté comme vous,
  // une abstention comptant pour moitié d'un côté comme de l'autre. Par exemple, vous pour, le groupe 60 pour, 30 contre et
  // 10 abstentions : (60 + 10 / 2) / 100 = 65 %. Pas compté : un groupe dont moins de 5 députés, ou moins d'un quart des
  // membres, ont voté. Censure : seuls les votes pour sont comptés, un député qui ne la vote pas est compté contre.
  var accord = function (a, b) { return a === b ? 1 : (a === 'abstention' || b === 'abstention') ? 0.5 : 0; };
  var VOTANTS_MIN = 5, PART_MIN = 0.25, DATE_CALCUL = '2026-10-28', CLE_CALCUL = 'concret-votez-calcul';
  function peuVotants(q, c) { var x = q.v.g[c]; if (!x || q.k === 'censure') return false; var t = x[1] + x[2] + x[3]; return t > 0 && (t < VOTANTS_MIN || t < PART_MIN * x[4]); }
  function accordFin(u, q, c) {
    var x = q.v.g[c]; if (!x || !q.pos[c]) return null;
    var p = x[1], k = x[2], a = x[3], t = p + k + a;
    if (q.k === 'censure') { t = x[4]; k = t - p; a = 0; }
    else if (peuVotants(q, c)) return null;
    if (!t) return null;
    return (u === 'pour' ? p + a / 2 : u === 'contre' ? k + a / 2 : a + (p + k) / 2) / t;
  }
  function resultat(D, filtre) {
    var mes = lireMes(), faits = D.Q.filter(function (q) { return CHOIX[mes[q.id]] && (!filtre || filtre(q)); });
    var comptes = faits.filter(function (q) { return !q.unanime; }), unan = faits.filter(function (q) { return q.unanime; });
    var L = D.groupes.map(function (g) {
      var s = 0, n = 0;
      comptes.forEach(function (q) { var x = accordFin(mes[q.id], q, g.c); if (x != null) { n++; s += x; } });
      return { c: g.c, n: g.n, nb: n, pct: n ? Math.round(100 * s / n) : null };
    }).filter(function (r) { return r.nb; }).sort(function (a, b) { return b.pct - a.pct || b.nb - a.nb; });
    var sa = 0; faits.forEach(function (q) { sa += accord(mes[q.id], q.majorite); });
    return { nb: faits.length, nbCompte: comptes.length, unan: unan.length, unanComme: unan.filter(function (q) { return mes[q.id] === q.unanime; }).length,
      groupes: L, assemblee: faits.length ? Math.round(100 * sa / faits.length) : null };
  }
  // L'ancien calcul (jusqu'au 27 octobre 2026 : la position de la majorité du groupe, 1, ½ ou 0 point, sur tous les votes),
  // gardé pour montrer une fois, à qui avait déjà un résultat, ses chiffres avant et après.
  function resultatAncien(D) {
    var mes = lireMes(), faits = D.Q.filter(function (q) { return CHOIX[mes[q.id]]; });
    return { nb: faits.length, groupes: D.groupes.map(function (g) {
      var s = 0, n = 0;
      faits.forEach(function (q) { var p = q.pos[g.c]; if (p) { n++; s += accord(mes[q.id], p); } });
      return { c: g.c, n: g.n, pct: n ? Math.round(100 * s / n) : null };
    }).filter(function (r) { return r.pct != null; }).sort(function (a, b) { return b.pct - a.pct; }) };
  }
  function lireCalcul() { try { return localStorage.getItem(CLE_CALCUL); } catch (e) { return DATE_CALCUL; } }
  function ecrireCalcul() { try { localStorage.setItem(CLE_CALCUL, DATE_CALCUL); } catch (e) {} }
  // Au premier chargement depuis le changement, avant tout nouveau vote : qui avait déjà un résultat (au moins MIN votes)
  // verra une fois ses chiffres avant et après ; les autres, rien.
  var avisCalcul = false;
  function decider(D) { if (lireCalcul() === DATE_CALCUL) return; if (resultatAncien(D).nb >= MIN) avisCalcul = true; else ecrireCalcul(); }
  function avis(D, R) {
    if (!avisCalcul) return '';
    var A = resultatAncien(D), nv = {}; R.groupes.forEach(function (g) { nv[g.c] = g.pct; });
    return '<div class="vz-avis" role="status"><p><b>Un calcul plus fin (depuis le ' + dateFr(DATE_CALCUL) + ').</b> Chaque député qui a voté compte désormais, et non plus seulement la position de la majorité de son groupe. Par exemple, un groupe vote à 60 pour, 30 contre et 10 abstentions, et vous votez pour : vous êtes d\'accord avec lui à 65 % sur ce texte, au lieu de 100 %. Les textes que tous les groupes ont votés de la même façon sont comptés à part.</p>' +
      '<p>Vos ' + A.nb + ' votes : ' + A.groupes.slice(0, 3).map(function (g) { return '<b>' + esc(g.n) + '</b> ' + (nv[g.c] != null ? nv[g.c] + '\u00a0%' : 'pas encore de résultat') + ' (avant\u00a0: ' + g.pct + '\u00a0%)'; }).join(' · ') + '.</p>' +
      '<button type="button" class="vz-avis-ok">Compris</button></div>';
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
      tete(q) + '<h2 class="vz-titre">' + esc(q.titre) + '</h2>' + expl(q) +
      '<p class="vz-q">' + esc(q.q) + '</p>' + (q.aide ? '<p class="vz-aide">' + esc(q.aide) + '</p>' : '') +
      '<div class="vz-choix" style="--n:' + q.choix.length + '">' + q.choix.map(function (c) { return '<button type="button" data-c="' + c + '" aria-pressed="false">' + CHOIX[c] + '</button>'; }).join('') + '</div>' +
      '<button type="button" class="vz-passe">Je ne sais pas : passer</button><div class="vz-rev" hidden></div>' + off + '</div>';
    var rev = el.querySelector('.vz-rev'), bs = el.querySelectorAll('.vz-choix button');
    // Les boutons restent actifs : toucher une autre réponse change le vote.
    function montrer(c, calme) {
      Array.prototype.forEach.call(bs, function (b) { b.setAttribute('aria-pressed', b.dataset.c === c ? 'true' : 'false'); });
      el.querySelector('.vz-choix').classList.add('fait'); el.querySelector('.vz-passe').hidden = true;
      var par = { pour: [], contre: [], abstention: [] }, comme = 0, n = 0, peu = D.groupes.filter(function (g) { return q.pos[g.c] && peuVotants(q, g.c); }).map(function (g) { return esc(g.c); });
      D.groupes.forEach(function (g) { var p = q.pos[g.c]; if (!p) return; n++; if (p === c) comme++; par[p].push('<span' + (p === c ? ' class="moi"' : '') + '>' + esc(g.n) + '</span>'); });
      // D'abord le résultat et le bouton du vote suivant (visibles sans descendre), puis le détail groupe par groupe.
      rev.innerHTML = '<p class="vz-sort">À l\'Assemblée : <b>' + esc(q.sort) + '</b><small>' + q.compte + '</small></p>' +
        '<p class="vz-comme">Vous avez voté comme <b>' + comme + ' groupe' + (comme > 1 ? 's' : '') + ' sur ' + n + '</b> (encadrés ci-dessous).' + (q.k === 'censure' ? ' Un groupe est compté pour si la majorité de ses membres a voté la censure.' : '') + '</p>' +
        '<p class="vz-change">Pour changer votre vote, touchez une autre réponse.</p>' +
        (q.avant ? '<p class="vz-comme">Vous aviez voté le ' + dateFr(q.avant.le) + ', avant l\'Assemblée. Les députés ont pu modifier le texte pendant le débat.</p>' : '') +
        (o.suivant ? '<button type="button" class="vz-suite">' + esc(o.suivantLabel || 'Vote suivant →') + '</button>' : '') +
        (q.unanime ? '<p class="vz-comme">Tous les groupes ont voté pareil : ce vote ne compte pas dans votre accord avec chaque groupe, il ne dit pas de qui vous êtes proche.</p>' : '') +
        (peu.length && !q.unanime ? '<p class="vz-comme">Trop peu de députés ont voté dans ' + (peu.length > 1 ? 'les groupes ' : 'le groupe ') + peu.join(', ') + ' (moins de ' + VOTANTS_MIN + ', ou moins d\'un quart du groupe) : ' + (peu.length > 1 ? 'ils ne sont pas comptés' : 'il n\'est pas compté') + ' sur ce vote.</p>' : '') +
        '<div class="vz-gr">' + ['pour', 'contre', 'abstention'].filter(function (p) { return par[p].length; }).map(function (p) { return '<b>' + CHOIX[p] + '</b><div>' + par[p].join('') + '</div>'; }).join('') + '</div>';
      rev.hidden = false;
      if (!calme && rev.scrollIntoView) rev.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      var s = rev.querySelector('.vz-suite'); if (s) s.addEventListener('click', o.suivant);
    }
    Array.prototype.forEach.call(bs, function (b) {
      b.addEventListener('click', function () { var m = lireMes(), change = CHOIX[m[q.id]]; if (m[q.id] === b.dataset.c) return; m[q.id] = b.dataset.c; ecrireMes(m); montrer(b.dataset.c, change); if (!change) compter(q.id); if (o.apres) o.apres(q, b.dataset.c); });
    });
    el.querySelector('.vz-passe').addEventListener('click', function () { var m = lireMes(); m[q.id] = 'passe'; ecrireMes(m); if (o.apres) o.apres(q, 'passe'); if (o.suivant) o.suivant(); });
    if (CHOIX[deja]) montrer(deja, true);
  }

  // En-tête d'une carte : le genre de vote et sa date, en pastilles.
  function tete(q) { return '<div class="vz-tete"><span class="vz-chip">' + esc(q.type) + '</span>' + (q.nouveau ? '<span class="vz-chip vz-neuf">Nouveau</span>' : '') + '<span class="vz-date">' + dateFr(q.d) + '</span></div>'; }
  // L'explication, dans son propre encadré : une phrase, puis au plus trois points.
  function expl(q) {
    return q.expl ? '<div class="vz-boite"><span class="eyebrow">' + (q.k === 'censure' || q.k === 'confiance' ? 'Ce qui est en jeu' : 'Ce que prévoit le texte') + '</span><p class="vz-expl">' + esc(q.expl.e) + '</p>' + ((q.expl.points || []).length ? '<ul class="vz-pts">' + q.expl.points.map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('') + '</ul>' : '') + '<p class="vz-lu">Lu dans : <a href="' + esc(q.expl.url) + '">' + esc(q.expl.src) + '</a>' +
      (q.explAvant || q.avenir ? ', avant le débat' : '') + '</p></div>' : '';
  }
  // Un vote à venir : on vote avant l'Assemblée ; le jour du vote, la carte montre ce qu'ont fait les groupes.
  function carteAvenir(el, q, D, o) {
    var deja = lireAv()[q.cle];
    el.innerHTML = '<div class="vz">' + (o.entete || '') + tete(q) +
      '<h2 class="vz-titre">' + esc(q.titre) + '</h2>' + expl(q) + '<p class="vz-q">' + esc(q.q) + '</p>' +
      '<div class="vz-choix" style="--n:3">' + q.choix.map(function (c) { return '<button type="button" data-c="' + c + '" aria-pressed="false">' + CHOIX[c] + '</button>'; }).join('') + '</div>' +
      '<div class="vz-rev" hidden></div>' +
      '<details class="vz-off"><summary>Sources</summary><p><a href="https://www.assemblee-nationale.fr/dyn/17/dossiers/' + esc(q.dos) + '">Le dossier du texte</a> · ordre du jour de l\'Assemblée nationale</p></details></div>';
    var rev = el.querySelector('.vz-rev'), bs = el.querySelectorAll('.vz-choix button');
    function montrer(c, le) {
      Array.prototype.forEach.call(bs, function (b) { b.setAttribute('aria-pressed', b.dataset.c === c ? 'true' : 'false'); });
      el.querySelector('.vz-choix').classList.add('fait');
      rev.innerHTML = '<p class="vz-sort">Vote de l\'Assemblée prévu le <b>' + dateFr(q.d) + '</b><small>Votre vote du ' + dateFr(le) + ' est gardé sur cet appareil. Revenez après le vote : vous verrez comment chaque groupe a voté, et ce vote comptera dans votre résultat.</small></p>' +
        '<p class="vz-change">Vous pouvez changer votre vote jusqu\'au vote de l\'Assemblée : touchez une autre réponse.</p>' +
        (o.suivant ? '<button type="button" class="vz-suite">' + esc(o.suivantLabel || 'Vote suivant →') + '</button>' : '');
      rev.hidden = false;
      var s = rev.querySelector('.vz-suite'); if (s) s.addEventListener('click', o.suivant);
    }
    Array.prototype.forEach.call(bs, function (b) {
      b.addEventListener('click', function () { var a = lireAv(), le = aujourdhui(), premier = !a[q.cle]; if (a[q.cle] && a[q.cle].c === b.dataset.c) return; a[q.cle] = { c: b.dataset.c, le: le }; ecrireAv(a); montrer(b.dataset.c, le); if (premier) compter('avenir-' + q.cle); if (o.apres) o.apres(q, b.dataset.c); });
    });
    if (deja && CHOIX[deja.c]) montrer(deja.c, deja.le);
  }

  // Le résultat, en hémicycle : chaque groupe à sa place et dans sa couleur sur le plan officiel de l'Assemblée, sa part
  // proportionnelle à ses sièges ; la partie colorée va du centre vers le bord selon l'accord de la personne avec lui.
  function hemicycle(D, R) {
    var acc = {}; (R ? R.groupes : []).forEach(function (g) { acc[g.c] = g; });
    var G = D.groupes.filter(function (g) { return g.a != null; }).slice().sort(function (p, q) { return q.a - p.a; });
    var tot = G.reduce(function (s, g) { return s + g.m; }, 0), W = 360, H = 200, cx = 180, cy = 186, r0 = 54, R1 = 168, t = Math.PI, ecart = 0.012;
    var pt = function (r, a) { return (cx + r * Math.cos(a)).toFixed(1) + ' ' + (cy - r * Math.sin(a)).toFixed(1); };
    var secteur = function (a0, a1, ra, rb) { var g = a0 - a1 > Math.PI ? 1 : 0; return 'M' + pt(ra, a0) + ' L' + pt(rb, a0) + ' A' + rb + ' ' + rb + ' 0 ' + g + ' 1 ' + pt(rb, a1) + ' L' + pt(ra, a1) + ' A' + ra + ' ' + ra + ' 0 ' + g + ' 0 ' + pt(ra, a0) + ' Z'; };
    var parts = G.map(function (g) {
      var a0 = t, a1 = t - Math.PI * g.m / tot; t = a1;
      var x = acc[g.c], rb = x ? r0 + (R1 - r0) * x.pct / 100 : r0;
      var info = esc(g.n) + ' (' + esc(g.c) + ') · ' + g.m + ' députés' + (x ? ' · vous : ' + x.pct + ' % d\'accord, sur ' + x.nb + ' vote' + (x.nb > 1 ? 's' : '') : '');
      var mid = (a0 + a1) / 2, court = g.c.replace('-NFP', ''), large = a0 - a1 > 0.2;
      // Le pourcentage d'accord écrit dans chaque part assez large (les autres : au toucher).
      var pc = x && large ? '<text x="' + (cx + (R1 - 15) * Math.cos(mid)).toFixed(1) + '" y="' + (cy - (R1 - 15) * Math.sin(mid) + 4).toFixed(1) + '" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--fg)" style="paint-order:stroke;stroke:var(--panel);stroke-width:3px">' + x.pct + '\u00a0%</text>' : '';
      var lab = large ? '<text x="' + (cx + (R1 + 13) * Math.cos(mid)).toFixed(1) + '" y="' + (cy - (R1 + 13) * Math.sin(mid) + 4).toFixed(1) + '" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--muted)">' + esc(court) + '</text>' : '';
      return '<g class="vz-hs" tabindex="0" data-info="' + info + '"' + (x ? ' data-pct="' + x.pct + '" data-c="' + esc(court) + '"' : '') + '><path d="' + secteur(a0 - ecart, a1 + ecart, r0, R1) + '" fill="' + g.coul + '" opacity=".16"/>' +
        (x ? '<path d="' + secteur(a0 - ecart, a1 + ecart, r0, rb) + '" fill="' + g.coul + '"/>' : '') + lab + pc + '</g>';
    }).join('');
    var top = R && R.groupes[0];
    return '<div class="vz-hemi"><svg viewBox="-12 -14 ' + (W + 24) + ' ' + (H + 14) + '" role="img" aria-label="Hémicycle : votre accord avec chaque groupe">' + parts +
      // Au centre : l'accord avec le groupe le plus proche, ou avec le groupe touché.
      (top ? '<text class="vz-c1" x="' + cx + '" y="' + (cy - 14) + '" text-anchor="middle" font-family="var(--serif)" font-size="30" fill="var(--fg)" data-def="' + top.pct + ' %">' + top.pct + ' %</text><text class="vz-c2" x="' + cx + '" y="' + (cy + 4) + '" text-anchor="middle" font-size="10.5" fill="var(--muted)" data-def="d\'accord avec ' + esc(top.c.replace('-NFP', '')) + '">d\'accord avec ' + esc(top.c.replace('-NFP', '')) + '</text>' : '') +
      '</svg><div class="vz-tip" hidden></div></div>';
  }
  // Image à partager (1080 × 1080) : la phrase, l'hémicycle de la personne tel qu'affiché, et l'adresse de la page.
  function image(svg, g, fin) {
    try {
      var cs = getComputedStyle(document.documentElement), v = function (n) { return cs.getPropertyValue(n).trim(); };
      var sans = getComputedStyle(document.body).fontFamily, serif = v('--serif') || 'Georgia, serif';
      var copie = svg.cloneNode(true);
      Array.prototype.forEach.call(copie.querySelectorAll('.vz-c1, .vz-c2'), function (t) { t.remove(); });
      copie.setAttribute('xmlns', 'http://www.w3.org/2000/svg'); copie.setAttribute('font-family', 'Helvetica Neue, Helvetica, Arial, sans-serif'); copie.setAttribute('width', '960'); copie.setAttribute('height', '535');
      var src = new XMLSerializer().serializeToString(copie).replace(/var\((--[\w-]+)\)/g, function (m, n) { return v(n) || '#888'; });
      var img = new Image();
      img.onload = function () {
        var c = document.createElement('canvas'); c.width = 1080; c.height = 1080;
        var x = c.getContext('2d'), fg = v('--fg') || '#0b1530', mu = v('--muted') || '#5b6275';
        var ajuste = function (t, taille, poids, police, larg) { do { x.font = poids + ' ' + taille + 'px ' + police; taille -= 2; } while (x.measureText(t).width > larg && taille > 20); };
        x.fillStyle = v('--panel') || v('--bg') || '#fff'; x.fillRect(0, 0, 1080, 1080);
        x.textAlign = 'center'; x.fillStyle = mu; x.font = '600 26px ' + sans; x.fillText('MON HÉMICYCLE', 540, 92);
        x.fillStyle = fg; x.font = '400 66px ' + serif; x.fillText('Je vote à ' + g.pct + ' % comme', 540, 178);
        ajuste(g.n, 50, 700, sans, 980); x.fillText(g.n, 540, 248);
        x.drawImage(img, 60, 300, 960, 535);
        x.font = '400 72px ' + serif; x.fillText(g.pct + ' %', 540, 790);
        x.fillStyle = mu; x.font = '400 26px ' + sans; x.fillText('d\'accord avec ' + g.c.replace('-NFP', ''), 540, 826);
        x.font = '400 28px ' + sans; x.fillText('De vrais votes de l\'Assemblée nationale. Et vous ?', 540, 930);
        x.fillStyle = v('--fr') || '#2f5bd3'; x.font = '700 34px ' + sans; x.fillText('concret2027.fr/votez', 540, 986);
        c.toBlob(function (b) { fin(b); }, 'image/png');
      };
      img.onerror = function () { fin(null); };
      img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(src);
    } catch (e) { fin(null); }
  }
  // Par thème : les textes rattachés à une page de Concret par les mots de leur titre (même règle que la page La vie politique).
  var THEMES = [['finances', 'Finances publiques'], ['vie', 'Vie des Français'], ['sante', 'Santé'], ['education', 'Éducation'], ['securite', 'Sécurité et justice'], ['defense', 'Défense'], ['demographie', 'Démographie et migrations']], MIN_THEME = 3;
  // Mêmes icônes que le menu du site (commun/menu.js).
  var IC_TH = {
    vie: '<path d="M4 8h16l-1.5 11h-13z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>',
    finances: '<path d="M17 6.5A6.5 6.5 0 1 0 17 17.5"/><path d="M4 10.5h9"/><path d="M4 13.5h9"/>',
    sante: '<path d="M10 4h4v6h6v4h-6v6h-4v-6H4v-4h6z"/>',
    education: '<path d="M2 9l10-5 10 5-10 5z"/><path d="M6 11v5c3 2 9 2 12 0v-5"/>',
    securite: '<path d="M12 4v16"/><path d="M8 20h8"/><path d="M5 7h14"/><path d="M5 7l-3 6a3 3 0 0 0 6 0z"/><path d="M19 7l-3 6a3 3 0 0 0 6 0z"/>',
    defense: '<path d="M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6z"/>',
    demographie: '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><circle cx="17" cy="9" r="2.4"/><path d="M16 14.2c2.8.2 5 2.6 5 5.8"/>'
  };
  // Chaque thème : une barre à la couleur du groupe le plus proche, remplie à sa part d'accord (deux barres si presque à égalité) ;
  // avant trois votes, une barre grise qui avance vers le résultat.
  // Thèmes qui ont déjà un résultat (au moins trois votes) ; le bloc replié le dit, et reste ouvert d'un vote à l'autre s'il l'a été.
  var thOuvert = false;
  function prets(D) { return THEMES.filter(function (t) { var R = resultat(D, function (q) { return q.pg.indexOf(t[0]) >= 0; }); return R.nbCompte >= MIN_THEME && R.groupes.length; }).length; }
  function parTheme(D) {
    return THEMES.map(function (t) {
      var R = resultat(D, function (q) { return q.pg.indexOf(t[0]) >= 0; }), dispo = D.Q.filter(function (q) { return q.pg.indexOf(t[0]) >= 0; }).length;
      var top = R.groupes.filter(function (g, i) { return i < 2 && (R.groupes[0] || {}).pct - g.pct < 3; });
      var pret = R.nbCompte >= MIN_THEME && top.length;
      var corps = pret ? top.map(function (g) {
        var c = (D.G[g.c] || {}).coul || 'var(--fr)';
        // Le nom du groupe et sa part, dans une barre remplie d'une teinte pâle de sa couleur dans l'hémicycle.
        return '<span class="bb" title="' + esc(g.n) + ' (' + esc(g.c) + ') : ' + g.pct + ' %"><span class="fi" style="width:' + g.pct + '%;--c:' + c + '"></span>' +
          '<span class="lb"><span class="nm">' + esc(g.n) + '</span><b>' + g.pct + '\u00a0%</b></span></span>';
      }).join('') : '<span class="b vide"><i style="width:' + Math.round(100 * Math.min(R.nbCompte, MIN_THEME) / MIN_THEME) + '%"></i></span>' +
        '<span class="g att">' + (dispo ? 'Encore ' + Math.max(1, MIN_THEME - R.nbCompte) + ' vote' + (MIN_THEME - R.nbCompte > 1 ? 's' : '') + ' sur ce thème pour un résultat' : 'Pas encore de texte sur ce thème') + '</span>';
      return '<li><a class="t" href="/' + t[0] + '/"><i aria-hidden="true"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + IC_TH[t[0]] + '</svg></i>' + t[1] + '</a><span class="n">' + R.nb + ' sur ' + dispo + ' texte' + (dispo > 1 ? 's' : '') + '</span>' + corps + '</li>';
    }).join('');
  }
  function bilan(el, D) {
    style();
    var R = resultat(D), assez = R.nbCompte >= MIN;
    var liste = R.groupes.map(function (g, i) {
      var c = (D.G[g.c] || {}).coul || 'var(--fr)';
      return '<li' + (i >= 3 ? ' class="vz-plus3" hidden' : '') + '><i style="background:' + c + '"></i><span class="n">' + esc(g.n) + ' <small>' + esc(g.c) + '</small></span><span class="v">' + g.pct + ' %</span><span class="b"><i style="width:' + g.pct + '%;background:' + c + '"></i></span></li>';
    }).join('');
    // Écart de moins de 3 points avec le suivant : les deux groupes sont nommés, « presque à égalité ».
    var top = R.groupes.filter(function (g, i) { return i < 2 && (R.groupes[0] || {}).pct - g.pct < 3; });
    el.innerHTML = avis(D, R) + '<span class="eyebrow">Votre hémicycle' + (R.nb ? ' · ' + R.nb + ' vote' + (R.nb > 1 ? 's' : '') : '') + '</span>' +
      '<h2>' + (assez ? 'Vous votez le plus souvent comme ' + (top.length > 1 ? top.map(function (g) { return esc(g.n) + ' (' + g.pct + '\u00a0%)'; }).join(' et ') + (top[0].pct === top[1].pct ? ', à égalité' : ', presque à égalité') : 'le groupe ' + esc(top[0].n)) : 'Votre hémicycle se remplit à partir de ' + MIN + ' votes') + '</h2>' +
      hemicycle(D, assez ? R : null) +
      '<p class="vz-lire">Chaque groupe est à sa place dans l\'hémicycle, de la gauche à la droite. ' + (assez ? 'Plus sa part est colorée, plus vous votez comme lui. Touchez un groupe pour voir son nom.' : 'Encore ' + (MIN - R.nbCompte) + ' vote' + (MIN - R.nbCompte > 1 ? 's' : '') + ' : avant, le résultat dépendrait d\'un ou deux textes seulement.' + (R.unan ? ' Les textes que tous les groupes ont votés pareil ne comptent pas.' : '')) + '</p>' +
      (assez && R.unan ? '<p class="vz-lire">' + R.unan + ' de vos votes portaient sur des textes que tous les groupes ont votés de la même façon : vous étiez du même avis sur ' + R.unanComme + '. Ils ne comptent pas dans votre accord avec chaque groupe.</p>' : '') +
      (assez ? '<ul class="vz-bars">' + liste + '</ul>' + (R.groupes.length > 3 ? '<button type="button" class="vz-plus">Voir les ' + R.groupes.length + ' groupes</button>' : '') +
        '<details class="vz-th"' + (thOuvert ? ' open' : '') + '><summary><span>Par thème<small>' + prets(D) + ' thème' + (prets(D) > 1 ? 's' : '') + ' sur ' + THEMES.length + ' avec un résultat</small></span></summary><ul>' + parTheme(D) + '</ul><p class="vz-lire">Le groupe dont vos votes sont le plus proches sur chaque thème. « 2 sur 4 textes » : vous avez voté 2 des 4 textes du thème ; un texte voté plusieurs fois à l\'Assemblée est une seule question, avec son dernier vote. Le thème d\'un texte vient des mots de son titre (règle de la page La vie politique).</p></details>' +
        '<button type="button" class="vz-suite vz-partage">Partager mon résultat</button><p class="vz-lire vz-copie" hidden></p>' : '') +
      '<details class="vz-off"><summary>En détail : les groupes et le calcul</summary>' +
      '<p>' + D.groupes.filter(function (g) { return g.a != null; }).slice().sort(function (p, q) { return q.a - p.a; }).map(function (g) { return '<b>' + esc(g.c) + '</b> : ' + esc(g.n) + ' (' + g.m + ' députés)'; }).join(' · ') + '.</p>' +
      '<p>Le calcul (depuis le ' + dateFr(DATE_CALCUL) + ') : sur chaque texte, votre choix est comparé à celui de chaque député du groupe qui a voté ; une abstention compte pour moitié, d\'un côté comme de l\'autre. Par exemple, vous votez pour et le groupe a voté 60 pour, 30 contre et 10 abstentions : 65 % d\'accord sur ce texte. Le pourcentage est la moyenne sur vos votes. Ne comptent pas : un groupe dont moins de ' + VOTANTS_MIN + ' députés, ou moins d\'un quart des membres, ont voté ; les textes que tous les groupes ont votés de la même façon, qui ne disent pas de qui vous êtes proche. Censure : seuls les votes pour sont comptés, un député qui ne la vote pas est compté contre. Jusqu\'au 27 octobre 2026, seule comptait la position de la majorité du groupe, sur tous les textes.' +
      (assez ? ' Accord avec le résultat de l\'Assemblée : ' + R.assemblee + ' % de vos votes.' : '') + '</p>' +
      '<p>Place, couleur et nombre de députés de chaque groupe : plan officiel de l\'hémicycle et données ouvertes de l\'Assemblée nationale. Les ' + ((D.G.NI || {}).m || '') + ' députés non inscrits ne forment pas un groupe : ils ne sont pas dessinés. Vos votes restent sur cet appareil.</p></details>';
    var ok = el.querySelector('.vz-avis-ok'); if (ok) ok.addEventListener('click', function () { ecrireCalcul(); avisCalcul = false; var a = el.querySelector('.vz-avis'); if (a) a.remove(); });
    var tip = el.querySelector('.vz-tip'), box = el.querySelector('.vz-hemi');
    var montre = function (g, e) {
      var c1 = el.querySelector('.vz-c1'), c2 = el.querySelector('.vz-c2');
      if (c1) { c1.textContent = g && g.dataset.pct ? g.dataset.pct + ' %' : c1.dataset.def; c2.textContent = g && g.dataset.pct ? 'd\'accord avec ' + g.dataset.c : c2.dataset.def; }
      if (!g) { tip.hidden = true; return; }
      tip.innerHTML = g.getAttribute('data-info'); tip.hidden = false;
      var r = box.getBoundingClientRect(), x = (e && e.clientX != null ? e.clientX : g.getBoundingClientRect().left + g.getBoundingClientRect().width / 2) - r.left;
      tip.style.left = Math.max(4, Math.min(r.width - tip.offsetWidth - 4, x - tip.offsetWidth / 2)) + 'px';
    };
    Array.prototype.forEach.call(el.querySelectorAll('.vz-hs'), function (g) {
      g.addEventListener('pointerenter', function (e) { montre(g, e); });
      g.addEventListener('click', function (e) { montre(g, e); });
      g.addEventListener('focus', function () { montre(g); });
    });
    box.addEventListener('pointerleave', function () { montre(null); });
    // Partager : l'image de l'hémicycle et une ligne, seulement si la personne le demande (rien n'est envoyé au site).
    var pa = el.querySelector('.vz-partage');
    if (pa) pa.addEventListener('click', function () {
      var g = R.groupes[0], txt = 'Je vote à ' + g.pct + ' % comme le groupe ' + g.n + ' à l\'Assemblée. Et vous ?', url = 'https://concret2027.fr/votez/';
      var dit = el.querySelector('.vz-copie'), montrer = function (m) { dit.textContent = m; dit.hidden = false; };
      var texte = function () {
        if (navigator.share) return navigator.share({ text: txt, url: url }).catch(function () {});
        if (navigator.clipboard) navigator.clipboard.writeText(txt + ' ' + url).then(function () { montrer('Copié : collez-le où vous voulez.'); }, function () {});
      };
      image(el.querySelector('.vz-hemi svg'), g, function (blob) {
        if (!blob) return texte();
        var f = new File([blob], 'mon-hemicycle-concret.png', { type: 'image/png' });
        if (navigator.canShare && navigator.canShare({ files: [f] })) return navigator.share({ files: [f], text: txt + ' ' + url }).catch(function () {});
        // Ordinateur : l'image est enregistrée et la phrase copiée.
        var a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = f.name; document.body.appendChild(a); a.click(); a.remove();
        if (navigator.clipboard) navigator.clipboard.writeText(txt + ' ' + url).then(function () { montrer('Image enregistrée, phrase copiée : collez-les où vous voulez.'); }, function () { montrer('Image enregistrée.'); });
        else montrer('Image enregistrée.');
      });
    });
    var th = el.querySelector('.vz-th'); if (th) th.addEventListener('toggle', function () { thOuvert = th.open; });
    var plus = el.querySelector('.vz-plus');
    if (plus) plus.addEventListener('click', function () { Array.prototype.forEach.call(el.querySelectorAll('.vz-plus3'), function (li) { li.hidden = false; }); plus.remove(); });
    return R;
  }

  window.ConcretVotez = {
    MIN: MIN, SERIE: SERIE, THEMES: THEMES, MIN_THEME: MIN_THEME, dateFr: dateFr, moisFr: moisFr, nf: nf, esc: esc, CHOIX: CHOIX,
    charger: function () {
      var lire = function (u) { return fetch(u, { cache: 'no-cache' }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }); };
      if (!donnees) donnees = Promise.all([lire('/donnees/votes.json'), lire('/donnees/votez_explications.json')]).then(function (r) { var D = construire(r[0], r[1].explications || {}); decider(D); return D; });
      return donnees;
    },
    mes: lireMes,
    oublier: function (id) { var m = lireMes(); delete m[id]; ecrireMes(m); },
    effacer: function () { try { localStorage.removeItem(CLE); localStorage.removeItem(CLE_AV); } catch (e) {} },
    avant: lireAv,
    resultat: resultat, carte: carte, bilan: bilan,
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
        carte(zone, q, D, { apres: function () { var R = resultat(D); pied.innerHTML = (R.nbCompte >= MIN && R.groupes.length ? '<p class="note" style="font-size:14px">Sur vos ' + R.nb + ' votes, vous êtes le plus proche du groupe <b>' + esc(R.groupes[0].n) + '</b> (' + R.groupes[0].pct + ' %).</p>' : '') + lien; } });
      }).catch(function () {});
    }
  };
})();
