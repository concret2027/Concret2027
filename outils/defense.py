#!/usr/bin/env python3
"""Séries de la page Défense, lues aux sources (jamais saisies à la main).

  - Dépense publique de défense et investissement public de défense, % du PIB : Eurostat (gov_10a_exp, fonction GF02 ;
    PIB : nama_10_gdp), rapport calculé par Concret à partir des montants en euros, France, Allemagne, Espagne.
  - Dépense de défense au sens de l'OTAN (% du PIB), part de l'équipement, militaires : classeur Excel de l'OTAN
    (Defence Investment of NATO Countries), France, Allemagne, Espagne, États-Unis ; militaires rapportés à la population
    au 1er janvier (Eurostat demo_gind ; États-Unis : Banque mondiale, SP.POP.TOTL).
La moyenne de l'UE de chaque indicateur est calculée par outils/ue_calc.py (à relancer après --ecrire).

  python3 outils/defense.py            compare aux séries de data.json, sans rien écrire
  python3 outils/defense.py --ecrire   écrit les séries (y, fr, de, es, us, est) dans data.json

Code de sortie 1 si une source est injoignable (rien n'est écrit)."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ue_calc as U

ROOT = U.ROOT
PAYS = ['FR', 'DE', 'ES']
EST = "Non compté : pour %d, l'OTAN ne publie qu'une estimation, révisée l'année suivante."
# Où va chaque série, et sa source (l'édition du classeur de l'OTAN change chaque année).
CIBLE = {'dep': 'C', 'inv': 'C', 'otan': 'C', 'equip': 'C', 'pers': 'AFF'}
SRC = {'otan': "OTAN, chiffres de défense des pays de l'OTAN, édition %d (classeur Excel), tableau 3",
       'equip': "OTAN, chiffres de défense des pays de l'OTAN, édition %d (classeur Excel), tableau 8a",
       'pers': "OTAN, chiffres de défense des pays de l'OTAN, édition %d (classeur Excel), tableau 7 ; population : Eurostat (demo_gind), calcul Concret",
       'pers_n': "OTAN, chiffres de défense des pays de l'OTAN, édition %d (classeur Excel), tableau 7"}


def eurostat3(table, filtres):
    """Comme ue_calc.eurostat, pour la France, l'Allemagne et l'Espagne."""
    d = json.loads(U.get(U.EST + table + '?format=JSON&' + filtres + ''.join('&geo=' + g for g in PAYS)))
    dims, tailles = d['id'], d['size']
    inv = {k: {i: c for c, i in d['dimension'][k]['category']['index'].items()} for k in dims}
    out = {}
    for idx, v in d['value'].items():
        idx, cle = int(idx), {}
        for k, s in zip(reversed(dims), reversed(tailles)):
            cle[k] = inv[k][idx % s]; idx //= s
        if v is not None:
            out.setdefault(cle['geo'], {})[int(cle['time'])] = v
    return out


def pop_us():
    d = json.loads(U.get('https://api.worldbank.org/v2/country/USA/indicator/SP.POP.TOTL?format=json&date=2010:2030&per_page=100'))
    return {int(x['date']): x['value'] for x in d[1] if x['value']}


def exportations():
    """Livraisons de grands matériels militaires (indice de volume TIV du SIPRI, repris par la Banque mondiale,
    MS.MIL.XPRT.KD) : part de chaque pays dans le total mondial, sur 5 ans glissants comme le SIPRI (une année seule
    dépend de quelques contrats). Vérifié : redonne les parts publiées par le SIPRI pour 2016-2020 et 2021-2025."""
    d = json.loads(U.get('https://api.worldbank.org/v2/country/FRA;DEU;ESP;ITA;USA;WLD/indicator/MS.MIL.XPRT.KD?format=json&date=1990:2030&per_page=2000'))
    r = {}
    for x in d[1]:
        if x['value'] is not None:
            r.setdefault(x['countryiso3code'], {})[int(x['date'])] = x['value']
    fin = max(r['WLD'])
    ans = [y for y in range(min(r['WLD']) + 4, fin + 1) if all(t in r['WLD'] for t in range(y - 4, y + 1))]
    part = lambda c, y: round(100 * sum(r.get(c, {}).get(t, 0) for t in range(y - 4, y + 1)) / sum(r['WLD'][t] for t in range(y - 4, y + 1)), 1)
    # Rang de la France parmi tous les pays sur les 5 dernières années (sans les regroupements de pays de la Banque mondiale).
    pays = json.loads(U.get('https://api.worldbank.org/v2/country?format=json&per_page=400'))[1]
    vrais = {p['id'] for p in pays if p['region']['value'] != 'Aggregates'}
    t = json.loads(U.get('https://api.worldbank.org/v2/country/all/indicator/MS.MIL.XPRT.KD?format=json&date=%d:%d&per_page=20000' % (fin - 4, fin)))[1]
    somme = {}
    for x in t:
        if x['countryiso3code'] in vrais and x['value']:
            somme[x['countryiso3code']] = somme.get(x['countryiso3code'], 0) + x['value']
    rang = sorted(somme, key=lambda c: -somme[c]).index('FRA') + 1
    return {'y': ans, 'fr': [part('FRA', y) for y in ans], 'de': [part('DEU', y) for y in ans], 'es': [part('ESP', y) for y in ans],
            'it': [part('ITA', y) for y in ans], 'us_dernier': part('USA', fin), 'fin': fin, 'rang': rang}


def series():
    """{critère: {pays: {année: valeur}}, 'est': [années estimées]}"""
    pib = eurostat3('nama_10_gdp', 'unit=CP_MEUR&na_item=B1GQ')
    # Prix du PIB (2015 = 100) : la dépense hors inflation, pour savoir si l'effort de la France recule (règle « effort »).
    prix = eurostat3('nama_10_gdp', 'unit=PD15_EUR&na_item=B1GQ')['FR']
    out, reel = {}, {}
    for k, op in (('dep', 'TE'), ('inv', 'P51G')):
        m = eurostat3('gov_10a_exp', 'unit=MIO_EUR&sector=S13&na_item=%s&cofog99=GF02' % op)
        out[k] = {g: {y: round(100 * v / pib[g][y], 3) for y, v in m.get(g, {}).items() if pib.get(g, {}).get(y)} for g in PAYS}
        reel[k] = {y: round(100 * v / prix[y], 1) for y, v in m['FR'].items() if prix.get(y)}
    pays = PAYS + ['US']
    t3, t8, t7 = U.otan_tab('Table 3', tous=True), U.otan_tab('Table 8a', tous=True), U.otan_tab('Table 7', tous=True)
    out['otan'] = {g: t3[g] for g in pays}
    out['equip'] = {g: t8[g] for g in pays}
    pop = eurostat3('demo_gind', 'indic_de=JAN&sinceTimePeriod=2010')
    pop['US'] = pop_us()
    # 4 décimales : à 2, deux évolutions minuscules s'afficheraient « 0,00 » sans qu'on voie laquelle est la plus grande.
    out['pers'] = {g: {y: round(1e6 * v / pop[g][y], 4) for y, v in t7[g].items() if pop[g].get(y)} for g in pays}
    out['pers_n'] = {g: t7[g] for g in pays}
    # Dépense de défense de la France à prix constants (OTAN, tableau 2, dollars de 2021) et sa part pour l'équipement.
    t2 = U.otan_tab('Table 2', 'Constant')['FR']
    reel['otan'] = dict(t2)
    reel['equip'] = {y: round(t8['FR'][y] * v / 100, 1) for y, v in t2.items() if y in t8['FR']}
    out['reel'] = reel
    # Années estimées : celles dont l'en-tête finit par « e » dans le classeur.
    wb, url = U.otan_xlsx()
    rows = list(wb['Table 3'].iter_rows(values_only=True))
    tete = next(r for r in rows if r[1] == 2014)
    out['est'] = [int(str(v)[:-1]) for v in tete[1:] if isinstance(v, str) and v.endswith('e')]
    out['url'] = url
    out['export'] = exportations()
    out['edition'] = int(re.search(r'def-exp-(\d{4})', url).group(1))
    # Repère affiché sous les effectifs : la Pologne, dont l'armée pèse le plus dans l'évolution de la moyenne de l'UE.
    pl = U.otan_tab('Table 7')['PL']
    reel = [y for y in sorted(pl) if y not in out['est']]
    out['pologne'] = {'y0': reel[0], 'v0': pl[reel[0]], 'y1': reel[-1], 'v1': pl[reel[-1]]}
    return out


def main():
    ecrire = '--ecrire' in sys.argv
    o = json.load(open(os.path.join(ROOT, 'data.json'), encoding='utf-8'))
    try:
        S = series()
    except Exception as e:
        print('Défense ✗ source injoignable (%s : %s). Rien écrit.' % (type(e).__name__, e))
        sys.exit(1)
    D = o['series'].get('defense')
    if D is None:
        print('series.defense absent de data.json : rien à mettre à jour.'); sys.exit(1)
    for k in ('dep', 'inv', 'otan', 'equip', 'pers'):
        c, s = D[CIBLE[k]][k], S[k]
        y0 = min(min(v) for v in s.values() if v)
        y1 = max(max(v) for v in s.values() if v)
        ys = list(range(y0, y1 + 1))
        neuf = {'y': ys}
        for g, w in (('FR', 'fr'), ('DE', 'de'), ('ES', 'es'), ('US', 'us')):
            if g in s:
                neuf[w] = [s[g].get(y) for y in ys]
        ch = [w for w in neuf if c.get(w) != neuf[w]]
        print('%s : %d-%d%s' % (k, y0, y1, (' ; changé : ' + ', '.join(ch)) if ch else ' ; inchangé'))
        for w in ch:
            if w != 'y' and c.get(w):
                old = dict(zip(c['y'], c[w]))
                print('    %s : %s' % (w, ', '.join('%d %s→%s' % (y, old.get(y), v) for y, v in zip(ys, neuf[w]) if old.get(y) != v)))
        if ecrire:
            # Les moyennes de l'UE calculées suivent les années : outils/ue_calc.py les recalcule ensuite.
            if c.get('y') != ys:
                for f in ('ue_calc', 'ue_calc_ev'):
                    if c.get(f):
                        old = dict(zip(c['y'], c[f])); c[f] = [old.get(y) for y in ys]
            c.update(neuf)
            if k in S['reel']:
                c['fr_reel'] = [S['reel'][k].get(y) for y in ys]
                c['fr_reel_u'] = "millions d'euros aux prix de 2015 (Eurostat, déflaté par le prix du PIB)" if k in ('dep', 'inv') else "millions de dollars aux prix de 2021 (OTAN)"
            if k in ('otan', 'equip', 'pers'):
                c['est'] = {str(y): EST % y for y in S['est'] if y in ys}
                c['url'] = S['url']
                c['source'] = SRC[k] % S['edition']
    if ecrire:
        D['AFF']['pers']['pologne'] = S['pologne']
        X, E = D['AFF'].setdefault('export', {}), S['export']
        X.update({k: E[k] for k in ('y', 'fr', 'de', 'es', 'it')})
        X['us_note'] = "Pas de courbe pour les États-Unis, hors de l'échelle : %s %% des livraisons mondiales sur %d-%d." % (('%.1f' % E['us_dernier']).replace('.', ','), E['fin'] - 4, E['fin'])
        X['periode'] = '%d-%d' % (E['fin'] - 4, E['fin'])
        X['rang_fr'] = E['rang']
        n = D['AFF']['pers_n']
        n['y'] = list(range(2014, max(S['pers_n']['FR']) + 1))
        # Sans les États-Unis : avec plus d'un million de militaires, ils écraseraient l'échelle de la courbe.
        for g, w in (('FR', 'fr'), ('DE', 'de'), ('ES', 'es')):
            n[w] = [S['pers_n'][g].get(y) for y in n['y']]
        n.pop('us', None)
        n['est'] = {str(y): EST % y for y in S['est']}
        n['url'], n['source'] = S['url'], SRC['pers_n'] % S['edition']
        open(os.path.join(ROOT, 'data.json'), 'w', encoding='utf-8').write(json.dumps(o, indent=0, ensure_ascii=False))
        print('Écrit dans data.json ; relancer python3 outils/ue_calc.py --ecrire --seul defense.dep,defense.inv,defense.otan,defense.equip,defense.AFF.pers')


if __name__ == '__main__':
    main()
