# À faire mardi 10 novembre 2026 (demandes de l'éditeur, 8 novembre 2026)

Pour l'éditeur : rien de tout cela n'est fait. Ce sont des idées à décider et à écrire mardi.

## 1. Articles de presse au toucher d'un nom
- Dans « Médias qui citent chaque candidat » (Baromètre, bloc Visibilité), toucher le nom d'un candidat déplie ses articles : titre, média, date, lien.
- Les données existent déjà dans l'archive de `outils/presse.py` (titre, lien, date, candidats ; jamais le texte). Reste la page.
- Aujourd'hui seuls les 3 derniers liens s'affichent, et seulement quand la courbe est active.

## 2. Wikipédia : fenêtre de lissage
- Aujourd'hui : moyenne sur 28 jours qui finissent la veille, un point tous les 7 jours (`outils/wikipedia.py`, `range(28)`).
- Idée : l'objectif est de voir si les gens réagissent à l'actualité, donc une fenêtre plus courte convient mieux qu'aux sondages.
- Proposition à choisir : trois vues au toucher, par jour, moyenne sur 7 jours, moyenne sur 30 jours (l'API Wikimedia donne les lectures par jour).
- À décider : la vue par défaut (7 jours ?), le texte « 28 jours » sous la courbe et dans « Méthode », et le recalcul de l'archive.

## 3. Presse : médias sur 7 jours
- Même logique : mettre la presse et Wikipédia sur la même période (7 jours) pour les comparer et pour le tableau « Part de visibilité » (qui prend le dernier point Wikipédia et les articles des 7 derniers jours).
- La presse a déjà « Aujourd'hui / Hier / 7 derniers jours » ; à décider si 7 jours devient le choix par défaut.
