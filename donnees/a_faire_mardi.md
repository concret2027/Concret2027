# À faire mardi 10 novembre 2026 (demandes de l'éditeur, 8 novembre 2026)

Rien de tout cela n'est fait côté page. Ce sont des décisions et des écritures pour mardi. Tout ce qui touche à `outils/presse.py` ou à la liste des médias a déjà été fait le 8 novembre (voir « Déjà fait »).

## A. Page « Visibilité en ligne » (Baromètre)
1. **Articles au toucher d'un nom** (bloc « Médias qui citent chaque candidat ») : quelques articles (récents d'abord, avec média, date, lien), puis « Voir tous ». Les données existent (archive de `outils/presse.py` : titre, lien, date, candidats ; jamais le texte). Repère du 8 novembre : Attal, 15 articles pour 5 médias.
2. **Total de médias au-dessus des barres** : « N médias sur 115 citent au moins un candidat » (aujourd'hui, hier, 7 jours), calculé dans la page à partir de `medias_jours`. Un média non lu reste compté dans le total, jamais zéro. Repère du 8 novembre : 55 médias sur 104 le 7 novembre ; 57 distincts sur les deux jours.
3. **Une ligne qui dit que le panel a changé** (104 → 115, le 8 novembre) : l'éditeur a dit « pas obligé » ; à décider.

## B. Wikipédia : fenêtre de lissage
- Aujourd'hui : moyenne sur 28 jours finissant la veille, un point tous les 7 jours (`outils/wikipedia.py`, `range(28)`).
- Objectif de l'éditeur : voir si les gens réagissent à l'actualité, donc une fenêtre plus courte qu'aux sondages.
- Proposition : trois vues au toucher, par jour, moyenne sur 7 jours (défaut), moyenne sur 30 jours (l'API Wikimedia donne les lectures par jour).
- À décider : la vue par défaut, le texte « 28 jours » sous la courbe et dans « Méthode », le recalcul de l'archive.
- Même période (7 jours) pour la presse et Wikipédia, pour le tableau « Part de visibilité ».

## C. Presse : suivis et panel
- **Suivis** : règle ramenée à 30 jours de sondages (60 avant) le 8 novembre ; Royal, Faure, Guedj et Maurel sortent. Suivis aujourd'hui : Arthaud, Attal, Dupont-Aignan, Glucksmann, Le Pen, Lisnard, Mélenchon, Philippe, Retailleau, Roussel, Tondelier, Zemmour, Hollande, Villepin. À décider : un minimum d'instituts ou de sondages pour sortir aussi Hollande et Villepin ?
- **Mélenchon en tête** : le 7 novembre, 46 médias (Philippe 22, Le Pen 20) ; le 8, 41 médias (Philippe et Attal 25). Mots : « Bourget », « porte-parole », « Kremlin » : un événement et une polémique. Vérifier sur une semaine calme s'il reste en tête : sinon, regarder le panel.
- **Comparer le classement par famille de médias** après une semaine de relevé (audiovisuel public, privé, presse nationale, hebdos, sites, régionale), pour voir si le panel penche d'un côté. Les médias sans candidat les 7 et 8 novembre sont surtout thématiques ou militants ; à revérifier.

## D. Médias absents : GDELT (décision de l'éditeur à confirmer)
- Idée : compter Le Monde, Le Point et les médias sans flux via GDELT (base ouverte d'articles, interface DOC 2.0, `domain:lemonde.fr "Nom"`).
- Forme retenue (l'éditeur voulait ne pas nommer les médias ; refusé car contraire à la transparence du site) : une ligne séparée « Médias lus via GDELT » avec son total, sans nom ni titre ni lien ; la liste de ces médias est dans « Méthode, médias et limites » ; une phrase dit que GDELT cherche dans le texte de l'article, pas dans le titre et le chapeau. Jamais mélangé au classement des 115 médias à flux.
- Avant tout : essai d'une semaine pour Le Monde, Le Point (Les Échos est déjà dans le panel). GDELT a refusé nos requêtes le 8 novembre (limite : une requête toutes les 5 secondes) : à réessayer, avec 5 secondes entre chaque requête. Couverture incomplète et retard possibles : à mesurer avant de publier.

## E. Médias sans flux : ce qui reste (30)
- Déjà écartés par leurs conditions : Le Monde (flux réservé à un usage personnel), Brut (usage exclusivement personnel). En attente : Le Point (flux politique OK, CGU à lire).
- Groupe Centre France (La Montagne, L'Yonne républicaine, La République du Centre, Le Journal du Centre, Le Populaire du Centre, L'Écho républicain) : offre commerciale de flux, https://solutionspro.centrefrance.com/flux-dactualite/ ; décider si on demande un tarif. Groupe Ouest-France (Le Maine libre, Le Courrier de l'Ouest, Presse Océan) : aucun flux propre trouvé.
- Pas de flux d'articles : RTL, Arte, M6 Info, i24NEWS (illisible), Le Télégramme (403), Charlie Hebdo (403), La Provence (flux politique 403, société OK mais hors politique), Corse-Matin, Le Courrier picard, Nord Éclair, L'Éclair des Pyrénées, Quotidien de La Réunion, Libération Champagne, Presse Océan, Le Nouvel Économiste (XML invalide), Le 1, Management, Famille chrétienne, Blast (site injoignable depuis l'environnement : copier à la main le lien « Flux RSS articles » de blastinfo.fr).
- Courriel aux éditeurs : brouillon corrigé disponible (il dit ce qu'on fait vraiment : titres et chapeaux lus, titres conservés dans l'archive publique, quelques titres avec lien affichés). Ne pas l'envoyer aux médias déjà dans le panel. À envoyer, éventuellement, à Le Monde, Le Point, Brut, Centre France, une fois la page décidée (point A). Aucun avis juridique : si besoin, en demander un.

## Déjà fait le 8 novembre (pour mémoire)
- Panel passé de 104 à 115 médias (161 flux) : La Nouvelle République, La Voix du Nord, Capital, Contexte, Les Échos (flux FeedBurner), Var-Matin, Monaco-Matin, Socialter, La Vie, Le Berry républicain, Le Média ; flux Une d'Ouest-France. La Presse de la Manche écartée (publiée sur actu.fr, déjà dans le panel : comptée deux fois sinon). Lecture des flux compressés corrigée dans `outils/presse.py`.
- Le fichier de repli `donnees/presse.json` passe à 115 au relevé de 23 h 30 UTC.
- Tableau d'audience mis à jour à 11 h 55. Deux anciens fichiers à supprimer à la main (le système a refusé) : `066097581444a6d6b82d15c2542f5548` et `da9b2dab66b151e77f515047fc8a9889`.
- Non vérifié ce jour : sondages (notices listées jusqu'au 5 novembre, scores non relus), cambriolages et vols en Allemagne (BKA, tentative 5), trois explications Votez les lois (1624, 8280, 9241) pas en ligne.
