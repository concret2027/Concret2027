#!/usr/bin/env python3
"""Chiffres du jour et du mois des pages Finances et Éducation, lus à la source par l'outil (jamais de saisie à la main).

- Taux de l'État à 10 ans et écart avec l'Allemagne (clôture de chaque séance) : Idéal Investisseur, données Banque de France
  et Bundesbank (fin_taux → datasets.pouls) ; chaque séance du tableau de la page absente de data.json est ajoutée.
- Chômage, France et UE (Eurostat une_rt_m, TOTAL) : series.finances.MO (uFr, uEu) et datasets.finances_mois (fin_chomage_mois).
- Chômage des moins de 25 ans (une_rt_m, Y_LT25) : series.education.MO (fr, eu) et datasets.education_mois (edu_chomage_jeunes_mois).
- Inflation (IPCH, Eurostat prc_hicp_minr, taux sur un an) : series.finances.MO (iFr, iEu) et datasets.finances_mois (fin_inflation).
- Croissance du PIB par trimestre (Eurostat namq_10_gdp, volumes CVS-CJO) : series.finances.GQ (fr, eu, frA, euA) (fin_pib_trim).

Les séries mensuelles et trimestrielles sont réécrites en entier depuis leur premier mois : Eurostat révise les mois passés,
le site reprend ses derniers chiffres. Le calendrier (donnees/calendrier.json) est mis à jour : dernière donnée, vérification
du jour, prochaine vérification (date habituelle de la publication suivante ; le lendemain si elle est attendue et pas encore là).
Les phrases d'actualité possibles sont affichées pour la tâche quotidienne, qui les reprend après lecture.

  python3 outils/chiffres.py            compare à data.json, sans rien écrire
  python3 outils/chiffres.py --ecrire   écrit data.json et donnees/calendrier.json ; chaque jour, en premier
"""
import calendar, html, json, os, re, subprocess, sys, time
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EUROSTAT = 'https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/'
OAT = 'https://www.ideal-investisseur.fr/en/markets/oat-bund-spread.html'
U_CHOMAGE = 'https://ec.europa.eu/eurostat/databrowser/view/une_rt_m/default/table'
U_INFLATION = 'https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_minr/default/table'
MOIS_EN = {m: i for i, m in enumerate(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'], 1)}
MOIS_FR = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
TRIM_FR = ['premier', 'deuxième', 'troisième', 'quatrième']
AUJ = date.today()


def get(url):
    for essai in range(3):
        r = subprocess.run(['curl', '-sS', '-m', '90', '-A', 'Mozilla/5.0 (concret2027.fr)', url], capture_output=True, text=True)
        if not r.returncode and r.stdout: return r.stdout
        time.sleep(10)
    raise IOError('lecture impossible : ' + url + ' ' + r.stderr.strip()[:200])


def eurostat(q):
    """{pays: {période: valeur}} ; les périodes sans valeur sont absentes."""
    j = json.loads(get(EUROSTAT + q))
    if 'value' not in j:
        raise IOError('Eurostat : ' + json.dumps(j)[:200])
    geo = j['dimension']['geo']['category']['index']; tm = j['dimension']['time']['category']['index']; nt = len(tm)
    inv = {v: k for k, v in tm.items()}
    out = {}
    for g, gi in geo.items():
        out[g] = {inv[t]: j['value'][str(gi * nt + t)] for t in range(nt) if str(gi * nt + t) in j['value']}
    return out, j.get('updated', '')


def mois(start, i):
    """start = [année, mois - 1] (comme new Date(année, mois) dans les pages)."""
    m = start[1] + i
    return '%d-%02d' % (start[0] + m // 12, m % 12 + 1)


def trim(start, i):
    q = start[1] - 1 + i
    return '%d-Q%d' % (start[0] + q // 4, q % 4 + 1)


def serie(start, src, cle):
    """Valeurs de src depuis start, jusqu'à la dernière période publiée sans trou."""
    out, i = [], 0
    while True:
        p = cle(start, i)
        if p not in src: break
        out.append(src[p]); i += 1
    return out


def fr(v, signe=False):
    s = ('%.1f' % abs(v)).replace('.', ',')
    return ('−' if v < 0 else ('+' if signe and v > 0 else '')) + s


def fin_mois(p):
    y, m = map(int, p.split('-')); return date(y, m, calendar.monthrange(y, m)[1])


def plus_mois(d, n):
    m = d.month - 1 + n; y = d.year + m // 12; m = m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def fin_trim(p):
    y, q = int(p[:4]), int(p[-1]); return fin_mois('%d-%02d' % (y, 3 * q))


def prochaine(attendue, revisions=()):
    """Date de la prochaine vérification : la publication suivante attendue (le lendemain si elle aurait dû paraître), ou une
    révision annoncée plus tôt. Renvoie (date, en retard ?)."""
    demain = AUJ + timedelta(days=1)
    futur = [d for d in revisions if d > AUJ]
    if attendue <= AUJ:
        return demain, AUJ > attendue + timedelta(days=5)
    return min([attendue] + futur), False


def main():
    ecrire = '--ecrire' in sys.argv
    o = json.load(open(os.path.join(ROOT, 'data.json'), encoding='utf-8'))
    s = open(os.path.join(ROOT, 'donnees', 'calendrier.json'), encoding='utf-8').read(); cal = json.loads(s)
    CAL = {i['id']: i for i in cal['indicateurs']}
    D, F, E = o['datasets'], o['series']['finances'], o['series']['education']
    rapport, actus, erreurs, faits = [], [], [], {}

    def maj(ident, derniere, attendue, revisions=()):
        i = CAL[ident]; pv, retard = prochaine(attendue, revisions)
        nouveau = derniere != i['derniere_donnee']
        i['derniere_verification'] = AUJ.isoformat(); i['prochaine_verification'] = pv.isoformat()
        if nouveau or not retard:
            i['derniere_donnee'] = derniere; i['statut'] = 'a_jour'; i['tentatives'] = 0
        else:
            i['statut'] = 'en_retard'; i['tentatives'] = i.get('tentatives', 0) + 1
        faits[ident] = '%s : dernière donnée %s%s, prochaine vérification %s' % (i['libelle'], derniere, ' (nouvelle)' if nouveau else '', pv.isoformat())

    def echec(idents, nom, e):
        """Source illisible : l'échec se voit (tentative + 1, en retard, revue demain) au lieu de passer sous silence."""
        erreurs.append(nom + ' : ' + str(e))
        for ident in idents:
            i = CAL[ident]; i['derniere_verification'] = AUJ.isoformat(); i['prochaine_verification'] = (AUJ + timedelta(days=1)).isoformat()
            i['statut'] = 'en_retard'; i['tentatives'] = i.get('tentatives', 0) + 1

    def suit(ds, inds, src, unite, url, depuis=None):
        """Reprend les révisions des lignes déjà là et ajoute les mois publiés depuis (depuis : premier mois à garder ;
        par défaut, seulement le dernier mois publié)."""
        for ind, sv in zip(inds, src):
            for r in D[ds]:
                if r['indicateur'] == ind and r['periode'] in sv: pose(ds, ind, r['periode'], sv[r['periode']], unite, url)
            for per in sorted(sv):
                if per >= (depuis or max(sv)): pose(ds, ind, per, sv[per], unite, url)

    def pose(ds, ind, per, val, unite, url):
        for r in D[ds]:
            if r['indicateur'] == ind and r['periode'] == per:
                if r['valeur'] != str(val): rapport.append('  %s %s %s : %s → %s (révision de la source)' % (ds, ind, per, r['valeur'], val)); r['valeur'] = str(val)
                return
        D[ds].append({'indicateur': ind, 'periode': per, 'valeur': str(val), 'unite': unite, 'source': 'Eurostat', 'url': url})
        rapport.append('  %s %s %s : %s (nouveau)' % (ds, ind, per, val))

    def remplace(obj, cle, nouv, nom, lab):
        anc = obj[cle]
        diff = ['%s %s → %s' % (lab(i), a, b) for i, (a, b) in enumerate(zip(anc, nouv)) if a != b]
        ajout = ['%s %s' % (lab(i), nouv[i]) for i in range(len(anc), len(nouv))]
        if len(nouv) < len(anc): erreurs.append('%s : la source a moins de périodes que data.json (%d contre %d), série gardée' % (nom, len(nouv), len(anc))); return
        if diff or ajout: rapport.append('  %s : %s' % (nom, '; '.join((['nouveau ' + a for a in ajout]) + (['révisé ' + x for x in diff]))))
        obj[cle] = nouv

    # 1. Taux à 10 ans et écart avec l'Allemagne
    try:
        t = html.unescape(re.sub(r'<[^>]+>', ' ', re.sub(r'<script.*?</script>|<style.*?</style>', '', get(OAT), flags=re.S)))
        t = re.sub(r'\s+', ' ', t)
        lignes = re.findall(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d{1,2}), (\d{4}) (\d+\.\d+) % (\d+\.\d+) % (-?\d+\.\d+) bps', t)
        if not lignes: raise IOError('tableau des séances introuvable sur la page')
        connu = {(r['indicateur'], r['date']): r for r in D['pouls']}
        dern = None
        for mo, j, a, oat, bund, sp in sorted(lignes, key=lambda x: (x[2], MOIS_EN[x[0]], int(x[1]))):
            dt = '%s-%02d-%02d' % (a, MOIS_EN[mo], int(j)); dern = max(dern or dt, dt)
            for ind, v, un in (('taux_10_ans', oat, '%'), ('ecart_allemagne', sp, 'pb')):
                r = connu.get((ind, dt))
                if r is None:
                    D['pouls'].append({'indicateur': ind, 'date': dt, 'valeur': v, 'unite': un, 'source': 'Idéal Investisseur', 'url': OAT})
                    rapport.append('  pouls %s %s : %s (nouveau)' % (ind, dt, v))
                elif float(r['valeur']) != float(v):
                    rapport.append('  pouls %s %s : %s dans data.json, %s sur la page (gardé, à vérifier)' % (ind, dt, r['valeur'], v))
        maj('fin_taux', dern, AUJ + timedelta(days=1))
    except Exception as e:
        echec(['fin_taux'], 'Taux à 10 ans', e)

    # 2. Chômage (tous âges et moins de 25 ans) et inflation, par mois
    try:
        u, _ = eurostat('une_rt_m?format=JSON&geo=FR&geo=EU27_2020&age=TOTAL&unit=PC_ACT&s_adj=SA&sex=T&sinceTimePeriod=2018-01')
        y, _ = eurostat('une_rt_m?format=JSON&geo=FR&geo=EU27_2020&age=Y_LT25&unit=PC_ACT&s_adj=SA&sex=T&sinceTimePeriod=2018-01')
        MO, EM = F['MO'], E['MO']; lab = lambda st: (lambda i: mois(st, i))
        remplace(MO, 'uFr', serie(MO['start'], u['FR'], mois), 'Chômage France', lab(MO['start']))
        remplace(MO, 'uEu', serie(MO['start'], u['EU27_2020'], mois), 'Chômage UE', lab(MO['start']))
        remplace(EM, 'fr', serie(EM['start'], y['FR'], mois), 'Chômage des moins de 25 ans France', lab(EM['start']))
        remplace(EM, 'eu', serie(EM['start'], y['EU27_2020'], mois), 'Chômage des moins de 25 ans UE', lab(EM['start']))
        pu = mois(MO['start'], len(MO['uFr']) - 1); py = mois(EM['start'], len(EM['fr']) - 1)
        suit('finances_mois', ('chomage_fr', 'chomage_ue'), (u['FR'], u['EU27_2020']), '%', U_CHOMAGE)
        suit('education_mois', ('chomage_jeunes_fr', 'chomage_jeunes_ue'), (y['FR'], y['EU27_2020']), '%', U_CHOMAGE, mois(EM['start'], 0))
        # Publié par Eurostat environ un mois après la fin du mois (septembre : fin octobre) : le mois suivant, un mois plus tard.
        if CAL['fin_chomage_mois']['derniere_donnee'] != pu:
            m = MOIS_FR[int(pu[5:]) - 1]; pm = '%d-%02d' % (int(pu[:4]) - (pu[5:] == '01'), (int(pu[5:]) - 2) % 12 + 1)
            actus.append(('actu_finances', "En %s %s, le taux de chômage est de %s %% en France (%s %% le mois précédent), contre %s %% dans l'UE." % (m, pu[:4], fr(u['FR'][pu]), fr(u['FR'][pm]), fr(u['EU27_2020'][pu])), U_CHOMAGE))
        if CAL['edu_chomage_jeunes_mois']['derniere_donnee'] != py:
            m = MOIS_FR[int(py[5:]) - 1]; pa = '%d-%s' % (int(py[:4]) - 1, py[5:])
            actus.append(('actu_education', "En %s %s, le taux de chômage des moins de 25 ans est de %s %% en France (%s %% un an plus tôt), contre %s %% dans l'UE." % (m, py[:4], fr(y['FR'][py]), fr(y['FR'][pa]), fr(y['EU27_2020'][py])), U_CHOMAGE))
        maj('fin_chomage_mois', pu, plus_mois(fin_mois(pu), 2) - timedelta(days=1))
        maj('edu_chomage_jeunes_mois', py, plus_mois(fin_mois(py), 2) - timedelta(days=1))
    except Exception as e:
        echec(['fin_chomage_mois', 'edu_chomage_jeunes_mois'], 'Chômage', e)
    try:
        i_, _ = eurostat('prc_hicp_minr?format=JSON&geo=FR&geo=EU27_2020&unit=RCH_A&coicop18=TOTAL&sinceTimePeriod=2024-01')
        MO = F['MO']; lab = lambda i: mois(MO['start'], i)
        remplace(MO, 'iFr', serie(MO['start'], i_['FR'], mois), 'Inflation France', lab)
        remplace(MO, 'iEu', serie(MO['start'], i_['EU27_2020'], mois), 'Inflation UE', lab)
        pi = mois(MO['start'], min(len(MO['iFr']), len(MO['iEu'])) - 1)
        suit('finances_mois', ('inflation_fr', 'inflation_ue'), (i_['FR'], i_['EU27_2020']), '%', U_INFLATION)
        if CAL['fin_inflation']['derniere_donnee'] != pi:
            m = MOIS_FR[int(pi[5:]) - 1]
            actus.append(('actu_finances', "En %s %s, les prix à la consommation (IPCH) augmentent de %s %% sur un an en France, contre %s %% dans l'UE." % (m, pi[:4], fr(i_['FR'][pi]), fr(i_['EU27_2020'][pi])), U_INFLATION))
        # Chiffre de l'UE vers le 17 du mois suivant : celui du mois d'après, un mois plus tard.
        maj('fin_inflation', pi, plus_mois(fin_mois(pi), 2).replace(day=16))
    except Exception as e:
        echec(['fin_inflation'], 'Inflation', e)

    # 3. Croissance du PIB par trimestre
    try:
        g, _ = eurostat('namq_10_gdp?format=JSON&geo=FR&geo=EU27_2020&unit=CLV_PCH_PRE&s_adj=SCA&na_item=B1GQ&sinceTimePeriod=2020-Q1')
        ga, _ = eurostat('namq_10_gdp?format=JSON&geo=FR&geo=EU27_2020&unit=CLV_PCH_SM&s_adj=SCA&na_item=B1GQ&sinceTimePeriod=2020-Q1')
        GQ = F['GQ']; lab = lambda i: trim(GQ['start'], i)
        for k, src, geo, nom in (('fr', g, 'FR', 'Croissance France'), ('eu', g, 'EU27_2020', 'Croissance UE'), ('frA', ga, 'FR', 'Croissance sur un an France'), ('euA', ga, 'EU27_2020', 'Croissance sur un an UE')):
            remplace(GQ, k, serie(GQ['start'], src[geo], trim), nom, lab)
        n = min(len(GQ[k]) for k in ('fr', 'eu', 'frA', 'euA')); pq = trim(GQ['start'], n - 1)
        if CAL['fin_pib_trim']['derniere_donnee'] != pq:
            v = g['FR'][pq]
            actus.append(('actu_finances', "Au %s trimestre %s, le PIB de la France %s de %s %% (%s %% sur un an), contre %s %% dans l'UE (première estimation)." % (TRIM_FR[int(pq[-1]) - 1], pq[:4], 'recule' if v < 0 else 'augmente' if v > 0 else 'varie', fr(abs(v)), fr(ga['FR'][pq], True), fr(g['EU27_2020'][pq], True)), 'https://ec.europa.eu/eurostat/databrowser/view/namq_10_gdp/default/table'))
        # Première estimation un mois après la fin du trimestre ; Eurostat révise vers le 45e jour.
        fq = fin_trim(pq)
        maj('fin_pib_trim', pq, plus_mois(fq, 4) - timedelta(days=1), (fq + timedelta(days=46),))
    except Exception as e:
        echec(['fin_pib_trim'], 'Croissance', e)

    print('Chiffres du jour et du mois (Finances, Éducation), lus à la source :')
    print('\n'.join(rapport) if rapport else '  rien de nouveau ni de révisé')
    for f in faits.values(): print('  ✓ ' + f)
    for e in erreurs: print('  ✗ ' + e + ' (calendrier : tentative + 1, revu demain)')
    if actus:
        print('Actualités possibles (à reprendre dans actu_<page> après lecture, en tête de liste) :')
        for k, t, url in actus: print('  %s : %s (%s)' % (k, t, url))
    if ecrire:
        open(os.path.join(ROOT, 'data.json'), 'w', encoding='utf-8').write(json.dumps(o, indent=0, ensure_ascii=False))
        open(os.path.join(ROOT, 'donnees', 'calendrier.json'), 'w', encoding='utf-8').write(json.dumps(cal, ensure_ascii=False, indent=1) + ('\n' if s.endswith('\n') else ''))
        print('Écrit : data.json et donnees/calendrier.json.')
    sys.exit(1 if erreurs else 0)


if __name__ == '__main__':
    main()
