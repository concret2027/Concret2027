# Concret (concret2027.fr) : règles permanentes

Site non partisan qui note les présidents et les gouvernements, mission par mission, en comparant la France à ses voisins. Site statique (GitHub Pages, branche `main`).

## Règle absolue

Tout chiffre publié a une source, et il a été lu à cette source. Rien d'inventé, rien d'estimé sans le dire. En cas de doute, on garde l'ancienne valeur et on le signale.

## Aucun jugement

Concret est fact-based et non partisan : aucun titre, aucune phrase ne porte de jugement ni d'adjectif évaluatif (« généreux », « mal », « vit à crédit »…). Les titres disent ce qui est mesuré (« Espérance de vie », « Coût »), les chiffres et la règle de notation parlent seuls.

## Anonymat

- Commits : `git config user.name "Concret"` et `git config user.email "noreply@concret2027.fr"`. Aucune ligne `Co-Authored-By`, aucun nom ni e-mail personnel, nulle part (code, commits, journal).
- Ne jamais modifier le domaine dans Settings → Pages : GitHub y crée un commit au nom du compte personnel.

## Toute donnée non comptée, absente ou exceptionnelle s'explique là où on la voit

Chaque fois qu'une donnée n'est pas comptée, manque ou fait exception (changement de méthode de mesure, chiffre pas encore publié, début des séries, égalité à ½ point, candidat non testé, mandat trop court pour une note fiable, etc.), on l'explique en clair, à l'endroit même où le lecteur la voit, en une phrase courte : ce qui se passe, et pourquoi ça ne compte pas.

- Dans les tableaux : on affiche quand même les chiffres et l'écart s'ils existent, on écrit « non compté » dans la colonne du point, et la phrase d'explication juste en dessous.
- Pas de jargon (« rupture », « n.d. », « n.c. », « non comparable ») et pas de long paragraphe.
- Les phrases toutes faites sont dans `commun/notes.js` (`POURQUOI` : changement de méthode, pas encore publié, début des séries, absent, égalité) : les réutiliser sur toute page, y compris Santé, Sécurité et justice, Défense, Vie des Français.
- Un changement de méthode n'est retenu que s'il est signalé à la source (pour Eurostat, le code « b » dans les données), en précisant qui a changé (la France, la moyenne européenne, ou les deux : `br_motif` dans `data.json`).
- `outils/controle.js verifier` signale le jargon s'il réapparaît dans `data.json`.

## Où sont les données

**`data.json` contient `updated`, `updated_iso`, `datasets`, `series` et `textes`. Toute écriture doit relire le fichier entier, modifier ce qu'il faut et réécrire l'objet complet : ne jamais supprimer `series` ni `textes` (sans eux, les pages Finances, Éducation et l'accueil n'affichent plus rien).**

Les pages HTML ne contiennent pas de chiffres : seulement de la mise en forme et des calculs.

- `data.json`
  - `datasets` : les données vivantes (sondages, taux, chiffres du mois, actualité, agendas). Valeurs en chaînes de caractères.
  - `series.<page>` : les séries annuelles, les listes de gouvernements et de présidents (`GOVS`, `PRES`), les questions du jour (`QUIZ` ; `v` : la courbe qui donne la réponse, `d` : une ligne qui explique le terme technique de la question, à écrire pour toute nouvelle question qui en emploie un), les chiffres du jour fixes (`FACTS`), et les paramètres sourcés `P` (`{v, source, url, date}`).
  - `textes.<page>.<clé>` : les paragraphes chiffrés affichés dans les éléments `data-t="<clé>"` (le HTML garde la même version en secours).
- `commun/notes.js` : les règles de notation, la méthode affichée sur le site, en code. Utilisées par les pages, par l'accueil (classement général, recalculé à chaque visite) et par le contrôle. Une note n'est jamais saisie à la main.
- `donnees/calendrier.json` : chaque indicateur, sa fréquence, sa source exacte, sa cible dans `data.json`, sa dernière donnée et sa prochaine vérification.
- `outils/recits.js` : les titres et conclusions chiffrés de chaque page, avec leur vérification. Ils ne changent jamais sans validation.
- `outils/secu.py` : déficit de la Sécurité sociale (Assurance maladie et ensemble), lu par l'outil dans le dernier rapport de la Commission des comptes de la Sécurité sociale ; `python3 outils/secu.py` compare, `--ecrire` ajoute les années closes. Jamais de saisie à la main.
- `outils/ue_calc.py` : moyenne de l'UE calculée par Concret quand la source n'en publie pas (27 pays, mêmes données que la France ; l'évolution notée porte sur les pays qui publient les deux années, au moins 70 % de la population de l'UE, sinon l'année n'est pas comptée). `python3 outils/ue_calc.py` compare, `--ecrire` écrit. Jamais de saisie à la main.
- `outils/defense.py` : séries de la page Défense (Eurostat pour la dépense et l'investissement publics de défense ; classeur Excel de l'OTAN pour la dépense au sens de l'OTAN, la part de l'équipement et les militaires, années estimées marquées `est`, affichées sans être comptées). `python3 outils/defense.py` compare, `--ecrire` écrit ; puis `outils/ue_calc.py` pour les moyennes de l'UE. Jamais de saisie à la main.
- `outils/vie.py` : séries de la page Vie des Français (Eurostat pour la France, l'Allemagne, l'Espagne et la moyenne de l'UE, changements de méthode lus dans le code « b » ; moral des ménages de la Commission européenne, moyenne des douze mois de chaque année complète et chiffre du mois dans `datasets.vie_moral` ; indice de développement humain du PNUD, affiché sans note, dernière édition trouvée par l'outil). `python3 outils/vie.py` compare, `--ecrire` écrit ; puis `outils/ue_calc.py` pour les moyennes de l'UE calculées (avant 2010 pour l'enquête sur les conditions de vie, et l'IDH). Jamais de saisie à la main.
- `outils/sondages.py` : mentions obligatoires des sondages du Baromètre (loi du 19 juillet 1977) : retrouve la notice de chaque sondage à la Commission des sondages et en lit le commanditaire et la marge d'erreur (`datasets.sondages_notices`) ; `--ecrire` écrit. Le contrôle refuse un sondage sans notice, et tout nouveau sondage la veille et le jour d'un tour (silence électoral). Polymarket : affiché, jamais de lien vers son site (plateforme non autorisée en France).
- `quiz/index.html` : le quiz du jour, sans chiffre propre : la question du jour de chaque page (`series.<page>.QUIZ`, même tirage que la page, réponses comptées ensemble) et deux questions fabriquées à partir des notes de `commun/notes.js` (meilleur président, meilleur gouvernement d'une mission). Score et classement du jour comptés par Abacus (`commun/quiz.js`).
- `outils/controle.js` : `node outils/controle.js a-faire` (indicateurs dus aujourd'hui) et `node outils/controle.js verifier` (validation, notes, récits, journal, notification). Ne jamais publier si `verifier` sort en erreur.
- `donnees/notes.json` (notes de la dernière publication), `donnees/a_valider.json` (récits à valider), `journal/AAAA-MM.md` (détail de chaque mise à jour).

## Mise à jour quotidienne

La tâche planifiée « Concret — mise à jour quotidienne » (son texte de référence est dans `outils/prompt_tache.md`) ne touche jamais au HTML. Elle lit `a-faire`, ne traite que les indicateurs dus, met à jour `data.json` et `donnees/calendrier.json` selon les règles du calendrier, lance `verifier`, publie seulement si le contrôle passe, et envoie la notification qu'il produit (une ligne si tout va bien, une ligne par problème, une ligne par texte à valider).

- Textes factuels (`textes`, `FACTS`, `QUIZ`, `EVENTS`) : mis à jour automatiquement quand un indicateur lié change, en une phrase factuelle (ce qui a changé, de combien, selon quelle source), sans adjectif ni jugement.
- Récits (titres, conclusions, `og:description`) : jamais modifiés par la tâche. Quand `verifier` en signale un, il attend la validation dans `donnees/a_valider.json`.

## Règle pour toute nouvelle page, tout nouvel indicateur, toute nouvelle source

Santé, Sécurité et justice, Défense, Vie des Français, ou tout indicateur ajouté à une page existante :

1. Les données vont dans `data.json` (`series.<page>`, `datasets`, `P` avec source, `textes`), jamais en dur dans le HTML.
2. Chaque indicateur est inscrit dans `donnees/calendrier.json` (fréquence, source exacte, URL, cible, prochaine vérification, textes liés) pour être pris en compte par la mise à jour automatique.
3. La notation suit la même méthode que Finances et Éducation : chaque année, 1 point si la France progresse mieux que la moyenne de l'UE, ou si elle fait déjà mieux qu'elle cette année-là et ne se dégrade pas (« avance tenue » : une avance qui se maintient n'est pas pénalisée parce que des pays en retard rattrapent), 0 sinon, ½ en cas d'égalité. Pour une dépense, « ne se dégrade pas » se mesure hors inflation quand la série existe (`fr_reel`). Les résultats jugés sur cinq ans, PISA et les programmes (vaccins, dépistages) gardent la seule évolution ; un indice qui n'a pas de niveau comparable (revenu réel des ménages, 100 en 2008) compare seulement sa hausse en % (règle `croissance`). La référence est toujours une moyenne européenne : celle de l'UE publiée par la source, sinon la moyenne de l'UE calculée par `outils/ue_calc.py` ; jamais un pays seul choisi par nous (l'Allemagne, l'Espagne, les États-Unis sont affichés comme repères). Le contrôle refuse un critère noté comparé à un pays ; note sur 20 ; règle affichée sur la page. Elle est codée dans `commun/notes.js`, et la nouvelle mission est ajoutée à `MISSIONS` pour entrer dans le classement général de l'accueil.
4. Chaque titre ou conclusion chiffré est inscrit dans `outils/recits.js` avec sa vérification.
5. `outils/controle.js verifier` est étendu si besoin (plages plausibles des nouvelles séries) et doit passer avant publication.
6. Même exigence partout : chaque chiffre sourcé et vérifié, rien d'inventé.
7. Lisible par tous, sans se noyer dans les chiffres :
   - le premier écran donne la réponse : où en est la France face à ses voisins, et la note des présidents ;
   - au plus 5 thèmes notés par page, chacun avec au plus 5 indicateurs, mesurés chaque année de la même façon en France et chez ses voisins ; chaque thème a sa note, la note de la page est leur moyenne ;
   - peu de texte : un intitulé neutre par thème, un tableau France / voisin / ✓ ✗, une courbe ; définitions et sources repliées ;
   - ce qui est seulement affiché (pas de comparaison annuelle possible, source industrielle, indicateur secondaire) est replié, avec la raison écrite dessous ;
   - les leviers (dépense, accès, prévention) sont jugés année par année, les résultats (espérance de vie, mortalité) sur le temps long (l'année et les quatre suivantes), comme PISA en Éducation ;
   - juger la France seule est réservé aux cas sans comparaison possible, et c'est écrit en clair là où on le voit.

## Avant de publier une modification du site

- Après une modification de `commun/notes.js`, `commun/partage.js`, `commun/bref.js` (le bloc « En bref » en tête de chaque page) `commun/menu.js` (bouton « Menu » sur téléphone et bloc « Les autres pages » en bas de chaque page, liste des pages à tenir à jour quand une page s'ajoute) ou `commun/quiz.js` (réponses à la question du jour, comptées sans rien qui identifie la personne par le service de compteurs Abacus, en temps réel ; nombre et part de chaque option affichés dès 2 réponses), changer le numéro `?v=` de leur balise `<script>` dans toutes les pages (sinon les navigateurs gardent l'ancienne version jusqu'à 10 minutes).
- Les cartes d'aperçu des liens (`donnees/apercu/<page>.png`, balises `og:image` de chaque page) montrent les chiffres du bloc « En bref » et le classement général : `outils/apercu.js` les refait, lancé par `verifier` ; une carte n'est refaite que si son contenu change.
- L'index du moteur de recherche (`donnees/recherche.json`) reprend le texte affiché des pages, chiffres compris : `node outils/controle.js verifier` le refait à chaque mise à jour des données (la tâche quotidienne le publie avec `data.json`). Après une modification des pages HTML, il est refait au prochain `verifier`, ou tout de suite par `node outils/recherche.js`.
- Comparer le rendu avant et après (textes, graphiques, erreurs de console) et vérifier que les notes n'ont pas bougé, sauf si c'est le but.
- `node outils/controle.js verifier` doit passer.
