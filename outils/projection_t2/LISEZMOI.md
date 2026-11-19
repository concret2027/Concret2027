# Projection du second tour Mélenchon – Le Pen (brouillon)

Reports de voix estimés bureau de vote par bureau de vote (régression écologique contrainte : chaque groupe
d'électeurs du premier tour se répartit entre gauche, RN et abstention/blanc/nul, total 100 %), sur les duels
gauche contre RN des législatives :

- 2024 : résultats définitifs par bureau de vote (ministère de l'Intérieur, data.gouv.fr) ; parti de chaque
  candidat d'union de la gauche lu sur les pages « Élections législatives de 2024 dans … » de Wikipédia
  (`partis.py`, `couleurs.py`) ; `build_bv.py` puis `reg_bv.py`.
- 2022 : résultats définitifs par bureau de vote (ministère de l'Intérieur) ; parti des candidats NUPES d'après
  « LEGIS-2022, codage des nuances politiques des candidats » (Sciences Po, data.gouv.fr) ; `build22.py`, `reg22.py`.
- Vérification hors échantillon (2024, communes) : erreur absolue moyenne 1,4 point par circonscription.
- Écartés : municipales 2026 (8 communes seulement en duel gauche contre RN, `mun26.py`) et Toulouse 2026
  (duel face au centre-droit, pas au RN, `toulouse.py`).

Résultat écrit dans `donnees/projection_t2.json`, lu par `barometre/projection.js`.
Les scripts attendent les fichiers téléchargés dans `dl/`, `l22/` et `mun/` (hors dépôt).
