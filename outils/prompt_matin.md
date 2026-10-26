Tu fais la mise à jour du matin du site Concret (https://concret2027.fr, dépôt GitHub concret2027/Concret2027, branche main) : le Baromètre 2027 seulement. Écris en français. Règle absolue : tout chiffre publié a été lu à sa source ; rien d'inventé ; en cas de doute, garde l'ancienne valeur et signale-le.

## 1. Préparer
1. Le dépôt concret2027/Concret2027 est attaché à cette session. Travaille dans sa copie locale ; s'il n'est pas encore cloné, clone-le (git clone https://github.com/concret2027/Concret2027). Fais git pull pour partir de la dernière version.
2. git config user.name "Concret" ; git config user.email "noreply@concret2027.fr". Aucune ligne Co-Authored-By ni Claude-Session, aucun nom ni e-mail personnel.
3. Lis CLAUDE.md, puis les formats de la section 2 de outils/prompt_tache.md (polymarket, polymarket_hist, sondages, evenements) : ce sont les mêmes règles.

## 2. Ne traiter que le Baromètre
- polymarket et polymarket_hist : relève du matin (même méthode que la mise à jour de midi ; dans polymarket_hist, remplace le point du jour s'il existe).
- Sondages : seulement ceux dont la notice est déposée à la Commission des sondages (https://www.commission-des-sondages.fr/notices/) ; après tout ajout, lance `python3 outils/sondages.py --ecrire`. Silence électoral : la veille et le jour de chaque tour, n'ajoute ni ne modifie aucun sondage.
- evenements : seulement un fait de campagne daté, lu à une source officielle ou à la source qui l'annonce, en une phrase neutre.
- Ne touche à aucune autre donnée, à aucune page HTML, ni à donnees/calendrier.json : la mise à jour de midi garde ses vérifications du jour (ne modifie pas prochaine_verification).

## 3. Contrôler et publier
1. Mets à jour "updated" et "updated_iso" (heure de Paris) ; écris data.json avec json.dump(..., ensure_ascii=False, indent=0), en gardant tout le reste du fichier tel quel.
2. Lance `node outils/controle.js verifier --compte-rendu <fichier hors du dépôt>` (compte rendu : sources lues, valeurs ancienne → nouvelle). S'il sort en erreur, ne publie rien.
3. Sinon : git add data.json donnees journal ; commit « Baromètre du matin (<date heure>) » ; git fetch origin main ; si origin/main a avancé, repars de origin/main, réapplique tes changements et relance verifier ; puis git push origin HEAD:main.

## 4. Notification
Une seule ligne : « Baromètre du matin : » suivi de ce qui a changé (nouveaux sondages, mouvement de Polymarket), ou « rien de nouveau ». Précédée d'une ligne « ÉCHEC GitHub : <erreur exacte> » si le push a échoué.
