/* Formulaire de contact de Concret : écrit dans chaque élément [data-contact] (page Contact, bas de l'accueil).
   Le message est envoyé par Web3Forms, depuis le navigateur du visiteur, à la boîte de Concret (contact@concret2027.fr). */
(function () {
  var css = '.ct-form { display: grid; gap: 14px; }.ct-form label { display: grid; gap: 6px; font-size: 14px; font-weight: 600; }.ct-form label small { font-weight: 400; color: var(--muted); }.ct-form input, .ct-form select, .ct-form textarea { font: inherit; font-size: 16px; color: var(--fg); background: var(--bg); border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; width: 100%; box-sizing: border-box; }.ct-form textarea { min-height: 160px; resize: vertical; }.ct-form input:focus-visible, .ct-form select:focus-visible, .ct-form textarea:focus-visible { outline: 2px solid var(--fr); outline-offset: 1px; }.ct-envoyer { font: inherit; font-size: 15px; font-weight: 700; color: var(--bg); background: var(--fr); border: 0; border-radius: 999px; padding: 12px 22px; cursor: pointer; justify-self: start; min-height: 44px; }.ct-envoyer[disabled] { opacity: .6; cursor: default; }.ct-piege { position: absolute; left: -9999px; }.ct-etat { margin: 0; font-size: 14.5px; font-weight: 600; }.ct-etat.ok { color: var(--ok); } .ct-etat.ko { color: var(--bad); }';
  var FORM = '<form class="ct-form" id="ct-form" novalidate><label for="ct-sujet">Sujet<select id="ct-sujet" name="sujet"><option>Erreur dans un chiffre ou une source</option><option>Suggestion</option><option>Question</option><option>Autre</option></select></label><label for="ct-message">Message<textarea id="ct-message" name="message" required maxlength="5000"></textarea></label><label for="ct-email">Votre e-mail <small>(facultatif, seulement si vous voulez une réponse)</small><input id="ct-email" name="email" type="email" autocomplete="email" inputmode="email"></label><input class="ct-piege" type="checkbox" name="botcheck" id="ct-botcheck" tabindex="-1" autocomplete="off" aria-hidden="true"><button class="ct-envoyer" type="submit" id="ct-envoyer">Envoyer</button><p class="ct-etat" id="ct-etat" role="status" aria-live="polite"></p></form>';
  function init() {
    var box = document.querySelector('[data-contact]'); if (!box) return;
    if (!document.getElementById('ct-css')) { var st = document.createElement('style'); st.id = 'ct-css'; st.textContent = css; document.head.appendChild(st); }
    box.innerHTML = FORM;
    var CLE = 'af6f46d5-2f1c-441c-b116-5fdb795ac8d6';
    var f = document.getElementById('ct-form'), etat = document.getElementById('ct-etat'), bt = document.getElementById('ct-envoyer');
    var dire = function (t, c) { etat.textContent = t; etat.className = 'ct-etat ' + (c || ''); };
    // Lecteur d'écran : la case à corriger est marquée, avec le message d'erreur comme description.
    var marquer = function (champ) { [f.message, f.email].forEach(function (x) { if (x === champ) { x.setAttribute('aria-invalid', 'true'); x.setAttribute('aria-describedby', 'ct-etat'); } else { x.removeAttribute('aria-invalid'); x.removeAttribute('aria-describedby'); } }); };
    [f.message, f.email].forEach(function (x) { x.addEventListener('input', function () { if (x.getAttribute('aria-invalid')) marquer(null); }); });
    f.addEventListener('submit', function (e) {
      e.preventDefault();
      var msg = f.message.value.trim(), mail = f.email.value.trim();
      if (msg.length < 5) { dire('Écrivez votre message avant d\'envoyer.', 'ko'); marquer(f.message); f.message.focus(); return; }
      if (mail && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(mail)) { dire('Cet e-mail ne semble pas complet ; corrigez-le ou laissez la case vide.', 'ko'); marquer(f.email); f.email.focus(); return; }
      marquer(null);
      if (f.botcheck.checked) return;
      bt.disabled = true; dire('Envoi…');
      fetch('https://api.web3forms.com/submit', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ access_key: CLE, subject: 'Concret : ' + f.sujet.value, from_name: 'Formulaire de concret2027.fr', sujet: f.sujet.value, message: msg, email: mail || 'non donné', page: document.referrer || '' }) })
        .then(function (r) { return r.json(); })
        .then(function (r) {
          if (!r.success) throw new Error(r.message);
          f.reset(); dire('Message envoyé. Merci' + (mail ? ' ; la réponse viendra à l\'adresse indiquée.' : '.'), 'ok');
        })
        .catch(function () { dire('L\'envoi n\'a pas abouti. Réessayez dans un moment ; votre message est toujours dans la case.', 'ko'); })
        .then(function () { bt.disabled = false; });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
