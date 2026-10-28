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
}
# Effet sur l'activité : la variante du modèle Mésange qui correspond au type de mesure (aucune pour l'impôt sur les sociétés,
# les droits de succession et les accises : le modèle ne les publie pas).
MACRO = {'depense': 'mult_mesange2017_depense_publique', 'tva': 'mult_mesange2017_tva', 'csg': 'mult_mesange2017_csg',
         'ir': 'mult_mesange2017_ir', 'cotis_emp': 'mult_mesange2017_cotis_employeurs', 'cotis_sal': 'mult_mesange2017_cotis_salaries',
         'invest': 'mult_mesange2017_invest_public'}

# Mesures des projets de loi 2027 : titre de carte (neutre), thème, étiquettes, type d'effet sur l'activité ;
# exclues : les transferts entre administrations, qui ne changent pas le solde public total selon le document.
M2027 = {
    'ir-indexation-bareme': {'l': "Geler le barème de l'impôt sur le revenu en 2027 (ne pas le relever de l'inflation)", 'theme': 'impots', 'qui': ['menages_imposables'], 'macro': 'ir', 'inverse': True},
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
THEMES = {'retraites': 'Retraites', 'sante': 'Santé', 'travail': 'Travail et formation', 'solidarite': 'Familles et solidarité', 'impots': 'Impôts des ménages',
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
        out[n] = {'d': s['dateScrutin'], 's': s['sort']['code'], 't': s['titre'].rstrip('.'), 'g': g}
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
             'quoi': x['quoi'], 'theme': c['theme'], 'qui': c['qui'], 'qui_texte': x['qui'], 'macro': c['macro'], 'sens': x['type'],
             'effet': effet_md(x['effet_meur'], inv), 'note': x.get('note') or '', 'statut': x.get('statut') or '',
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
        ('allegements-moins-10', "Réduire de 10 % les allègements généraux de cotisations patronales", "Les employeurs paient plus de cotisations sur les salaires proches du SMIC : les réductions générales de cotisations baissent de 10 %.", 'entreprises', ['entreprises'], 'cotis_emp', 5.6, ag, [], "La source chiffre 1 % ; Concret multiplie par 10. Coût des allègements généraux prévu pour " + an1 + " : 72,8 Md€ (même rapport, p. 67). Effet sur l'emploi : compté par le modèle Mésange (cotisations des employeurs), si l'effet sur l'activité est coché."),
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
        'cartes': cartes, 'ecartees': ecartees, 'themes': THEMES, 'qui': QUI,
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
