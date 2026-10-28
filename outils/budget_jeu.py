#!/usr/bin/env python3
"""Jeu « Votre quinquennat » (brouillon) : les cartes de mesures et les paramètres du modèle, dans donnees/budget_jeu.json.

Chaque carte est une vraie mesure avec un chiffrage officiel, lu à sa source et recopié avec sa citation dans
donnees/budget_sources/ :
- mesures_2027.json : mesures des projets de loi de finances et de financement de la sécurité sociale pour 2027
  (évaluations préalables, rapport annexé) ;
- depenses_fiscales.json : niches fiscales d'au moins 1 Md€ (Évaluation des voies et moyens, tome II) ;
- parametres_macro.json : effets sur l'activité et le solde (variantes du modèle Mésange, DG Trésor et Insee), taux à 10 ans,
  durée de vie de la dette, retraites ;
- leviers_depense.json et smic_emploi_taux.json s'ils existent.
Règle de choix des cartes (fixe, non partisane) : toutes les mesures des deux projets de loi d'au moins 300 M€ en 2027 qui
changent le solde de l'ensemble des administrations publiques, et toutes les niches fiscales d'au moins 1 Md€ chiffrées.

Départ (« si rien ne change ») : le solde primaire de la dernière année publiée par Eurostat reste le même, en part du PIB,
chaque année ; croissance, inflation et taux d'intérêt moyen de la dette : prévision du FMI (donnees/budget.json).

  python3 outils/budget_jeu.py            compare
  python3 outils/budget_jeu.py --ecrire   écrit donnees/budget_jeu.json
"""
import json, os, re, sys, urllib.request
from datetime import date

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(RACINE, 'donnees', 'budget_sources')
SORTIE = os.path.join(RACINE, 'donnees', 'budget_jeu.json')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Qui paie ou qui reçoit, au sens du texte : une liste fixe d'étiquettes.
QUI = {
    'retraites': 'Retraités', 'salaries': 'Salariés', 'menages_imposables': 'Ménages imposables', 'malades': 'Malades et accidentés du travail',
    'entreprises': 'Entreprises', 'grandes_entreprises': 'Grandes entreprises', 'familles': 'Familles', 'collectivites': 'Collectivités',
    'prime_activite': 'Allocataires de la prime d\'activité', 'consommateurs': 'Consommateurs', 'patrimoine': 'Patrimoine et transmissions',
    'formation': 'Formation et apprentissage', 'complementaires': 'Mutuelles et assurances santé', 'menages_employeurs': 'Ménages qui emploient à domicile',
    'donateurs': 'Donateurs', 'logement': 'Travaux dans les logements', 'restauration': 'Restauration', 'agriculture': 'Agriculture et forêt',
    'transport': 'Transport routier', 'outre_mer': 'Outre-mer', 'handicap': 'Personnes handicapées', 'automobilistes': 'Acheteurs de voitures',
    'agents_publics': 'Agents publics', 'chomeurs': 'Chômeurs', 'smic': 'Salariés au SMIC', 'assures': 'Assurés sociaux', 'soignants': 'Hôpitaux et soignants',
    'pays_aides': 'Pays aidés', 'logement_aide': 'Logement et hébergement', 'ecologie': 'Transports, énergie et environnement', 'etudiants_recherche': 'Étudiants et recherche',
    'solidarite': 'Allocataires des minima et personnes handicapées', 'culture': 'Culture et médias', 'etrangers': 'Étrangers et demandeurs d\'asile', 'justice': 'Justice et prisons',
    'securite': 'Police, gendarmerie, secours', 'etudiants': 'Étudiants', 'ecoles': 'Écoles, collèges, lycées', 'defense': 'Défense', 'associations': 'Sport et associations', 'etat': 'Services de l\'État', 'anciens_combattants': 'Anciens combattants',
}
# Effet sur l'activité : la variante du modèle Mésange qui correspond au type de mesure (aucune pour l'impôt sur les sociétés,
# les droits de succession et les accises : le modèle ne les publie pas).
MACRO = {'depense': 'mult_mesange2017_depense_publique', 'tva': 'mult_mesange2017_tva', 'csg': 'mult_mesange2017_csg',
         'ir': 'mult_mesange2017_ir', 'cotis_emp': 'mult_mesange2017_cotis_employeurs', 'cotis_sal': 'mult_mesange2017_cotis_salaries',
         'invest': 'mult_mesange2017_invest_public'}

# Mesures des projets de loi 2027 : titre de carte (neutre), thème, étiquettes, type d'effet sur l'activité ;
# exclues : les transferts entre administrations, qui ne changent pas le solde public total selon le document.
M2027 = {
    'ir-indexation-bareme': {'l': "Geler le barème de l'impôt sur le revenu en 2027 (ne pas le relever de l'inflation)", 'theme': 'impots', 'qui': ['menages_imposables'], 'macro': 'ir', 'inverse': True,
                             'quoi': "Les tranches de l'impôt sur le revenu restent celles de 2026 au lieu d'être relevées comme les prix : avec un même revenu, les ménages imposables paient plus. Le Gouvernement propose au contraire de les relever (l'entrée dans la tranche à 11 % passerait de 11 600 € à 11 844 €).",
                             'statut': "L'Assemblée a adopté le relèvement du barème (article 2, scrutin n° 8737, 15 octobre 2026) : elle n'a pas retenu ce gel.",
                             'note': "Le document chiffre ce que rapporterait le fait de ne pas relever les tranches : « environ 4,2 Md€ en 2027 »."},
    'ir-indemnites-rupture': {'theme': 'travail', 'qui': ['salaries'], 'macro': 'ir'},
    'secu-indemnites-rupture': {'theme': 'travail', 'qui': ['salaries', 'entreprises'], 'macro': 'cotis_sal'},
    'ir-indemnites-journalieres': {'theme': 'sante', 'qui': ['malades'], 'macro': 'ir'},
    'csg-indemnites-journalieres': {'theme': 'sante', 'qui': ['malades'], 'macro': 'csg'},
    'ir-abattement-retraites': {'theme': 'retraites', 'qui': ['retraites'], 'macro': 'ir', 'exclusif': 'abattement-retraites'},
    'apport-cession': {'theme': 'patrimoine', 'qui': ['patrimoine'], 'macro': None},
    'contribution-grandes-entreprises': {'theme': 'entreprises', 'qui': ['grandes_entreprises'], 'macro': None, 'note_plus': "Ce que les taux visent : « L’assiette de la contribution est égale à la moyenne de l’IS dû au titre de l’exercice au titre duquel la contribution est due et au titre de l’exercice précédent » (même document, article 15)."},
    'contribution-transport-maritime': {'theme': 'entreprises', 'qui': ['grandes_entreprises'], 'macro': None},
    'tva-television': {'theme': 'impots', 'qui': ['consommateurs'], 'macro': 'tva'},
    'taxe-infrastructures-transport': {'theme': 'entreprises', 'qui': ['grandes_entreprises'], 'macro': None},
    'avoirs-desherence': {'theme': 'patrimoine', 'qui': ['patrimoine'], 'macro': None},
    'cpeb': {'theme': 'collectivites', 'qui': ['collectivites'], 'macro': None},
    'cufpa-plafond': {'theme': 'travail', 'qui': ['formation'], 'macro': 'depense'},
    'prime-activite-gel': {'theme': 'solidarite', 'qui': ['prime_activite'], 'macro': 'depense'},
    'formation-pric-cfa': {'theme': 'travail', 'qui': ['formation'], 'macro': 'depense'},
    'cpf-participation': {'theme': 'travail', 'qui': ['formation'], 'macro': 'depense'},
    'allegements-complements-salaire': {'theme': 'entreprises', 'qui': ['entreprises'], 'macro': 'cotis_emp'},
    'taxe-produits-sucres': {'theme': 'sante', 'qui': ['consommateurs'], 'macro': None},
    'contribution-complementaires-sante': {'theme': 'sante', 'qui': ['complementaires'], 'macro': None},
    'pensions-revalorisation-2027': {'theme': 'retraites', 'qui': ['retraites'], 'macro': 'depense'},
    'prestations-familiales-gel': {'theme': 'solidarite', 'qui': ['familles'], 'macro': 'depense'},
    'allocation-rentree-scolaire': {'theme': 'solidarite', 'qui': ['familles'], 'macro': 'depense'},
}
EXCLUES = {'fctva-taux': "versement de l'État aux collectivités : le document ne chiffre que l'économie de l'État, pas l'effet sur l'ensemble du déficit public",
           'tva-collectivites': "part de TVA conservée par l'État au lieu d'être versée aux collectivités : transfert entre administrations publiques",
}
# Votes de l'Assemblée qui portent sur la mesure elle-même : (scrutin, sens) ; sens -1 quand le vote est sur sa suppression.
# Mesures d'un seul exercice : rien après la dernière année chiffrée. Les autres gardent leur dernier montant (aucun chiffrage
# officiel au-delà : c'est une hypothèse de Concret, écrite sur la carte).
PONCTUELLES = {'avoirs-desherence', 'contribution-complementaires-sante', 'contribution-transport-maritime', 'contribution-grandes-entreprises'}
SCRUTINS = {'ir-indemnites-journalieres': (8727, -1), 'csg-indemnites-journalieres': (8727, -1), 'ir-abattement-retraites': (8738, -1),
            'cpeb': (8887, -1), 'allegements-complements-salaire': (8998, 1), 'taxe-produits-sucres': (9033, -1),
            'contribution-complementaires-sante': (9077, -1), 'contribution-grandes-entreprises': (9123, -1), 'contribution-transport-maritime': (9123, -1)}

# Niches fiscales : titre de carte, thème, étiquettes, type d'effet sur l'activité. Écartées : 130201 (chiffrage contradictoire
# dans le document) et 110261 (réductions d'impôt d'investissements déjà réalisés).
NICHES = {
    '200302': {'l': "Supprimer le crédit d'impôt recherche", 'theme': 'entreprises', 'qui': ['entreprises'], 'macro': None},
    '110246': {'l': "Supprimer le crédit d'impôt pour l'emploi d'un salarié à domicile", 'theme': 'impots', 'qui': ['menages_employeurs'], 'macro': 'ir'},
    '120401': {'l': "Supprimer l'abattement de 10 % sur les pensions et retraites", 'theme': 'retraites', 'qui': ['retraites'], 'macro': 'ir', 'exclusif': 'abattement-retraites'},
    '520110': {'l': "Supprimer l'exonération partielle de droits de succession et de donation lors de la transmission d'une entreprise", 'theme': 'patrimoine', 'qui': ['patrimoine'], 'macro': None},
    '120108': {'l': "Soumettre à l'impôt sur le revenu la participation, l'intéressement et l'épargne salariale", 'theme': 'travail', 'qui': ['salaries'], 'macro': 'ir'},
    '730213': {'l': "Appliquer le taux normal de TVA aux travaux dans les logements (aujourd'hui 10 %)", 'theme': 'impots', 'qui': ['logement'], 'macro': 'tva'},
    '730221': {'l': "Appliquer le taux normal de TVA à la restauration (aujourd'hui 10 %)", 'theme': 'impots', 'qui': ['restauration', 'consommateurs'], 'macro': 'tva'},
    '120146': {'l': "Soumettre à l'impôt sur le revenu les heures supplémentaires", 'theme': 'travail', 'qui': ['salaries'], 'macro': 'ir'},
    '110201': {'l': "Supprimer la réduction d'impôt pour les dons des particuliers", 'theme': 'impots', 'qui': ['donateurs'], 'macro': 'ir'},
    '110203': {'l': "Supprimer le crédit d'impôt pour frais de garde des enfants de moins de 6 ans", 'theme': 'solidarite', 'qui': ['familles'], 'macro': 'ir'},
    '210309': {'l': "Supprimer la réduction d'impôt pour les dons des entreprises", 'theme': 'entreprises', 'qui': ['entreprises'], 'macro': None},
    '800229': {'l': "Supprimer le tarif réduit d'accise sur le carburant des travaux agricoles et forestiers", 'theme': 'entreprises', 'qui': ['agriculture'], 'macro': None},
    '120202': {'l': "Soumettre à l'impôt sur le revenu les prestations familiales et l'allocation aux adultes handicapés", 'theme': 'solidarite', 'qui': ['familles', 'handicap'], 'macro': 'ir'},
    '800401': {'l': "Supprimer le régime particulier de l'accise sur les carburants en Guadeloupe, Guyane, Martinique, à La Réunion et à Mayotte", 'theme': 'impots', 'qui': ['outre_mer'], 'macro': None},
    '940102': {'l': "Soumettre les voitures électriques et à hydrogène à la taxe sur la masse (malus au poids)", 'theme': 'impots', 'qui': ['automobilistes'], 'macro': None},
    '710103': {'l': "Appliquer en Guadeloupe, en Martinique et à La Réunion les taux de TVA de la métropole", 'theme': 'impots', 'qui': ['outre_mer', 'consommateurs'], 'macro': 'tva'},
    '210326': {'l': "Supprimer le taux d'impôt de 10 % sur les revenus des brevets et de la propriété industrielle", 'theme': 'entreprises', 'qui': ['entreprises'], 'macro': None},
    '800221': {'l': "Supprimer le remboursement partiel d'accise sur le gazole des camions de 7,5 tonnes et plus", 'theme': 'entreprises', 'qui': ['transport'], 'macro': None},
    '730223': {'l': "Appliquer le taux normal de TVA aux travaux de rénovation énergétique des logements (aujourd'hui 5,5 %)", 'theme': 'impots', 'qui': ['logement'], 'macro': 'tva'},
}
# Défis du jour (un par jour, le même pour tous) ; chaque chiffre a sa source.
REGLE = {'v': 3, 'source': "Eurostat, glossaire « Procédure concernant les déficits excessifs » : selon le protocole annexé au traité de Maastricht, le déficit ne doit pas dépasser 3 % du PIB",
         'url': 'https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Glossary:Excessive_deficit_procedure_(EDP)'}
DEFIS = [
    {'id': 'd3-an1', 't': 'Ramenez le déficit de 2027 à 3 % du PIB ou moins.', 'c': [{'type': 'deficit_an1', 'v': 3}], 'src': REGLE},
    {'id': 'dette', 't': "Faites baisser la dette d'ici la fin du quinquennat.", 'c': [{'type': 'dette_baisse'}]},
    {'id': 'd3-sans-impot', 't': "Ramenez le déficit de la dernière année à 3 % sans augmenter aucun impôt ni cotisation.", 'c': [{'type': 'deficit_fin', 'v': 3}, {'type': 'sans_impot'}], 'src': REGLE},
    {'id': 'd3-sans-retraites', 't': "Ramenez le déficit de la dernière année à 3 % sans toucher aux retraites.", 'c': [{'type': 'deficit_fin', 'v': 3}, {'type': 'sans_theme', 'theme': 'retraites'}], 'src': REGLE},
    {'id': 'equilibre', 't': "Atteignez l'équilibre (aucun déficit) la dernière année.", 'c': [{'type': 'deficit_fin', 'v': 0}]},
    {'id': 'd3-sans-sante', 't': "Ramenez le déficit de la dernière année à 3 % sans mesure sur la santé.", 'c': [{'type': 'deficit_fin', 'v': 3}, {'type': 'sans_theme', 'theme': 'sante'}], 'src': REGLE},
]
# Titre court de chaque carte (60 caractères environ) ; l'intitulé complet reste dans les détails.
# Chaque carte en deux phrases simples : ce qui se passe aujourd'hui, ce qui est proposé (repris des textes cités sur la carte).
# {licence}, {master}, {doctorat}, {boite}, {consultation}, {transport}, {plafond} : remplacés par les montants en vigueur (parametres_cas.json).
CLAIR = {
    "ir-indexation-bareme": ("L'impôt sur le revenu se calcule par tranches : chaque taux s'applique à la part du revenu qui dépasse un seuil. D'habitude, ces seuils sont relevés chaque année comme les prix. Le Gouvernement propose de le faire en 2027 : le taux de 11 % s'appliquerait à partir de 11 844 € au lieu de 11 600 €.", "Les laisser au niveau de 2026 : par rapport à des seuils relevés, les ménages imposables paient plus, et certains qui ne payaient pas d'impôt en paient."),
    "ir-indemnites-rupture": ("Quand un contrat de travail prend fin par un licenciement, une rupture conventionnelle (fin du contrat décidée d'un commun accord) ou une mise à la retraite, le salarié reçoit une indemnité. Une partie échappe à l'impôt sur le revenu.", "N'exonérer d'impôt que les premiers 48 060 € (le « plafond annuel de la Sécurité sociale » de 2026, un montant de référence fixé chaque année). Au-delà, l'indemnité est soumise à l'impôt sur le revenu."),
    "ir-indemnites-journalieres": ("Pendant un arrêt de travail, la Sécurité sociale verse des indemnités journalières. Pour une affection de longue durée (ALD : maladie grave ou chronique reconnue par l'Assurance maladie), elles ne sont pas soumises à l'impôt sur le revenu. Après un accident du travail ou une maladie professionnelle, la moitié est soumise à l'impôt.", "Soumettre à l'impôt la moitié des indemnités d'ALD, et la totalité de celles des accidents du travail et des maladies professionnelles."),
    "csg-indemnites-journalieres": ("Les indemnités d'arrêt de travail (maladie, accident du travail) paient la CSG (contribution sociale généralisée, un prélèvement sur les revenus qui finance la Sécurité sociale) à un taux réduit de 6,2 %.", "Leur appliquer le taux de 9,2 %, celui des salaires."),
    "ir-abattement-retraites": ("Les retraités déduisent 10 % de leurs pensions du revenu sur lequel est calculé leur impôt, au plus 4 439 € par foyer.", "Limiter cette déduction à 3 000 € : les foyers imposables qui touchent plus d'environ 30 000 € de retraites par an paient plus d'impôt."),
    "apport-cession": ("Une personne peut apporter ses titres (actions ou parts d'une société) à une holding (une société qui détient des parts d'autres sociétés). L'impôt sur son gain (la plus-value) est alors mis en attente. Si elle donne ensuite les titres reçus en échange, ou s'ils sont transmis par héritage, cet impôt est effacé.", "Dans ce cas, faire payer l'impôt mis en attente (impôt sur le revenu et prélèvements sociaux, qui financent la protection sociale)."),
    "contribution-grandes-entreprises": ("Depuis 2025, les plus grandes entreprises paient une contribution exceptionnelle sur leurs bénéfices, en plus de l'impôt sur les sociétés. Elle est prévue pour deux années : pour les entreprises qui font au moins 1 milliard d'euros de chiffre d'affaires (leurs ventes de l'année) la première année, et au moins 1,5 milliard la deuxième.", "La faire payer une troisième année (versements attendus en 2027), à des taux plus bas : 15,7 % ou 31,4 % de leur impôt sur les sociétés (moyenne de deux années), selon le chiffre d'affaires, pour les entreprises qui font au moins 1,5 milliard d'euros de chiffre d'affaires."),
    "contribution-transport-maritime": ("Les grandes entreprises de transport maritime dont l'impôt est calculé d'après le tonnage de leurs navires, et non d'après leurs bénéfices, ont payé une contribution exceptionnelle pour une seule année. Elle était de 12 % de leur résultat d'exploitation (ce que leur activité rapporte une fois ses frais payés).", "La faire payer une deuxième année, au taux de 8 % (le projet de budget compte cette recette en 2027). L'argent va à l'Agence de financement des infrastructures de transport de France."),
    "tva-television": ("Les abonnements de télévision paient une TVA de 10 %.", "Leur appliquer le taux normal de 20 %."),
    "taxe-infrastructures-transport": ("Les sociétés qui exploitent des infrastructures de transport de longue distance paient une taxe de 4,6 % quand leurs revenus dépassent 120 millions d'euros et leur rentabilité 10 %.", "Garder 4,6 % tant que la rentabilité ne dépasse pas 20 %. Entre 20 % et 30 %, le taux monte peu à peu. Au-delà de 30 %, il est de 12,2 %."),
    "avoirs-desherence": ("L'argent des comptes bancaires et des assurances-vie oubliés est gardé par la Caisse des dépôts, en attendant que les titulaires ou leurs héritiers le réclament.", "En prélever 17 % en 2027 ; une personne qui se manifeste ensuite est remboursée en totalité."),
    "cpeb": (None, "En 2027, 40 % des communes, 60 % des départements et les intercommunalités (groupements de communes qui ont leurs propres impôts), hors outre-mer, versent une contribution au budget de l'État. L'État la prend sur les impôts locaux qu'il leur reverse. Son taux dépend des moyens de chacune."),
    "cufpa-plafond": ("Les employeurs paient une contribution pour la formation professionnelle et l'apprentissage. Elle va à France compétences, l'organisme public qui finance la formation professionnelle et l'apprentissage.", "Limiter ce que reçoit France compétences à 10 279 millions d'euros (environ 10,3 milliards) : ce qui dépasse va au budget de l'État."),
    "prime-activite-gel": ("La prime d'activité est versée en plus de leurs revenus du travail aux personnes qui gagnent peu. Elle augmente chaque 1er avril comme les prix (2,3 % prévus en 2027).", "Ne pas l'augmenter en 2027 (le Gouvernement peut décider de l'augmenter quand même). Le RSA (revenu de solidarité active), l'allocation aux adultes handicapés, le minimum vieillesse et l'allocation de solidarité spécifique continuent, eux, d'augmenter comme les prix."),
    "formation-pric-cfa": ("L'État paie, avec les régions, des programmes de formation (les « pactes régionaux d'investissement dans les compétences »). Il verse aussi aux régions de l'argent pour aider les centres de formation d'apprentis (CFA, les écoles où les apprentis suivent leurs cours).", "Arrêter ces financements. Créer un fonds national de 25 millions d'euros pour les centres de formation d'apprentis."),
    "cpf-participation": ("Le compte personnel de formation (CPF) paie des formations choisies par chacun ; le titulaire en paie une partie.", "Pour une formation sans lien démontré avec un projet professionnel, le titulaire paie une part plus grande, ou le CPF ne la paie plus. Le CPF paie aussi moins de frais de jury pour la VAE (validation des acquis de l'expérience : obtenir un diplôme grâce à son expérience)."),
    "secu-indemnites-rupture": ("Quand un contrat de travail prend fin par un licenciement, une rupture conventionnelle (fin du contrat décidée d'un commun accord) ou une mise à la retraite, le salarié reçoit une indemnité. Une partie échappe aux cotisations sociales.", "N'exonérer de cotisations que les premiers 48 060 € (le « plafond annuel de la Sécurité sociale » de 2026, un montant de référence fixé chaque année). Au-delà, le salarié et l'employeur paient les cotisations."),
    "allegements-complements-salaire": ("Les employeurs paient moins de cotisations sur les bas salaires. Pour savoir si un salaire y donne droit, et pour combien, on ne compte pas certaines primes versées en plus du salaire, comme la prime de partage de la valeur.", "Compter ces primes dans le salaire : les employeurs qui les versent ont une baisse de cotisations plus petite, donc paient plus de cotisations. La prime de partage de la valeur devait perdre fin 2026 ses exonérations de cotisations : elles deviennent permanentes."),
    "taxe-produits-sucres": ("Les boissons sucrées paient une taxe (la « taxe soda »).", "Taxer aussi les produits sucrés vendus emballés qui contiennent des additifs (confiseries, chocolats, biscuits, céréales, pâtisseries, glaces), dès 10 kg de sucre pour 100 kg de produit. La taxe va de 4,07 € à 22 € pour 100 kg de produit, selon la quantité de sucre."),
    "contribution-complementaires-sante": ("Les mutuelles et assurances santé ont déjà payé une contribution exceptionnelle de 2,05 % sur les cotisations santé que leur versent leurs clients.", "La leur faire payer de nouveau en 2027."),
    "pensions-revalorisation-2027": ("Chaque année, les retraites de base augmentent comme les prix (cette règle ne concerne pas les retraites complémentaires).", "En 2027, la retraite de base n'augmente comme les prix que si la retraite totale (base et complémentaire) est inférieure à 1 260 € par mois. Au-dessus, le Gouvernement peut décider par décret une hausse plus petite, ou aucune ; s'il n'a rien décidé au 31 octobre 2027, ces retraites restent au montant de 2026."),
    "prestations-familiales-gel": ("Les prestations familiales augmentent chaque 1er avril avec les prix.", "Ne pas les augmenter en 2027 : elles restent au montant de 2026."),
    "allocation-rentree-scolaire": (None, "Changer les montants de l'allocation de rentrée scolaire selon l'âge des enfants, pour dépenser moins. Les nouveaux montants ne sont pas encore connus : ils seront fixés après une concertation."),
    "niche-200302": ("Les entreprises qui font de la recherche reçoivent un crédit d'impôt (une somme retirée de leur impôt ; la part qui dépasse l'impôt dû peut être remboursée) : 17 593 entreprises.", "Le supprimer."),
    "niche-110246": ("Les ménages qui emploient un salarié à domicile reçoivent un crédit d'impôt (une somme retirée de l'impôt, ou versée si elle dépasse l'impôt dû) : 4,9 millions de ménages.", "Le supprimer."),
    "niche-120401": ("Les retraités et les personnes qui reçoivent une pension (dont une pension alimentaire) déduisent 10 % de ces sommes du revenu sur lequel est calculé leur impôt (15,1 millions de ménages).", "Supprimer cette déduction : l'impôt est calculé sur toute la somme reçue."),
    "niche-520110": ("Quand une entreprise est donnée ou transmise par héritage, l'impôt payé par celui qui la reçoit (droits de donation ou de succession) est réduit, sous conditions.", "Faire payer cet impôt en entier."),
    "niche-120108": ("Certaines sommes que l'entreprise verse à ses salariés (participation et intéressement, liés aux résultats de l'entreprise, et certaines primes) ne sont pas soumises à l'impôt sur le revenu quand elles sont placées sur un plan d'épargne salariale ou de retraite d'entreprise.", "Les soumettre à l'impôt sur le revenu."),
    "niche-730213": ("Les travaux d'amélioration, de transformation, d'aménagement et d'entretien des logements de plus de 2 ans ont une TVA de 10 % (5,5 % pour la rénovation énergétique).", "Leur appliquer le taux normal de 20 %."),
    "niche-730221": ("Les repas au restaurant, sur place ou à emporter, ont une TVA de 10 %.", "Leur appliquer le taux normal de 20 %."),
    "niche-120146": ("Les heures supplémentaires ne sont pas soumises à l'impôt sur le revenu, dans certaines limites.", "Les soumettre à l'impôt sur le revenu."),
    "niche-110201": ("Les dons donnent droit à une réduction d'impôt sur le revenu (une somme retirée de l'impôt dû) : 5,6 millions de ménages.", "La supprimer."),
    "niche-110203": ("Les frais de garde des enfants de moins de 6 ans donnent droit à un crédit d'impôt (une somme retirée de l'impôt, ou versée si elle dépasse l'impôt dû) : 1,9 million de ménages.", "Le supprimer."),
    "niche-210309": ("Les dons des entreprises aux œuvres et organismes d'intérêt général donnent droit à une réduction d'impôt (une somme retirée de l'impôt dû) : 157 399 entreprises.", "La supprimer."),
    "niche-800229": ("Le gazole et les autres carburants utilisés pour les travaux agricoles et forestiers paient une taxe réduite.", "Leur appliquer la taxe normale."),
    "niche-120202": ("Les prestations familiales et l'allocation aux adultes handicapés ne sont pas soumises à l'impôt sur le revenu.", "Les soumettre à l'impôt sur le revenu."),
    "niche-800401": ("En Guadeloupe, en Martinique, en Guyane, à La Réunion et à Mayotte, seuls l'essence et le gazole sont soumis à la taxe sur les carburants, et ces territoires peuvent baisser le montant de cette taxe.", "Taxer les carburants comme en métropole."),
    "niche-940102": ("Les voitures à hydrogène et les voitures électriques à faible empreinte carbone ne paient pas le malus au poids (exonération réduite par la loi de finances pour 2025).", "Le leur faire payer."),
    "niche-710103": ("En Guadeloupe, en Martinique et à La Réunion, la TVA est de 8,5 % (taux normal) et de 2,1 % (taux réduit).", "Appliquer les taux de métropole (le taux normal y est de 20 %)."),
    "niche-210326": ("Les revenus que des entreprises tirent de certains brevets (droits sur une invention) et autres droits de propriété industrielle sont imposés à 10 %.", "Les imposer au taux normal de l'impôt sur les sociétés."),
    "niche-800221": ("Le gazole des camions de 7,5 tonnes et plus paie une taxe réduite (une partie est remboursée).", "Leur appliquer la taxe normale."),
    "niche-730223": ("Les travaux de rénovation énergétique des logements de plus de 2 ans ont une TVA de 5,5 %.", "Leur appliquer le taux normal de 20 %."),
    "retraites-fin-suspension": ("La hausse de l'âge minimum de départ prévue par la réforme de 2023 a été mise en pause en 2026. L'âge minimum est de 62 ans et 9 mois pour les personnes nées entre le 1er janvier 1963 et le 31 mars 1965. Il monte ensuite jusqu'à 64 ans pour celles nées à partir de 1969.", "Revenir au calendrier de 2023 : l'âge minimum monte plus vite et atteint 64 ans pour les personnes nées en 1968."),
    "smic-2": ("Le SMIC (salaire minimum) est de 1 867,02 € bruts par mois pour 35 heures par semaine. Il augmente déjà automatiquement.", "En 2027, l'augmenter de 2 % en plus de sa hausse automatique : appliqué au SMIC actuel, cela fait 1 904,36 € bruts par mois."),
    "smic-5": ("Le SMIC (salaire minimum) est de 1 867,02 € bruts par mois pour 35 heures par semaine. Il augmente déjà automatiquement.", "En 2027, l'augmenter de 5 % en plus de sa hausse automatique : appliqué au SMIC actuel, cela fait 1 960,37 € bruts par mois."),
    "ondam-moins-1": ("Chaque année, le Parlement fixe un objectif : de combien peuvent augmenter les dépenses de l'assurance maladie (soins de ville, comme les médecins et les pharmacies, hôpitaux, établissements pour personnes âgées ou handicapées). Pour 2027, une hausse de 2,0 % est proposée.", "En 2027, dépenser 1 % de moins que l'objectif prévu (1 % du total de ces dépenses)."),
    "ondam-plus-1": ("Chaque année, le Parlement fixe un objectif : de combien peuvent augmenter les dépenses de l'assurance maladie (soins de ville, comme les médecins et les pharmacies, hôpitaux, établissements pour personnes âgées ou handicapées). Pour 2027, une hausse de 2,0 % est proposée.", "En 2027, dépenser 1 % de plus que l'objectif prévu (1 % du total de ces dépenses)."),
    "revalo-moins-1": ("Les retraites de base (pas les retraites complémentaires), les prestations familiales et d'autres prestations sociales augmentent chaque année comme les prix.", "Les augmenter d'un point de moins que les prix : par exemple de 1 % si les prix montent de 2 %."),
    "revalo-plus-1": ("Les retraites de base (pas les retraites complémentaires), les prestations familiales et d'autres prestations sociales augmentent chaque année comme les prix.", "Les augmenter d'un point de plus que les prix : par exemple de 3 % si les prix montent de 2 %."),
    "allegements-moins-10": ("Les employeurs paient moins de cotisations sur les bas salaires.", "Rendre ces baisses de cotisations 10 % plus petites (un dixième de moins) : les employeurs paient plus de cotisations."),
    "point-indice-plus-1": ("Le salaire de base des fonctionnaires dépend du point d'indice ; le projet de budget 2027 prévoit de ne pas l'augmenter.", "L'augmenter de 1 %."),
    "etrangers-residence-prestations": (None, "Exiger des étrangers venus d'un pays hors de l'Union européenne qu'ils résident en France depuis au moins un an pour toucher les prestations familiales et les aides au logement."),
    "univ-master-doctorat": ("Les droits d'inscription à l'université sont de {licence} par an en licence, {master} en master et {doctorat} en doctorat ; les boursiers ne paient pas.", "Les porter à 965 € en master et 781 € en doctorat ; la licence ne change pas, les boursiers restent exonérés."),
    "univ-30": ("Les droits d'inscription à l'université sont de {licence} par an en licence, {master} en master et {doctorat} en doctorat ; les boursiers ne paient pas.", "Les augmenter de 30 % ; les boursiers restent exonérés."),
    "carence-3-jours": ("Les agents de l'État ne sont pas payés le premier jour d'un arrêt maladie.", "Ne pas les payer les trois premiers jours."),
    "isf": ("Depuis 2018, l'impôt sur la fortune ne porte que sur l'immobilier : l'impôt sur la fortune immobilière (IFI) a remplacé l'ISF.", "Rétablir un impôt sur la fortune qui porte sur tout le patrimoine, placements financiers compris."),
    "taxe-zucman": (None, "Les foyers dont le patrimoine dépasse 100 millions d'euros doivent payer chaque année, en tout, des impôts égaux à au moins 2 % de ce patrimoine : s'ils paient déjà moins, ils paient la différence."),
    "franchises-x2": ("Le patient paie {boite} par boîte de médicament, {consultation} par consultation et {transport} par transport, au plus {plafond} par an et par personne.", "Doubler ces montants et leurs plafonds."),
    "retraite-63": ("La réforme de 2023 fait monter l'âge minimum de départ jusqu'à 64 ans. Cette hausse a été mise en pause en 2026 : l'âge minimum est de 62 ans et 9 mois pour les personnes nées entre le 1er janvier 1963 et le 31 mars 1965, puis il monte jusqu'à 64 ans pour celles nées à partir de 1969.", "Arrêter la hausse à 63 ans au lieu de 64 ans. Le montant est calculé par rapport à 64 ans, pas par rapport à l'âge d'aujourd'hui."),
    "retraite-62": ("La réforme de 2023 fait monter l'âge minimum de départ jusqu'à 64 ans. Cette hausse a été mise en pause en 2026 : l'âge minimum est de 62 ans et 9 mois pour les personnes nées entre le 1er janvier 1963 et le 31 mars 1965, puis il monte jusqu'à 64 ans pour celles nées à partir de 1969.", "Ramener l'âge minimum à 62 ans pour tous, au lieu de 64 ans à terme. Le montant est calculé par rapport à 64 ans, pas par rapport à l'âge d'aujourd'hui."),
    "retraite-65": ("La réforme de 2023 fait monter l'âge minimum de départ jusqu'à 64 ans. Cette hausse a été mise en pause en 2026 : l'âge minimum est de 62 ans et 9 mois pour les personnes nées entre le 1er janvier 1963 et le 31 mars 1965, puis il monte jusqu'à 64 ans pour celles nées à partir de 1969.", "Porter l'âge minimum à 65 ans à terme, au lieu de 64 ans. Le montant est calculé par rapport à 64 ans, pas par rapport à l'âge d'aujourd'hui."),
    "fonctionnaires-1-sur-2": (None, "Ne remplacer que la moitié des agents de l'État qui partent à la retraite."),
}

COURT = {
    'ir-indexation-bareme': "Ne pas relever les tranches de l'impôt sur le revenu en 2027",
    'ir-indemnites-rupture': "Impôt sur les indemnités de départ au-delà de 48 060 €",
    'secu-indemnites-rupture': "Cotisations sur les indemnités de départ au-delà de 48 060 €",
    'ir-indemnites-journalieres': "Imposer une partie des indemnités d'arrêt de travail",
    'csg-indemnites-journalieres': "Relever la CSG sur les indemnités d'arrêt de travail",
    'ir-abattement-retraites': "Limiter à 3 000 € la déduction de 10 % sur les retraites",
    'apport-cession': "Imposer le gain en attente quand on donne des titres d'une holding",
    'contribution-grandes-entreprises': "Prolonger la surtaxe sur les bénéfices des grandes entreprises",
    'contribution-transport-maritime': "Rétablir la surtaxe sur les grandes compagnies maritimes",
    'tva-television': "TVA au taux normal sur les abonnements télé",
    'taxe-infrastructures-transport': "Taxer plus les infrastructures de transport les plus rentables",
    'avoirs-desherence': "Prélever 17 % sur l'argent des comptes oubliés",
    'cpeb': "Faire contribuer communes, départements et intercommunalités",
    'cufpa-plafond': "Limiter l'argent de la formation versé à France compétences",
    'prime-activite-gel': "Geler la prime d'activité en 2027",
    'formation-pric-cfa': "Arrêter des aides de l'État à la formation et aux écoles d'apprentis",
    'cpf-participation': "Faire payer plus les formations du CPF sans projet professionnel",
    'allegements-complements-salaire': "Compter certaines primes dans le salaire qui donne droit à des baisses de cotisations",
    'taxe-produits-sucres': "Étendre la « taxe soda » aux produits sucrés",
    'contribution-complementaires-sante': "Prolonger la taxe sur les mutuelles",
    'pensions-revalorisation-2027': "N'augmenter comme les prix que les retraites sous 1 260 € par mois",
    'prestations-familiales-gel': "Geler les prestations familiales en 2027",
    'allocation-rentree-scolaire': "Réduire l'allocation de rentrée scolaire",
    'etrangers-residence-prestations': "Un an de résidence pour les aides des étrangers hors UE",
    'niche-200302': "Supprimer le crédit d'impôt recherche",
    'niche-110246': "Supprimer le crédit d'impôt pour l'emploi à domicile",
    'niche-120401': "Supprimer la déduction de 10 % sur les retraites et pensions",
    'niche-520110': "Supprimer la baisse d'impôt sur les entreprises données ou héritées",
    'niche-120108': "Imposer l'épargne salariale (participation, intéressement)",
    'niche-730213': "TVA au taux normal sur les travaux dans les logements",
    'niche-730221': "TVA au taux normal dans les restaurants",
    'niche-120146': "Imposer les heures supplémentaires",
    'niche-110201': "Supprimer la réduction d'impôt pour les dons",
    'niche-110203': "Supprimer le crédit d'impôt pour la garde des jeunes enfants",
    'niche-210309': "Supprimer la réduction d'impôt des dons d'entreprises",
    'niche-800229': "Supprimer le tarif réduit de taxe sur le carburant agricole et forestier",
    'niche-120202': "Imposer les prestations familiales et l'allocation aux adultes handicapés",
    'niche-800401': "Taxer les carburants outre-mer comme en métropole",
    'niche-940102': "Malus au poids pour les voitures électriques",
    'niche-710103': "TVA de métropole aux Antilles et à La Réunion",
    'niche-210326': "Supprimer le taux d'impôt réduit sur les brevets",
    'niche-800221': "Supprimer le tarif réduit de taxe sur le gazole des camions",
    'niche-730223': "TVA au taux normal sur la rénovation énergétique",
    'retraites-fin-suspension': "Revenir à la réforme des retraites (64 ans)",
    'smic-2': "SMIC : 2 % de hausse en plus de la hausse automatique", 'smic-5': "SMIC : 5 % de hausse en plus de la hausse automatique",
    'ondam-moins-1': "Dépenses d'assurance maladie : 1 % de moins", 'ondam-plus-1': "Dépenses d'assurance maladie : 1 % de plus",
    'revalo-moins-1': "Prestations sociales : hausse de 1 point de moins que les prix", 'revalo-plus-1': "Prestations sociales : hausse de 1 point de plus que les prix",
    'allegements-moins-10': "Baisses de cotisations des employeurs : 10 % de moins",
    'point-indice-plus-1': "Point d'indice des fonctionnaires : +1 %",
    'univ-master-doctorat': "Université : master à 965 €, doctorat à 781 €", 'univ-30': "Université : droits d'inscription +30 %",
    'carence-3-jours': "Arrêt maladie : 3 jours non payés au lieu d'1 pour les agents de l'État",
    'isf': "Rétablir l'impôt sur la fortune (ISF)",
    'taxe-zucman': "Impôt minimum de 2 % sur les patrimoines de plus de 100 M€ (« taxe Zucman »)",
    'franchises-x2': "Doubler les franchises médicales",
    'retraite-63': "Retraite à 63 ans", 'retraite-62': "Retraite à 62 ans", 'retraite-65': "Retraite à 65 ans",
    'fonctionnaires-1-sur-2': "Ne remplacer qu'un fonctionnaire de l'État sur deux",
}
# Qui a donné le chiffre, pour les mesures débattues.
PAR_QUI = {'univ-master-doctorat': "chiffrage de la Cour des comptes", 'univ-30': "chiffrage de la Cour des comptes", 'carence-3-jours': "chiffrage des inspections générales, cité par le Sénat",
           'isf': "chiffrage cité par le Sénat", 'taxe-zucman': "chiffrage d'un rapport de l'Assemblée", 'franchises-x2': "chiffrage de la Cour des comptes",
           'retraite-63': "chiffrage de la Cour des comptes", 'retraite-62': "chiffrage de la Cour des comptes", 'retraite-65': "chiffrage de la Cour des comptes",
           'fonctionnaires-1-sur-2': "chiffrage de la Cour des comptes (2015)"}


# Ce que les députés ont fait de la mesure, quand une phrase plus précise est utile (lue dans le statut de la carte).
# « (1re lecture) » reste en fin de phrase : la page y insère le décompte des voix.
STATUT_CLAIR = {
    'ir-indemnites-rupture': "Les députés ont adopté cette mesure en la modifiant : les indemnités de licenciement ne sont plus concernées, et la règle vaut pour les indemnités reçues à partir du 1er janvier 2027 (1re lecture)",
    'apport-cession': "Les députés ont adopté cette mesure en la modifiant : la transmission par héritage n'est plus concernée, le don est imposé sous conditions, et la règle ne vaut que pour les apports faits à partir du 7 octobre 2026 (1re lecture)",
    'secu-indemnites-rupture': "Les députés ont adopté cette mesure en excluant les ruptures prévues par un plan social (plan de sauvegarde de l'emploi) validé avant le 31 décembre 2026, puis ont rejeté tout le budget de la Sécurité sociale (1re lecture)",
}
# Mesures retirées par un même vote : l'autre mesure retirée en même temps.
MEME_VOTE = {'ir-indemnites-journalieres': "la hausse de la CSG sur ces indemnités", 'csg-indemnites-journalieres': "l'impôt sur le revenu sur ces indemnités",
             'contribution-grandes-entreprises': "la surtaxe sur les grandes compagnies maritimes", 'contribution-transport-maritime': "la surtaxe sur les bénéfices des grandes entreprises"}


# Qui paie ou qui reçoit, dit en clair sur la carte (remplace le texte du document ; les étiquettes de QUI restent les groupes du bilan).
# Seulement ce que disent les textes de la carte ; nombre de bénéficiaires : Évaluation des voies et moyens.
QUI_CLAIR = {
    'ir-indemnites-rupture': "Salariés qui reçoivent une indemnité de départ de plus de 48 060 €",
    'secu-indemnites-rupture': "Salariés qui reçoivent une indemnité de départ de plus de 48 060 €, et leurs employeurs",
    'ir-indemnites-journalieres': "Personnes en arrêt de travail pour une affection de longue durée, un accident du travail ou une maladie professionnelle",
    'csg-indemnites-journalieres': "Personnes en arrêt maladie, ou en arrêt après un accident du travail ou une maladie professionnelle",
    'ir-abattement-retraites': "Foyers imposables qui touchent une retraite (4,6 millions de foyers, selon l'étude du Gouvernement jointe au projet de loi)",
    'apport-cession': "Personnes qui ont apporté leurs titres à une holding sans payer tout de suite l'impôt sur leur gain, puis donnent les titres reçus ou les transmettent par héritage",
    'contribution-grandes-entreprises': "Entreprises qui font au moins 1,5 milliard d'euros de chiffre d'affaires (ventes de l'année)",
    'taxe-infrastructures-transport': "Sociétés les plus rentables qui exploitent des infrastructures de transport de longue distance",
    'avoirs-desherence': "Titulaires des comptes et assurances-vie oubliés, ou leurs héritiers (remboursés en totalité s'ils se manifestent)",
    'cpeb': "Communes, départements et intercommunalités (groupements de communes)",
    'cufpa-plafond': "France compétences (organisme public qui finance la formation professionnelle et l'apprentissage)",
    'prime-activite-gel': "Personnes qui touchent la prime d'activité",
    'cpf-participation': "Personnes qui utilisent leur compte personnel de formation (CPF)",
    'allegements-complements-salaire': "Employeurs qui ont des baisses de cotisations sur les bas salaires et versent ces primes",
    'taxe-produits-sucres': "Entreprises qui doivent payer cette taxe sur les produits sucrés",
    'contribution-complementaires-sante': "Mutuelles et assurances santé",
    'pensions-revalorisation-2027': "Retraités dont la retraite totale dépasse 1 260 € par mois (5,2 millions entre 1 260 € et 2 000 €, 7,0 millions au-dessus, selon l'étude du Gouvernement jointe au projet de loi)",
    'prestations-familiales-gel': "Familles qui touchent des prestations familiales",
    'allocation-rentree-scolaire': "Familles qui touchent l'allocation de rentrée scolaire",
    'niche-200302': "17 593 entreprises qui font de la recherche",
    'niche-110246': "4,9 millions de ménages qui emploient un salarié à domicile",
    'niche-120401': "15,1 millions de ménages qui touchent une retraite ou une pension",
    'niche-520110': "Personnes qui reçoivent une entreprise par donation ou par héritage",
    'niche-120108': "Salariés qui placent de la participation, de l'intéressement ou certaines primes sur un plan d'épargne d'entreprise",
    'niche-730213': "303 850 entreprises qui font des travaux dans les logements",
    'niche-730221': "Restaurants et leurs clients",
    'niche-120146': "Salariés qui font des heures supplémentaires",
    'niche-110201': "5,6 millions de ménages qui font des dons",
    'niche-110203': "1,9 million de ménages qui font garder un enfant de moins de 6 ans",
    'niche-210309': "157 399 entreprises qui font des dons",
    'niche-800229': "240 000 entreprises qui utilisent du carburant pour des travaux agricoles ou forestiers",
    'niche-120202': "Foyers qui touchent des prestations familiales ou l'allocation aux adultes handicapés",
    'niche-800401': "Les cinq territoires concernés : Guadeloupe, Guyane, Martinique, La Réunion, Mayotte",
    'niche-710103': "90 911 entreprises de Guadeloupe, de Martinique et de La Réunion",
    'niche-210326': "1 065 entreprises qui ont des revenus de brevets ou d'autres droits de propriété industrielle",
    'niche-800221': "33 271 entreprises de transport de marchandises par camions de 7,5 tonnes et plus",
    'niche-730223': "100 601 entreprises qui font des travaux de rénovation énergétique des logements",
    'ondam-moins-1': "Patients, hôpitaux et soignants", 'ondam-plus-1': "Patients, hôpitaux et soignants",
    'revalo-moins-1': "Retraités et familles qui touchent des prestations de la Sécurité sociale", 'revalo-plus-1': "Retraités et familles qui touchent des prestations de la Sécurité sociale",
    'allegements-moins-10': "Employeurs de salariés payés près du SMIC",
    'point-indice-plus-1': "Agents publics : 5,85 millions fin 2024 (direction générale de l'administration et de la fonction publique, DGAFP)",
    'etrangers-residence-prestations': "Étrangers venus d'un pays hors de l'Union européenne, en France depuis moins d'un an",
    'univ-master-doctorat': "Étudiants non boursiers en master et en doctorat", 'univ-30': "Étudiants non boursiers",
    'carence-3-jours': "Agents de l'État en arrêt maladie",
    'isf': "Foyers qui paieraient l'impôt sur la fortune rétabli",
    'taxe-zucman': "Foyers dont le patrimoine dépasse 100 millions d'euros",
    'franchises-x2': "Patients (moins bien remboursés)",
    'retraite-62': "Futurs retraités", 'retraite-63': "Futurs retraités", 'retraite-65': "Futurs retraités",
    'fonctionnaires-1-sur-2': "Services de l'État : la moitié des agents qui partent à la retraite ne sont pas remplacés",
}
# Intitulé de la ligne « qui », quand « Paient plus » ou « Reçoivent moins » ne dit pas ce qui change.
QUI_TITRE = {'cufpa-plafond': 'Reçoit moins', 'franchises-x2': 'Paient plus', 'point-indice-plus-1': 'Reçoivent plus', 'fonctionnaires-1-sur-2': 'Qui est concerné',
             'retraite-62': 'Peuvent partir plus tôt', 'retraite-63': 'Peuvent partir plus tôt', 'retraite-65': 'Ne peuvent plus partir aussi tôt',
             'retraites-fin-suspension': 'Ne peuvent plus partir aussi tôt'}


def statut_court(t, i=None):
    """Ce que les députés ont fait de la mesure, en mots courants."""
    t = t or ''
    if not t: return ''
    if i in STATUT_CLAIR: return STATUT_CLAIR[i]
    if t.startswith('Supprimée'):
        return "Les députés ont retiré du texte cette mesure et %s (1re lecture)" % MEME_VOTE[i] if i in MEME_VOTE else "Les députés ont retiré cette mesure du texte (1re lecture)"
    if t.startswith('Adoptée'): return "Les députés ont adopté cette mesure (1re lecture)"
    if t.startswith('Modifiée'): return "Les députés ont adopté cette mesure en la modifiant (1re lecture)"
    if t.startswith('Article adopté'): return "Les députés ont adopté cette mesure, puis ont rejeté tout le budget de la Sécurité sociale (1re lecture)"
    if t.startswith('Article rejeté'): return "Les députés ont rejeté cette mesure (1re lecture)"
    if t.startswith('Non examinée'): return "Les députés n'ont pas voté sur cette mesure : ils ont rejeté le budget de la Sécurité sociale avant d'y arriver (1re lecture)"
    if t.startswith('Rapport annexé'): return "Les députés ont supprimé le rapport joint au texte qui décrivait cette mesure, puis ont rejeté tout le budget de la Sécurité sociale (1re lecture)"
    if t.startswith('Projet de loi rejeté'): return "Les députés ont rejeté tout le budget de la Sécurité sociale, qui contenait cette mesure (1re lecture)"
    if t.startswith("L'Assemblée a adopté le relèvement"): return "Les députés ont voté le relèvement des tranches proposé par le Gouvernement, pas ce gel (1re lecture)"
    return t.split(' (')[0].split(' ; ')[0]


THEMES = {'etudes': 'Études', 'retraites': 'Retraites', 'sante': 'Santé', 'travail': 'Travail et formation', 'solidarite': 'Familles et solidarité', 'impots': 'Impôts des ménages',
          'entreprises': 'Entreprises', 'patrimoine': 'Patrimoine', 'collectivites': 'Collectivités', 'etat': 'État et fonctionnaires', 'economie': 'Économie'}


def fr_nb(v):
    return ('{:,.2f}'.format(v).replace(',', ' ').replace('.', ',')).replace(',00', '')


def charger(nom):
    p = os.path.join(SRC, nom)
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None


def effet_md(e, signe=1):
    """{année: M€} → {année: Md€}, arrondi au million."""
    return {a: round(signe * v / 1000, 3) for a, v in sorted(e.items())}


def positions(nums):
    """Position de chaque groupe dans les scrutins demandés (données ouvertes de l'Assemblée)."""
    import parlement
    gp = parlement.groupes(parlement.lire_zip(parlement.SRC['organes'], 'json/organe/'))
    out = {}
    for s in parlement.lire_zip(parlement.SRC['scrutins']):
        s = s['scrutin']
        n = int(s['numero'])
        if n not in nums:
            continue
        g = {}
        for x in parlement.liste(((s.get('ventilationVotes') or {}).get('organe') or {}).get('groupes', {}).get('groupe')):
            if x['organeRef'] in gp:
                v = x['vote']; d = v.get('decompteVoix') or {}
                tot = parlement.nb(d.get('pour')) + parlement.nb(d.get('contre')) + parlement.nb(d.get('abstentions'))
                g[gp[x['organeRef']]['c']] = v.get('positionMajoritaire') if tot else 'nv'
        dec = s['syntheseVote']['decompte']
        out[n] = {'d': s['dateScrutin'], 's': s['sort']['code'], 't': s['titre'].rstrip('.'), 'g': g,
                  'pour': parlement.nb(dec.get('pour')), 'contre': parlement.nb(dec.get('contre')), 'abst': parlement.nb(dec.get('abstentions'))}
    return out


def eurostat_depart():
    """Solde public et intérêts de la dernière année publiée (Eurostat, gov_10a_main), en % du PIB."""
    from budget import lire
    ans = [str(date.today().year - k) for k in range(1, 3)]
    m = lire('gov_10a_main', geo='FR', sector='S13', unit='PC_GDP', na_item=['B9', 'D41PAY'], time=ans)
    an = max(a for (g, a, k) in m if k == 'B9' and ('FR', a, 'D41PAY') in m)
    pib = lire('nama_10_gdp', geo='FR', unit='CP_MEUR', na_item='B1GQ', time=[an])
    return {'an': int(an), 'solde': m[('FR', an, 'B9')], 'interets': m[('FR', an, 'D41PAY')], 'pib_md': round(pib[('FR', an)] / 1000, 1),
            'primaire': round(m[('FR', an, 'B9')] + m[('FR', an, 'D41PAY')], 2),
            'source': "Eurostat, principaux agrégats des administrations publiques (gov_10a_main) : solde et intérêts payés",
            'url': 'https://ec.europa.eu/eurostat/databrowser/view/gov_10a_main/default/table'}


def construire():
    mes, nic, mac = charger('mesures_2027.json'), charger('depenses_fiscales.json'), charger('parametres_macro.json')
    P = {x['cle']: x for x in mac['parametres']}
    cartes, ecartees = [], []
    nums = {n for n, _ in SCRUTINS.values()}
    pos = positions(nums)
    for x in mes['mesures']:
        if x['id'] in EXCLUES:
            ecartees.append({'id': x['id'], 'l': x['l'], 'pourquoi': EXCLUES[x['id']]}); continue
        c = M2027.get(x['id'])
        if not c:
            ecartees.append({'id': x['id'], 'l': x['l'], 'pourquoi': 'pas encore classée'}); continue
        inv = -1 if c.get('inverse') else 1
        k = {'id': x['id'], 'origine': 'plf' if x['texte'].startswith('PLF ') else 'plfss', 'texte': x['texte'], 'l': c.get('l', x['l']),
             'quoi': c.get('quoi', x['quoi']), 'theme': c['theme'], 'qui': c['qui'], 'qui_texte': x['qui'], 'macro': c['macro'], 'sens': x['type'],
             'effet': effet_md(x['effet_meur'], inv), 'note': (c.get('note', x.get('note') or '') + (' ' + c['note_plus'] if c.get('note_plus') else '')).strip(), 'statut': c.get('statut', x.get('statut') or ''),
             'src': {'doc': x.get('document') or x['texte'], 'page': x.get('page'), 'url': x['url'], 'citation': x['citation']}}
        if c.get('exclusif'): k['exclusif'] = c['exclusif']
        if x['id'] in PONCTUELLES: k['ponctuelle'] = True
        if x['id'] in SCRUTINS:
            n, sens = SCRUTINS[x['id']]
            if n in pos:
                k['an'] = {'n': n, 'sens': sens, **pos[n]}
        cartes.append(k)
    for n in nic['niches']:
        c = NICHES.get(n['num'])
        if n['num'] == '940102':
            ecartees.append({'id': 'niche-940102', 'l': n['l'], 'pourquoi': "exonération réduite par la loi de finances pour 2025 (voitures à hydrogène et électriques à faible empreinte carbone seulement) : le chiffrage publié porte sur l'ancienne exonération"}); continue
        if not c:
            ecartees.append({'id': 'niche-' + n['num'], 'l': n['l'], 'pourquoi': 'chiffrage contradictoire ou réductions déjà acquises'}); continue
        an = n.get('annee_retenue') or max(a for a, v in n['cout_meur'].items() if v)
        v = n['cout_meur'][an]
        k = {'id': 'niche-' + n['num'], 'origine': 'niche', 'l': c['l'], 'officiel': n['l'], 'theme': c['theme'], 'qui': c['qui'],
             'qui_texte': n.get('beneficiaires') or '', 'macro': c['macro'], 'sens': 'recette', 'effet': {an: round(v / 1000, 3)},
             'cout_annee': an, 'fiabilite': n.get('fiabilite'), 'impot': n['impot'],
             'src': {'doc': nic['source']['titre'], 'page': n.get('page'), 'url': nic['source']['url'], 'citation': n['citation']}}
        if c.get('exclusif'): k['exclusif'] = c['exclusif']
        cartes.append(k)
    # Retraites : la suspension de la réforme de 2023 (chiffrage du Gouvernement au dépôt de la lettre rectificative).
    s = P.get('retraites2023_suspension_cout_gouvernement')
    if s:
        e = s['valeurs']['ensemble du système de retraite (Md€)']
        cartes.append({'id': 'retraites-fin-suspension', 'origine': 'levier', 'l': "Revenir sur la suspension de la réforme des retraites de 2023 (âge légal porté à 64 ans)",
                       'quoi': "La réforme de 2023, suspendue par la loi de financement de la sécurité sociale pour 2026, s'applique de nouveau : l'âge légal de départ continue d'augmenter jusqu'à 64 ans.",
                       'theme': 'retraites', 'qui': ['salaries'], 'qui_texte': 'Personnes proches de la retraite', 'macro': 'depense', 'sens': 'depense',
                       'effet': {a: v for a, v in sorted(e.items())}, 'note': "Chiffrage du coût de la suspension par le Gouvernement ; aucun chiffrage officiel après " + max(e) + " : le même montant est gardé ensuite (hypothèse de Concret).",
                       'src': {'doc': s['l'], 'page': s.get('page'), 'url': s['url'], 'citation': s['citation']}})
    # SMIC : coût d'une hausse de 1 % pour les finances publiques (simulation de la DG Trésor, rapport du groupe d'experts) ;
    # une hausse de p % est comptée p fois ce coût (proportionnalité : hypothèse de Concret).
    sm = charger('smic_emploi_taux.json')
    E = {x['cle']: x for x in sm['elements']} if sm else {}
    x, el = E.get('smic_cout_hausse_1pct_finances_publiques'), E.get('elasticite_emploi_cout_travail_smic')
    if x:
        for pc in (2, 5):
            cartes.append({'id': 'smic-%d' % pc, 'origine': 'levier', 'exclusif': 'smic',
                           'l': "Augmenter le SMIC de %d %% en %s, en plus de sa revalorisation automatique" % (pc, date.today().year + 1),
                           'quoi': "Le SMIC brut passe de %s € à %s € par mois." % (fr_nb(E['smic_mensuel_brut']['valeurs']['brut']), fr_nb(E['smic_mensuel_brut']['valeurs']['brut'] * (1 + pc / 100))),
                           'theme': 'travail', 'qui': ['smic', 'entreprises'], 'qui_bilan': ['smic'], 'qui_titre': 'Qui reçoit et qui paie', 'qui_texte': 'Salariés au SMIC (plus de salaire) ; employeurs (coût du travail)',
                           'macro': None, 'sens': 'depense', 'effet': {str(date.today().year + 1): round(pc * x['valeurs']['total'] / 1000, 3)},
                           'note': "Chiffrage de la DG Trésor pour une hausse de 1 %% (coût des allègements de cotisations, salaires publics, prestations, impôts), sans effet sur l'emploi ; Concret le multiplie par %d. Effet sur l'emploi : le groupe d'experts sur le SMIC retient qu'une hausse de 1 %% du coût du travail au niveau du SMIC réduit la demande de travail à ce niveau de %s à %s %% ; aucune source officielle ne donne un nombre d'emplois, il n'est pas compté ici." % (pc, fr_nb(-el['valeurs']['basse']), fr_nb(-el['valeurs']['haute'])) if el else '',
                           'src': {'doc': x['l'], 'page': x.get('page'), 'url': x['url'], 'citation': x['citation']}})
    # Leviers de dépense chiffrés par la Commission des comptes de la Sécurité sociale (tableau de sensibilité, octobre 2026)
    # et par le Gouvernement (point d'indice, 2022). Une hausse ou une baisse de x fois l'unité est comptée x fois (hypothèse de Concret).
    an1 = str(date.today().year + 1)
    CCSS = {'doc': "Commission des comptes de la Sécurité sociale, rapport d'octobre 2026, tableau 2 « Sensibilité des résultats des régimes et branches de sécurité sociale aux hypothèses de prévision »",
            'page': '8', 'url': 'https://www.securite-sociale.fr/files/live/sites/SSFR/files/medias/CCSS/2026/CCSS-octobre-2026_assemble_VDEF.pdf'}
    ondam = "Dépenses maladie : impact d’une hausse de 1 % dans le champ de l’ONDAM […] Tous régimes 2 650 (en millions d’euros)"
    revalo = "Inflation : impact (en année pleine) d’une hausse de 1 point du taux d'inflation sur la revalorisation légale des prestations […] Tous régimes 3 370 (en millions d’euros)"
    ag = "Allègements généraux (AG) : impact d’une hausse de 1 % du coût sur les cotisations nettes […] Tous régimes -560 (en millions d’euros)"
    lev = [
        ('ondam-moins-1', "Faire progresser les dépenses d'assurance maladie (ONDAM) de 1 % de moins en " + an1, "Les dépenses remboursées par l'assurance maladie (soins de ville, hôpitaux, médico-social) augmentent de 1 % de moins que l'objectif prévu.", 'sante', ['assures', 'soignants'], 'depense', 2.65, ondam, ['ondam-plus-1'], "Objectif proposé pour " + an1 + " : +2,0 %, soit 278,7 Md€ (projet de loi de financement de la sécurité sociale, article 43)."),
        ('ondam-plus-1', "Faire progresser les dépenses d'assurance maladie (ONDAM) de 1 % de plus en " + an1, "Les dépenses remboursées par l'assurance maladie augmentent de 1 % de plus que l'objectif prévu.", 'sante', ['assures', 'soignants'], 'depense', -2.65, ondam, ['ondam-moins-1'], ''),
        ('revalo-moins-1', "Revaloriser toutes les prestations de sécurité sociale d'un point de moins que l'inflation en " + an1, "Pensions de base, prestations familiales et autres prestations des régimes de base augmentent d'un point de moins que la hausse des prix.", 'retraites', ['retraites', 'familles'], 'depense', 3.37, revalo, ['revalo-plus-1', 'pensions-revalorisation-2027', 'prestations-familiales-gel'], "Régimes de base seulement (pas les retraites complémentaires Agirc-Arrco)."),
        ('revalo-plus-1', "Revaloriser toutes les prestations de sécurité sociale d'un point de plus que l'inflation en " + an1, "Pensions de base, prestations familiales et autres prestations des régimes de base augmentent d'un point de plus que la hausse des prix.", 'retraites', ['retraites', 'familles'], 'depense', -3.37, revalo, ['revalo-moins-1', 'pensions-revalorisation-2027', 'prestations-familiales-gel'], "Régimes de base seulement (pas les retraites complémentaires Agirc-Arrco)."),
        ('allegements-moins-10', "Faire payer plus de cotisations aux employeurs sur les salaires proches du SMIC (allègements réduits de 10 %)", "Les réductions générales de cotisations patronales baissent de 10 % : les employeurs paient plus de cotisations sur ces salaires.", 'entreprises', ['entreprises'], 'cotis_emp', 5.6, ag, [], "La source chiffre 1 % ; Concret multiplie par 10. Coût des allègements généraux prévu pour " + an1 + " : 72,8 Md€ (même rapport, p. 67). Effet sur l'emploi : compté par le modèle Mésange (cotisations des employeurs), si l'effet sur l'activité est coché."),
    ]
    for i, l, q, th, qui, mac, v, cit, exc, note in lev:
        cartes.append({'id': i, 'origine': 'levier', 'l': l, 'quoi': q, 'theme': th, 'qui': qui, 'qui_texte': '', 'macro': mac,
                       'sens': 'depense' if mac == 'depense' else 'recette', 'effet': {an1: v}, 'exclut': exc,
                       'note': (note + ' ' if note else '') + "Effet en année pleine, gardé chaque année ensuite.", 'src': dict(CCSS, citation=cit)})
    pi = P.get('cout_1pct_point_indice')
    if pi:
        cartes.append({'id': 'point-indice-plus-1', 'origine': 'levier', 'l': "Augmenter de 1 % le point d'indice des fonctionnaires en " + an1,
                       'quoi': "Le traitement de base des agents des trois fonctions publiques (État, collectivités, hôpitaux) augmente de 1 %. Le projet de budget 2027 prévoit de ne pas le revaloriser.",
                       'theme': 'etat', 'qui': ['agents_publics'], 'qui_titre': 'Qui reçoit', 'qui_texte': '5,85 millions d\'agents publics fin 2024 (DGAFP)', 'macro': 'depense', 'sens': 'depense',
                       'effet': {an1: -round(7.5 / 3.5, 2)}, 'note': "Dernier chiffrage officiel : la hausse de 3,5 % de juillet 2022 a coûté 7,5 Md€ ; Concret divise par 3,5. Montant de 2022, sans tenir compte de la hausse des salaires depuis.",
                       'src': {'doc': pi['l'], 'page': pi.get('page'), 'url': pi['url'], 'citation': pi['citation']}})
    # Assiettes des « mesures à vous » : le montant officiel d'un impôt ou d'une dépense ; le visiteur choisit un pourcentage,
    # l'effet est ce pourcentage du montant (calcul de Concret, à comportements inchangés hors effet sur l'activité).
    assiettes = []
    lvd = charger('leviers_depense.json')
    LV = {x['id']: x for x in lvd['leviers']} if lvd else {}
    def ass(k, l, groupe, md, an, qui, macro, x, note='', exclut=()):  # x : élément de source (l, page, url, citation)
        assiettes.append({'k': k, 'l': l, 'groupe': groupe, 'md': round(md, 3), 'an': an, 'qui': qui, 'macro': macro, 'exclut': list(exclut),
                          'note': note, 'src': {'doc': x.get('l', ''), 'page': x.get('page'), 'url': x['url'], 'citation': x['citation']}})
    if LV:
        ass('retraites', 'Retraites (toutes les pensions)', 'depense', LV['retraites-depense']['montant']['2025, ensemble du système de retraite (Md€)'], 2025, ['retraites'], 'depense', LV['retraites-depense'],
            "Ensemble du système de retraite, régimes de base et complémentaires (Conseil d'orientation des retraites).", ['pensions-revalorisation-2027', 'revalo-moins-1', 'revalo-plus-1'])
        ass('ondam', "Assurance maladie (soins remboursés, hôpitaux)", 'depense', 278.7, 2027, ['assures', 'soignants'], 'depense', LV['sante-ondam'], "Objectif de dépenses de l'assurance maladie (ONDAM) proposé par le Gouvernement pour 2027.", ['ondam-moins-1', 'ondam-plus-1'])
        ass('remunerations', 'Salaires des agents publics (État, collectivités, hôpitaux, sécurité sociale)', 'depense', LV['fp-masse-salariale-apu']['montant']['2025 (Md€, toutes administrations publiques)'], 2025, ['agents_publics'], 'depense', LV['fp-masse-salariale-apu'], "Rémunérations versées par l'ensemble des administrations publiques (Insee), enseignants et militaires compris.", ['point-indice-plus-1', 'enseignement', 'defense'])
        ass('enseignement', "Enseignement scolaire (écoles, collèges, lycées)", 'depense', LV['education-enseignement-scolaire']['montant']['crédits de paiement hors CAS Pensions (Md€)']['PLF 2027'], 2027, ['ecoles'], 'depense', LV['education-enseignement-scolaire'], "Crédits de la mission Enseignement scolaire du budget de l'État, hors pensions (comptées dans les retraites).", ['remunerations'])
        ass('defense', 'Défense', 'depense', LV['defense-credits']['montant']['crédits de paiement hors CAS Pensions (Md€)']['PLF 2027'], 2027, ['defense'], 'depense', LV['defense-credits'], "Crédits de la mission Défense du budget de l'État, hors pensions (comptées dans les retraites).", ['remunerations'])
        ass('chomage', "Allocations chômage", 'depense', LV['chomage-depense']['montant']['allocations brutes et aides (Md€)']['2027'], 2027, ['chomeurs'], 'depense', LV['chomage-depense'], "Allocations et aides versées par l'Unédic (prévision).")
        ass('apl', 'Aides au logement (APL)', 'depense', LV['prestations-apl']['montant']["dépense d'aides personnelles au logement (Md€)"]['2025'], 2025, ['familles'], 'depense', LV['prestations-apl'], '')
        ass('alloc-familiales', 'Allocations familiales', 'depense', LV['prestations-allocations-familiales']['montant']['allocations familiales (M€)']['2027 prévision'] / 1000, 2027, ['familles'], 'depense', LV['prestations-allocations-familiales'], '', ['prestations-familiales-gel'])
        ass('aah', "Allocation aux adultes handicapés (AAH)", 'depense', LV['prestations-aah']['montant']['2027, PLF 2027 (Md€)'], 2027, ['handicap'], 'depense', LV['prestations-aah'], '')
        ass('allegements', "Baisses de cotisations accordées aux employeurs (les réduire = les employeurs paient plus)", 'depense', LV['entreprises-allegements-generaux']['montant']['coût des allègements généraux, champ régimes de base, Unédic, Agirc-Arrco et FNAL (M€)']['2027 prévision'] / 1000, 2027, ['entreprises'], 'cotis_emp', LV['entreprises-allegements-generaux'],
            "Réductions de cotisations sur les salaires : les réduire, c'est faire payer plus de cotisations aux employeurs.", ['allegements-moins-10'])
    if LV:
        ij = LV['sante-indemnites-journalieres']
        ass('ij-maladie', "Indemnités journalières maladie (arrêts maladie)", 'depense', ij['montant']['dont maladie (M€)']['2025'] / 1000, 2025, ['malades'], 'depense', ij, "Régime général (y compris anciens indépendants), Commission des comptes de la Sécurité sociale.")
        ass('ij-atmp', "Indemnités journalières des accidents du travail et maladies professionnelles", 'depense', ij['montant']['dont accidents du travail et maladies professionnelles (M€)']['2025'] / 1000, 2025, ['malades'], 'depense', ij, "Régime général, Commission des comptes de la Sécurité sociale.")
    asd = charger('assiettes.json')
    AE = {x['cle']: x for x in asd['elements']} if asd else {}
    def asx(cle):
        x = AE[cle]; return {'l': x['l'], 'page': x.get('page'), 'url': x['url'], 'citation': x['citation']}
    if AE:
        an2 = date.today().year + 1
        ass('ir', "Impôt sur le revenu", 'recette', AE['ir_net']['valeurs']['2027_plf'], an2, ['menages_imposables'], 'ir', asx('ir_net'), "Recette nette prévue pour l'État en " + str(an2) + " (projet de loi de finances).", ['ir-indexation-bareme'])
        ass('is', "Impôt sur les sociétés", 'recette', AE['is_net']['valeurs']['2027_plf'], an2, ['entreprises'], None, asx('is_net'), "Recette nette prévue pour l'État en " + str(an2) + " (projet de loi de finances). Le modèle Mésange (direction du Trésor et Insee) ne donne pas l'effet de cet impôt sur l'activité.")
        # Toute la TVA des administrations publiques (Eurostat) : un changement de taux touche aussi les parts de la Sécurité sociale et des collectivités.
        if 'tva_apu' in AE:
            ass('tva', "TVA", 'recette', AE['tva_apu']['valeurs']['2025_eurostat'], 2025, ['consommateurs'], 'tva', asx('tva_apu'), "Toute la TVA des administrations publiques (État, Sécurité sociale, collectivités) : un changement de taux touche chacune de ces parts. Montant de 2025, qui suit ensuite la croissance de l'économie.")
        else:
            ass('tva', "TVA (part de l'État)", 'recette', AE['tva_nette_etat']['valeurs']['2027_plf'], an2, ['consommateurs'], 'tva', asx('tva_nette_etat'), "Recette nette de l'État ; une autre part de la TVA va à la Sécurité sociale et aux collectivités.")
        ass('csg', "CSG (contribution sociale généralisée)", 'recette', AE['csg_produit']['valeurs']['2027_p'] / 1000, an2, ['salaries', 'retraites'], 'csg', asx('csg_produit'), "Produit prévu (Commission des comptes de la Sécurité sociale) ; un point de CSG rapporte environ 18,4 Md€.")
        ass('carburants', "Taxes sur les carburants (accise, ex-TICPE)", 'recette', AE['accise_energies_nette']['valeurs']['2027_plf_euros_carburants'] / 1e9, an2, ['automobilistes', 'consommateurs'], None, asx('accise_energies_nette'), "Part de l'État seulement : les régions et départements reçoivent aussi une part de cette taxe, que la source ne chiffre pas ici. Le montant d'un changement de tarif est donc un minimum. Le modèle Mésange (direction du Trésor et Insee) ne donne pas l'effet de cette taxe sur l'activité.")
        ass('ame', "Aide médicale de l'État (AME)", 'depense', AE['ame_credits_2027']['valeurs']['2027_plf_CP'] / 1e9, an2, ['etrangers'], 'depense', asx('ame_credits_2027'),
            "Crédits prévus. En 2025, la dépense réelle a été de 1,47 Md€ pour 1,21 Md€ de crédits ; " + '{:,}'.format(AE['ame_beneficiaires']['valeurs']['31_12_2025']).replace(',', ' ') + " bénéficiaires fin 2025.")
        ass('c2s', "Complémentaire santé solidaire (C2S, ex-CMU complémentaire)", 'depense', AE['c2s_depense']['valeurs']['2024_depense_nette'], 2024, ['assures'], 'depense', asx('c2s_depense'), "Dépense nette 2024, dernier chiffre publié ; 7,79 millions de bénéficiaires fin 2024.")
        ass('rsa', "RSA (versé par les départements)", 'depense', AE['rsa_departements']['valeurs']['2025'] / 1000, 2025, ['solidarite'], 'depense', asx('rsa_departements'), "Dépense des départements en 2025. Dans certains départements, c'est l'État qui verse le RSA : cette part n'est pas comptée.")
        ass('prime-activite', "Prime d'activité", 'depense', AE['prime_activite']['valeurs']['2027_plf'], an2, ['prime_activite'], 'depense', asx('prime_activite'), "Dépense prévue de l'État.", ['prime-activite-gel'])
        ass('aspa', "Minimum vieillesse (ASPA, régime général)", 'depense', AE['aspa_minimum_vieillesse']['valeurs']['2027_p_cnav'] / 1000, an2, ['retraites'], 'depense', asx('aspa_minimum_vieillesse'), "Dépense prévue de la caisse nationale d'assurance vieillesse seule (pas tous les régimes).")
        # l'APL du projet de loi de finances remplace le chiffre de 2025
        for a in assiettes:
            if a['k'] == 'apl':
                a.update({'md': AE['apl']['valeurs']['2027_plf'], 'an': an2, 'note': "Dépense prévue de l'État (contribution au Fonds national des aides au logement).", 'src': {'doc': AE['apl']['l'], 'page': AE['apl'].get('page'), 'url': AE['apl']['url'], 'citation': AE['apl']['citation']}})
        x = AE['etrangers_carence_prestations_familiales_apl']['valeurs']
        cartes.append({'id': 'etrangers-residence-prestations', 'origine': 'plfss', 'texte': 'PLFSS 2027, article 37', 'l': "Exiger un an de résidence aux étrangers hors Union européenne pour les prestations familiales et les aides au logement",
                       'quoi': "Les étrangers venus d'un pays hors de l'Union européenne doivent résider en France depuis au moins un an pour toucher les prestations familiales et les aides au logement.",
                       'theme': 'solidarite', 'qui': ['etrangers'], 'qui_texte': '', 'macro': 'depense', 'sens': 'depense',
                       'effet': {str(an2): round((x['famille_2027'] + x['apl_2027']) / 1000, 4), str(an2 + 1): round((x['famille_annee_pleine'] + x['apl_annee_pleine']) / 1000, 4)},
                       'statut': "Projet de loi rejeté par l'Assemblée en première lecture le 23 octobre 2026.",
                       'note': "Sous le seuil de 300 M€ des autres cartes du budget de la Sécurité sociale : ajoutée parce que c'est la seule mesure chiffrée officiellement sur l'accès des étrangers aux prestations.",
                       'src': asx('etrangers_carence_prestations_familiales_apl') | {'doc': AE['etrangers_carence_prestations_familiales_apl']['l']}})
    # Mesures souvent débattues, chacune avec un chiffrage officiel (Cour des comptes, rapports parlementaires, Gouvernement).
    mdb = charger('mesures_debattues.json')
    MD = {x['cle']: x for x in mdb['elements']} if mdb else {}
    def srcd(cle):
        x = MD[cle]; return {'doc': x['l'], 'page': x.get('page'), 'url': x['url'], 'citation': x['citation']}
    def debat(i, l, quoi, theme, qui, macro, sens, effet, cle, note, exclut=(), qui_titre=None):
        c = {'id': i, 'origine': 'debat', 'l': l, 'quoi': quoi, 'theme': theme, 'qui': qui, 'qui_texte': '', 'macro': macro, 'sens': sens,
             'effet': effet, 'exclut': list(exclut), 'note': note, 'src': srcd(cle)}
        if qui_titre: c['qui_titre'] = qui_titre
        cartes.append(c)
    if MD:
        a1 = date.today().year + 1
        u = MD['univ_hausse_droits_cour_2018']['valeurs']
        debat('univ-master-doctorat', "Porter les droits d'inscription à l'université à %d € en master et %d € en doctorat" % (u['master porté à (€)'], u['doctorat porté à (€)']),
              "Les droits annuels augmentent en master et en doctorat ; la licence ne change pas. Les étudiants boursiers restent exonérés.", 'etudes', ['etudiants'], None, 'recette',
              {str(a1): u['recette supplémentaire visée (M€ par an, 2018-2019)'] / 1000}, 'univ_hausse_droits_cour_2018',
              "Scénario de la Cour des comptes (2018) : la recette va aux universités. Si l'État compense davantage l'exonération des boursiers, il lui en coûterait de %d à %d M€ par an selon la Cour ; non compté ici." % tuple(u["surcoût pour l'État de la compensation des boursiers, scénario central (M€ par an)"]), ['univ-30'])
        debat('univ-30', "Augmenter de 30 % tous les droits d'inscription à l'université", "Les droits annuels de licence, master et doctorat augmentent de 30 %. Les boursiers restent exonérés.", 'etudes', ['etudiants'], None, 'recette',
              {str(a1): u['hausse générale de 30 % : recette supplémentaire (M€)'] / 1000}, 'univ_hausse_droits_cour_2018', "Chiffrage de la Cour des comptes pour 2018-2019.", ['univ-master-doctorat'])
        debat('carence-3-jours', "Passer à 3 jours de carence pour les arrêts maladie des fonctionnaires de l'État", "Les trois premiers jours d'un arrêt maladie ne sont plus payés aux agents de l'État (un seul aujourd'hui).", 'etat', ['agents_publics'], 'depense', 'depense',
              {str(a1): MD['carence_fonction_publique']['valeurs']["3 jours de carence, fonction publique de l'État (M€ par an, IGF-IGAS 2024)"] / 1000}, 'carence_fonction_publique',
              "Chiffrage de l'inspection générale des finances et de l'inspection générale des affaires sociales (2024), cité par la commission des finances du Sénat. Fonction publique de l'État seulement.")
        debat('isf', "Rétablir l'impôt sur la fortune (ISF) à la place de l'impôt sur la fortune immobilière", "L'impôt sur la fortune porte de nouveau sur tout le patrimoine (placements financiers compris), et plus seulement sur l'immobilier.", 'patrimoine', ['patrimoine'], None, 'recette',
              {str(a1): MD['isf_retablissement']['valeurs']['perte de recettes 2022 (comité de suivi de la réforme de la fiscalité du capital, Md€)']}, 'isf_retablissement',
              "Montant : ce que le remplacement de l'ISF par l'IFI a fait perdre à l'État en 2022 (comité de suivi, cité par le Sénat). Aucun chiffrage officiel d'un rétablissement, avec ses effets sur les comportements.")
        z = MD['taxe_zucman_chiffrages']['valeurs']
        debat('taxe-zucman', "Créer un impôt plancher de 2 % sur les patrimoines de plus de 100 millions d'euros (« taxe Zucman »)", "Les foyers dont le patrimoine dépasse 100 M€ paient au moins 2 % de ce patrimoine par an, impôts déjà payés compris.", 'patrimoine', ['patrimoine'], None, 'recette',
              {str(a1): z['scénario prudent (40 % des fortunes hors dispositif, Md€)']}, 'taxe_zucman_chiffrages',
              "Compté : le scénario prudent du rapport de la commission des finances de l'Assemblée (%s Md€). Les économistes auditionnés donnent %d à %d Md€ ; l'administration fiscale dit ne pas pouvoir simuler cet impôt, et le Gouvernement n'a publié aucun montant." % (str(z['scénario prudent (40 % des fortunes hors dispositif, Md€)']).replace('.', ','), z['économistes auditionnés, fourchette (Md€ par an)'][0], z['économistes auditionnés, fourchette (Md€ par an)'][1]))
        debat('franchises-x2', "Doubler les franchises médicales et les participations forfaitaires", "Ce qui reste à payer par le patient sur les médicaments, consultations et transports (franchises et participations) double, plafonds compris.", 'sante', ['assures'], 'depense', 'depense',
              {str(a1): MD['franchises_doublement']['valeurs']['doublement des montants et plafonds, année pleine (Md€)']}, 'franchises_doublement', "Chiffrage en année pleine (Cour des comptes, 2026) ; ce doublement avait été annoncé puis abandonné.")
        ra = MD['retraite_age_cour_comptes_2025']['valeurs']
        def rampe(v35, debut):
            # Le chiffrage porte sur 2035. L'effet commence l'année où l'âge change vraiment pour quelqu'un (d'après le calendrier
            # écrit sur la carte), puis Concret le fait monter en ligne droite jusqu'en 2035 (hypothèse écrite sur la carte).
            # Pas d'effet avant 2032 : 0 chaque année du jeu.
            if debut > 2031: return {str(a1): 0.0}
            return {str(a): (round(v35 * (a - debut + 1) / (2035 - debut + 1), 3) if a >= debut else 0.0) for a in range(a1, 2032)}
        age = ['retraite-62', 'retraite-63', 'retraite-65', 'retraites-fin-suspension']
        noteR = "Chiffrage de la Cour des comptes pour 2035 (système de retraite). "
        cal = "D'après ce calendrier, l'âge minimum passe 63 ans pour les personnes nées en 1966 (en 2029) et atteint 64 ans pour celles nées en 1969 (en 2033). "
        n62 = noteR + "L'âge de 62 ans change les départs dès %d (aujourd'hui, 62 ans et 9 mois) ; Concret fait monter l'effet en ligne droite de %d à 2035 (hypothèse). " % (a1, a1)
        n63 = noteR + cal + "S'arrêter à 63 ans change donc les départs à partir de 2029 environ ; Concret fait monter l'effet en ligne droite de 2029 à 2035 (hypothèse). "
        n65 = noteR + cal + "Passer à 65 ans ne change donc les départs qu'après 2031 : rien n'est compté dans les cinq ans du jeu. "

        debat('retraite-63', "Ramener l'âge légal de départ à la retraite à 63 ans", "L'âge minimum de départ est de 62 ans et 9 mois pour les personnes nées entre le 1er janvier 1963 et le 31 mars 1965, puis monte jusqu'à 64 ans pour celles nées à partir de 1969 (réforme de 2023, suspendue en 2026). La hausse s'arrête à 63 ans au lieu de 64 ans. Le chiffrage de la Cour des comptes compare à 64 ans.", 'retraites', ['salaries'], 'depense', 'depense',
              rampe(-ra['âge ramené de 64 à 63 ans : dépense supplémentaire en 2035 (Md€)'], 2029), 'retraite_age_cour_comptes_2025', n63 + "Dépense en plus en 2035 : 5,8 Md€.", [x for x in age if x != 'retraite-63'], 'Qui reçoit')
        debat('retraite-62', "Revenir à la retraite à 62 ans", "L'âge minimum de départ est de 62 ans et 9 mois pour les personnes nées entre le 1er janvier 1963 et le 31 mars 1965, puis monte jusqu'à 64 ans pour celles nées à partir de 1969 (réforme de 2023, suspendue en 2026). L'âge minimum est ramené à 62 ans pour tous, au lieu de 64 ans à terme. Le chiffrage de la Cour des comptes compare à 64 ans.", 'retraites', ['salaries'], 'depense', 'depense',
              rampe(-ra['retour à 62 ans : « en gros, deux fois plus » (Md€, ordre de grandeur)'], a1), 'retraite_age_cour_comptes_2025', n62 + "Pour 62 ans, la Cour dit « en gros, deux fois plus » que pour 63 ans : 11,6 Md€ en 2035 (ordre de grandeur).", [x for x in age if x != 'retraite-62'], 'Qui reçoit')
        debat('retraite-65', "Porter l'âge légal de départ à la retraite à 65 ans", "L'âge minimum de départ est de 62 ans et 9 mois pour les personnes nées entre le 1er janvier 1963 et le 31 mars 1965, puis monte jusqu'à 64 ans pour celles nées à partir de 1969 (réforme de 2023, suspendue en 2026). L'âge minimum est porté à 65 ans à terme, au lieu de 64 ans. Le chiffrage de la Cour des comptes compare à 64 ans.", 'retraites', ['salaries'], 'depense', 'depense',
              rampe(ra['âge porté à 65 ans : gain en 2035 (Md€)'], 2032), 'retraite_age_cour_comptes_2025', n65 + "Économie en 2035 : 8,4 Md€, après les cinq ans du jeu. Se vote avec « Revenir à la réforme des retraites », qui accélère la hausse jusqu'à 64 ans.", ['retraite-62', 'retraite-63'])
        cartes[-1]['hors_jeu'] = {'an': 2035, 'md': ra['âge porté à 65 ans : gain en 2035 (Md€)']}
        f = MD['fonctionnaires_non_remplacement_un_sur_deux']['valeurs']
        debat('fonctionnaires-1-sur-2', "Ne remplacer qu'un fonctionnaire de l'État sur deux partant à la retraite", "La moitié des agents de l'État qui partent à la retraite ne sont pas remplacés.", 'etat', ['agents_publics'], 'depense', 'depense',
              # Chaque année, une nouvelle vague de départs n'est pas remplacée : les économies s'ajoutent (0,75 Md€ la première année
              # pour chaque vague, 0,98 Md€ les années suivantes).
              {str(a): round((f["économie brute immédiate, budget de l'État (M€ par an)"] + f['économie à moyen terme, au coût moyen sur la carrière (M€ par an)'] * (a - a1)) / 1000, 3) for a in range(a1, 2032)}, 'fonctionnaires_non_remplacement_un_sur_deux',
              "Chiffrage de la Cour des comptes (2015), le plus récent : montants de 2015, sans la hausse des salaires depuis. Chaque année, la moitié des départs de l'année n'est pas remplacée : les économies s'ajoutent. Concret compte, pour chaque vague de départs, 0,75 Md€ la première année et 0,98 Md€ les années suivantes (« à moyen terme », selon la Cour). De 2008 à 2012, la même règle a économisé 4,2 Md€ en cinq ans.")
        ass('audiovisuel', 'Audiovisuel public (France Télévisions, Radio France, Arte…)', 'depense', MD['audiovisuel_public_2027']['valeurs']["TVA affectée au compte « Avances à l'audiovisuel public », 2027 (€)"] / 1e9, a1, ['culture'], 'depense',
            {'l': MD['audiovisuel_public_2027']['l'], 'page': MD['audiovisuel_public_2027'].get('page'), 'url': MD['audiovisuel_public_2027']['url'], 'citation': MD['audiovisuel_public_2027']['citation']}, "Part de TVA affectée à l'audiovisuel public en " + str(a1) + ".")
    # Budget de l'État : chaque mission et chaque programme du projet de loi de finances (crédits de paiement de l'année à venir,
    # pensions des agents comprises). Écartés : les remboursements d'impôts, la charge de la dette, les dotations non réparties,
    # les subventions aux régimes de retraite (comptées dans les retraites), les concours aux collectivités (transferts),
    # et l'enseignement scolaire et la défense, déjà proposés hors pensions.
    import budget_missions
    HORS = ('Crédits non répartis', 'Régimes sociaux et de retraite', 'Remboursements et dégrèvements', 'Engagements financiers',
            'Relations avec les collectivités', 'Enseignement scolaire', 'Défense')
    QUI_M = {'Aide publique au développement': ['pays_aides'], 'Cohésion des territoires': ['logement_aide'], 'Écologie': ['ecologie'],
             'Recherche et enseignement supérieur': ['etudiants_recherche'], 'Solidarité': ['solidarite'], 'Travail, emploi': ['chomeurs', 'entreprises'],
             'Agriculture': ['agriculture'], 'Culture': ['culture'], 'Immigration': ['etrangers'], 'Justice': ['justice'], 'Outre-mer': ['outre_mer'],
             'Sécurités': ['securite'], 'Sport': ['associations'], 'Médias': ['culture'], 'Santé': ['assures'], 'Économie': ['entreprises'],
             'Investir pour la France': ['entreprises'], 'Monde combattant': ['anciens_combattants']}
    an_plf = date.today().year + 1
    for m in budget_missions.missions():
        if m['nom'].startswith(HORS) or not m['cp27']:
            continue
        qui = next((v for k, v in QUI_M.items() if m['nom'].startswith(k)), ['etat'])
        def src(r):
            return {'doc': budget_missions.TITRE, 'page': str(r['page']), 'url': budget_missions.PLF_URL,
                    'citation': "Ligne « %s » : crédits de paiement PLF %d : %s €" % (r['nom'], an_plf, '{:,}'.format(r['cp27']).replace(',', ' '))}
        kids = [r for r in m['programmes'] if r['cp27']]
        mk = 'mi:' + re.sub(r'\W+', '-', m['nom'].lower())[:40]
        assiettes.append({'k': mk, 'l': m['nom'], 'groupe': 'depense', 'etat': True, 'md': round(m['cp27'] / 1e9, 3), 'an': an_plf, 'qui': qui, 'macro': 'depense',
                          'exclut': [], 'note': "Mission du budget de l'État : ce que l'État prévoit de dépenser (crédits de paiement), salaires et retraites des agents compris.", 'src': src(m)})
        for r in kids:
            if len(kids) < 2: break
            k = 'pr:' + re.sub(r'\W+', '-', r['nom'].lower())[:40]
            assiettes.append({'k': k, 'l': r['nom'], 'groupe': 'depense', 'etat': True, 'parent': mk, 'md': round(r['cp27'] / 1e9, 3), 'an': an_plf, 'qui': qui, 'macro': 'depense',
                              'exclut': [mk], 'note': "Programme de la mission « " + m['nom'] + " ».", 'src': src(r)})
        # La mission exclut ses programmes (et inversement).
        M = next(a for a in assiettes if a['k'] == mk)
        M['exclut'] = [a['k'] for a in assiettes if a.get('parent') == mk]
    # Recoupements avec les autres montants : APL = programme « Aide à l'accès au logement » ; AAH dans « Handicap et dépendance ».
    A = {a['k']: a for a in assiettes}
    for a in assiettes:
        if a['l'].startswith('Aide à l’accès au logement') or a['l'].startswith("Aide à l'accès au logement"):
            a['exclut'] += ['apl']; A['apl']['exclut'].append(a['k'])
        if a['l'].startswith('Handicap et dépendance'):
            a['exclut'] += ['aah']; A['aah']['exclut'].append(a['k'])
        if a['l'].startswith('Solidarité, insertion'):
            a['exclut'] += ['aah']; A['aah']['exclut'].append(a['k'])
        if a['l'].startswith('Protection maladie') or a['l'].startswith('Santé'):
            a['exclut'] += ['ame']; A.get('ame', {'exclut': []})['exclut'].append(a['k'])
        if a['l'].startswith('Cohésion des territoires'):
            a['exclut'] += ['apl']; A['apl']['exclut'].append(a['k'])
    # Pour une personne : règles en vigueur et montant moyen, lus à la source (budget_sources/par_personne.json).
    # La moyenne n'est recalculée avec le pourcentage choisi que si elle a le même champ que la ligne du budget
    # (enseignement : dépense de tous les financeurs ; arrêts maladie : moyenne de 2023, avant le plafond actuel).
    PP_CLES = {'vie-etudiante': 'pr:vie-étudiante'}
    PP_PROPORTION = {'retraites', 'chomage', 'alloc-familiales', 'rsa', 'prime-activite', 'remunerations'}
    pp = charger('par_personne.json') if os.path.exists(os.path.join(SRC, 'par_personne.json')) else {}
    for k, v in pp.items():
        if k.startswith('_') or k == 'aide-developpement' or not v:
            continue
        a = A.get(PP_CLES.get(k, k))
        if a:
            a['pp'] = {x: v.get(x) for x in ('beneficiaires', 'moyenne', 'regles')}
            a['pp']['proportion'] = k in PP_PROPORTION
    # Population (Insee), pour ramener chaque ligne à un montant par habitant (calcul de Concret).
    if pp.get('aide-developpement', {}).get('beneficiaires'):
        x = pp['aide-developpement']['beneficiaires']
        population = {'v': x['v'] * 1e6, 'annee': x['annee'], 'source': x['source'], 'url': x['url'], 'citation': x['citation']}
    else:
        population = None
    # Recruter ou construire : coût d'un emploi (coût d'entrée publié, hors contribution au CAS Pensions) ou d'une place de prison.
    UNITES = [('policier', 'Policiers', 'pr:police-nationale'), ('gendarme', 'Gendarmes', 'pr:gendarmerie-nationale'),
              ('enseignant_1er_degre', 'Professeurs des écoles', 'enseignement'), ('enseignant_2nd_degre', 'Professeurs de collège et de lycée', 'enseignement'),
              ('magistrat', 'Magistrats (juges et procureurs)', 'pr:justice-judiciaire'), ('greffier', 'Greffiers', 'pr:justice-judiciaire'),
              ('surveillant_penitentiaire', 'Surveillants de prison', 'pr:administration-pénitentiaire'), ('militaire', 'Militaires du rang', 'defense'),
              ('place_prison_construction', 'Places de prison à construire', 'pr:administration-pénitentiaire')]
    unites = []
    if os.path.exists(os.path.join(SRC, 'couts_unitaires.json')):
        CU = charger('couts_unitaires.json')
        for k, l, ligne in UNITES:
            x = CU.get(k)
            if not x:
                continue
            m = re.search(r"Coût d'entrée : ([\d\s\u202f\u00a0]+) €", x.get('champ') or '')
            pc = x.get('par_categorie') or {}
            entree = int(re.sub(r'\D', '', m.group(1))) if m else next((v['entree'] for v in pc.values() if v.get('global') == x['v']), None)
            u = {'k': k, 'l': l, 'ligne': ligne if ligne in A else None, 'cout': x['v'], 'entree': entree, 'unite': x['unite'], 'annee': x['annee'],
                 'effectif': x.get('effectif'), 'source': x['source'], 'url': x['url'], 'page': x.get('page'), 'type': 'construction' if k.startswith('place_') else 'emploi'}
            if u['type'] == 'construction':
                u['cout_cp'] = x.get('cout_centre_penitentiaire')
                for kk in ('journee_detention', 'places_prison_operationnelles'):
                    if CU.get(kk):
                        u[kk] = {z: CU[kk].get(z) for z in ('v', 'annee', 'source', 'url', 'effectif')}
            unites.append(u)
    # Paramètres officiels des cas types (« Concrètement »), lus à la source (budget_sources/parametres_cas.json).
    cas = {}
    if os.path.exists(os.path.join(SRC, 'parametres_cas.json')):
        for k, v in charger('parametres_cas.json').items():
            if not k.startswith('_') and v:
                cas[k] = {x: v.get(x) for x in ('v', 'unite', 'date_effet', 'source', 'url')}
    for c in cartes:
        # Budgets prêts à jouer : le texte du Gouvernement tel que déposé, et ce qu'il en reste après les votes de l'Assemblée
        # en première lecture (mesure supprimée, article ou projet de loi rejeté, ou mesure non examinée : retirée).
        if c.get('origine') in ('plf', 'plfss'):
            st = c.get('statut') or ''
            retire = bool(re.search(r"Supprimée|Article rejeté|Non examinée|projet de loi rejeté|Projet de loi rejeté|Rapport annexé supprimé|n'a pas rete", st))
            c['preset'] = {'gouv': True, 'an': not retire, 'modifie': (not retire) and bool(re.search(r'Modifiée|modification', st))}
        c['sens'] = 'depense' if c['sens'] in ('dépense', 'depense') else c['sens']
        c['titre'] = COURT.get(c['id'], c['l'])
        if c['id'] in CLAIR:
            c['clair'] = {'a': CLAIR[c['id']][0], 'p': CLAIR[c['id']][1]}
        if c['id'] in PAR_QUI: c['par'] = PAR_QUI[c['id']]
        c['statut_court'] = statut_court(c.get('statut'), c['id'])
        if c['id'] in QUI_CLAIR: c['qui_texte'] = QUI_CLAIR[c['id']]
        if c['id'] in QUI_TITRE: c['qui_titre'] = QUI_TITRE[c['id']]
        ks = sorted(c['effet'])
        c['duree'] = 'une seule année' if c.get('ponctuelle') else 'par an'
    # Paramètres du modèle.
    var = {}
    for t, cle in MACRO.items():
        x = P.get(cle)
        if not x or not x.get('valeurs'):
            continue
        # Normalisé : effet d'une mesure qui améliore le solde de 1 point de PIB (baisse de dépense ou hausse d'impôt) ;
        # le modèle est linéaire (source, p. 100) : on inverse le signe des variantes publiées dans l'autre sens.
        hausse = t == 'tva'
        sg = 1 if hausse else -1
        em = E.get(cle.replace('mult_', 'emploi_'))
        if em and em.get('valeurs'):
            ev = em['valeurs']
            emp = {k: round(sg * v) for k, v in (ev.get('emploi_salarie_marchand_milliers') or {}).items()}
            cho = {k: round(sg * v, 3) for k, v in (ev.get('taux_chomage_points') or {}).items()}
        else:
            emp, cho = {}, {}
        var[t] = {'emploi': emp, 'chomage': cho, 'pib': {k: round(sg * v, 3) for k, v in x['valeurs'].items()},
                  'solde': {k: round(sg * v, 3) for k, v in (x.get('solde_primaire_pts_pib') or {}).items()},
                  'l': x['l'], 'page': x.get('page'), 'url': x['url']}
    budget = json.load(open(os.path.join(RACINE, 'donnees', 'budget.json'), encoding='utf-8'))
    return {
        'maj': date.today().isoformat(),
        'depart': eurostat_depart(),
        'cartes': cartes, 'assiettes': assiettes, 'population': population, 'cas': cas, 'unites': unites, 'ecartees': ecartees, 'themes': THEMES, 'qui': QUI,
        'groupes': json.load(open(os.path.join(RACINE, 'donnees', 'votes.json'), encoding='utf-8'))['GROUPES'],
        'variantes': var, 'regle': REGLE, 'defis': DEFIS,
        'pays_fmi': charger('fmi_pays.json'),
        'cible': ({'v': -AE['cible_solde_2027']['valeurs']['2027_plf_pct_pib'], 'an': AE['cible_solde_2027']['annee'], 'source': AE['cible_solde_2027']['document'] + ', ' + AE['cible_solde_2027']['page'],
                   'url': AE['cible_solde_2027']['url'], 'citation': AE['cible_solde_2027']['citation']} if 'cible_solde_2027' in AE else None),
        'variantes_source': P['mesange2017_linearite']['citation'] if 'mesange2017_linearite' in P else '',
        'taux': {**{k: P[k] for k in ('oat10_moyenne_annuelle', 'oat10_dernier_mois', 'dette_etat_duree_vie_moyenne') if k in P},
                 **({'mensuel': E['taux_etat_10ans_dernier_mois']} if 'taux_etat_10ans_dernier_mois' in E else {})},
        'projection': budget['projection'],
        'sources': {'mesures': mes.get('sources'), 'niches': nic['source']},
    }


def main():
    o = construire()
    d = o['depart']
    print('Départ', d['an'], ': solde', d['solde'], ', intérêts', d['interets'], ', solde primaire', d['primaire'])
    print(len(o['cartes']), 'cartes ;', len(o['ecartees']), 'écartées :', ', '.join(e['id'] for e in o['ecartees']))
    for c in o['cartes']:
        print('  %-36s %-6s %-12s %s' % (c['id'], c['origine'], c['macro'] or '—', c['effet']))
    print('Variantes :', ', '.join(o['variantes']))
    if '--ecrire' in sys.argv:
        json.dump(o, open(SORTIE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('Écrit :', SORTIE)


if __name__ == '__main__':
    main()
