#!/usr/bin/env python3
"""Page « Votre budget de la France » (brouillon) : les dépenses et les recettes publiques des 27 pays de l'UE, lues chez Eurostat.

Dépenses par fonction (COFOG, gov_10a_exp), recettes par type (gov_10a_taxag, gov_10a_main), dette (gov_10dd_edpt1),
PIB et population (nama_10_gdp, nama_10_pe) ; administrations publiques (État, Sécurité sociale, collectivités), en % du PIB,
dernière année publiée pour la France. Rien n'est estimé : un pays sans chiffre pour l'année est laissé de côté.

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
    return {
        'maj': date.today().isoformat(), 'annee': int(an), 'ocde_ecartees': sorted(set(ecartees)),
        'hors_ue': HORS_UE_EUROSTAT + list(OCDE),
        'sources': {
            'depenses': {'source': 'Eurostat, dépenses des administrations publiques par fonction (COFOG), gov_10a_exp', 'url': 'https://ec.europa.eu/eurostat/databrowser/view/gov_10a_exp/default/table'},
            'recettes': {'source': 'Eurostat, principaux impôts et cotisations sociales, gov_10a_taxag', 'url': 'https://ec.europa.eu/eurostat/databrowser/view/gov_10a_taxag/default/table'},
            'totaux': {'source': 'Eurostat, principaux agrégats des administrations publiques, gov_10a_main', 'url': 'https://ec.europa.eu/eurostat/databrowser/view/gov_10a_main/default/table'},
            'dette': {'source': 'Eurostat, dette publique (critère de Maastricht), gov_10dd_edpt1', 'url': 'https://ec.europa.eu/eurostat/databrowser/view/gov_10dd_edpt1/default/table'},
            'pib': {'source': 'Eurostat, PIB à prix courants, nama_10_gdp ; population, nama_10_pe', 'url': 'https://ec.europa.eu/eurostat/databrowser/view/nama_10_gdp/default/table'},
            'ocde': {'source': "OCDE, comptes des administrations publiques : dépenses par fonction (tableau 11), recettes (tableau 12), PIB (tableau 1)", 'url': 'https://data-explorer.oecd.org/'},
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
    if '--ecrire' in sys.argv:
        json.dump(o, open(SORTIE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('Écrit :', SORTIE)


if __name__ == '__main__':
    main()
