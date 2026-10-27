#!/usr/bin/env python3
"""Page « Votre budget de la France » (brouillon) : les dépenses et les recettes publiques des 27 pays de l'UE, lues chez Eurostat.

Dépenses par fonction (COFOG, gov_10a_exp), recettes par type (gov_10a_taxag, gov_10a_main), dette (gov_10dd_edpt1),
PIB et population (nama_10_gdp, nama_10_pe) ; administrations publiques (État, Sécurité sociale, collectivités), en % du PIB,
dernière année publiée pour la France. Rien n'est estimé : un pays sans chiffre pour l'année est laissé de côté.

Pour la France, en plus :
- des repères concrets, en euros (Eurostat) : dépense de retraite par retraité, d'enseignement par élève, de police par policier
  ou gendarme, de prison par détenu, de chômage par chômeur ; ce que les ménages et leurs complémentaires paient pour se soigner ;
- la dette dans cinq ans : prévision du FMI (Perspectives de l'économie mondiale et Moniteur des finances publiques), croissance,
  inflation, solde primaire, intérêts ; la page y ajoute l'effet des choix de la personne, et deux scénarios de croissance ;
- les défis du jour, chacun avec la source de son chiffre.

  python3 outils/budget.py            compare avec donnees/budget.json
  python3 outils/budget.py --ecrire   écrit donnees/budget.json
"""
import json, os, sys, urllib.request
from datetime import date

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SORTIE = os.path.join(RACINE, 'donnees', 'budget.json')
API = 'https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/'
PAYS = ['BE', 'BG', 'CZ', 'DK', 'DE', 'EE', 'IE', 'EL', 'ES', 'FR', 'HR', 'IT', 'CY', 'LV', 'LT', 'LU', 'HU', 'MT', 'NL', 'AT',
        'PL', 'PT', 'RO', 'SI', 'SK', 'FI', 'SE']
NOMS = {'BE': 'la Belgique', 'BG': 'la Bulgarie', 'CZ': 'la Tchéquie', 'DK': 'le Danemark', 'DE': "l'Allemagne", 'EE': "l'Estonie",
        'IE': "l'Irlande", 'EL': 'la Grèce', 'ES': "l'Espagne", 'FR': 'la France', 'HR': 'la Croatie', 'IT': "l'Italie", 'CY': 'Chypre',
        'LV': 'la Lettonie', 'LT': 'la Lituanie', 'LU': 'le Luxembourg', 'HU': 'la Hongrie', 'MT': 'Malte', 'NL': 'les Pays-Bas',
        'AT': "l'Autriche", 'PL': 'la Pologne', 'PT': 'le Portugal', 'RO': 'la Roumanie', 'SI': 'la Slovénie', 'SK': 'la Slovaquie',
        'FI': 'la Finlande', 'SE': 'la Suède', 'EU27_2020': "la moyenne de l'UE",
        'NO': 'la Norvège', 'IS': "l'Islande", 'CH': 'la Suisse', 'UK': 'le Royaume-Uni', 'JP': 'le Japon', 'US': 'les États-Unis'}
# Hors UE : chez Eurostat (mêmes tableaux) ; chez l'OCDE (mêmes nomenclatures, en monnaie nationale, rapportées au PIB).
HORS_UE_EUROSTAT = ['NO', 'IS', 'CH']
OCDE = {'UK': 'GBR', 'JP': 'JPN', 'US': 'USA'}
OCDE_API = 'https://sdmx.oecd.org/public/rest/data/'
FMI_API = 'https://www.imf.org/external/datamapper/api/v1/'
# Prévision du FMI : croissance réelle, inflation, solde, dette (Perspectives de l'économie mondiale), solde primaire (Moniteur des finances publiques).
FMI = {'croissance': 'NGDP_RPCH', 'inflation': 'PCPIPCH', 'solde': 'GGXCNL_NGDP', 'dette': 'GGXWDG_NGDP', 'primaire': 'GGXONLB_G01_GDP_PT'}
HORIZON = 5        # la dette dans cinq ans (cinq ans après l'année en cours)
ECART_CROISSANCE = 1.0   # scénarios : croissance plus forte ou plus faible d'un point chaque année (hypothèse de Concret, écrite sur la page)

# Défis du jour : un par jour, le même pour tous, tiré dans l'ordre de la liste. Chaque chiffre a sa source.
# Conditions : solde_min (déficit au plus), solde_reel (pas plus de déficit qu'aujourd'hui), dep_min (un poste au moins à),
# pas_baisse / pas_hausse / fixe (un poste, ou 'rec:*' pour tous les impôts), dette_baisse (dette dans cinq ans sous celle
# d'aujourd'hui, scénario central), rembourser (tous les soins remboursés), proche (le pays le plus proche).
GLOSSAIRE_EDP = {'source': "Eurostat, glossaire « Procédure concernant les déficits excessifs » : selon le protocole annexé au traité de Maastricht, le déficit ne doit pas dépasser 3 % du PIB", 'url': 'https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Glossary:Excessive_deficit_procedure_(EDP)'}
OTAN_2035 = {'source': "OTAN, déclaration du sommet de La Haye (25 juin 2025) : au moins 3,5 % du PIB d'ici 2035 pour la défense, selon la définition de l'OTAN", 'url': 'https://www.nato.int/cps/en/natohq/official_texts_236705.htm'}
DEFIS = [
    {'id': 'deficit3', 't': 'Ramenez le déficit à 3 % du PIB ou moins.', 'c': [{'type': 'solde_min', 'v': -3}], 'src': GLOSSAIRE_EDP},
    {'id': 'defense', 't': "Portez la défense à 3,5 % du PIB, l'objectif de l'OTAN pour 2035, sans plus de déficit qu'aujourd'hui.", 'c': [{'type': 'dep_min', 'k': 'defense', 'v': 3.5}, {'type': 'solde_reel'}], 'src': OTAN_2035},
    {'id': 'retraites3', 't': 'Ramenez le déficit à 3 % du PIB sans baisser les retraites.', 'c': [{'type': 'solde_min', 'v': -3}, {'type': 'pas_baisse', 'k': 'retraites'}], 'src': GLOSSAIRE_EDP},
    {'id': 'dette', 't': "Faites baisser la dette d'ici cinq ans.", 'c': [{'type': 'dette_baisse'}]},
    {'id': 'impots3', 't': "Ramenez le déficit à 3 % du PIB sans augmenter aucun impôt ni cotisation.", 'c': [{'type': 'solde_min', 'v': -3}, {'type': 'pas_hausse', 'k': 'rec:*'}], 'src': GLOSSAIRE_EDP},
    {'id': 'allemagne', 't': "Faites un budget qui ressemble le plus à celui de l'Allemagne.", 'c': [{'type': 'proche', 'g': 'DE'}]},
    {'id': 'soins', 't': "Remboursez tous les soins, sans plus de déficit qu'aujourd'hui.", 'c': [{'type': 'rembourser'}, {'type': 'solde_reel'}]},
    {'id': 'equilibre', 't': "Votez un budget à l'équilibre : autant de recettes que de dépenses.", 'c': [{'type': 'solde_min', 'v': 0}]},
    {'id': 'ecole_sante', 't': "Ramenez le déficit à 3 % du PIB sans toucher à l'école ni à la santé.", 'c': [{'type': 'solde_min', 'v': -3}, {'type': 'fixe', 'k': 'ecole'}, {'type': 'fixe', 'k': 'sante'}], 'src': GLOSSAIRE_EDP},
    {'id': 'suede', 't': 'Faites un budget qui ressemble le plus à celui de la Suède.', 'c': [{'type': 'proche', 'g': 'SE'}]},
    {'id': 'dette_impots', 't': "Faites baisser la dette d'ici cinq ans sans augmenter aucun impôt ni cotisation.", 'c': [{'type': 'dette_baisse'}, {'type': 'pas_hausse', 'k': 'rec:*'}]},
    {'id': 'suisse', 't': 'Faites un budget qui ressemble le plus à celui de la Suisse.', 'c': [{'type': 'proche', 'g': 'CH'}]},
]

# Dépenses : les postes de la page, chacun une somme de fonctions COFOG. Les intérêts de la dette ne se choisissent pas :
# ils suivent la dette (affichés à part).
DEP = [
    ('retraites', 'Retraites', ['GF1002', 'GF1003']),
    ('sante', 'Santé', ['GF07']),
    ('ecole', 'École et enseignement', ['GF09']),
    ('maladie', 'Arrêts maladie et handicap', ['GF1001']),
    ('famille', 'Famille et enfants', ['GF1004']),
    ('chomage', 'Chômage', ['GF1005']),
    ('logement', 'Aides au logement et pauvreté', ['GF1006', 'GF1007', 'GF1008', 'GF1009']),
    ('defense', 'Défense', ['GF02']),
    ('securite', 'Police et justice', ['GF03']),
    ('economie', 'Transports, énergie, aides aux entreprises', ['GF04']),
    ('cadre', 'Environnement, équipements, culture', ['GF05', 'GF06', 'GF08']),
    ('admin', 'Administration', ['GF01', '-GF0107']),
]
INTERETS = ['GF0107']
# Recettes : impôts et cotisations par type ; le reste des recettes (ventes, revenus de la propriété…) à part.
REC = [
    ('tva', 'TVA', ['D211']),
    ('conso', 'Autres taxes sur la consommation (carburants, tabac…)', ['D21', '-D211']),
    ('production', 'Impôts sur la production (foncier, salaires…)', ['D29']),
    ('revenu', 'Impôt sur le revenu et CSG', ['D51A']),
    ('societes', 'Impôt sur les sociétés', ['D51B']),
    ('cotisations', 'Cotisations sociales', ['D61']),
    ('patrimoine', 'Patrimoine et successions', ['D59', 'D91']),
]


def lire(ds, **f):
    q = '&'.join(f'{k}={v}' for k, vs in f.items() for v in (vs if isinstance(vs, list) else [vs]))
    d = json.load(urllib.request.urlopen(API + ds + '?' + q, timeout=120))
    dims, tailles = d['id'], d['size']
    lab = {k: {i: v for v, i in d['dimension'][k]['category']['index'].items()} for k in dims}
    out = {}
    for flat, val in d['value'].items():
        n, c = int(flat), []
        for t in reversed(tailles):
            c.append(n % t); n //= t
        cle = dict(zip(dims, [lab[k][x] for k, x in zip(dims, reversed(c))]))
        out[(cle['geo'], cle['time']) + tuple(cle[k] for k in dims if k not in ('geo', 'time', 'freq') and tailles[dims.index(k)] > 1)] = val
    return out


def ocde(flux, cle, depuis):
    """Lignes CSV d'un tableau de l'OCDE (SDMX), valeurs multipliées par 10^UNIT_MULT."""
    import csv, io
    req = urllib.request.Request(OCDE_API + flux + '/' + cle + '?startPeriod=' + depuis, headers={'Accept': 'application/vnd.sdmx.data+csv', 'User-Agent': 'Mozilla/5.0 (Concret, concret2027.fr)'})
    rows = list(csv.DictReader(io.StringIO(urllib.request.urlopen(req, timeout=300).read().decode('utf-8'))))
    for r in rows:
        r['v'] = float(r['OBS_VALUE']) * 10 ** int(r.get('UNIT_MULT') or 0) if r.get('OBS_VALUE') not in (None, '') else None
    return rows


def lire_ocde(ans):
    """Mêmes postes que pour l'UE, lus à l'OCDE (dépenses par fonction : tableau 11 ; recettes : tableau 12 ; PIB : tableau 1),
    en % du PIB. La France est relue de la même façon pour vérifier que les deux sources concordent."""
    zones = '+'.join(list(OCDE.values()) + ['FRA'])
    t11 = ocde('OECD.SDD.NAD,DSD_NASEC10@DF_TABLE11,', 'A.' + zones + '.S13' + '.' * 10, ans[-1])
    t12 = ocde('OECD.SDD.NAD,DSD_NASEC10@DF_TABLE12_REV,', 'A.' + zones + '.S13' + '.' * 10, ans[-1])
    t1 = ocde('OECD.SDD.NAD,DSD_NAMAIN10@DF_TABLE1_EXPENDITURE,', 'A.' + zones + '.' * 12, ans[-1])
    pib = {(r['REF_AREA'], r['TIME_PERIOD']): r['v'] for r in t1 if r['TRANSACTION'] == 'B1GQ' and r['UNIT_MEASURE'] == 'XDC' and r['PRICE_BASE'] == 'V' and r['TRANSFORMATION'] == 'N' and r['SECTOR'] == 'S1'}
    dep = {(r['REF_AREA'], r['TIME_PERIOD'], r['EXPENDITURE']): r['v'] for r in t11 if r['TRANSACTION'] == 'OTE' and r['UNIT_MEASURE'] == 'XDC'}
    rec = {(r['REF_AREA'], r['TIME_PERIOD'], r['TRANSACTION']): r['v'] for r in t12 if r['UNIT_MEASURE'] == 'XDC'}
    pct = {}
    for (z, a, c), v in list(dep.items()) + list(rec.items()):
        if v is not None and pib.get((z, a)):
            pct[(z, a, c)] = round(100 * v / pib[(z, a)], 2)
    return pct, pib


def somme(table, geo, an, codes):
    t = 0.0
    for c in codes:
        signe, c = (-1, c[1:]) if c.startswith('-') else (1, c)
        v = table.get((geo, an, c))
        if v is None:
            return None
        t += signe * v
    return round(t, 2)


def fmi():
    """Prévision du FMI pour la France, de la dernière année connue à cinq ans plus tard."""
    V = {}
    for k, code in FMI.items():
        # Le FMI refuse certains navigateurs déclarés : la requête part avec l'en-tête par défaut de Python.
        d = json.load(urllib.request.urlopen(FMI_API + code + '/FRA', timeout=120))
        V[k] = d['values'][code]['FRA']
    # L'édition de chaque série, telle que le FMI la nomme (par exemple « World Economic Outlook (October 2026) »).
    ind = json.load(urllib.request.urlopen(FMI_API + 'indicators', timeout=120))['indicators']
    V['editions'] = sorted({ind[c].get('source', '') for c in FMI.values() if c in ind})
    return V


def repere(table, an_max, codes, ans):
    """Dernière année (au plus an_max) où toutes les valeurs existent."""
    for a in ans:
        if int(a) <= an_max and all(table.get(c + (a,)) is not None for c in codes):
            return a
    return None


def concret(an):
    """Repères en euros pour la France : chaque dépense rapportée au nombre de personnes concernées, la même année."""
    ans = [str(an - k) for k in range(0, 5)]
    eur = lire('gov_10a_exp', geo='FR', sector='S13', na_item='TE', unit='MIO_EUR', cofog99=['GF1002', 'GF1003', 'GF09', 'GF0301', 'GF0304', 'GF1005'], time=ans)
    def dep(c, a): return eur.get(('FR', a, c))
    ret = lire('spr_pns_ben', geo='FR', spdepm='TOTAL', sex='T', spscheme='TOTAL', unit='PER', spdepb='OLD_SRV', time=ans)
    ele = lire('educ_uoe_enra01', geo='FR', isced11='ED0-8', sector='TOT_SEC', sex='T', worktime='TOTAL', time=ans)
    pol = lire('crim_just_job', geo='FR', isco08='OC5412', unit='NR', sex='T', time=ans)
    pri = lire('crim_pris_cap', geo='FR', unit='NR', indic_cr=['PRIS_ACT_CAP', 'PRIS_OFF_CAP'], time=ans)
    cho = lire('une_rt_a', geo='FR', age='Y15-74', unit='THS_PER', sex='T', time=ans)
    soi = lire('hlth_sha11_hf', geo='FR', icha11_hf=['HF2', 'HF3'], unit='MIO_EUR', time=ans)
    out = {}
    def ajoute(cle, poste, l, unite, montant, nombre, a, src, par=1, plus=None):
        out[cle] = {'poste': poste, 'l': l, 'unite': unite, 'annee': int(a), 'depense_meur': round(montant, 1), 'nombre': nombre,
                    'v': round(montant * 1e6 / nombre / par), 'source': src}
        if plus: out[cle].update(plus)
    for a in ans:
        if dep('GF1002', a) and dep('GF1003', a) and ret.get(('FR', a)):
            ajoute('retraite', 'retraites', 'Dépense publique de vieillesse et de réversion, par retraité', '€ par mois', dep('GF1002', a) + dep('GF1003', a), ret[('FR', a)], a,
                   "Eurostat : dépenses de vieillesse et de survie (COFOG, gov_10a_exp) ; retraités, pensions de vieillesse et de réversion (spr_pns_ben)", 12); break
    for a in ans:
        if dep('GF09', a) and ele.get(('FR', a)):
            ajoute('eleve', 'ecole', "Dépense publique d'enseignement par élève ou étudiant", '€ par an', dep('GF09', a), ele[('FR', a)], a,
                   "Eurostat : dépense d'enseignement (COFOG, gov_10a_exp) ; élèves et étudiants, de la maternelle au doctorat, public et privé (educ_uoe_enra01)"); break
    for a in ans:
        if dep('GF0301', a) and pol.get(('FR', a)):
            ajoute('policier', 'securite', 'Dépense de police (salaires, matériel, bâtiments) par policier ou gendarme', '€ par an', dep('GF0301', a), pol[('FR', a)], a,
                   "Eurostat : services de police (COFOG, gov_10a_exp) ; policiers et gendarmes (crim_just_job)"); break
    for a in ans:
        if dep('GF0304', a) and pri.get(('FR', a, 'PRIS_ACT_CAP')) and pri.get(('FR', a, 'PRIS_OFF_CAP')):
            ajoute('detenu', 'securite', 'Dépense de prison par détenu', '€ par an', dep('GF0304', a), pri[('FR', a, 'PRIS_ACT_CAP')], a,
                   "Eurostat : prisons (COFOG, gov_10a_exp) ; personnes détenues et places de prison (crim_pris_cap)", 1, {'places': pri[('FR', a, 'PRIS_OFF_CAP')]}); break
    for a in ans:
        if dep('GF1005', a) and cho.get(('FR', a)):
            ajoute('chomeur', 'chomage', 'Dépense publique de chômage par chômeur', '€ par an', dep('GF1005', a), cho[('FR', a)] * 1000, a,
                   "Eurostat : dépenses de chômage (COFOG, gov_10a_exp) ; chômeurs de 15 à 74 ans, au sens du BIT (une_rt_a)"); break
    # Rembourser tous les soins : ce que paient les complémentaires (mutuelles, assurances) et les ménages eux-mêmes, l'année du budget.
    a = str(an)
    if soi.get(('FR', a, 'HF2')) and soi.get(('FR', a, 'HF3')):
        out['soins'] = {'poste': 'sante', 'annee': an, 'complementaires_meur': soi[('FR', a, 'HF2')], 'menages_meur': soi[('FR', a, 'HF3')],
                        'source': "Eurostat, dépense de santé par financeur (hlth_sha11_hf) : régimes facultatifs (mutuelles, assurances) et paiements directs des ménages"}
    return out


def projection(V, d0, an0):
    """Chaque année : croissance du PIB en valeur, taux d'intérêt moyen de la dette et solde primaire du FMI, et le reste
    (achats et ventes d'actifs, écarts de calcul) tel que le FMI le prévoit implicitement. Dette de départ : Eurostat."""
    fin = min(date.today().year + HORIZON, max(int(a) for a in V['dette']))
    ans = [str(a) for a in range(an0 + 1, fin + 1)]
    L = []
    dprec = V['dette'][str(an0)]
    for a in ans:
        p = str(int(a) - 1)
        g = (1 + V['croissance'][a] / 100) * (1 + V['inflation'][a] / 100) - 1
        interets = V['primaire'][a] - V['solde'][a]
        i = interets / V['dette'][p] * (1 + g)
        calc = dprec * (1 + i) / (1 + g) - V['primaire'][a]
        L.append({'an': int(a), 'croissance': V['croissance'][a], 'inflation': V['inflation'][a], 'g': round(g, 5), 'i': round(i, 5),
                  'primaire': round(V['primaire'][a], 2), 'interets': round(interets, 2), 'reste': round(V['dette'][a] - calc, 3), 'dette_fmi': V['dette'][a]})
        dprec = V['dette'][a]
    return {'depart': {'an': an0, 'dette': d0, 'dette_fmi': V['dette'][str(an0)]}, 'ans': L, 'ecart_croissance': ECART_CROISSANCE,
            'premier_budget': date.today().year + 1, 'editions': V['editions']}


def construire():
    geos = PAYS + ['EU27_2020'] + HORS_UE_EUROSTAT
    ans = [str(date.today().year - k) for k in range(1, 4)]
    exp = lire('gov_10a_exp', geo=geos, sector='S13', na_item='TE', unit='PC_GDP', time=ans)
    tax = lire('gov_10a_taxag', geo=geos, sector='S13_S212', unit='PC_GDP', time=ans)
    main = lire('gov_10a_main', geo=geos, sector='S13', unit='PC_GDP', na_item=['TE', 'TR', 'B9'], time=ans)
    dette = lire('gov_10dd_edpt1', geo=geos, sector='S13', unit='PC_GDP', na_item='GD', time=ans)
    pib = lire('nama_10_gdp', geo=geos, unit='CP_MEUR', na_item='B1GQ', time=ans)
    pop = lire('nama_10_pe', geo=geos, unit='THS_PER', na_item='POP_NC', time=ans)
    # Année : la dernière où la France a toutes ses dépenses par fonction et ses recettes.
    an = next(a for a in ans if exp.get(('FR', a, 'TOTAL')) is not None and tax.get(('FR', a, 'D211')) is not None)
    P = {}
    for g in geos:
        # Chaque pays à sa dernière année complète (certains publient leurs dépenses par fonction un an plus tard).
        for a in ans:
            if int(a) > int(an):
                continue
            dep = {k: somme(exp, g, a, c) for k, _, c in DEP}
            rec = {k: somme(tax, g, a, c) for k, _, c in REC}
            te, tr, b9 = (main.get((g, a, x)) for x in ('TE', 'TR', 'B9'))
            # Une ligne non publiée par un pays (par exemple l'impôt sur le revenu séparé de celui des sociétés) reste vide :
            # le pays est gardé si ses totaux et la plupart de ses lignes existent.
            vides = [v for v in list(dep.values()) + list(rec.values()) if v is None]
            if None not in (te, tr, b9) and len(vides) <= 3:
                break
        else:
            continue
        taxes = somme(tax, g, a, ['D2', 'D5', 'D91', 'D61'])
        P[g] = {'nom': NOMS[g], 'annee': int(a), 'source': 'Eurostat', 'dep': dep, 'interets': somme(exp, g, a, INTERETS), 'rec': rec,
                'social': somme(exp, g, a, ['GF10']),
                'impots_revenus': somme(tax, g, a, ['D51']),
                'autres_recettes': round(tr - taxes, 2) if taxes is not None else None,
                'depenses': te, 'depenses_fonctions': somme(exp, g, a, ['TOTAL']), 'recettes': tr, 'solde': b9, 'dette': dette.get((g, a)),
                'pib_meur': pib.get((g, a)), 'pop_milliers': pop.get((g, a))}
    # Hors UE, chez l'OCDE : une ligne n'est gardée que si la France, relue à l'OCDE, redonne le chiffre d'Eurostat (à 0,2 point).
    pct, pibo = lire_ocde(ans)
    ecartees = []
    REC_OCDE = {'tva': ['D211'], 'conso': ['D21', '-D211'], 'production': ['D29'], 'cotisations': ['D61'], 'patrimoine': ['D59', 'D91']}
    def ok_fr(code_eu, v_fr):
        return v_fr is not None and code_eu is not None and abs(v_fr - code_eu) <= 0.2
    an_fr = str(an)
    for g, z in OCDE.items():
        for a in ans:
            if pct.get((z, a, '_T')) is None or pct.get((z, a, 'OTR')) is None:
                continue
            dep = {}
            for k, _, c in DEP:
                v, vf = somme(pct, z, a, c), somme(pct, 'FRA', an_fr, c)
                if not ok_fr(P['FR']['dep'][k], vf):
                    if g == 'UK': ecartees.append('dépense ' + k)
                    v = None
                dep[k] = v
            rec = {}
            for k, _, c in REC:
                cc = REC_OCDE.get(k)
                v = somme(pct, z, a, cc) if cc else None
                vf = somme(pct, 'FRA', an_fr, cc) if cc else None
                if cc and not ok_fr(P['FR']['rec'][k], vf):
                    if g == 'UK': ecartees.append('recette ' + k)
                    v = None
                rec[k] = v
            ir = somme(pct, z, a, ['D51'])
            P[g] = {'nom': NOMS[g], 'annee': int(a), 'source': 'OCDE', 'dep': dep, 'interets': somme(pct, z, a, INTERETS), 'rec': rec,
                    'social': somme(pct, z, a, ['GF10']) if ok_fr(somme(exp, 'FR', an_fr, ['GF10']), somme(pct, 'FRA', an_fr, ['GF10'])) else None,
                    'impots_revenus': ir if ok_fr(P['FR']['impots_revenus'], somme(pct, 'FRA', an_fr, ['D51'])) else None,
                    'autres_recettes': None, 'depenses': pct.get((z, a, '_T')), 'recettes': pct.get((z, a, 'OTR')),
                    'solde': round(pct[(z, a, 'OTR')] - pct[(z, a, '_T')], 2), 'dette': None, 'pib_meur': None, 'pop_milliers': None}
            break
    # La dette dans cinq ans : départ à la dernière dette publiée par Eurostat, prévision du FMI ensuite.
    dfin = lire('gov_10dd_edpt1', geo='FR', sector='S13', unit='PC_GDP', na_item='GD', time=[str(date.today().year - k) for k in range(1, 3)])
    an0 = max(int(a) for (g, a) in dfin)
    V = fmi()
    proj = projection(V, dfin[('FR', str(an0))], an0)
    return {
        'maj': date.today().isoformat(), 'annee': int(an), 'ocde_ecartees': sorted(set(ecartees)),
        'concret': concret(int(an)), 'projection': proj, 'defis': DEFIS,
        'hors_ue': HORS_UE_EUROSTAT + list(OCDE),
        'sources': {
            'depenses': {'source': 'Eurostat, dépenses des administrations publiques par fonction (COFOG), gov_10a_exp', 'url': 'https://ec.europa.eu/eurostat/databrowser/view/gov_10a_exp/default/table'},
            'recettes': {'source': 'Eurostat, principaux impôts et cotisations sociales, gov_10a_taxag', 'url': 'https://ec.europa.eu/eurostat/databrowser/view/gov_10a_taxag/default/table'},
            'totaux': {'source': 'Eurostat, principaux agrégats des administrations publiques, gov_10a_main', 'url': 'https://ec.europa.eu/eurostat/databrowser/view/gov_10a_main/default/table'},
            'dette': {'source': 'Eurostat, dette publique (critère de Maastricht), gov_10dd_edpt1', 'url': 'https://ec.europa.eu/eurostat/databrowser/view/gov_10dd_edpt1/default/table'},
            'pib': {'source': 'Eurostat, PIB à prix courants, nama_10_gdp ; population, nama_10_pe', 'url': 'https://ec.europa.eu/eurostat/databrowser/view/nama_10_gdp/default/table'},
            'ocde': {'source': "OCDE, comptes des administrations publiques : dépenses par fonction (tableau 11), recettes (tableau 12), PIB (tableau 1)", 'url': 'https://data-explorer.oecd.org/'},
            'concret': {'source': 'Eurostat (tableaux nommés à chaque ligne)', 'url': 'https://ec.europa.eu/eurostat/data/database'},
            'fmi': {'source': "FMI, Perspectives de l'économie mondiale (croissance, inflation, solde, dette) et Moniteur des finances publiques (solde primaire), dernière édition", 'url': 'https://www.imf.org/external/datamapper/datasets/WEO'},
        },
        'DEP': [{'k': k, 'l': l, 'cofog': c} for k, l, c in DEP],
        'REC': [{'k': k, 'l': l, 'codes': c} for k, l, c in REC],
        'pays': P,
    }


def main():
    o = construire()
    fr = o['pays']['FR']
    print('Année de la France', o['annee'], ';', len(o['pays']) - 1, 'pays sur 27 ;', 'années :', sorted({p['annee'] for p in o['pays'].values()}), '; avant', o['annee'], ':', [g for g, p in o['pays'].items() if p['annee'] < o['annee']])
    print('France : dépenses', fr['depenses'], '% du PIB, recettes', fr['recettes'], ', solde', fr['solde'], ', dette', fr['dette'])
    print('  postes de dépense :', ', '.join(f'{k} {v}' for k, v in fr['dep'].items()), '; intérêts', fr['interets'])
    print('  recettes :', ', '.join(f'{k} {v}' for k, v in fr['rec'].items()), '; autres', fr['autres_recettes'])
    print('  somme des postes + intérêts :', round(sum(fr['dep'].values()) + fr['interets'], 2), '; total par fonction', fr['depenses_fonctions'], '; total des comptes', fr['depenses'], '; PIB', fr['pib_meur'], 'M€ ; population', fr['pop_milliers'], 'milliers')
    print('Hors UE :', ', '.join(f"{o['pays'][g]['nom']} {o['pays'][g]['annee']} (lignes vides : {sum(1 for v in list(o['pays'][g]['dep'].values()) + list(o['pays'][g]['rec'].values()) if v is None)})" for g in o['hors_ue'] if g in o['pays']))
    print('Lignes OCDE écartées (la France relue à l\'OCDE ne redonne pas le chiffre d\'Eurostat) :', o['ocde_ecartees'] or 'aucune')
    print('Repères :', ', '.join(f"{k} {v.get('v', round((v.get('complementaires_meur') or 0) + (v.get('menages_meur') or 0)))} {v.get('unite', 'M€')} ({v['annee']})" for k, v in o['concret'].items()))
    pj = o['projection']
    print('Dette fin', pj['depart']['an'], ':', pj['depart']['dette'], '(Eurostat) ;', pj['depart']['dette_fmi'], '(FMI) ; FMI', pj['ans'][-1]['an'], ':', pj['ans'][-1]['dette_fmi'])
    if abs(pj['depart']['dette'] - pj['depart']['dette_fmi']) > 1:
        print('⚠ La dette de départ du FMI et celle d\'Eurostat diffèrent de plus d\'un point.')
    if '--ecrire' in sys.argv:
        json.dump(o, open(SORTIE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('Écrit :', SORTIE)


if __name__ == '__main__':
    main()
