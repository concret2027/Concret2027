"""Les 27 pays de l'UE pour le menu « + Ajouter un pays » (toile et courbes) : donnees/pays.json.

Chaque série du site est relue à sa source pour les 27 pays, avec les mêmes tables et les mêmes filtres que la France.
Contrôle avant d'écrire : la série n'est gardée que si la France, l'Allemagne et l'Espagne lues ainsi redonnent les
chiffres déjà publiés dans data.json (au dixième près, sur au moins 90 % des années communes). Sinon elle est écartée
et signalée : le pays ajouté serait mesuré autrement que la France.
Ces pays sont affichés comme repères : ils ne changent aucune note.

  python3 outils/pays.py            compare et résume
  python3 outils/pays.py --ecrire   écrit donnees/pays.json
"""
import json, os, subprocess, sys
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


def essais_tous():
    """Essais cliniques : les 27 avec la même requête que la France (outils/ue_calc.py) ; les pays hors UE avec le pays exact
    du centre (champ LocationCountry de ClinicalTrials.gov), parce que la recherche par mot y mêle des lieux d'un autre pays
    (« New Mexico » pour le Mexique). Pour la France, les deux requêtes donnent le même nombre à 0,3 % près."""
    CT = {'US': 'United States', 'UK': 'United Kingdom', 'KR': 'Korea, Republic of', 'RU': 'Russian Federation', 'TR': 'Turkey'}
    def f():
        ue = ue_seul(ue_calc('sante.essais'))()
        from concurrent.futures import ThreadPoolExecutor
        import urllib.parse
        def n(g, y):
            q = 'AREA[StudyType]INTERVENTIONAL AND AREA[StartDate]RANGE[%d-01-01,%d-12-31] AND AREA[LocationCountry]"%s"' % (y, y, CT.get(g, U.NOM_EN[g]))
            u = 'https://clinicaltrials.gov/api/v2/studies?filter.advanced=' + urllib.parse.quote(q) + '&countTotal=true&pageSize=1&fields=NCTId'
            return g, y, json.loads(U.get(u))['totalCount']
        with ThreadPoolExecutor(4) as ex:
            res = list(ex.map(lambda a: n(*a), [(g, y) for g in HORS for y in range(2008, date.today().year)]))
        pop = U.pop_banque_mondiale()
        for g, y, v in res:
            if pop.get(g, {}).get(y):
                ue.setdefault(g, {})[y] = 1e6 * v / pop[g][y]
        return ue
    return f


def exportations_tous():
    """Part des livraisons mondiales de grands matériels militaires, sur 5 ans glissants (SIPRI, indice TIV, repris par la
    Banque mondiale, MS.MIL.XPRT.KD), calculée pour chaque pays comme pour la France dans outils/defense.py."""
    def f():
        d = json.loads(U.get('https://api.worldbank.org/v2/country/%s;WLD/indicator/MS.MIL.XPRT.KD?format=json&date=1990:2030&per_page=20000' % ';'.join(U.ISO3[g] for g in UE)))
        inv = {v: k for k, v in U.ISO3.items()}
        r = {}
        for x in d[1] or []:
            if x['value'] is not None:
                r.setdefault(x['countryiso3code'], {})[int(x['date'])] = x['value']
        W = r['WLD']
        ans = [y for y in range(min(W) + 4, max(W) + 1) if all(t in W for t in range(y - 4, y + 1))]
        out = {}
        for c, s in r.items():
            if c in inv:
                out[inv[c]] = {y: 100 * sum(s.get(t, 0) for t in range(y - 4, y + 1)) / sum(W[t] for t in range(y - 4, y + 1)) for y in ans}
        return out
    return f


def wuenic(oms, unicef):
    """Couverture vaccinale (estimations OMS et Unicef, WUENIC) : l'API de l'OMS, comme pour la France ; si elle ne répond pas,
    les mêmes estimations publiées par l'Unicef (SDMX, flux IMMUNISATION). Le papillomavirus n'a que l'OMS : l'Unicef y publie
    la dernière dose, pas la première."""
    def f():
        try:
            return U.oms(oms)
        except Exception:
            if not unicef:
                raise
        import csv, io
        inv = {v: k for k, v in U.ISO3.items()}
        txt = U.get('https://sdmx.data.unicef.org/ws/public/sdmxapi/rest/data/UNICEF,IMMUNISATION,1.0/%s.%s.?format=csv&startPeriod=1995' % ('+'.join(U.ISO3[g] for g in UE), unicef)).decode('utf-8-sig')
        out = {}
        for x in csv.DictReader(io.StringIO(txt)):
            if x['REF_AREA'] in inv and x['OBS_VALUE'] and float(x['OBS_VALUE']):
                out.setdefault(inv[x['REF_AREA']], {})[int(x['TIME_PERIOD'])] = float(x['OBS_VALUE'])
        return out
    return f


def arwu():
    """Classement de Shanghai : nombre d'universités de chaque pays dans les 100 premières, chaque année (API de
    shanghairanking.com, la même que pour la France ; un pays absent des 100 premières compte 0)."""
    ALIAS = {'Russia': 'RU', 'South Korea': 'KR', 'Korea': 'KR', 'Czech Republic': 'CZ', 'Czechia': 'CZ', 'Turkey': 'TR', 'Türkiye': 'TR',
             'United Kingdom': 'UK', 'Greece': 'EL', 'China': 'CN', 'United States': 'US'}
    def f():
        par_nom = {U.NOM_EN[g]: g for g in UE}
        out = {}
        for v in range(2003, date.today().year + 1):
            try:
                d = json.loads(U.get('https://www.shanghairanking.com/api/pub/v1/arwu/rank?version=%d' % v))['data']['rankings']
            except Exception:
                continue
            if not d:
                continue
            for g in UE:
                out.setdefault(g, {})[v] = 0
            for x in d:
                if str(x.get('ranking', '')).isdigit() and int(x['ranking']) <= 100:
                    g = ALIAS.get(x['region']) or par_nom.get(x['region'])
                    if g:
                        out[g][v] += 1
        return out
    return f


import pays_pdf as PDF  # rapports de l'EFPIA (W.A.I.T., « The Pharmaceutical Industry in Figures ») lus dans leurs PDF
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
    'sante.essais': essais_tous(),
    # Programmes (vaccins, dépistages) : chaque élément a sa courbe (« ch-vac-grippe » → « sante.vac-grippe »).
    # Innovation : nouveaux médicaments (W.A.I.T.) et ventes de médicaments, lus dans les rapports de l'EFPIA (outils/pays_pdf.py).
    'sante.wd': PDF.wait_dispo, 'sante.wt': PDF.wait_delai, 'sante.a-med': PDF.medicaments,
    'sante.vac-grippe': est('hlth_ps_immu', 'unit=PC'),
    'sante.vac-rougeole': wuenic('MCV2', 'IM_MCV2'), 'sante.vac-dtp3': wuenic('WHS4_100', 'IM_DTP3'), 'sante.vac-hpv': wuenic('SDGHPVRECEIVED', None),
    'sante.dep-sein': ue_calc('sante.dep.sein'), 'sante.dep-colon': ue_calc('sante.dep.colon'), 'sante.dep-col': ue_calc('sante.dep.col'),
    # Sécurité et justice
    'securite.hom': ue_calc('securite.hom'), 'securite.rob': ue_calc('securite.rob'), 'securite.bur': ue_calc('securite.bur'),
    'securite.occ': ue_calc('securite.occ'), 'securite.places': ue_calc('securite.places'),
    'securite.dpol': ue_calc('securite.dpol'), 'securite.dtrib': ue_calc('securite.dtrib'), 'securite.dpris': ue_calc('securite.dpris'),
    'securite.quart': est('ilc_mddw03', 'hhcomp=TOTAL&rskpovth=TOTAL&unit=PC'),
    'securite.eloi': ratio(est('migr_eirtn', 'c_dest=TOTAL&citizen=TOTAL&sex=T&age=TOTAL&unit=PER'), est('migr_eiord', 'citizen=TOTAL&sex=T&age=TOTAL&unit=PER'), 100),
    # Courbes affichées sans note (series.<page>.AFF), clé « <page>.a-<nom de la courbe> » comme leur graphique (« ch-a-hly »)
    'sante.a-hly': est('hlth_hlye', 'hlth_hle=HLY_Y0&sex=T&unit=YR'),
    'sante.a-dep': est('hlth_sha11_hf', 'unit=PC_GDP&icha11_hf=TOT_HF'),
    'sante.a-tabac': lambda: U.ocde('OECD.ELS.HD,DSD_HEALTH_LVNG@DF_HEALTH_LVNG_TC,', dict(MEASURE='SP_DS', AGE='Y_GE15', SEX='_T', UNIT_MEASURE='PT_POP')),
    'defense.a-pers': ue_calc('defense.AFF.pers'),
    'defense.a-export': exportations_tous(),
    'vie.a-idh': ue_calc('vie.AFF.idh'),
    'securite.a-sex': est('crim_off_cat', 'iccs=ICCS0301&unit=P_HTHAB'),
    'securite.a-det': est('crim_pris_cap', 'unit=P_HTHAB&indic_cr=PRIS_ACT_CAP'),
    'securite.a-jug': est('crim_just_job', 'isco08=OC2612A&sex=T&unit=P_HTHAB'),
    'securite.a-pol': est('crim_just_job', 'isco08=OC5412&sex=T&unit=P_HTHAB'),
    'securite.a-oqtf': ratio(est('migr_eiord', 'citizen=TOTAL&sex=T&age=TOTAL&unit=PER'), est('demo_gind', 'indic_de=JAN'), 100000),
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
    'education.arwu': arwu(),
    'education.dep': est('gov_10a_exp', 'unit=PC_GDP&sector=S13&cofog99=GF09&na_item=TE'),
    'finances.retraites': est('gov_10a_exp', 'unit=PC_GDP&sector=S13&cofog99=GF1002&na_item=TE'),
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


# Nom de la courbe affichée sans note dans series.<page>.AFF, d'après son graphique (« ch-a-dep » → « depense »).
AFFN = {'dep': 'depense', 'det': 'detenus', 'jug': 'juges', 'pol': 'police', 'med': 'medic'}


def reference(o, cle):
    """La série publiée dans data.json : {'y': années, 'FR': [...], 'DE': [...], 'ES': [...]} (None si absente)."""
    S = o['series']
    p, rest = cle.split('.', 1)
    if cle == 'finances.retraites':
        d = S['finances']['retraites']
        return {'y': d['annees'], 'FR': d['fr'], 'DE': d.get('de'), 'ES': d.get('es')}
    if cle == 'education.arwu':
        d = S['education']['ARWU']
        return {'y': d['y'], 'FR': d['fr'], 'DE': d.get('de'), 'ES': d.get('es')}
    if cle == 'education.dep':
        d = S['education']['SP']
        return {'y': list(range(2002, 2002 + len(d['fr']))), 'FR': d['fr'], 'DE': d.get('de'), 'ES': d.get('es')}
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
    elif '-' in rest and not rest.startswith('a-'):
        c, j = rest.split('-', 1)
        d = S[p]['C'][c]['sous'][j]
    elif rest.startswith('a-'):
        d = S[p]['AFF'][AFFN.get(rest[2:], rest[2:])]
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
    # --seulement k1,k2 : ne relit que ces séries et garde les autres telles qu'elles sont dans donnees/pays.json.
    seul = sys.argv[sys.argv.index('--seulement') + 1].split(',') if '--seulement' in sys.argv else None
    try:
        avant = json.load(open(os.path.join(ROOT, 'donnees', 'pays.json'), encoding='utf-8'))['series']
    except Exception:
        avant = {}
    sans = {}
    if seul:
        try:
            sans = {k: v for k, v in json.load(open(os.path.join(ROOT, 'donnees', 'pays_index.json'), encoding='utf-8')).get('sans', {}).items() if k not in seul}
        except Exception:
            pass
        out = {k: v for k, v in avant.items() if k not in seul}
    for cle, f in DEFS.items():
        if seul and cle not in seul:
            continue
        try:
            ref = reference(o, cle)
            lu = f()
        except Exception as e:  # source injoignable : la série déjà relue est gardée ; sinon écartée, signalée et expliquée sur la page
            if cle in avant:
                out[cle] = avant[cle]; ecartes.append('%s : source injoignable, série du relevé précédent gardée' % cle)
            else:
                ecartes.append('%s : %s' % (cle, str(e)[:90]))
                sans[cle] = "Pas d'autres pays pour l'instant : la source ne répondait pas au dernier relevé ; ils seront ajoutés au prochain."
            continue
        ok, n = accord(lu, ref)
        if not n or ok < 0.9 * n:
            ecartes.append('%s : redonne %d chiffres publiés sur %d' % (cle, ok, n))
            sans[cle] = "Pas d'autres pays : relue à la source pour tous les pays, cette série ne redonne pas les chiffres publiés ici pour la France, l'Allemagne et l'Espagne ; les autres pays seraient mesurés autrement."
            continue
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
        idx = {'maj': doc['maj'], 'noms': doc['noms'], 'hors_ue': doc['hors_ue'], 'regions': {g: REG.get(g, 'Hors UE') for g in HORS}, 'cles': sorted(out), 'dispo': dispo, 'sans': sans}
        open(os.path.join(ROOT, 'donnees', 'pays_index.json'), 'w', encoding='utf-8').write(json.dumps(idx, ensure_ascii=False, separators=(',', ':')))
        print('Écrit : donnees/pays.json et donnees/pays_index.json')
        # La place de la France dans l'UE (sous le titre des courbes) suit les nouveaux chiffres : outils/rangs.js l'ajoute à l'index.
        subprocess.run(['node', os.path.join(ROOT, 'outils', 'rangs.js')], check=False)


if __name__ == '__main__':
    main()
