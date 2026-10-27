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
        'FI': 'la Finlande', 'SE': 'la Suède', 'EU27_2020': "la moyenne de l'UE"}

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
    geos = PAYS + ['EU27_2020']
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
        P[g] = {'nom': NOMS[g], 'annee': int(a), 'dep': dep, 'interets': somme(exp, g, a, INTERETS), 'rec': rec,
                'impots_revenus': somme(tax, g, a, ['D51']),
                'autres_recettes': round(tr - taxes, 2) if taxes is not None else None,
                'depenses': te, 'depenses_fonctions': somme(exp, g, a, ['TOTAL']), 'recettes': tr, 'solde': b9, 'dette': dette.get((g, a)),
                'pib_meur': pib.get((g, a)), 'pop_milliers': pop.get((g, a))}
    return {
        'maj': date.today().isoformat(), 'annee': int(an),
        'sources': {
            'depenses': {'source': 'Eurostat, dépenses des administrations publiques par fonction (COFOG), gov_10a_exp', 'url': 'https://ec.europa.eu/eurostat/databrowser/view/gov_10a_exp/default/table'},
            'recettes': {'source': 'Eurostat, principaux impôts et cotisations sociales, gov_10a_taxag', 'url': 'https://ec.europa.eu/eurostat/databrowser/view/gov_10a_taxag/default/table'},
            'totaux': {'source': 'Eurostat, principaux agrégats des administrations publiques, gov_10a_main', 'url': 'https://ec.europa.eu/eurostat/databrowser/view/gov_10a_main/default/table'},
            'dette': {'source': 'Eurostat, dette publique (critère de Maastricht), gov_10dd_edpt1', 'url': 'https://ec.europa.eu/eurostat/databrowser/view/gov_10dd_edpt1/default/table'},
            'pib': {'source': 'Eurostat, PIB à prix courants, nama_10_gdp ; population, nama_10_pe', 'url': 'https://ec.europa.eu/eurostat/databrowser/view/nama_10_gdp/default/table'},
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
    if '--ecrire' in sys.argv:
        json.dump(o, open(SORTIE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('Écrit :', SORTIE)


if __name__ == '__main__':
    main()
