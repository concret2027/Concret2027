#!/usr/bin/env python3
"""Séries de la page Vie des Français, lues aux sources (jamais saisies à la main).

  - Eurostat, pour la France, l'Allemagne, l'Espagne et la moyenne de l'UE publiée par Eurostat (EU27_2020) :
    revenu réel des ménages par habitant, retards de paiement, pauvreté ou exclusion sociale, privation sévère,
    écart de revenu S80/S20, coût et surpeuplement du logement, logement mal chauffé, taux d'emploi, pauvreté des
    personnes qui travaillent, écart de salaire entre femmes et hommes, satisfaction dans la vie.
    Un changement de méthode n'est retenu que s'il est signalé par Eurostat (code « b ») : champ br.
  - Moral des ménages : enquête de la Commission européenne (Eurostat ei_bsco_m, indicateur de confiance des
    consommateurs, corrigé des effets de saison), moyenne des douze mois de chaque année complète, calcul Concret ;
    le dernier mois publié va dans datasets.vie_moral.
  - Indice de développement humain : PNUD (fichier des séries complètes du dernier Rapport sur le développement humain),
    affiché sans note ; la moyenne de l'UE est calculée par outils/ue_calc.py (vie.AFF.idh).

  python3 outils/vie.py            compare aux séries de data.json, sans rien écrire
  python3 outils/vie.py --ecrire   écrit les séries (y, fr, de, es, ue, br) dans data.json

Code de sortie 1 si une source est injoignable (rien n'est écrit)."""
import csv, io, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ue_calc as U

ROOT = U.ROOT
GEO = {'FR': 'fr', 'DE': 'de', 'ES': 'es', 'EU27_2020': 'ue'}
# Critère : (table Eurostat, filtres). Une seule valeur par pays et par année une fois filtrée.
TABLES = {
    'rev': ('tepsr_wc310', 'na_item=B6G_R_HAB_2008&unit=CP_MNAC&direct=PAID&sector=S14_S15'),
    'arr': ('ilc_mdes05', 'hhcomp=TOTAL&rskpovth=TOTAL&unit=PC'),
    'arope': ('ilc_peps01n', 'unit=PC&age=TOTAL&sex=T'),
    'priv': ('ilc_mdsd11', 'unit=PC&age=TOTAL&sex=T'),
    's80': ('ilc_di11', 'unit=RAT&age=TOTAL&sex=T'),
    'surch': ('ilc_lvho07a', 'unit=PC&age=TOTAL&sex=T&rskpovth=TOTAL'),
    'surp': ('ilc_lvho05a', 'unit=PC&age=TOTAL&sex=T&rskpovth=TOTAL'),
    'froid': ('ilc_mdes01', 'hhcomp=TOTAL&rskpovth=TOTAL&unit=PC'),
    'emp': ('lfsi_emp_a', 'indic_em=EMP_LFS&unit=PC_POP&age=Y20-64&sex=T'),
    'iw': ('ilc_iw01', 'wstatus=EMP&age=Y_GE18&sex=T&unit=PC'),
    'ecsal': ('sdg_05_20', 'unit=PC&nace_r2=B-S_X_O'),
    'sat': ('ilc_pw01', 'statinfo=AVG&unit=RTG&isced11=TOTAL&life_sat=LIFE&sex=T&age=Y_GE16'),
}
# Fichier des séries complètes du dernier Rapport sur le développement humain : l'outil essaie l'édition la plus récente.
PNUD_MODELE = 'https://hdr.undp.org/sites/default/files/%d_HDR/HDR%02d_Composite_indices_complete_time_series.csv'
_pnud = {}


def pnud_csv():
    """(lignes du fichier, url, édition) de la dernière édition publiée (essaie l'année prochaine, puis en arrière)."""
    if not _pnud:
        from datetime import date
        for a in range(date.today().year + 1, 2024, -1):
            url = PNUD_MODELE % (a, a % 100)
            try:
                txt = U.get(url, essais=1)
            except IOError:
                continue
            _pnud.update(lignes=list(csv.DictReader(io.StringIO(txt.decode('latin-1')))), url=url, edition=a)
            break
        else:
            raise IOError('aucune édition du fichier du PNUD trouvée')
    return _pnud['lignes'], _pnud['url'], _pnud['edition']


def eurostat4(table, filtres):
    """{pays: {année ou mois: valeur}}, {pays: {année: drapeau}} pour la France, l'Allemagne, l'Espagne et l'UE."""
    d = json.loads(U.get(U.EST + table + '?format=JSON&' + filtres + ''.join('&geo=' + g for g in GEO)))
    dims, tailles = d['id'], d['size']
    inv = {k: {i: c for c, i in d['dimension'][k]['category']['index'].items()} for k in dims}
    for k, s in zip(dims, tailles):
        if s > 1 and k not in ('geo', 'time'):
            raise ValueError('%s : plusieurs valeurs pour %s, filtre incomplet' % (table, k))
    out, drap = {}, {}
    for idx in set(d['value']) | set(d.get('status', {})):
        i, cle = int(idx), {}
        for k, s in zip(reversed(dims), reversed(tailles)):
            cle[k] = inv[k][i % s]; i //= s
        v, f = d['value'].get(idx), d.get('status', {}).get(idx, '')
        if v is not None:
            out.setdefault(cle['geo'], {})[cle['time']] = v
        if 'b' in f:
            drap.setdefault(cle['geo'], {})[cle['time']] = 'b'
    return out, drap


def pnud():
    """IDH de la France, de l'Allemagne, de l'Espagne et des États-Unis, et rang de la France la dernière année."""
    r, url, edition = pnud_csv()
    cols = sorted(int(c[4:]) for c in r[0] if re.fullmatch(r'hdi_\d{4}', c))
    lig = {x['iso3']: x for x in r}
    out = {}
    for iso, w in (('FRA', 'fr'), ('DEU', 'de'), ('ESP', 'es'), ('USA', 'us')):
        out[w] = {y: float(lig[iso]['hdi_%d' % y]) for y in cols if lig[iso].get('hdi_%d' % y)}
    fin = max(y for y in cols if lig['FRA'].get('hdi_%d' % y))
    rang = lig['FRA'].get('hdi_rank_%d' % fin) or lig['FRA'].get('hdi_rank')
    return out, fin, int(float(rang)), edition, url


def series():
    S = {}
    for k, (t, f) in TABLES.items():
        v, drap = eurostat4(t, f)
        S[k] = {'v': {GEO[g]: {int(a): x for a, x in s.items()} for g, s in v.items()},
                'b': {GEO[g]: [int(a) for a in s] for g, s in drap.items()}}
    # Moral des ménages : moyenne des douze mois de chaque année complète (chaque mois publié pour le pays).
    m, _ = eurostat4('ei_bsco_m', 'indic=BS-CSMCI&s_adj=SA&unit=BAL')
    an = {}
    for g, s in m.items():
        par = {}
        for mois, x in s.items():
            par.setdefault(int(mois[:4]), []).append(x)
        an[GEO[g]] = {y: round(sum(l) / 12, 1) for y, l in par.items() if len(l) == 12}
    S['conf'] = {'v': an, 'b': {}}
    dernier = max(m['FR'])
    S['moral_mois'] = {'mois': dernier, 'fr': m['FR'][dernier], 'ue': m['EU27_2020'].get(dernier),
                       'de': m['DE'].get(dernier), 'es': m['ES'].get(dernier)}
    S['idh'], S['idh_fin'], S['idh_rang'], S['idh_edition'], S['idh_url'] = pnud()
    return S


def br(b, y, calc):
    # Moyenne calculée par Concret (ue_calc) : seul compte le changement de méthode de la France.
    fr, ue = y in b.get('fr', []), not calc and y in b.get('ue', [])
    return 'fr_ue' if fr and ue else 'fr' if fr else 'ue' if ue else None


MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']


def main():
    ecrire = '--ecrire' in sys.argv
    o = json.load(open(os.path.join(ROOT, 'data.json'), encoding='utf-8'))
    try:
        S = series()
    except Exception as e:
        print('Vie des Français ✗ source injoignable (%s : %s). Rien écrit.' % (type(e).__name__, e))
        sys.exit(1)
    V = o['series'].get('vie')
    if V is None:
        print('series.vie absent de data.json : rien à mettre à jour.'); sys.exit(1)
    for k in list(TABLES) + ['conf']:
        c, s = V['C'][k], S[k]
        ys = sorted(set().union(*[set(v) for v in s['v'].values()]))
        # Le moral des ménages est mesuré depuis 1985 : on garde depuis 1994, l'année avant le premier mandat noté.
        # La série commence à la première année publiée pour la France.
        y0 = min(y for y in ys if s['v'].get('fr', {}).get(y) is not None)
        ys = list(range(max(y0, 1994), ys[-1] + 1))
        neuf = {'y': ys}
        # Moyenne de l'UE calculée par Concret (ue_calc) : on ne garde pas en plus celle d'Eurostat (une seule courbe de moyenne).
        for w in (('fr', 'de', 'es') if c.get('ref') == 'ue_calc' else ('fr', 'ue', 'de', 'es')):
            neuf[w] = [s['v'].get(w, {}).get(y) for y in ys]
        calc = c.get('ref') == 'ue_calc'
        b = {str(y): br(s['b'], y, calc) for y in ys[1:] if br(s['b'], y, calc)}
        if b or c.get('br'):
            neuf['br'] = b
        # Dernières années publiées pour la moyenne de l'UE mais pas encore pour la France : on le dit.
        fin_fr = max(y for y in ys if s['v'].get('fr', {}).get(y) is not None)
        m = {str(y): "Non compté : le chiffre %d de la France n'est pas encore publié par Eurostat." % y for y in ys if y > fin_fr}
        # Années sans chiffre français au milieu de la série (Eurostat ne l'a pas mesuré ou pas publié).
        m.update({str(y): "Non compté : Eurostat n'a pas publié ce chiffre pour la France cette année-là." for y in ys if y < fin_fr and s['v'].get('fr', {}).get(y) is None})
        if m or c.get('manque'):
            neuf['manque'] = m
        ch = [w for w in neuf if c.get(w) != neuf[w]]
        print('%s : %d-%d%s' % (k, ys[0], ys[-1], (' ; changé : ' + ', '.join(ch)) if ch else ' ; inchangé'))
        for w in ch:
            if w not in ('y', 'br', 'manque') and c.get(w):
                old = dict(zip(c['y'], c[w]))
                print('    %s : %s' % (w, ', '.join('%d %s→%s' % (y, old.get(y), v) for y, v in zip(ys, neuf[w]) if old.get(y) != v)))
        if ecrire:
            c.update(neuf)
            if c.get('ref') == 'ue_calc':
                c.pop('ue', None)
            if not neuf.get('br'):
                c.pop('br', None)
            if not neuf.get('manque'):
                c.pop('manque', None)
    i, I = V['AFF']['idh'], S['idh']
    ys = list(range(1995, S['idh_fin'] + 1))
    neuf = {'y': ys}
    for w in ('fr', 'de', 'es', 'us'):
        neuf[w] = [I[w].get(y) for y in ys]
    ch = [w for w in neuf if i.get(w) != neuf[w]]
    print('idh : %d-%d, rang de la France %d (édition %d)%s' % (ys[0], ys[-1], S['idh_rang'], S['idh_edition'], (' ; changé : ' + ', '.join(ch)) if ch else ' ; inchangé'))
    mm = S['moral_mois']
    print('moral du mois : %s, France %s, UE %s' % (mm['mois'], mm['fr'], mm['ue']))
    if ecrire:
        if i.get('y') != ys and i.get('ue_calc'):
            for f in ('ue_calc', 'ue_calc_ev'):
                old = dict(zip(i['y'], i[f])); i[f] = [old.get(y) for y in ys]
        i.update(neuf)
        i['rang_fr'], i['annee_rang'] = S['idh_rang'], S['idh_fin']
        i['source'] = "PNUD, Rapport sur le développement humain %d, séries complètes de l'indice" % S['idh_edition']
        i['url'] = S['idh_url']
        i['us_note'] = 'États-Unis : même source (PNUD).'
        a, mo = mm['mois'].split('-')
        txt = lambda v: ('%.1f' % v).replace('.', ',').replace('-', '−')
        o['datasets']['vie_moral'] = [{'mois': '%s %s' % (MOIS[int(mo) - 1], a), 'periode': mm['mois'],
                                      'fr': txt(mm['fr']), 'ue': txt(mm['ue']), 'de': txt(mm['de']), 'es': txt(mm['es']),
                                      'source': "Commission européenne, enquête auprès des consommateurs (Eurostat, ei_bsco_m), corrigé des effets de saison",
                                      'url': 'https://ec.europa.eu/eurostat/databrowser/view/ei_bsco_m/default/table'}]
        open(os.path.join(ROOT, 'data.json'), 'w', encoding='utf-8').write(json.dumps(o, indent=0, ensure_ascii=False))
        print('Écrit dans data.json ; relancer python3 outils/ue_calc.py --ecrire --seul vie.AFF.idh')


if __name__ == '__main__':
    main()
