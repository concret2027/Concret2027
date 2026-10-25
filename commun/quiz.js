/* Question du jour : chaque réponse est comptée sans rien qui identifie la personne (un événement GoatCounter par
   question et par option), puis la page affiche combien de personnes ont répondu et la part de chaque option, à partir
   de SEUIL réponses (en dessous, une phrase le dit). Les totaux sont relus au compteur public de GoatCounter, qui les garde en cache jusqu'à quatre heures :
   juste après un clic, la réponse de la personne est ajoutée à ce qu'il renvoie. Si le compteur ne répond pas, rien ne
   s'affiche en plus. Chaque page appelle ConcretQuiz.repondu(page, Q, choix, nouveau) dans sa fonction reveal. */
(function () {
  var COMPTEUR = 'https://concret2027.goatcounter.com/counter/', SEUIL = 2;
  var css = '.opt .qz-pc{display:block;margin-top:2px;font-size:12px;font-weight:500;color:var(--muted);text-decoration:none;font-variant-numeric:tabular-nums}' +
    '.opt.qz-bar{background-image:linear-gradient(90deg,var(--line) 0,var(--line) var(--qz,0%),transparent var(--qz,0%));background-repeat:no-repeat;background-size:100% 4px;background-position:0 100%}' +
    '.qz-res{margin:8px 0 0;font-size:13px;color:var(--muted)}';
  // Un identifiant court et stable pour la question (son texte) : la même question tirée un autre jour garde ses totaux.
  var empreinte = function (t) { var h = 5381; for (var i = 0; i < t.length; i++) h = ((h * 33) ^ t.charCodeAt(i)) >>> 0; return h.toString(36); };
  var chemin = function (page, Q, i) { return 'quiz-' + page + '-' + empreinte(Q.q) + '-' + i; };

  function compter(page, Q, i) {
    var ev = { path: chemin(page, Q, i), title: 'Question du jour (' + page + ') : ' + Q.o[i], event: true }, n = 0;
    var t = setInterval(function () {
      if (window.goatcounter && window.goatcounter.count) { clearInterval(t); window.goatcounter.count(ev); }
      else if (++n > 40) clearInterval(t);
    }, 250);
  }

  // Le total d'une option : 404 = personne n'a encore choisi cette option ; toute autre erreur (compteur fermé, hors ligne) = rien.
  function lire(p) {
    return fetch(COMPTEUR + encodeURIComponent(p) + '.json').then(function (r) {
      if (r.status === 404) return 0;
      if (!r.ok) throw new Error(r.status);
      return r.json().then(function (j) { return +String(j.count).replace(/\D/g, '') || 0; });
    });
  }

  function afficher(Q, opts, ans, n, choix, nouveau) {
    if (nouveau) n[choix]++;
    var tot = n.reduce(function (a, b) { return a + b; }, 0); if (!tot) return;
    var p = document.getElementById('quiz-res') || ans.parentNode.insertBefore(document.createElement('p'), ans.nextSibling);
    p.id = 'quiz-res'; p.className = 'qz-res';
    if (tot < SEUIL) { p.textContent = 'Les pourcentages s\'affichent dès ' + SEUIL + ' réponses. Une réponse peut mettre jusqu\'à 4 heures à apparaître dans le total.'; return; }
    Array.prototype.forEach.call(opts.children, function (b, i) {
      var pc = Math.round(100 * n[i] / tot), s = b.querySelector('.qz-pc') || b.appendChild(document.createElement('span'));
      s.className = 'qz-pc'; s.textContent = pc + ' % des réponses'; b.classList.add('qz-bar'); b.style.setProperty('--qz', pc + '%');
    });
    p.textContent = (tot === 1 ? '1 personne a répondu à cette question' : tot.toLocaleString('fr-FR') + ' personnes ont répondu à cette question') +
      (nouveau ? ', vous compris' : '') + '. Réponses comptées de façon anonyme ; une réponse peut mettre jusqu\'à 4 heures à apparaître.';
  }

  // nouveau : la personne vient de cliquer (sinon la page rappelle une réponse déjà donnée sur cet appareil).
  function repondu(page, Q, choix, nouveau) {
    var opts = document.getElementById('quiz-opts'), ans = document.getElementById('quiz-a'); if (!opts || !ans || !window.fetch) return;
    if (!document.getElementById('quiz-css')) { var st = document.createElement('style'); st.id = 'quiz-css'; st.textContent = css; document.head.appendChild(st); }
    if (nouveau) compter(page, Q, choix);
    Promise.all(Q.o.map(function (o, i) { return lire(chemin(page, Q, i)); }))
      .then(function (n) { afficher(Q, opts, ans, n, choix, nouveau); })
      .catch(function () {});
  }
  window.ConcretQuiz = { repondu: repondu, chemin: chemin };
})();
