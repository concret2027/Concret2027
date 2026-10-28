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
                             'statut': "L'Assemblée a adopté le relèvement du barème (article 2, scrutin n° 8737, 15 octobre 2026) : elle n'a pas retenu ce gel."},
    'ir-indemnites-rupture': {'theme': 'travail', 'qui': ['salaries'], 'macro': 'ir'},
    'secu-indemnites-rupture': {'theme': 'travail', 'qui': ['salaries', 'entreprises'], 'macro': 'cotis_sal'},
    'ir-indemnites-journalieres': {'theme': 'sante', 'qui': ['malades'], 'macro': 'ir'},
    'csg-indemnites-journalieres': {'theme': 'sante', 'qui': ['malades'], 'macro': 'csg'},
    'ir-abattement-retraites': {'theme': 'retraites', 'qui': ['retraites'], 'macro': 'ir', 'exclusif': 'abattement-retraites'},
    'apport-cession': {'theme': 'patrimoine', 'qui': ['patrimoine'], 'macro': None},
    'contribution-grandes-entreprises': {'theme': 'entreprises', 'qui': ['grandes_entreprises'], 'macro': None},
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
EXCLUES = {'fctva-taux': "versement de l'État aux collectivités : le document chiffre la moindre dépense de l'État, pas l'effet sur le déficit public total",
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
COURT = {
    'ir-indexation-bareme': "Geler le barème de l'impôt sur le revenu",
    'ir-indemnites-rupture': "Imposer les indemnités de rupture au-delà de 48 060 €",
    'secu-indemnites-rupture': "Cotisations sur les indemnités de rupture au-delà de 48 060 €",
    'ir-indemnites-journalieres': "Imposer une partie des indemnités d'arrêt de travail",
    'csg-indemnites-journalieres': "Relever la CSG sur les indemnités d'arrêt de travail",
    'ir-abattement-retraites': "Plafonner à 3 000 € l'abattement de 10 % des retraités",
    'apport-cession': "Taxer des plus-values transmises par une holding",
    'contribution-grandes-entreprises': "Prolonger la surtaxe sur les bénéfices des grandes entreprises",
    'contribution-transport-maritime': "Prolonger la surtaxe sur les grands armateurs",
    'tva-television': "TVA au taux normal sur les abonnements télé",
    'taxe-infrastructures-transport': "Taxer plus les exploitants de transport les plus rentables",
    'avoirs-desherence': "Prélever 17 % sur l'argent des comptes oubliés",
    'cpeb': "Faire contribuer les collectivités à l'effort budgétaire",
    'cufpa-plafond': "Plafonner l'argent versé à France compétences",
    'prime-activite-gel': "Geler la prime d'activité en 2027",
    'formation-pric-cfa': "Arrêter des aides régionales à la formation et aux CFA",
    'cpf-participation': "Faire payer plus les formations du CPF sans projet",
    'allegements-complements-salaire': "Moins d'allègements de cotisations sur les primes",
    'taxe-produits-sucres': "Étendre la « taxe soda » aux produits sucrés",
    'contribution-complementaires-sante': "Prolonger la taxe sur les mutuelles",
    'pensions-revalorisation-2027': "Ne revaloriser que les retraites sous 1 260 € par mois",
    'prestations-familiales-gel': "Geler les prestations familiales en 2027",
    'allocation-rentree-scolaire': "Réduire l'allocation de rentrée scolaire",
    'etrangers-residence-prestations': "Un an de résidence pour les aides des étrangers hors UE",
    'niche-200302': "Supprimer le crédit d'impôt recherche",
    'niche-110246': "Supprimer le crédit d'impôt pour l'emploi à domicile",
    'niche-120401': "Supprimer l'abattement de 10 % des retraités",
    'niche-520110': "Taxer normalement les transmissions d'entreprises",
    'niche-120108': "Imposer la participation et l'intéressement",
    'niche-730213': "TVA au taux normal sur les travaux dans les logements",
    'niche-730221': "TVA au taux normal dans les restaurants",
    'niche-120146': "Imposer les heures supplémentaires",
    'niche-110201': "Supprimer la réduction d'impôt pour les dons",
    'niche-110203': "Supprimer le crédit d'impôt pour la garde des jeunes enfants",
    'niche-210309': "Supprimer la réduction d'impôt des dons d'entreprises",
    'niche-800229': "Taxer normalement le gazole agricole et forestier",
    'niche-120202': "Imposer les allocations familiales et l'AAH",
    'niche-800401': "Taxer les carburants outre-mer comme en métropole",
    'niche-940102': "Malus au poids pour les voitures électriques",
    'niche-710103': "TVA de métropole aux Antilles et à La Réunion",
    'niche-210326': "Supprimer le taux d'impôt réduit sur les brevets",
    'niche-800221': "Taxer normalement le gazole des camions",
    'niche-730223': "TVA au taux normal sur la rénovation énergétique",
    'retraites-fin-suspension': "Revenir à la réforme des retraites (64 ans)",
    'smic-2': "Augmenter le SMIC de 2 % de plus", 'smic-5': "Augmenter le SMIC de 5 % de plus",
    'ondam-moins-1': "Dépenses d'assurance maladie : 1 % de moins", 'ondam-plus-1': "Dépenses d'assurance maladie : 1 % de plus",
    'revalo-moins-1': "Prestations sociales : 1 point sous l'inflation", 'revalo-plus-1': "Prestations sociales : 1 point au-dessus de l'inflation",
    'allegements-moins-10': "Allègements de cotisations patronales : −10 %",
    'point-indice-plus-1': "Point d'indice des fonctionnaires : +1 %",
    'univ-master-doctorat': "Université : master à 965 €, doctorat à 781 €", 'univ-30': "Université : droits d'inscription +30 %",
    'carence-3-jours': "3 jours de carence pour les fonctionnaires de l'État",
    'isf': "Rétablir l'impôt sur la fortune (ISF)",
    'taxe-zucman': "Taxe Zucman : 2 % sur les patrimoines de plus de 100 M€",
    'franchises-x2': "Doubler les franchises médicales",
    'retraite-63': "Retraite à 63 ans", 'retraite-62': "Retraite à 62 ans", 'retraite-65': "Retraite à 65 ans",
    'fonctionnaires-1-sur-2': "Ne remplacer qu'un fonctionnaire de l'État sur deux",
}
# Qui a donné le chiffre, pour les mesures débattues.
PAR_QUI = {'univ-master-doctorat': "chiffrage de la Cour des comptes", 'univ-30': "chiffrage de la Cour des comptes", 'carence-3-jours': "chiffrage des inspections générales, cité par le Sénat",
           'isf': "chiffrage cité par le Sénat", 'taxe-zucman': "chiffrage d'un rapport de l'Assemblée", 'franchises-x2': "chiffrage de la Cour des comptes",
           'retraite-63': "chiffrage de la Cour des comptes", 'retraite-62': "chiffrage de la Cour des comptes", 'retraite-65': "chiffrage de la Cour des comptes",
           'fonctionnaires-1-sur-2': "chiffrage de la Cour des comptes (2015)"}


def statut_court(t):
    """Le sort de la mesure à l'Assemblée, en mots courants."""
    t = t or ''
    if not t: return ''
    if t.startswith('Supprimée'): return "Les députés l'ont supprimée (1re lecture)"
    if t.startswith('Adoptée'): return "Les députés l'ont adoptée (1re lecture)"
    if t.startswith('Modifiée'): return "Les députés l'ont modifiée (1re lecture)"
    if t.startswith('Article adopté'): return "Les députés l'ont adoptée, puis ont rejeté le budget de la Sécurité sociale (1re lecture)"
    if t.startswith('Article rejeté'): return "Les députés l'ont rejetée (1re lecture)"
    if t.startswith('Non examinée'): return "Pas examinée : les députés ont rejeté le budget de la Sécurité sociale avant (1re lecture)"
    if t.startswith('Rapport annexé') or t.startswith('Projet de loi rejeté'): return "Les députés ont rejeté le budget de la Sécurité sociale qui la contenait (1re lecture)"
    if t.startswith("L'Assemblée a adopté le relèvement"): return "Les députés ont adopté le relèvement du barème, pas ce gel (1re lecture)"
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
             'effet': effet_md(x['effet_meur'], inv), 'note': x.get('note') or '', 'statut': c.get('statut', x.get('statut') or ''),
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
                           'theme': 'travail', 'qui': ['smic', 'entreprises'], 'qui_titre': 'Qui reçoit et qui paie', 'qui_texte': 'Salariés au SMIC (plus de salaire) ; employeurs (coût du travail)',
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
        ass('ondam', "Assurance maladie (soins remboursés, hôpitaux)", 'depense', 278.7, 2027, ['assures', 'soignants'], 'depense', LV['sante-ondam'], "Objectif national de dépenses d'assurance maladie proposé pour 2027.", ['ondam-moins-1', 'ondam-plus-1'])
        ass('remunerations', 'Salaires des agents publics (État, collectivités, hôpitaux, sécurité sociale)', 'depense', LV['fp-masse-salariale-apu']['montant']['2025 (Md€, toutes administrations publiques)'], 2025, ['agents_publics'], 'depense', LV['fp-masse-salariale-apu'], "Rémunérations versées par l'ensemble des administrations publiques (Insee), enseignants et militaires compris.", ['point-indice-plus-1', 'enseignement', 'defense'])
        ass('enseignement', "Enseignement scolaire (écoles, collèges, lycées)", 'depense', LV['education-enseignement-scolaire']['montant']['crédits de paiement hors CAS Pensions (Md€)']['PLF 2027'], 2027, ['ecoles'], 'depense', LV['education-enseignement-scolaire'], "Crédits de la mission Enseignement scolaire du budget de l'État, hors pensions (comptées dans les retraites).", ['remunerations'])
        ass('defense', 'Défense', 'depense', LV['defense-credits']['montant']['crédits de paiement hors CAS Pensions (Md€)']['PLF 2027'], 2027, ['defense'], 'depense', LV['defense-credits'], "Crédits de la mission Défense du budget de l'État, hors pensions (comptées dans les retraites).", ['remunerations'])
        ass('chomage', "Allocations chômage", 'depense', LV['chomage-depense']['montant']['allocations brutes et aides (Md€)']['2027'], 2027, ['chomeurs'], 'depense', LV['chomage-depense'], "Allocations et aides versées par l'Unédic (prévision).")
        ass('apl', 'Aides au logement (APL)', 'depense', LV['prestations-apl']['montant']["dépense d'aides personnelles au logement (Md€)"]['2025'], 2025, ['familles'], 'depense', LV['prestations-apl'], '')
        ass('alloc-familiales', 'Allocations familiales', 'depense', LV['prestations-allocations-familiales']['montant']['allocations familiales (M€)']['2027 prévision'] / 1000, 2027, ['familles'], 'depense', LV['prestations-allocations-familiales'], '', ['prestations-familiales-gel'])
        ass('aah', "Allocation aux adultes handicapés (AAH)", 'depense', LV['prestations-aah']['montant']['2027, PLF 2027 (Md€)'], 2027, ['handicap'], 'depense', LV['prestations-aah'], '')
        ass('allegements', "Allègements de cotisations patronales (baisser = les employeurs paient plus)", 'depense', LV['entreprises-allegements-generaux']['montant']['coût des allègements généraux, champ régimes de base, Unédic, Agirc-Arrco et FNAL (M€)']['2027 prévision'] / 1000, 2027, ['entreprises'], 'cotis_emp', LV['entreprises-allegements-generaux'],
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
        ass('is', "Impôt sur les sociétés", 'recette', AE['is_net']['valeurs']['2027_plf'], an2, ['entreprises'], None, asx('is_net'), "Recette nette prévue pour l'État en " + str(an2) + " (projet de loi de finances). Le modèle Mésange ne publie pas l'effet de cet impôt sur l'activité.")
        ass('tva', "TVA (part de l'État)", 'recette', AE['tva_nette_etat']['valeurs']['2027_plf'], an2, ['consommateurs'], 'tva', asx('tva_nette_etat'), "Recette nette de l'État ; une autre part de la TVA va à la Sécurité sociale et aux collectivités.")
        ass('csg', "CSG (contribution sociale généralisée)", 'recette', AE['csg_produit']['valeurs']['2027_p'] / 1000, an2, ['salaries', 'retraites'], 'csg', asx('csg_produit'), "Produit prévu (Commission des comptes de la Sécurité sociale) ; un point de CSG rapporte environ 18,4 Md€.")
        ass('carburants', "Taxes sur les carburants (accise, ex-TICPE)", 'recette', AE['accise_energies_nette']['valeurs']['2027_plf_euros_carburants'] / 1e9, an2, ['automobilistes', 'consommateurs'], None, asx('accise_energies_nette'), "Part de l'État. Le modèle Mésange ne publie pas l'effet de cette taxe sur l'activité.")
        ass('ame', "Aide médicale de l'État (AME)", 'depense', AE['ame_credits_2027']['valeurs']['2027_plf_CP'] / 1e9, an2, ['etrangers'], 'depense', asx('ame_credits_2027'),
            "Crédits prévus. En 2025, la dépense réelle a été de 1,47 Md€ pour 1,21 Md€ de crédits ; " + '{:,}'.format(AE['ame_beneficiaires']['valeurs']['31_12_2025']).replace(',', ' ') + " bénéficiaires fin 2025.")
        ass('c2s', "Complémentaire santé solidaire (C2S, ex-CMU complémentaire)", 'depense', AE['c2s_depense']['valeurs']['2024_depense_nette'], 2024, ['assures'], 'depense', asx('c2s_depense'), "Dépense nette 2024, dernier chiffre publié ; 7,79 millions de bénéficiaires fin 2024.")
        ass('rsa', "RSA (versé par les départements)", 'depense', AE['rsa_departements']['valeurs']['2025'] / 1000, 2025, ['solidarite'], 'depense', asx('rsa_departements'), "Dépense des départements en 2025 ; le RSA versé par l'État dans les départements où il est recentralisé n'est pas compté.")
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
        def rampe(v35):
            # Le chiffrage porte sur 2035 : Concret le fait monter en ligne droite depuis 2027 (hypothèse écrite sur la carte).
            return {str(a): round(v35 * (a - a1 + 1) / (2035 - a1 + 1), 3) for a in range(a1, 2032)}
        age = ['retraite-62', 'retraite-63', 'retraite-65', 'retraites-fin-suspension']
        noteR = "Chiffrage de la Cour des comptes pour 2035 (système de retraite) ; Concret le fait monter en ligne droite de %d à 2035 (hypothèse). " % a1
        debat('retraite-63', "Ramener l'âge légal de départ à la retraite à 63 ans", "L'âge minimum de départ à la retraite, qui doit atteindre 64 ans avec la réforme de 2023 (suspendue depuis 2026 : 62 ans et 9 mois pour les personnes nées entre le 1er janvier 1963 et le 31 mars 1965), est fixé à 63 ans. Le chiffrage de la Cour des comptes compare à 64 ans.", 'retraites', ['salaries'], 'depense', 'depense',
              rampe(-ra['âge ramené de 64 à 63 ans : dépense supplémentaire en 2035 (Md€)']), 'retraite_age_cour_comptes_2025', noteR + "Dépense en plus en 2035 : 5,8 Md€.", [x for x in age if x != 'retraite-63'], 'Qui reçoit')
        debat('retraite-62', "Revenir à la retraite à 62 ans", "L'âge minimum de départ à la retraite, qui doit atteindre 64 ans avec la réforme de 2023 (suspendue depuis 2026 : 62 ans et 9 mois pour les personnes nées entre le 1er janvier 1963 et le 31 mars 1965), est fixé à 62 ans. Le chiffrage de la Cour des comptes compare à 64 ans.", 'retraites', ['salaries'], 'depense', 'depense',
              rampe(-ra['retour à 62 ans : « en gros, deux fois plus » (Md€, ordre de grandeur)']), 'retraite_age_cour_comptes_2025', noteR + "Pour 62 ans, la Cour dit « en gros, deux fois plus » que pour 63 ans : 11,6 Md€ en 2035 (ordre de grandeur).", [x for x in age if x != 'retraite-62'], 'Qui reçoit')
        debat('retraite-65', "Porter l'âge légal de départ à la retraite à 65 ans", "L'âge minimum de départ à la retraite, qui doit atteindre 64 ans avec la réforme de 2023 (suspendue depuis 2026 : 62 ans et 9 mois pour les personnes nées entre le 1er janvier 1963 et le 31 mars 1965), est fixé à 65 ans. Le chiffrage de la Cour des comptes compare à 64 ans.", 'retraites', ['salaries'], 'depense', 'depense',
              rampe(ra['âge porté à 65 ans : gain en 2035 (Md€)']), 'retraite_age_cour_comptes_2025', noteR + "Économie en 2035 : 8,4 Md€.", [x for x in age if x != 'retraite-65'])
        f = MD['fonctionnaires_non_remplacement_un_sur_deux']['valeurs']
        debat('fonctionnaires-1-sur-2', "Ne remplacer qu'un fonctionnaire de l'État sur deux partant à la retraite", "La moitié des agents de l'État qui partent à la retraite ne sont pas remplacés.", 'etat', ['agents_publics'], 'depense', 'depense',
              {str(a1): f["économie brute immédiate, budget de l'État (M€ par an)"] / 1000, str(a1 + 1): f['économie à moyen terme, au coût moyen sur la carrière (M€ par an)'] / 1000}, 'fonctionnaires_non_remplacement_un_sur_deux',
              "Chiffrage de la Cour des comptes (2015), le plus récent : montants de 2015, sans la hausse des salaires depuis.")
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
                          'exclut': [], 'note': "Mission du budget de l'État : crédits de paiement prévus, salaires et pensions des agents compris.", 'src': src(m)})
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
    # Paramètres officiels des cas types (« Concrètement »), lus à la source (budget_sources/parametres_cas.json).
    cas = {}
    if os.path.exists(os.path.join(SRC, 'parametres_cas.json')):
        for k, v in charger('parametres_cas.json').items():
            if not k.startswith('_') and v:
                cas[k] = {x: v.get(x) for x in ('v', 'unite', 'date_effet', 'source', 'url')}
    for c in cartes:
        c['sens'] = 'depense' if c['sens'] in ('dépense', 'depense') else c['sens']
        c['titre'] = COURT.get(c['id'], c['l'])
        if c['id'] in PAR_QUI: c['par'] = PAR_QUI[c['id']]
        c['statut_court'] = statut_court(c.get('statut'))
        ks = sorted(c['effet'])
        c['duree'] = 'une seule année' if c.get('ponctuelle') and len(ks) == 1 else 'par an'
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
        'cartes': cartes, 'assiettes': assiettes, 'population': population, 'cas': cas, 'ecartees': ecartees, 'themes': THEMES, 'qui': QUI,
        'groupes': json.load(open(os.path.join(RACINE, 'donnees', 'votes.json'), encoding='utf-8'))['GROUPES'],
        'variantes': var, 'regle': REGLE, 'defis': DEFIS,
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
