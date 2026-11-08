# À faire mardi 10 novembre 2026 (demandes de l'éditeur, 8 novembre 2026)

Pour l'éditeur : rien de tout cela n'est fait. Ce sont des idées à décider et à écrire mardi.

## 1. Articles de presse au toucher d'un nom
- Dans « Médias qui citent chaque candidat » (Baromètre, bloc Visibilité), toucher le nom d'un candidat déplie ses articles : titre, média, date, lien.
- Les données existent déjà dans l'archive de `outils/presse.py` (titre, lien, date, candidats ; jamais le texte). Reste la page.
- Aujourd'hui seuls les 3 derniers liens s'affichent, et seulement quand la courbe est active.

- Ajouter au-dessus des barres une ligne : « N médias sur 104 citent au moins un candidat » (aujourd'hui, hier, 7 jours), calculée dans la page à partir des médias par candidat (`medias_jours`). Un média non lu reste compté dans les 104, jamais zéro.
- Au toucher d'un nom : quelques articles (récents d'abord, avec média et lien) puis « Voir tous ». Repère du 8 novembre : Attal, 15 articles pour 5 médias.

## 2. Wikipédia : fenêtre de lissage
- Aujourd'hui : moyenne sur 28 jours qui finissent la veille, un point tous les 7 jours (`outils/wikipedia.py`, `range(28)`).
- Idée : l'objectif est de voir si les gens réagissent à l'actualité, donc une fenêtre plus courte convient mieux qu'aux sondages.
- Proposition à choisir : trois vues au toucher, par jour, moyenne sur 7 jours, moyenne sur 30 jours (l'API Wikimedia donne les lectures par jour).
- À décider : la vue par défaut (7 jours ?), le texte « 28 jours » sous la courbe et dans « Méthode », et le recalcul de l'archive.

## 3. Presse : médias sur 7 jours
- Même logique : mettre la presse et Wikipédia sur la même période (7 jours) pour les comparer et pour le tableau « Part de visibilité » (qui prend le dernier point Wikipédia et les articles des 7 derniers jours).
- La presse a déjà « Aujourd'hui / Hier / 7 derniers jours » ; à décider si 7 jours devient le choix par défaut.

## 4. Presse : suivis, panel, médias absents (8 novembre 2026)
- Règle des suivis ramenée à 30 jours de sondages (60 avant) : Royal, Faure, Guedj et Maurel sortent. À revoir : un minimum d'instituts ou de sondages pour sortir aussi Hollande et Villepin ?
- Panel passé de 104 à 108 médias : La Nouvelle République, La Voix du Nord, Capital, Contexte ajoutés (flux vérifiés le 8 novembre). Lecture des flux compressés corrigée dans `outils/presse.py`.
- Gros médias encore absents : Le Monde (conditions du flux : usage personnel seulement), Les Échos, Le Point, Le Télégramme (erreur 403, pas contourné), RTL, La Provence, Le Courrier picard (pas de flux trouvé). Décider : demande d'accès au flux auprès du média, ou les laisser en explication sur la page.
- Après une semaine de relevé : comparer le classement des candidats par famille de médias, pour voir si le panel penche d'un côté. Les 47 médias qui n'ont rien cité les 7 et 8 novembre sont surtout thématiques ; à revérifier sur une semaine.
