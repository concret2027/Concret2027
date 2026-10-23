Tu fais la mise à jour quotidienne du site Concret (https://concret2027.fr, dépôt GitHub concret2027/Concret2027, branche main, GitHub Pages). Écris en français. Règle absolue : tout chiffre publié a été lu à sa source ; rien d'inventé ; en cas de doute, garde l'ancienne valeur et signale-le.

## 1. Préparer
1. Le dépôt concret2027/Concret2027 est attaché à cette session. Travaille dans sa copie locale ; s'il n'est pas encore cloné, clone-le (git clone https://github.com/concret2027/Concret2027). Fais git pull pour partir de la dernière version.
2. git config user.name "Concret" ; git config user.email "noreply@concret2027.fr". Aucune ligne Co-Authored-By ni Claude-Session, aucun nom ni e-mail personnel.
3. Lis CLAUDE.md, puis lance `node outils/controle.js a-faire` : c'est la liste des seuls indicateurs à traiter aujourd'hui. Ne cherche rien d'autre.

## 2. Mettre à jour les indicateurs dus
Pour chaque indicateur listé, va à la source indiquée (URL de départ dans donnees/calendrier.json), récupère la donnée avec WebFetch ou l'outil adapté, puis applique les règles de donnees/calendrier.json (clé « regles ») :
- nouvelle donnée vérifiée : écris-la dans sa cible de data.json, puis dans le calendrier : derniere_donnee, derniere_verification = aujourd'hui, tentatives = 0, statut = a_jour, prochaine_verification = prochaine publication lue dans le calendrier de diffusion de la source (publication_attendue seulement si la date est lue dans un calendrier officiel), sinon la date habituelle selon la fréquence ;
- rien de nouveau et rien d'attendu avant une date connue : derniere_verification = aujourd'hui, prochaine_verification = cette date ;
- publication attendue mais introuvable : tentatives + 1, statut = en_retard, prochaine_verification = demain ;
- statut a_verifier ou a_recuperer : établis la valeur avec une source officielle (et une seconde source pour fin_retraites, voir la règle « retraites »), puis passe le statut à a_jour ; si impossible, laisse le statut et note pourquoi.

Formats de data.json (relis le fichier entier et réécris l'objet complet : ne supprime jamais series ni textes ; toutes les valeurs des datasets sont des chaînes ; conserve tous les jeux de données et toutes les clés, même inconnues) :
- polymarket {candidat, probabilite, releve} : https://gamma-api.polymarket.com/events?slug=next-french-presidential-election ; 12 candidats les plus probables (nom complet) + « Autres candidats » = somme des autres ; probabilité = premier élément de outcomePrices × 100, 1 décimale. polymarket_hist {date, candidat (nom court), probabilite (2 décimales)} : ajoute ou remplace la date du jour pour les 6 premiers, ne touche pas au passé ; si l'un des 6 n'a aucun historique, récupère-le une fois sur https://clob.polymarket.com/prices-history?market=<premier clobTokenIds>&interval=max&fidelity=10080 (un point par semaine).
- sondages_t1 {date, institut, terrain, echantillon, candidat, score, hypotheses} (un objet par candidat testé ; score = moyenne des hypothèses où il figure ; date = dernier jour du terrain) et sondages_t2 {date, institut, candidat_rn, adversaire, score_rn, score_adversaire, source} : seulement des sondages dont tu as lu la notice (https://www.commission-des-sondages.fr/notices/) ou le rapport officiel.
- pouls {indicateur, date, valeur, unite, source, url} : taux_10_ans (%), ecart_allemagne (pb), confiance_menages (indice), dette_publique_pib (% du PIB), dette_publique_md (Md€) ; une entrée par date et par indicateur ; on n'efface jamais.
- finances_mois et education_mois {indicateur, periode AAAA-MM, valeur, unite, source, url} ; finances_trim {indicateur, periode AAAA-Qn, valeur, unite, source, url} (Insee pour la 1re estimation française, puis Eurostat).
- evenements {date, evenement, court, source, url} (10 au plus) ; agenda_barometre {date, evenement, source, url} ; actu_finances et actu_education {date, texte, source, url} (6 au plus) ; agenda_finances {date, evenement} ; agenda_education {date, quand, evenement, source, url}. Retire les rendez-vous passés depuis plus de 3 jours ; garde les tours de scrutin (18 avril et 2 mai 2027) jusqu'à ce qu'ils aient eu lieu ; n'invente aucune date.
- series.<page> : séries annuelles en nombres (null si absent), une valeur par année, dans l'ordre existant ; P.<clé> = {v, source, url, date}.
Phrases d'actualité, d'agenda et d'événements : une phrase neutre et factuelle, sans adjectif ni jugement, avec une source lue.

## 3. Textes
- Quand une cible change, mets à jour ses textes liés (textes_lies du calendrier → data.json textes.<page>.<clé>.html) et les entrées de series.<page>.FACTS, QUIZ ou EVENTS qui citent ce chiffre : ce qui a changé, de combien, selon quelle source, sans adjectif ni jugement. Garde le style et le balisage existants.
- Ne modifie jamais aucun fichier HTML, ni CNAME, ni README.md, ni CLAUDE.md, ni commun/, ni outils/. Les notes et le classement de l'accueil se recalculent seuls.
- Ne modifie jamais un titre ou une conclusion (récits) : si l'un d'eux ne tient plus, le contrôle le signale et il attend la validation d'Olivier.

## 4. Contrôler et publier
1. Mets à jour "updated" (date du jour, ex. « 23 octobre 2026 », heure de Paris) et "updated_iso" (heure actuelle, ISO 8601 avec +01:00 ou +02:00) ; écris data.json avec json.dump(..., ensure_ascii=False, indent=0). Publie même si aucune autre donnée n'a changé.
2. Écris hors du dépôt un compte rendu détaillé (sources consultées avec URL, valeurs ancienne → nouvelle, ce qui manque et pourquoi), puis lance `node outils/controle.js verifier --compte-rendu <ce fichier>`. Il valide data.json, recalcule les notes, vérifie les récits, écrit journal/AAAA-MM.md, donnees/notes.json et donnees/a_valider.json, et imprime la notification.
3. S'il sort en erreur (code 1) : ne publie rien ; corrige si l'erreur vient de ta saisie et relance, sinon arrête-toi.
4. Sinon : git add data.json donnees journal ; commit « Mise à jour des données (<date heure>) » ; git fetch origin main ; si origin/main a avancé, repars de origin/main, réapplique tes changements et relance verifier ; puis git push origin HEAD:main.
5. Secours Claude : lis l'artifact https://claude.ai/artifact/QE3F4NgDPn1Z4aPET1YY4A avec l'outil Artifact (action « read »), remplace uniquement le contenu de la balise `<script id="baro-data" type="application/json">…</script>` par {"updated", "datasets"} de data.json (json.dumps(..., ensure_ascii=False), chaque « </ » remplacé par « <\/ »), vérifie qu'il reste une seule balise baro-data, et republie (action « publish », même url, sans icon).

## 5. Notification
1. E-mail quotidien, même si tout va bien et même si une étape a échoué : charge l'outil Gmail avec ToolSearch (« select:mcp__Gmail__send_message ») et envoie un message à l'adresse du propriétaire (écrite seulement dans la tâche planifiée, jamais dans le dépôt).
   - Objet : « Concret, <date> : tout est à jour » si verifier n'affiche aucun ⚠ ni « À valider », sinon « Concret, <date> : N point(s) à regarder ». En cas d'échec (verifier en erreur, push refusé, dépôt inaccessible) : « Concret, <date> : ÉCHEC, rien publié ».
   - Corps en texte simple (pas de Markdown) : la sortie complète de verifier ; puis, en une ligne par indicateur, ce qui a été vérifié aujourd'hui (source lue, ancienne → nouvelle valeur, ou « inchangé ») ; puis le lien vers le journal du mois (https://github.com/concret2027/Concret2027/blob/main/journal/AAAA-MM.md) et vers https://concret2027.fr.
   - Un chiffre que tu n'as pas pu lire à sa source n'est jamais présenté comme vérifié : écris-le comme non vérifié, avec la raison.
   - Si l'envoi échoue, ajoute la ligne « ÉCHEC e-mail : <erreur exacte> » à ta réponse finale.
2. Ta réponse finale est exactement la sortie de `controle.js verifier` (une ligne si tout va bien ; une ligne par problème ; une ligne par texte à valider), précédée d'une seule ligne « ÉCHEC GitHub : <erreur exacte> » si le push a échoué. Rien d'autre : le détail est dans le journal du dépôt.

Sois économe : un appel par source, pas de recherche hors des indicateurs dus.
