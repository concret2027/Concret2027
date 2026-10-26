/* Question du jour : chaque réponse est comptée sans rien qui identifie la personne (le compteur de Concret, un petit
   programme Cloudflare Workers avec une base D1 : outils/compteur_worker.js ; il ne garde qu'un total par option), en temps
   réel, puis la page affiche combien de personnes ont répondu et la part de chaque option, à partir de SEUIL réponses (en
   dessous, une phrase le dit). Si le compteur ne répond pas, rien ne s'affiche en plus. Chaque page appelle
   ConcretQuiz.repondu(page, Q, choix, nouveau) dans sa fonction reveal ; Q.v (facultatif) est l'identifiant de la courbe ou
   du chiffre de la page qui donne la réponse, vérifié par outils/controle.js. */
(function () {
  var API = 'https://compteur.square-brook-9d65.workers.dev/', SEUIL = 2;
  var css = '.opt .qz-pc{display:inline-block;width:100%;margin-top:2px;font-size:12px;font-weight:500;color:var(--muted);text-decoration:none;font-variant-numeric:tabular-nums}' +
    '.opt.qz-bar{background-image:linear-gradient(90deg,var(--line) 0,var(--line) var(--qz,0%),transparent var(--qz,0%));background-repeat:no-repeat;background-size:100% 4px;background-position:0 100%}' +
    '.qz-aide{margin:-4px 0 2px;font-size:13.5px;line-height:1.4;color:var(--muted)}.qz-res{margin:8px 0 0;font-size:13px;color:var(--muted)}.qz-voir{font-weight:600;white-space:nowrap;color:var(--fr)}';
  // Un identifiant court et stable pour la question (son texte) : la même question tirée un autre jour garde ses totaux.
  var empreinte = function (t) { var h = 5381; for (var i = 0; i < t.length; i++) h = ((h * 33) ^ t.charCodeAt(i)) >>> 0; return h.toString(36); };
  var chemin = function (page, Q) { return 'quiz-' + page + '-' + empreinte(Q.q); };

  // op : 'hit' (ajoute 1 à l'option i et renvoie les totaux de toutes les options) ou 'get' (lit les totaux) ; n : nombre d'options.
  // En cas d'erreur du réseau ou du serveur, deux nouveaux essais, espacés.
  function compteur(op, cle, n, i) {
    var u = API + op + '?k=' + encodeURIComponent(cle) + '&n=' + n + (op === 'hit' ? '&i=' + i : '');
    var essai = function (k) {
      return fetch(u, { method: op === 'hit' ? 'POST' : 'GET', cache: 'no-store' }).then(function (x) {
        if (x.status === 429 || x.status >= 500) { var e = new Error(x.status); e.reessayer = true; throw e; }
        if (!x.ok) throw new Error(x.status);
        return x.json();
      }).then(function (j) { return j.v; }, function (e) {
        if ((e.reessayer || e instanceof TypeError) && k < 2) return new Promise(function (r) { setTimeout(r, 1500 * (k + 1)); }).then(function () { return essai(k + 1); });
        throw e;
      });
    };
    return essai(0);
  }

  // Les totaux de chaque option ; si la personne vient de répondre, son choix est compté.
  function totaux(page, Q, choix, nouveau) { return compteur(nouveau ? 'hit' : 'get', chemin(page, Q), Q.o.length, choix); }

  function afficher(opts, ans, n, nouveau) {
    var tot = n.reduce(function (a, b) { return a + b; }, 0); if (!tot) return;
    var p = ans.qzRes || (ans.qzRes = ans.parentNode.insertBefore(document.createElement('p'), ans.nextSibling));
    p.className = 'qz-res';
    if (tot < SEUIL) { p.textContent = (nouveau ? 'Vous êtes la première personne à répondre à cette question. ' : '') + 'Les pourcentages s\'affichent dès ' + SEUIL + ' réponses.'; return; }
    Array.prototype.forEach.call(opts.children, function (b, i) {
      var pc = Math.round(100 * n[i] / tot), s = b.querySelector('.qz-pc') || b.appendChild(document.createElement('span'));
      s.className = 'qz-pc'; s.textContent = pc + ' % des réponses'; b.classList.add('qz-bar'); b.style.setProperty('--qz', pc + '%');
    });
    p.textContent = tot.toLocaleString('fr-FR') + ' personnes ont répondu à cette question' + (nouveau ? ', vous compris' : '') + '. Réponses comptées de façon anonyme.';
  }

  function style() { if (!document.getElementById('quiz-css')) { var st = document.createElement('style'); st.id = 'quiz-css'; st.textContent = css; document.head.appendChild(st); } }
  // Q.d (facultatif) : une ligne qui explique le terme technique de la question, affichée sous la question avant la réponse.
  function aide(Q, qEl) {
    if (!Q || !Q.d || !qEl || (qEl.nextElementSibling && qEl.nextElementSibling.className === 'qz-aide')) return;
    style(); var p = document.createElement('p'); p.className = 'qz-aide'; p.textContent = Q.d; qEl.parentNode.insertBefore(p, qEl.nextSibling);
  }

  // nouveau : la personne vient de cliquer (sinon la page rappelle une réponse déjà donnée sur cet appareil).
  // el (facultatif) : { opts, ans } quand la page a plusieurs questions ; sinon #quiz-opts et #quiz-a.
  function repondu(page, Q, choix, nouveau, el) {
    var opts = el ? el.opts : document.getElementById('quiz-opts'), ans = el ? el.ans : document.getElementById('quiz-a');
    if (!opts || !ans || !window.fetch || !window.Promise) return Promise.resolve(null);
    style();
    // Le lien vers la courbe ou le chiffre de la page qui donne la réponse (Q.v : son identifiant).
    var cible = Q.v && document.getElementById(Q.v);
    if (cible && !ans.querySelector('.qz-voir')) {
      var a = document.createElement('a'); a.className = 'qz-voir'; a.href = '#' + Q.v;
      a.textContent = /^ch-|chart/.test(Q.v) ? 'Vérifier sur la courbe ↓' : 'Vérifier sur la page ↓';
      a.addEventListener('click', function (ev) { if (window.ConcretBref) { ev.preventDefault(); ConcretBref.aller(Q.v); } });
      ans.appendChild(document.createTextNode(' ')); ans.appendChild(a);
    }
    // Sur une page de mission, un lien vers le quiz complet du jour.
    if (!el && !ans.querySelector('.qz-tout')) {
      var t = document.createElement('a'); t.className = 'qz-voir qz-tout'; t.href = '/quiz/'; t.textContent = 'Toutes les questions du jour →';
      ans.appendChild(document.createTextNode(' ')); ans.appendChild(t);
    }
    return totaux(page, Q, choix, nouveau).then(function (n) { afficher(opts, ans, n, nouveau); return n; }, function () { return null; });
  }
  window.ConcretQuiz = { repondu: repondu, chemin: chemin, compteur: compteur, aide: aide, api: API };
})();
