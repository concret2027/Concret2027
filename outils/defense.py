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
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ue_calc as U

ROOT = U.ROOT
PAYS = ['FR', 'DE', 'ES']
EST = "Non compté : pour %d, l'OTAN ne publie qu'une estimation, révisée l'année suivante."


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


def series():
    """{critère: {pays: {année: valeur}}, 'est': [années estimées]}"""
    pib = eurostat3('nama_10_gdp', 'unit=CP_MEUR&na_item=B1GQ')
    out = {}
    for k, op in (('dep', 'TE'), ('inv', 'P51G')):
        m = eurostat3('gov_10a_exp', 'unit=MIO_EUR&sector=S13&na_item=%s&cofog99=GF02' % op)
        out[k] = {g: {y: round(100 * v / pib[g][y], 3) for y, v in m.get(g, {}).items() if pib.get(g, {}).get(y)} for g in PAYS}
    pays = PAYS + ['US']
    t3, t8, t7 = U.otan_tab('Table 3', tous=True), U.otan_tab('Table 8a', tous=True), U.otan_tab('Table 7', tous=True)
    out['otan'] = {g: t3[g] for g in pays}
    out['equip'] = {g: t8[g] for g in pays}
    pop = eurostat3('demo_gind', 'indic_de=JAN&sinceTimePeriod=2010')
    pop['US'] = pop_us()
    out['pers'] = {g: {y: round(1e6 * v / pop[g][y], 2) for y, v in t7[g].items() if pop[g].get(y)} for g in pays}
    out['pers_n'] = {g: t7[g] for g in pays}
    # Années estimées : celles dont l'en-tête finit par « e » dans le classeur.
    wb, url = U.otan_xlsx()
    rows = list(wb['Table 3'].iter_rows(values_only=True))
    tete = next(r for r in rows if r[1] == 2014)
    out['est'] = [int(str(v)[:-1]) for v in tete[1:] if isinstance(v, str) and v.endswith('e')]
    out['url'] = url
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
        c, s = D['C'][k], S[k]
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
            if k in ('otan', 'equip', 'pers'):
                c['est'] = {str(y): EST % y for y in S['est'] if y in ys}
                c['url'] = S['url']
    if ecrire:
        n = D['AFF']['pers_n']
        n['y'] = list(range(2014, max(S['pers_n']['FR']) + 1))
        # Sans les États-Unis : avec plus d'un million de militaires, ils écraseraient l'échelle de la courbe.
        for g, w in (('FR', 'fr'), ('DE', 'de'), ('ES', 'es')):
            n[w] = [S['pers_n'][g].get(y) for y in n['y']]
        n.pop('us', None)
        n['est'] = {str(y): EST % y for y in S['est']}
        open(os.path.join(ROOT, 'data.json'), 'w', encoding='utf-8').write(json.dumps(o, indent=0, ensure_ascii=False))
        print('Écrit dans data.json ; relancer python3 outils/ue_calc.py --ecrire --seul defense.dep,defense.inv,defense.otan,defense.equip,defense.pers')


if __name__ == '__main__':
    main()
