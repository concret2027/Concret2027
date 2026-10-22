# Concret (concret2027.fr) : règles permanentes

Site non partisan qui note les présidents et les gouvernements, mission par mission, en comparant la France à ses voisins. Site statique (GitHub Pages, branche `main`).

## Règle absolue

Tout chiffre publié a une source, et il a été lu à cette source. Rien d'inventé, rien d'estimé sans le dire. En cas de doute, on garde l'ancienne valeur et on le signale.

## Anonymat

- Commits : `git config user.name "Concret"` et `git config user.email "noreply@concret2027.fr"`. Aucune ligne `Co-Authored-By`, aucun nom ni e-mail personnel, nulle part (code, commits, journal).
- Ne jamais modifier le domaine dans Settings → Pages : GitHub y crée un commit au nom du compte personnel.

## Où sont les données

Les pages HTML ne contiennent pas de chiffres : seulement de la mise en forme et des calculs.

- `data.json`
  - `datasets` : les données vivantes (sondages, taux, chiffres du mois, actualité, agendas). Valeurs en chaînes de caractères.
  - `series.<page>` : les séries annuelles, les listes de gouvernements et de présidents (`GOVS`, `PRES`), les questions du jour (`QUIZ`), les chiffres du jour fixes (`FACTS`), et les paramètres sourcés `P` (`{v, source, url, date}`).
  - `textes.<page>.<clé>` : les paragraphes chiffrés affichés dans les éléments `data-t="<clé>"` (le HTML garde la même version en secours).
- `commun/notes.js` : les règles de notation, la méthode affichée sur le site, en code. Utilisées par les pages, par l'accueil (classement général, recalculé à chaque visite) et par le contrôle. Une note n'est jamais saisie à la main.
- `donnees/calendrier.json` : chaque indicateur, sa fréquence, sa source exacte, sa cible dans `data.json`, sa dernière donnée et sa prochaine vérification.
- `outils/recits.js` : les titres et conclusions chiffrés de chaque page, avec leur vérification. Ils ne changent jamais sans validation.
- `outils/controle.js` : `node outils/controle.js a-faire` (indicateurs dus aujourd'hui) et `node outils/controle.js verifier` (validation, notes, récits, journal, notification). Ne jamais publier si `verifier` sort en erreur.
- `donnees/notes.json` (notes de la dernière publication), `donnees/a_valider.json` (récits à valider), `journal/AAAA-MM.md` (détail de chaque mise à jour).

## Mise à jour quotidienne

La tâche planifiée « Concret — mise à jour quotidienne (midi) » ne touche jamais au HTML. Elle lit `a-faire`, ne traite que les indicateurs dus, met à jour `data.json` et `donnees/calendrier.json` selon les règles du calendrier, lance `verifier`, publie seulement si le contrôle passe, et envoie la notification qu'il produit (une ligne si tout va bien, une ligne par problème, une ligne par texte à valider).

- Textes factuels (`textes`, `FACTS`, `QUIZ`, `EVENTS`) : mis à jour automatiquement quand un indicateur lié change, en une phrase factuelle (ce qui a changé, de combien, selon quelle source), sans adjectif ni jugement.
- Récits (titres, conclusions, `og:description`) : jamais modifiés par la tâche. Quand `verifier` en signale un, il attend la validation dans `donnees/a_valider.json`.

## Règle pour toute nouvelle page, tout nouvel indicateur, toute nouvelle source

Santé, Sécurité et justice, Défense, Vie des Français, ou tout indicateur ajouté à une page existante :

1. Les données vont dans `data.json` (`series.<page>`, `datasets`, `P` avec source, `textes`), jamais en dur dans le HTML.
2. Chaque indicateur est inscrit dans `donnees/calendrier.json` (fréquence, source exacte, URL, cible, prochaine vérification, textes liés) pour être pris en compte par la mise à jour automatique.
3. La notation suit la même méthode que Finances et Éducation : chaque année, 1 point si la France fait mieux que ses voisins, 0 sinon, ½ en cas d'égalité ; note sur 20 ; règle affichée sur la page. Elle est codée dans `commun/notes.js`, et la nouvelle mission est ajoutée à `MISSIONS` pour entrer dans le classement général de l'accueil.
4. Chaque titre ou conclusion chiffré est inscrit dans `outils/recits.js` avec sa vérification.
5. `outils/controle.js verifier` est étendu si besoin (plages plausibles des nouvelles séries) et doit passer avant publication.
6. Même exigence partout : chaque chiffre sourcé et vérifié, rien d'inventé.

## Avant de publier une modification du site

- Comparer le rendu avant et après (textes, graphiques, erreurs de console) et vérifier que les notes n'ont pas bougé, sauf si c'est le but.
- `node outils/controle.js verifier` doit passer.
