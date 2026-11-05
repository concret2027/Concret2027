/* « Les grandes lois » : ce que chaque gouvernement a fait voter depuis juin 2012, mission par mission, sans calcul.
   Données : series.politique.GRANDES et P.mots de data.json (outils/parlement.py, données ouvertes de l'Assemblée nationale).
   Usage : <div data-lois="securite"></div> (une mission) ou <div data-lois="toutes"></div> (onglets par mission, page La vie politique).
   Le bloc se remplit à sa première ouverture (ou tout de suite s'il est visible) : data.json est déjà dans le cache du navigateur. */
(function () {
  var MISSIONS = [['finances', 'Finances'], ['sante', 'Santé'], ['vie', 'Vie des Français'], ['education', 'Éducation'], ['securite', 'Sécurité et justice'], ['defense', 'Défense'], ['demographie', 'Démographie'], ['autres', 'Autres']];
  var NOM = {}; MISSIONS.forEach(function (m) { NOM[m[0]] = m[1]; });
  var MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
  var MC = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'];
  var esc = function (t) { return String(t == null ? '' : t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;'); };
  var dl = function (d) { return (+d.slice(8) === 1 ? '1er' : +d.slice(8)) + ' ' + MOIS[+d.slice(5, 7) - 1] + ' ' + d.slice(0, 4); };
  var dc = function (d) { return MC[+d.slice(5, 7) - 1] + ' ' + d.slice(0, 4); };
  var nf = function (v) { return new Intl.NumberFormat('fr-FR').format(v); };
  var css = '.lo-onglets{display:flex;flex-wrap:wrap;gap:6px;margin:2px 0 4px}' +
    '.lo-onglets button{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--bg);color:var(--fg);padding:6px 12px;border-radius:999px;cursor:pointer;min-height:36px}' +
    '.lo-onglets button[aria-pressed="true"]{background:var(--fg);color:var(--bg);border-color:var(--fg)}.lo-onglets small{opacity:.7}' +
    '.lo-gov{border-top:1px solid var(--line)}.lo-gov>summary{cursor:pointer;list-style:none;display:flex;justify-content:space-between;align-items:center;gap:10px;padding:9px 0;min-height:44px;box-sizing:border-box}' +
    '.lo-gov>summary::-webkit-details-marker{display:none}.lo-gov>summary b{font-size:15px}.lo-gov>summary .lo-per{font-size:13px;color:var(--muted)}' +
    '.lo-n{font-weight:700;color:var(--fr);white-space:nowrap;font-size:14px}.lo-n::after{content:"\\00a0▾"}.lo-gov[open] .lo-n::after{content:"\\00a0▴"}' +
    '.lo-gov.vide>summary{cursor:default}.lo-gov.vide .lo-n{color:var(--muted);font-weight:500}.lo-gov.vide .lo-n::after{content:""}' +
    '.lo-liste{list-style:none;margin:0 0 12px;padding:0;display:grid;gap:12px}.lo-liste li{font-size:14px;line-height:1.4}.lo-liste li b{font-weight:600}' +
    '.lo-m{display:flex;flex-wrap:wrap;gap:2px 12px;font-size:12.5px;color:var(--muted);margin-top:3px}.lo-m a{color:inherit}.lo-m a.lo-pg{color:var(--fr);font-weight:600;text-decoration:none}' +
    '.lo-regle>summary{cursor:pointer;font-size:13px;font-weight:600;color:var(--fr);list-style:none;min-height:32px;display:inline-flex;align-items:center}.lo-regle>summary::-webkit-details-marker{display:none}' +
    '.lo-regle>summary::after{content:"\\00a0▾"}.lo-regle[open]>summary::after{content:"\\00a0▴"}.lo-regle p{margin:4px 0 0;font-size:13.5px;line-height:1.45}';

  var donnees = null;
  function charger() {
    if (!donnees) donnees = fetch('/data.json', { cache: 'force-cache' }).then(function (r) { return r.json(); }).then(function (D) { return (D.series || {}).politique; });
    return donnees;
  }

  // Gouvernements : de la nomination d'un Premier ministre (frise de la page La vie politique) à celle du suivant, depuis 2012.
  function gouvernements(PO) {
    var G = [];
    PO.FRISE.filter(function (e) { return e.k === 'gouvernement'; }).forEach(function (e) {
      var n = e.t.replace(/ nommée? Premi.*$/, ''), g = G[G.length - 1];
      if (!g || g.n !== n) G.push({ n: n, de: e.d });
    });
    G.forEach(function (g, i) { g.a = G[i + 1] ? G[i + 1].de : null; });
    return G.filter(function (g) { return !g.a || g.a > '2012-06-20'; }).reverse();
  }

  function motif(l) {
    var v = l.sc, t = [];
    if (l.motif === 'budget') t.push(l.a493 ? 'budget, adopté par l\'article 49.3' : 'budget');
    else if (l.motif === 'sol' && v) t.push('vote solennel du ' + dl(v.d) + ' : ' + nf(v.p) + ' pour, ' + nf(v.c) + ' contre');
    else if (l.motif === '493') t.push('adoptée sans vote, par l\'article 49.3');
    if (l.cc) t.push('soumise au Conseil constitutionnel');
    return t.join(' · ');
  }

  function liste(L, PO, avecPages) {
    var G = gouvernements(PO);
    return G.map(function (g) {
      var mine = L.filter(function (l) { return l.d >= g.de && (!g.a || l.d < g.a); });
      var per = g.a ? dc(g.de) + ' à ' + dc(g.a) : 'depuis ' + dc(g.de);
      return '<details class="lo-gov' + (mine.length ? '' : ' vide') + '"><summary' + (mine.length ? '' : ' tabindex="-1"') + '><span><b>' + esc(g.n) + '</b> <span class="lo-per">· ' + per + '</span></span><span class="lo-n">' + (mine.length ? mine.length + ' loi' + (mine.length > 1 ? 's' : '') : 'aucune') + '</span></summary>' +
        (mine.length ? '<ul class="lo-liste">' + mine.map(function (l) {
          var pages = avecPages ? (l.pg || []).map(function (p) { return '<a class="lo-pg" href="/' + p + '/">' + esc(NOM[p]) + ' →</a>'; }).join('') : '';
          return '<li><b>Loi n° ' + esc(l.code) + '</b> du ' + dl(l.d) + ' ' + esc(l.t) + '<div class="lo-m"><span>' + esc(motif(l)) + '</span>' +
            (l.sc ? '<a href="https://www.assemblee-nationale.fr/dyn/' + l.leg + '/scrutins/' + l.sc.n + '">le scrutin</a>' : '') +
            '<a href="https://www.assemblee-nationale.fr/dyn/' + l.leg + '/dossiers/' + esc(l.dos) + '">le dossier</a>' + pages + '</div></li>';
        }).join('') + '</ul>' : '') + '</details>';
    }).join('');
  }

  function regle(PO, mission) {
    var mots = (PO.P.mots || {})[mission];
    return '<details class="lo-regle"><summary>Comment les lois sont choisies</summary>' +
      '<p>Une grande loi est une loi publiée au Journal officiel qui remplit au moins un de ces critères : un vote solennel à l\'Assemblée nationale (sa Conférence des présidents le réserve aux textes qu\'elle juge importants), une adoption par l\'article 49.3, une saisine du Conseil constitutionnel par des parlementaires ou l\'exécutif, ou un budget (loi de finances, budget de la Sécurité sociale).</p>' +
      (mission === 'toutes' ? '<p>Une loi est rattachée à une mission par les mots de son titre (liste sur chaque page de mission) ; les budgets de l\'État vont aux Finances, ceux de la Sécurité sociale à la Santé et à la Vie des Français. Une loi peut compter pour plusieurs missions ; celles qui n\'entrent dans aucune sont dans « Autres ».</p>'
        : mots ? '<p>Elle est rattachée à cette page quand son titre contient un de ces mots : ' + mots.map(esc).join(', ') + (mission === 'finances' ? ' ; et chaque budget de l\'État' : mission === 'sante' || mission === 'vie' ? ' ; et chaque budget de la Sécurité sociale' : '') + '.</p>' : '') +
      '<p>Chaque loi est comptée pour le gouvernement en place le jour de sa promulgation. Avant juin 2012 (Jacques Chirac, Nicolas Sarkozy), les données ouvertes de l\'Assemblée nationale ne couvrent pas ces années. Pas de résultat sur 20 : un nombre de lois n\'est ni bon ni mauvais.</p>' +
      '<p>Source : <a href="' + esc(PO.P.grandes.url) + '">' + esc(PO.P.grandes.source) + '</a>.</p></details>';
  }

  function remplir(box) {
    if (box.dataset.fait) return; box.dataset.fait = '1';
    box.innerHTML = '<p class="note">Chargement…</p>';
    charger().then(function (PO) {
      if (!PO || !PO.GRANDES) { box.innerHTML = '<p class="note">Les lois ne sont pas disponibles pour le moment.</p>'; return; }
      var mission = box.getAttribute('data-lois'), GL = PO.GRANDES;
      if (mission !== 'toutes') {
        var L = GL.filter(function (l) { return (l.pg || []).indexOf(mission) >= 0; });
        box.innerHTML = '<p class="note">' + L.length + ' grandes lois depuis juin 2012 pour ce thème, gouvernement par gouvernement. Touchez un nombre pour voir les lois.</p>' + liste(L, PO, false) + regle(PO, mission);
      } else {
        var par = function (m) { return GL.filter(function (l) { return m === 'tout' ? true : m === 'autres' ? !(l.pg || []).length : (l.pg || []).indexOf(m) >= 0; }); };
        var ong = [['tout', 'Toutes']].concat(MISSIONS);
        box.innerHTML = '<div class="lo-onglets" role="group" aria-label="Choisir une mission">' + ong.map(function (m, i) { return '<button type="button" data-m="' + m[0] + '" aria-pressed="' + (i === 0) + '">' + esc(m[1]) + ' <small>' + par(m[0]).length + '</small></button>'; }).join('') + '</div><div class="lo-corps"></div>' + regle(PO, 'toutes');
        var corps = box.querySelector('.lo-corps'), voir = function (m) { corps.innerHTML = liste(par(m), PO, true); };
        box.querySelector('.lo-onglets').addEventListener('click', function (e) {
          var b = e.target.closest('button'); if (!b) return;
          Array.prototype.forEach.call(this.children, function (x) { x.setAttribute('aria-pressed', x === b); }); voir(b.dataset.m);
        });
        voir('tout');
      }
      Array.prototype.forEach.call(box.querySelectorAll('.lo-gov.vide>summary'), function (s) { s.addEventListener('click', function (e) { e.preventDefault(); }); });
      var t = document.querySelector('[data-lois-teaser]');
      if (t && mission !== 'toutes') t.textContent = box.querySelectorAll('.lo-liste li').length + ' grandes lois depuis 2012, gouvernement par gouvernement';
    }).catch(function () { box.dataset.fait = ''; box.innerHTML = '<p class="note">Les lois n\'ont pas pu être chargées. Rouvrez le bloc dans un moment.</p>'; });
  }

  function init() {
    var boxes = document.querySelectorAll('[data-lois]'); if (!boxes.length) return;
    if (!document.getElementById('lo-css')) { var st = document.createElement('style'); st.id = 'lo-css'; st.textContent = css; document.head.appendChild(st); }
    Array.prototype.forEach.call(boxes, function (box) {
      var d = box.closest('details');
      if (!d || d.open) remplir(box);
      if (d) d.addEventListener('toggle', function () { if (d.open) remplir(box); });
    });
  }
  window.ConcretLois = { remplir: remplir };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
