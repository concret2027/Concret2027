#!/usr/bin/env python3
"""Séries de la page Population et immigration, lues à Eurostat (jamais saisies à la main). Pas de note sur cette page.

  - Démographie (France, Allemagne, Espagne, moyenne de l'UE publiée par Eurostat) : enfants par femme (demo_find),
    naissances, solde naturel et solde migratoire pour 1 000 habitants (demo_gind), part des 65 ans et plus et âge
    médian (demo_pjanind) ; pour la France, les nombres : naissances, décès, solde naturel, solde migratoire, population.
  - Pyramide des âges au 1er janvier de la dernière année publiée (demo_pjangroup), France et UE, en % de la population.
  - Migrations : premiers titres de séjour par motif (migr_resfirst : famille, études, travail, autres), premières
    demandes d'asile (migr_asyappctza), étrangers hors UE trouvés en situation irrégulière (migr_eipre), obligations de
    quitter le territoire (migr_eiord) et départs qui ont suivi (migr_eirtn) ; pour comparer les pays, rapportés par
    Concret à la population moyenne de l'année (demo_gind, AVG), pour 1 000 habitants.
  Changements de méthode : seulement ceux signalés par Eurostat (code « b ») ; chiffres provisoires (« p ») et estimés
  (« e ») : signalés sous la courbe.

  python3 outils/population.py            compare aux séries de data.json, sans rien écrire
  python3 outils/population.py --ecrire   écrit series.population dans data.json et met à jour le calendrier

Code de sortie 1 si une source est injoignable (rien n'est écrit)."""
import json, os, sys
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ue_calc as U

ROOT = U.ROOT
GEO = {'FR': 'fr', 'DE': 'de', 'ES': 'es', 'EU27_2020': 'ue'}
DEBUT = 2000
PAGE = 'https://ec.europa.eu/eurostat/databrowser/view/%s/default/table?lang=fr'


def eurostat(table, filtres, geos=GEO):
    """{pays: {année: valeur}}, {pays: {année: drapeaux}} ; une seule valeur par pays et par année une fois filtrée."""
    d = json.loads(U.get(U.EST + table + '?format=JSON&sinceTimePeriod=%d&' % DEBUT + filtres + ''.join('&geo=' + g for g in geos)))
    dims, tailles = d['id'], d['size']
    inv = {k: {i: c for c, i in d['dimension'][k]['category']['index'].items()} for k in dims}
    libre = [k for k, s in zip(dims, tailles) if s > 1 and k not in ('geo', 'time')]
    if libre:
        raise ValueError('%s : plusieurs valeurs pour %s, filtre incomplet' % (table, ', '.join(libre)))
    out, drap = {}, {}
    for idx in set(d['value']) | set(d.get('status', {})):
        i, cle = int(idx), {}
        for k, s in zip(reversed(dims), reversed(tailles)):
            cle[k] = inv[k][i % s]; i //= s
        v, f = d['value'].get(idx), d.get('status', {}).get(idx, '')
        if v is not None:
            out.setdefault(cle['geo'], {})[int(cle['time'])] = v
        if f:
            drap.setdefault(cle['geo'], {})[int(cle['time'])] = f
    return out, drap


# Courbes comparées : (table, filtres, intitulé, unité, décimales, source affichée)
COMP = {
    'fec': ('demo_find', 'indic_de=TOTFERRT', 'Enfants par femme', 'enfants par femme', 2, 'Eurostat (demo_find, indicateur conjoncturel de fécondité)'),
    'nat': ('demo_gind', 'indic_de=GBIRTHRT', 'Naissances', 'pour 1 000 habitants', 1, 'Eurostat (demo_gind, taux brut de natalité)'),
    'solnat': ('demo_gind', 'indic_de=NATGROWRT', 'Solde naturel (naissances moins décès)', 'pour 1 000 habitants', 1, 'Eurostat (demo_gind, taux brut d\'accroissement naturel)'),
    'solmig': ('demo_gind', 'indic_de=CNMIGRATRT', 'Solde migratoire (arrivées moins départs)', 'pour 1 000 habitants', 1, 'Eurostat (demo_gind, taux brut de solde migratoire, ajustement statistique compris)'),
    'p65': ('demo_pjanind', 'indic_de=PC_Y65_MAX', 'Part des 65 ans et plus', '% de la population', 1, 'Eurostat (demo_pjanind)'),
    'med': ('demo_pjanind', 'indic_de=MEDAGEPOP', 'Âge médian', 'ans', 1, 'Eurostat (demo_pjanind)'),
}
# Migrations : nombres (France) et taux pour 1 000 habitants calculés par Concret (quatre pays).
MIGR = {
    'titres': ('migr_resfirst', 'reason=TOTAL&duration=TOTAL&citizen=TOTAL&unit=PER', 'Premiers titres de séjour', 'Eurostat (migr_resfirst, premiers titres de séjour délivrés à des ressortissants de pays hors UE, tous motifs)'),
    'asile': ('migr_asyappctza', 'applicant=FRST&citizen=TOTAL&sex=T&age=TOTAL&unit=PER', 'Premières demandes d\'asile', 'Eurostat (migr_asyappctza, primo-demandeurs)'),
    'irreg': ('migr_eipre', 'reason=TOTAL&apprehen=TOTAL&citizen=TOTAL&sex=T&age=TOTAL&unit=PER', 'Étrangers trouvés en situation irrégulière', 'Eurostat (migr_eipre, ressortissants de pays hors UE trouvés en situation irrégulière)'),
    'oqtf': ('migr_eiord', 'citizen=TOTAL&sex=T&age=TOTAL&unit=PER', 'Obligations de quitter le territoire', 'Eurostat (migr_eiord, ressortissants de pays hors UE ayant reçu l\'ordre de quitter le territoire)'),
    'departs': ('migr_eirtn', 'c_dest=TOTAL&citizen=TOTAL&sex=T&age=TOTAL&unit=PER', 'Départs après une obligation de quitter le territoire', 'Eurostat (migr_eirtn, ressortissants de pays hors UE ayant quitté le territoire à la suite d\'un ordre)'),
}
MOTIFS = [('FAM', 'Famille'), ('EDUC', 'Études'), ('EMP', 'Travail'), ('OTH', 'Autres motifs (dont protection internationale)')]
COMPTES = [('LBIRTH', 'nais'), ('DEATH', 'deces'), ('NATGROW', 'solnat'), ('CNMIGRAT', 'solmig'), ('JAN', 'pop')]
AGES = ['Y_LT5', 'Y5-9', 'Y10-14', 'Y15-19', 'Y20-24', 'Y25-29', 'Y30-34', 'Y35-39', 'Y40-44', 'Y45-49', 'Y50-54', 'Y55-59', 'Y60-64', 'Y65-69', 'Y70-74', 'Y75-79', 'Y80-84', 'Y_GE85']


def notes_drapeaux(drap, ou='fr'):
    """Phrases courtes sous la courbe : provisoire, estimé ; changements de méthode à part (br)."""
    prov, br = {}, {}
    for y, f in (drap.get('FR') or {}).items():
        if 'p' in f:
            prov[str(y)] = 'Chiffre %d de la France provisoire (Eurostat).' % y
        elif 'e' in f:
            prov[str(y)] = 'Chiffre %d de la France estimé (Eurostat).' % y
    for g, w in GEO.items():
        for y, f in (drap.get(g) or {}).items():
            if 'b' in f:
                br.setdefault(str(y), []).append(w)
    return prov, {y: ('les deux' if set(ws) >= {'fr', 'ue'} else 'fr' if 'fr' in ws else 'ue' if 'ue' in ws else ws[0]) for y, ws in br.items()}


def serie(vals, ys, g):
    return [None if vals.get(g, {}).get(y) is None else round(vals[g][y], 4) for y in ys]


def construire():
    auj = date.today().isoformat()
    C = {}
    for k, (t, f, l, u, dec, src) in COMP.items():
        v, dr = eurostat(t, f)
        ys = sorted(y for y in set().union(*[set(x) for x in v.values()]) if y >= DEBUT)
        while ys and v.get('FR', {}).get(ys[-1]) is None:
            ys.pop()
        prov, br = notes_drapeaux(dr)
        C[k] = {'l': l, 'unite': u, 'dec': dec, 'y': ys, 'source': src, 'url': PAGE % t}
        for g, w in GEO.items():
            C[k][w] = serie(v, ys, g)
        if prov:
            C[k]['prov'] = prov
        if br:
            C[k]['br'] = {y: 1 for y in br}
            C[k]['br_motif'] = br
    # Population moyenne de chaque année (dénominateur des taux pour 1 000 habitants).
    pop, _ = eurostat('demo_gind', 'indic_de=AVG')
    M, N = {}, {}
    for k, (t, f, l, src) in MIGR.items():
        v, dr = eurostat(t, f)
        ys = sorted(y for y in v.get('FR', {}) if y >= DEBUT)
        prov, br = notes_drapeaux(dr)
        c = {'l': l, 'unite': 'pour 1 000 habitants', 'dec': 2, 'y': ys, 'source': src + ' ; population moyenne : Eurostat (demo_gind), calcul Concret', 'url': PAGE % t}
        for g, w in GEO.items():
            c[w] = [None if v.get(g, {}).get(y) is None or not pop.get(g, {}).get(y) else round(1000 * v[g][y] / pop[g][y], 3) for y in ys]
        if prov:
            c['prov'] = prov
        if br:
            c['br'] = {y: 1 for y in br}; c['br_motif'] = br
        M[k] = c
        N[k] = {'y': ys, 'fr': [v['FR'].get(y) for y in ys], 'l': l, 'source': src, 'url': PAGE % t}
    # Premiers titres de séjour de la France, par motif.
    T = {'y': N['titres']['y'], 'source': MIGR['titres'][3].replace('tous motifs', 'par motif'), 'url': PAGE % 'migr_resfirst', 'motifs': []}
    for code, nom in MOTIFS:
        v, _ = eurostat('migr_resfirst', 'reason=%s&duration=TOTAL&citizen=TOTAL&unit=PER' % code, {'FR': 'fr'})
        T['motifs'].append({'c': code, 'l': nom, 'fr': [v.get('FR', {}).get(y) for y in T['y']]})
    # Nombres de la France.
    K = {}
    for code, k in COMPTES:
        v, dr = eurostat('demo_gind', 'indic_de=' + code, {'FR': 'fr'})
        ys = sorted(v.get('FR', {}))
        K[k] = {'y': ys, 'fr': [v['FR'][y] for y in ys]}
        p = [y for y, f in (dr.get('FR') or {}).items() if 'p' in f or 'e' in f]
        if p:
            K[k]['prov'] = sorted(p)
    K['source'] = 'Eurostat (demo_gind : naissances vivantes, décès, solde naturel, solde migratoire ajustement compris, population au 1er janvier)'
    K['url'] = PAGE % 'demo_gind'
    # Pyramide des âges : dernière année publiée à la fois pour la France et l'UE.
    PY = None
    for an in range(date.today().year, date.today().year - 4, -1):
        try:
            res = {}
            for sx in ('M', 'F'):
                d = json.loads(U.get(U.EST + 'demo_pjangroup?format=JSON&unit=NR&sex=%s&time=%d&geo=FR&geo=EU27_2020' % (sx, an) + ''.join('&age=' + a for a in AGES + ['TOTAL'])))
                idx = d['dimension']['age']['category']['index']; gi = d['dimension']['geo']['category']['index']
                na, ng = len(idx), len(gi)
                pos = {k: i for k, i in idx.items()}
                for g in ('FR', 'EU27_2020'):
                    val = lambda a: d['value'].get(str(gi[g] * na + pos[a])) if d['id'].index('geo') < d['id'].index('age') else d['value'].get(str(pos[a] * ng + gi[g]))
                    res.setdefault(g, {})[sx] = [val(a) for a in AGES]
                    res[g].setdefault('T', 0)
                    res[g]['T'] += val('TOTAL') or 0
            if all(x is not None for g in res for sx in ('M', 'F') for x in res[g][sx]):
                PY = {'annee': an, 'ages': ['0-4', '5-9', '10-14', '15-19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49', '50-54', '55-59', '60-64', '65-69', '70-74', '75-79', '80-84', '85 et plus'],
                      'source': 'Eurostat (demo_pjangroup, population au 1er janvier par âge et sexe), en % de la population, calcul Concret', 'url': PAGE % 'demo_pjangroup'}
                for g, w in (('FR', 'fr'), ('EU27_2020', 'ue')):
                    tot = res[g]['T']
                    PY[w] = {'H': [round(100 * x / tot, 3) for x in res[g]['M']], 'F': [round(100 * x / tot, 3) for x in res[g]['F']]}
                break
        except (IOError, KeyError, ValueError):
            continue
    if not PY:
        raise IOError('pyramide des âges introuvable')
    P = {'irreguliers': {'v': 'Le nombre d\'étrangers en situation irrégulière présents en France est difficile à évaluer. Il est généralement estimé à partir du nombre de bénéficiaires de l\'aide médicale d\'État (439 000 en juin 2023), mais cette estimation présente de nombreuses limites.',
                         'source': 'Cour des comptes, « La politique de lutte contre l\'immigration irrégulière », janvier 2024', 'url': 'https://www.ccomptes.fr/fr/publications/la-politique-de-lutte-contre-limmigration-irreguliere', 'date': '2024-01-04'}}
    return {'maj': auj, 'C': C, 'M': M, 'N': N, 'K': K, 'TITRES': T, 'PYR': PY, 'P': P}


def main():
    try:
        S = construire()
    except (IOError, KeyError, ValueError) as x:
        print('Eurostat : lecture impossible :', x)
        sys.exit(1)
    o = json.load(open(os.path.join(ROOT, 'data.json'), encoding='utf-8'))
    avant = (o.get('series') or {}).get('population') or {}
    for bloc in ('C', 'M'):
        for k, c in S[bloc].items():
            a = (avant.get(bloc) or {}).get(k) or {}
            der = max(i for i, v in enumerate(c['fr']) if v is not None)
            print('%-8s %-45s France %s : %s%s' % (k, c['l'][:45], c['y'][der], c['fr'][der], '' if a.get('y') == c['y'] and a.get('fr') == c['fr'] else '  (nouveau ou changé)'))
    K = S['K']
    print('France %d : %s naissances, %s décès, solde naturel %s, solde migratoire %s ; population au 1er janvier %d : %s'
          % (K['nais']['y'][-1], K['nais']['fr'][-1], K['deces']['fr'][-1], K['solnat']['fr'][-1], K['solmig']['fr'][-1], K['pop']['y'][-1], K['pop']['fr'][-1]))
    print('Pyramide des âges :', S['PYR']['annee'])
    if '--ecrire' in sys.argv:
        o.setdefault('series', {})['population'] = S
        assert 'textes' in o and 'datasets' in o
        open(os.path.join(ROOT, 'data.json'), 'w', encoding='utf-8').write(json.dumps(o, indent=0, ensure_ascii=False))
        cp = os.path.join(ROOT, 'donnees/calendrier.json')
        cal = json.load(open(cp, encoding='utf-8'))
        for it in cal.get('indicateurs', []):
            if it.get('id') in ('pop_demo', 'pop_migr'):
                it['derniere_verification'] = date.today().isoformat()
                it['derniere_donnee'] = str(K['nais']['y'][-1] if it['id'] == 'pop_demo' else max(S['M']['titres']['y']))
                it['prochaine_verification'] = (date.today() + timedelta(days=30)).isoformat()
        open(cp, 'w', encoding='utf-8').write(json.dumps(cal, indent=1, ensure_ascii=False) + '\n')
        print('Écrit : series.population.')


if __name__ == '__main__':
    main()
