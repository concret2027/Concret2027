Tu fais la mise à jour du matin du site Concret (https://concret2027.fr, dépôt GitHub concret2027/Concret2027, branche main) : le Baromètre 2027 seulement. Écris en français. Règle absolue : tout chiffre publié a été lu à sa source ; rien d'inventé ; en cas de doute, garde l'ancienne valeur et signale-le.

## 1. Préparer
1. Le dépôt concret2027/Concret2027 est attaché à cette session. Travaille dans sa copie locale ; s'il n'est pas encore cloné, clone-le (git clone https://github.com/concret2027/Concret2027). Fais git pull pour partir de la dernière version.
2. git config user.name "Concret" ; git config user.email "noreply@concret2027.fr". Aucune ligne Co-Authored-By ni Claude-Session, aucun nom ni e-mail personnel.
3. Lis CLAUDE.md, puis les formats de la section 2 de outils/prompt_tache.md (polymarket, polymarket_hist, sondages, evenements) : ce sont les mêmes règles.

## 2. Ne traiter que le Baromètre
- polymarket, polymarket_hist, polymarket_t1 et polymarket_t1_hist : relève du matin (même méthode que la mise à jour de midi ; dans polymarket_hist, remplace le point du jour s'il existe).
- Sondages : un nouveau sondage ne s'ajoute qu'avec ses mentions obligatoires lues à la source. Si sa notice est en ligne à la Commission des sondages (https://www.commission-des-sondages.fr/notices/), elle fait foi. Sinon, s'il est publié avec un rapport complet de l'institut ou du média (institut, commanditaire, dates du terrain, nombre de personnes interrogées, marge d'erreur ; un article de presse seul ne suffit pas), lis ses scores et ses mentions dans ce rapport, ajoute ses lignes dans sondages_t1 ou sondages_t2, et une ligne dans sondages_rapports {date (dernier jour du terrain), institut, terrain, echantillon, commanditaire, marge (« x,x à y,y », en points ; si le rapport ne donne pas de fourchette, celle de la formule standard pour 5 % et 50 % sur l'échantillon, comme outils/sondages.py), url (le rapport lu)}. Puis lance `python3 outils/sondages.py --ecrire` : à chaque passage, il cherche la notice de chaque sondage et la substitue au rapport dès qu'elle est en ligne ; recopie dans le compte rendu tout écart qu'il affiche. Silence électoral (loi du 19 juillet 1977) : la veille et le jour de chaque tour, n'ajoute ni ne modifie aucun sondage.
- wikipedia_vues et wikipedia_info (bloc « Par ailleurs : qui fait parler de lui ») : si datasets.wikipedia_info[0].releve n'est pas la date du jour, lance `python3 outils/wikipedia.py --ecrire` (moyenne des 28 jours jusqu'à hier ; il respecte le délai demandé par Wikimedia). S'il ne lit aucun candidat, n'insiste pas : les chiffres précédents restent, ce n'est pas un problème à signaler.
- evenements : seulement un fait de campagne daté, lu à une source officielle ou à la source qui l'annonce, en une phrase neutre.
- Ne touche à aucune autre donnée, à aucune page HTML, ni à donnees/calendrier.json : la mise à jour de midi garde ses vérifications du jour (ne modifie pas prochaine_verification).

## 3. Contrôler et publier
1. Mets à jour "updated" et "updated_iso" (heure de Paris) ; écris data.json avec json.dump(..., ensure_ascii=False, indent=0), en gardant tout le reste du fichier tel quel.
2. Lance `node outils/controle.js verifier --compte-rendu <fichier hors du dépôt>` (compte rendu : sources lues, valeurs ancienne → nouvelle). S'il sort en erreur, ne publie rien.
3. Sinon : git add data.json donnees journal ; commit « Baromètre du matin (<date heure>) » ; git fetch origin main ; si origin/main a avancé, repars de origin/main, réapplique tes changements et relance verifier ; puis git push origin HEAD:main.

## 4. Notification
Une seule ligne : « Baromètre du matin : » suivi de ce qui a changé (nouveaux sondages, mouvement de Polymarket), ou « rien de nouveau ». Précédée d'une ligne « ÉCHEC GitHub : <erreur exacte> » si le push a échoué.
