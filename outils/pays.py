"""Les 27 pays de l'UE pour le menu « + Ajouter un pays » (toile et courbes) : donnees/pays.json.

Chaque série du site est relue à sa source pour les 27 pays, avec les mêmes tables et les mêmes filtres que la France.
Contrôle avant d'écrire : la série n'est gardée que si la France, l'Allemagne et l'Espagne lues ainsi redonnent les
chiffres déjà publiés dans data.json (au dixième près, sur au moins 90 % des années communes). Sinon elle est écartée
et signalée : le pays ajouté serait mesuré autrement que la France.
Ces pays sont affichés comme repères : ils ne changent aucune note.

  python3 outils/pays.py            compare et résume
  python3 outils/pays.py --ecrire   écrit donnees/pays.json
"""
import json, os, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ue_calc as U

ROOT = U.ROOT
# Pays hors UE proposés aussi : ils n'ont des chiffres que là où la même source les publie (Eurostat pour la Norvège, la
# Suisse, l'Islande et le Royaume-Uni jusqu'en 2019 ; Banque mondiale, OCDE, OTAN, PISA pour les autres : États-Unis, Japon, Canada,
# Corée du Sud, Australie, Nouvelle-Zélande, Turquie, Chine, Inde, Russie, Brésil, Argentine, Chili, Mexique, Colombie).
HORS = {'US': ('USA', 'United States', 'États-Unis'), 'UK': ('GBR', 'United Kingdom', 'Royaume-Uni'), 'NO': ('NOR', 'Norway', 'Norvège'),
        'CH': ('CHE', 'Switzerland', 'Suisse'), 'IS': ('ISL', 'Iceland', 'Islande'), 'JP': ('JPN', 'Japan', 'Japon'), 'CA': ('CAN', 'Canada', 'Canada'),
        'KR': ('KOR', 'Korea', 'Corée du Sud'), 'AU': ('AUS', 'Australia', 'Australie'), 'NZ': ('NZL', 'New Zealand', 'Nouvelle-Zélande'),
        'TR': ('TUR', 'Türkiye', 'Turquie'), 'CN': ('CHN', 'China', 'Chine'), 'IN': ('IND', 'India', 'Inde'), 'RU': ('RUS', 'Russia', 'Russie'),
        'BR': ('BRA', 'Brazil', 'Brésil'), 'AR': ('ARG', 'Argentina', 'Argentine'), 'CL': ('CHL', 'Chile', 'Chili'), 'MX': ('MEX', 'Mexico', 'Mexique'),
        'CO': ('COL', 'Colombia', 'Colombie')}
for _g, (_iso, _en, _fr) in HORS.items():
    U.ISO3[_g], U.NOM_EN[_g], U.NOM_FR[_g] = _iso, _en, _fr
    if _g not in U.UE:
        U.UE.append(_g)
UE = U.UE
UE27 = [g for g in UE if g not in HORS]


def ue_seul(f):
    """Une source interrogée pays par pays (essais cliniques) : seulement les 27, pour ne pas multiplier les requêtes."""
    def g():
        garde = U.UE[:]
        U.UE[:] = UE27
        try:
            return f()
        finally:
            U.UE[:] = garde
    return g


def est(table, filtres):
    return lambda: U.eurostat(table, filtres)


def ratio(num, den, fac=1):
    def f():
        a, b = num(), den()
        return {g: {y: fac * v / b[g][y] for y, v in a.get(g, {}).items() if b.get(g, {}).get(y)} for g in UE}
    return f


def ecart(table, f1, f2):
    """Différence entre deux lignes d'une même table (premier quintile moins dernier quintile)."""
    def f():
        a, b = U.eurostat(table, f1), U.eurostat(table, f2)
        return {g: {y: v - b[g][y] for y, v in a.get(g, {}).items() if b.get(g, {}).get(y) is not None} for g in UE}
    return f


def moyenne_annuelle(table, filtres):
    """Moyenne des douze mois de chaque année complète (moral des ménages)."""
    def f():
        d = json.loads(U.get(U.EST + table + '?format=JSON&' + filtres))
        dims, tailles = d['id'], d['size']
        inv = {k: {i: c for c, i in d['dimension'][k]['category']['index'].items()} for k in dims}
        par = {}
        for idx, v in d['value'].items():
            idx, cle = int(idx), {}
            for k, s in zip(reversed(dims), reversed(tailles)):
                cle[k] = inv[k][idx % s]; idx //= s
            if cle['geo'] in UE and v is not None:
                par.setdefault(cle['geo'], {}).setdefault(int(cle['time'][:4]), []).append(v)
        return {g: {y: sum(l) / 12 for y, l in a.items() if len(l) == 12} for g, a in par.items()}
    return f


def banque_mondiale(code):
    def f():
        d = json.loads(U.get('https://api.worldbank.org/v2/country/%s/indicator/%s?format=json&per_page=20000' % (';'.join(U.ISO3[g] for g in UE), code)))
        inv = {v: k for k, v in U.ISO3.items()}
        out = {}
        for r in d[1] or []:
            g = inv.get(r['countryiso3code'])
            if g and r['value'] is not None:
                out.setdefault(g, {})[int(r['date'])] = r['value']
        return out
    return f


def ue_calc(cle):
    """Une série dont Concret calcule déjà la moyenne de l'UE (outils/ue_calc.py) : les mêmes chiffres, pays par pays."""
    ind = next(i for i in U.INDICATEURS if i['cle'] == cle)
    if 'taux' in ind:
        return ind['taux']
    return ratio(ind['num'], ind['den'], ind['facteur'])


import vie as V
import demographie as DM

# Clé du site → (où lire la série dans data.json, comment la relire pour les 27 pays)
DEFS = {
    # Santé
    'sante.esp': est('demo_mlexpec', 'sex=T&age=Y_LT1&unit=YR'),
    'sante.minf': est('demo_minfind', 'indic_de=INFMORRT'),
    'sante.mev': est('hlth_cd_apr', 'unit=RT&sex=T&icd10=TOTAL&mortalit=TOTAL'),
    'sante.ren': est('hlth_silc_08', 'reason=TXP_TFAR_WLIST&quant_inc=TOTAL&age=Y_GE16&sex=T&unit=PC'),
    'sante.equ': ecart('hlth_silc_08', 'reason=TXP_TFAR_WLIST&quant_inc=QU1&age=Y_GE16&sex=T&unit=PC', 'reason=TXP_TFAR_WLIST&quant_inc=QU5&age=Y_GE16&sex=T&unit=PC'),
    'sante.rac': est('hlth_sha11_hf', 'unit=PC_CHE&icha11_hf=HF3'),
    'sante.alc': ue_calc('sante.alc'),
    'sante.essais': ue_seul(ue_calc('sante.essais')),
    # Sécurité et justice
    'securite.hom': ue_calc('securite.hom'), 'securite.rob': ue_calc('securite.rob'), 'securite.bur': ue_calc('securite.bur'),
    'securite.occ': ue_calc('securite.occ'), 'securite.places': ue_calc('securite.places'),
    'securite.dpol': ue_calc('securite.dpol'), 'securite.dtrib': ue_calc('securite.dtrib'), 'securite.dpris': ue_calc('securite.dpris'),
    'securite.quart': est('ilc_mddw03', 'hhcomp=TOTAL&rskpovth=TOTAL&unit=PC'),
    'securite.eloi': ratio(est('migr_eirtn', 'c_dest=TOTAL&citizen=TOTAL&sex=T&age=TOTAL&unit=PER'), est('migr_eiord', 'citizen=TOTAL&sex=T&age=TOTAL&unit=PER'), 100),
    # Défense
    'defense.dep': ue_calc('defense.dep'), 'defense.inv': ue_calc('defense.inv'), 'defense.otan': ue_calc('defense.otan'), 'defense.equip': ue_calc('defense.equip'),
    # Vie des Français
    'vie.conf': moyenne_annuelle('ei_bsco_m', 'indic=BS-CSMCI&s_adj=SA&unit=BAL'),
    # Finances
    'finances.D.dette': est('gov_10dd_edpt1', 'unit=PC_GDP&sector=S13&na_item=GD'),
    'finances.D.deficit': est('gov_10dd_edpt1', 'unit=PC_GDP&sector=S13&na_item=B9'),
    'finances.D.dep': est('gov_10a_main', 'unit=PC_GDP&sector=S13&na_item=TE'),
    'finances.D.po': est('gov_10a_taxag', 'unit=PC_GDP&sector=S13_S212&na_item=D2_D5_D91_D61_M_D995'),
    'finances.PIB': banque_mondiale('NY.GDP.PCAP.PP.KD'),
    'finances.X94.u': banque_mondiale('SL.UEM.TOTL.ZS'),  # estimations de l'OIT, comme la page
    'finances.X95.i': est('gov_10a_main', 'unit=PC_GDP&sector=S13&na_item=D41PAY'),
    'finances.X95.x': banque_mondiale('NE.EXP.GNFS.ZS'),
    'finances.X95.m': banque_mondiale('NE.IMP.GNFS.ZS'),
    # Éducation
    'education.S.el': est('edat_lfse_14', 'sex=T&wstatus=POP&unit=PC'),
    'education.S.ne': est('edat_lfse_20', 'sex=T&age=Y15-29&wstatus=NEMP&training=NO_FE_NO_NFE&unit=PC'),
    'education.S.te': est('edat_lfse_03', 'sex=T&age=Y25-34&isced11=ED5-8&unit=PC'),
    'education.S.yu': banque_mondiale('SL.UEM.1524.ZS'),  # estimations de l'OIT, comme la page
    'education.PI.m': U.pisa('m'), 'education.PI.r': U.pisa('r'), 'education.PI.s': U.pisa('s'),
}
for k, (t, f) in V.TABLES.items():
    DEFS['vie.' + k] = est(t, f)
for k, (t, f, *_r) in DM.COMP.items():
    DEFS['demographie.' + k] = est(t, f)
_pop1 = est('migr_pop1ctz', 'citizen=TOTAL&age=TOTAL&sex=T&unit=NR')
_pop3 = est('migr_pop3ctb', 'c_birth=TOTAL&age=TOTAL&sex=T&unit=NR')
DEFS['demographie.nes'] = ratio(est('migr_pop3ctb', 'c_birth=FOR&age=TOTAL&sex=T&unit=NR'), _pop3, 100)
DEFS['demographie.nes_hue'] = ratio(est('migr_pop3ctb', 'c_birth=NEU27_2020_FOR&age=TOTAL&sex=T&unit=NR'), _pop3, 100)
DEFS['demographie.etr'] = ratio(est('migr_pop1ctz', 'citizen=FOR_STLS&age=TOTAL&sex=T&unit=NR'), _pop1, 100)
_avg = est('demo_gind', 'indic_de=AVG')
for k, (t, f, *_r) in DM.MIGR.items():
    DEFS['demographie.M.' + k] = ratio(est(t, f), _avg, 1000)


def reference(o, cle):
    """La série publiée dans data.json : {'y': années, 'FR': [...], 'DE': [...], 'ES': [...]} (None si absente)."""
    S = o['series']
    p, rest = cle.split('.', 1)
    if p == 'finances':
        F = S['finances']
        if rest.startswith('D.'):
            d = F['D'][rest[2:]]; ys = list(range(1995, 1995 + len(d['fr'])))
            return {'y': ys, 'FR': d['fr'], 'DE': d.get('de'), 'ES': d.get('es')}
        if rest == 'PIB':
            d = F['PIB']; ys = list(range(1990, 1990 + len(d['fr'])))
            return {'y': ys, 'FR': d['fr'], 'DE': d.get('de'), 'ES': d.get('es')}
        tab, k = rest.split('.')
        X = F[tab]; y0 = 1994 if tab == 'X94' else 1995
        return {'y': list(range(y0, y0 + len(X[k + 'Fr']))), 'FR': X[k + 'Fr'], 'DE': X.get(k + 'De'), 'ES': X.get(k + 'Es')}
    if p == 'education':
        tab, k = rest.split('.')
        d = S['education'][tab][k]
        ys = d.get('y') or list(range(2002, 2002 + len(d['fr'])))
        return {'y': ys, 'FR': d['fr'], 'DE': d.get('de'), 'ES': d.get('es')}
    if p == 'demographie' and rest.startswith('M.'):
        d = S['demographie']['M'][rest[2:]]
    else:
        d = S[p]['C'][rest]
    return {'y': d['y'], 'FR': d.get('fr'), 'DE': d.get('de'), 'ES': d.get('es')}


def accord(lu, ref):
    """Part des années où la série relue redonne le chiffre publié (France, Allemagne, Espagne)."""
    ok = n = 0
    for g in ('FR', 'DE', 'ES'):
        if not ref.get(g):
            continue
        for y, v in zip(ref['y'], ref[g]):
            w = lu.get(g, {}).get(y)
            if v is None or w is None:
                continue
            n += 1
            if abs(w - v) <= max(0.06, 0.006 * abs(v)):
                ok += 1
    return ok, n


def main():
    o = json.load(open(os.path.join(ROOT, 'data.json'), encoding='utf-8'))
    out, ecartes = {}, []
    for cle, f in DEFS.items():
        try:
            ref = reference(o, cle)
            lu = f()
        except Exception as e:  # source injoignable ou série absente : écartée, signalée
            ecartes.append('%s : %s' % (cle, str(e)[:90])); continue
        ok, n = accord(lu, ref)
        if not n or ok < 0.9 * n:
            ecartes.append('%s : redonne %d chiffres publiés sur %d' % (cle, ok, n)); continue
        ys = sorted({y for g in UE for y in lu.get(g, {}) if y >= 1995})
        dec = 3 if cle.startswith('demographie.M.') else 2
        out[cle] = {'y': ys}
        for g in UE:
            if g in ('FR', 'DE', 'ES'):
                continue
            s = [None if lu.get(g, {}).get(y) is None else round(lu[g][y], dec) for y in ys]
            if any(v is not None for v in s):
                out[cle][g] = s
        print('%-26s %3d/%-3d chiffres publiés retrouvés · %d pays' % (cle, ok, n, len(out[cle]) - 1))
    # Commerce : taux de couverture (exportations ÷ importations), contrôlé sur les chiffres publiés.
    if 'finances.X95.x' in out and 'finances.X95.m' in out:
        x, m = out.pop('finances.X95.x'), out.pop('finances.X95.m')
        c = {'y': x['y']}
        for g in x:
            if g != 'y' and g in m:
                c[g] = [None if a is None or not b else round(100 * a / b, 2) for a, b in zip(x[g], m[g])]
        out['finances.X95.cov'] = c
    print('\n%d séries pour %d pays.' % (len(out), len(UE) - 3))
    for g in HORS:
        print('  %s : %d séries' % (U.NOM_FR[g], sum(1 for k in out if g in out[k])))
    for e in ecartes:
        print('Écartée : ' + e)
    if '--ecrire' in sys.argv:
        doc = {'maj': date.today().isoformat(), 'noms': {g: U.NOM_FR[g] for g in UE if g not in ('FR', 'DE', 'ES')}, 'hors_ue': sorted(HORS), 'series': out}
        open(os.path.join(ROOT, 'donnees', 'pays.json'), 'w', encoding='utf-8').write(json.dumps(doc, ensure_ascii=False, separators=(',', ':')))
        # Petit index (les courbes qui peuvent recevoir un pays, et les noms) : chargé par chaque page, le gros fichier seulement si un pays est choisi.
        # Et, pour chaque courbe, les pays qui ont un chiffre : le menu ne propose qu'eux. Les pays hors UE sont rangés par région.
        REG = {'NO': 'Europe hors UE', 'CH': 'Europe hors UE', 'IS': 'Europe hors UE', 'UK': 'Europe hors UE', 'TR': 'Europe hors UE', 'RU': 'Europe hors UE',
               'US': 'Amériques', 'CA': 'Amériques', 'MX': 'Amériques', 'BR': 'Amériques', 'AR': 'Amériques', 'CL': 'Amériques', 'CO': 'Amériques',
               'JP': 'Asie et Océanie', 'KR': 'Asie et Océanie', 'CN': 'Asie et Océanie', 'IN': 'Asie et Océanie', 'AU': 'Asie et Océanie', 'NZ': 'Asie et Océanie'}
        dispo = {k: sorted(g for g in out[k] if g != 'y' and any(v is not None for v in out[k][g])) for k in out}
        idx = {'maj': doc['maj'], 'noms': doc['noms'], 'hors_ue': doc['hors_ue'], 'regions': {g: REG.get(g, 'Hors UE') for g in HORS}, 'cles': sorted(out), 'dispo': dispo}
        open(os.path.join(ROOT, 'donnees', 'pays_index.json'), 'w', encoding='utf-8').write(json.dumps(idx, ensure_ascii=False, separators=(',', ':')))
        print('Écrit : donnees/pays.json et donnees/pays_index.json')


if __name__ == '__main__':
    main()
