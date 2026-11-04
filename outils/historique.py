#!/usr/bin/env python3
"""Sondages de premier tour des campagnes 2016-2017 et 2021-2022, pour comparer la campagne en cours (Baromètre).

Sources, lues par l'outil :
- les listes de sondages de Wikipédia en français (« Liste de sondages sur l'élection présidentielle française de 2017 »,
  « … de 2022 »), wikitexte brut, chaque sondage avec le lien vers son rapport ou sa notice ;
- pour 2022, contre-vérification avec le jeu de données ouvert NSPPolls (github.com/nsppolls/nsppolls), recueilli sondage
  par sondage : la moyenne des hypothèses de Le Pen et de Mélenchon doit être la même (à 0,3 point près) dans au moins
  85 % des sondages présents dans les deux, sinon l'outil s'arrête ;
- les résultats officiels du premier tour, lus dans la déclaration du Conseil constitutionnel (voix de chaque candidat
  rapportées aux suffrages exprimés).

Même règle que pour 2027 : pour chaque sondage, la moyenne des hypothèses où le candidat figure ; un institut dont les
terrains se chevauchent (rolling) ne compte qu'une vague par période de terrain sans chevauchement.

python3 outils/historique.py            compare avec donnees/sondages_passes.json
python3 outils/historique.py --ecrire   écrit donnees/sondages_passes.json
(dépendance : pip install wikitextparser)
"""
import csv, datetime as D, html, io, json, os, re, sys, time, urllib.request
from collections import defaultdict

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import historique_wp as WP  # noqa: E402

RACINE = os.path.dirname(ICI)
SORTIE = os.path.join(RACINE, 'donnees', 'sondages_passes.json')
UA = {'User-Agent': 'Concret/1.0 (https://concret2027.fr)'}
# Les candidats testés pour 2027 (au moins 10 sondages) qui l'ont aussi été en 2016-2017 ou en 2021-2022.
CANDIDATS = ['Le Pen', 'Mélenchon', 'Zemmour', 'Dupont-Aignan', 'Roussel', 'Arthaud', 'Hollande']
NOMS = {'Marine Le Pen': 'Le Pen', 'Jean-Luc Mélenchon': 'Mélenchon', 'Nicolas Dupont-Aignan': 'Dupont-Aignan',
        'Nathalie Arthaud': 'Arthaud', 'Fabien Roussel': 'Roussel', 'Éric Zemmour': 'Zemmour', 'Eric Zemmour': 'Zemmour',
        'François Hollande': 'Hollande'}
CAMPAGNES = [
    {'annee': 2017, 'premier_tour': '2017-04-23', 'wp': "Liste_de_sondages_sur_l'élection_présidentielle_française_de_2017",
     'cc': 'https://www.conseil-constitutionnel.fr/decision/2017/2017169PDR.htm', 'decision': 'Décision n° 2017-169 PDR du 26 avril 2017',
     'second_tour': '2017-05-07', 'cc2': 'https://www.conseil-constitutionnel.fr/decision/2017/2017171PDR.htm', 'decision2': 'Décision n° 2017-171 PDR du 10 mai 2017'},
    {'annee': 2022, 'premier_tour': '2022-04-10', 'wp': "Liste_de_sondages_sur_l'élection_présidentielle_française_de_2022",
     'cc': 'https://www.conseil-constitutionnel.fr/decision/2022/2022195PDR.htm', 'decision': 'Décision n° 2022-195 PDR du 13 avril 2022',
     'second_tour': '2022-04-24', 'cc2': 'https://www.conseil-constitutionnel.fr/decision/2022/2022197PDR.htm', 'decision2': 'Décision n° 2022-197 PDR du 27 avril 2022'},
]
NSP = 'https://raw.githubusercontent.com/nsppolls/nsppolls/master/presidentielle.csv'
MOIS_AVANT = 24  # on garde les sondages des 24 mois avant le premier tour


def lire(url, essais=4):
    for k in range(essais):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:  # noqa: BLE001
            if k == essais - 1: raise
            time.sleep(5 * (k + 1))


def institut(s):
    s = s.lower()
    for k, v in (('ifop', 'Ifop'), ('ipsos', 'Ipsos'), ('elabe', 'Elabe'), ('opinionway', 'OpinionWay'), ('opinion way', 'OpinionWay'),
                 ('harris', 'Harris Interactive'), ('odoxa', 'Odoxa'), ('bva', 'BVA'), ('kantar', 'Kantar'), ('sofres', 'Kantar'),
                 ('yougov', 'YouGov'), ('cluster', 'Cluster17'), ('csa', 'CSA'), ('dedicated', 'Dedicated Research'), ('viavoice', 'Viavoice')):
        if k in s: return v
    return re.sub(r'\s+', ' ', s).strip().title()


def sondages(lignes):
    by = defaultdict(list)
    for r in lignes:
        by[(institut(r['institut']), r['fin'], r['echantillon'])].append(r)
    polls = []
    for (i, fin, ech), rows in by.items():
        sc = defaultdict(list)
        for r in rows:
            for c, v in r['scores'].items():
                c = NOMS.get(c, c)
                if c in CANDIDATS: sc[c].append(v)
        if not sc: continue
        polls.append({'institut': i, 'debut': min(r['debut'] for r in rows), 'fin': fin, 'echantillon': ech,
                      'scores': {c: round(sum(v) / len(v), 2) for c, v in sc.items()}, 'url': rows[0]['url']})
    polls.sort(key=lambda p: (p['institut'], p['fin']))
    garde, ecartes, der = [], 0, {}
    for p in polls:
        d = der.get(p['institut'])
        if d and p['debut'] <= d['fin']: ecartes += 1; continue
        der[p['institut']] = p; garde.append(p)
    garde.sort(key=lambda p: p['fin'])
    return garde, ecartes


def resultats(url, second=False):
    t = html.unescape(re.sub(r'<[^>]+>', ' ', lire(url))); t = re.sub(r'\s+', ' ', t)
    if second: i = t.find('Les résultats du second tour'); t = t[i:t.find('Ainsi', i)]
    else: i = t.find('Article 1'); t = t[i:t.find('Article 2', i)]
    ex = int(re.sub(r'\D', '', re.search(r'Suffrages exprimés : ([\d  ]+)', t).group(1)))
    out = {}
    for m in re.finditer(r"(?:M\.|Mme) ([^:]+?) : ([\d  ]+)", t):
        n = m.group(1).strip()
        n = ' '.join(w.capitalize() if w.isupper() else w for w in n.split())
        n = {'Le Pen': 'Le Pen'}.get(n, n)
        for full, court in NOMS.items():
            if full.lower() == n.lower().replace('é', 'é'): n = court
        voix = int(re.sub(r'\D', '', m.group(2)))
        nom = next((c for c in CANDIDATS + ['Macron'] if c.lower() in n.lower()), None)
        if nom: out[nom] = round(100 * voix / ex, 2)
    return out, ex


ADV = {'Bruno Le Maire': 'Le Maire', 'Jean-Luc Mélenchon': 'Mélenchon', 'Emmanuel Macron': 'Macron'}


def duels(lignes):
    """Second tour : les duels avec Marine Le Pen, score de Le Pen et de son adversaire, un par sondage et par duel."""
    by = defaultdict(list)
    for r in lignes:
        if len(r['scores']) != 2 or 'Marine Le Pen' not in r['scores']: continue
        adv = [c for c in r['scores'] if c != 'Marine Le Pen'][0]
        by[(institut(r['institut']), r['fin'], r['echantillon'], ADV.get(adv, adv.split()[-1]))].append(r)
    polls = []
    for (i, fin, ech, adv), rows in by.items():
        v = [r['scores']['Marine Le Pen'] for r in rows]
        polls.append({'institut': i, 'debut': min(r['debut'] for r in rows), 'fin': fin, 'echantillon': ech, 'adversaire': adv,
                      'score': round(sum(v) / len(v), 2), 'url': rows[0]['url']})
    polls.sort(key=lambda p: (p['institut'], p['adversaire'], p['fin']))
    garde, ecartes, der = [], 0, {}
    for p in polls:
        d = der.get((p['institut'], p['adversaire']))
        if d and p['debut'] <= d['fin']: ecartes += 1; continue
        der[(p['institut'], p['adversaire'])] = p; garde.append(p)
    garde.sort(key=lambda p: p['fin'])
    return garde, ecartes


def controle_nsp(polls):
    rows = [x for x in csv.DictReader(io.StringIO(lire(NSP))) if x['tour'] == 'Premier tour']
    N = defaultdict(list)
    for x in rows:
        c = NOMS.get(x['candidat'])
        if c in ('Le Pen', 'Mélenchon'): N[(institut(x['nom_institut']), x['fin_enquete'], c)].append(float(x['intentions']))
    ok = ko = 0
    for p in polls:
        for c in ('Le Pen', 'Mélenchon'):
            v = N.get((p['institut'], p['fin'], c))
            if c not in p['scores'] or not v: continue
            if abs(sum(v) / len(v) - p['scores'][c]) <= 0.3: ok += 1
            else: ko += 1
    return ok, ko


def main():
    ecrire = '--ecrire' in sys.argv
    out = {'releve': D.date.today().isoformat(), 'candidats': CANDIDATS, 'campagnes': [],
           'methode': "Pour chaque sondage, moyenne des hypothèses où le candidat figure ; un institut dont les terrains se chevauchent (rolling) ne compte qu'une vague par période de terrain sans chevauchement."}
    for c in CAMPAGNES:
        src = lire('https://fr.wikipedia.org/w/index.php?title=' + urllib.parse.quote(c['wp']) + '&action=raw')
        tmp = os.path.join(os.environ.get('TMPDIR', '/tmp'), 'concret_wp_%d.wiki' % c['annee'])
        open(tmp, 'w', encoding='utf-8').write(src)
        lignes, rejets = WP.main(tmp, c['annee'])
        polls, ecartes = sondages(lignes)
        t1 = D.date.fromisoformat(c['premier_tour'])
        debut = (t1 - D.timedelta(days=int(MOIS_AVANT * 30.44))).isoformat()
        polls = [p for p in polls if debut <= p['fin'] < c['premier_tour']]
        res, ex = resultats(c['cc'])
        print('%d : %d lignes lues (%d écartées : %s), %d sondages gardés depuis le %s (%d vagues de rolling écartées) ; résultats : %s'
              % (c['annee'], len(lignes), len(rejets), ', '.join(sorted({r[0] for r in rejets})) or '—', len(polls), debut, ecartes,
                 ', '.join('%s %.2f %%' % kv for kv in res.items())))
        camp = {'annee': c['annee'], 'premier_tour': c['premier_tour'],
                'source': {'titre': 'Wikipédia, ' + c['wp'].replace('_', ' '), 'url': 'https://fr.wikipedia.org/wiki/' + urllib.parse.quote(c['wp'])},
                'resultats': res, 'resultats_source': {'titre': 'Conseil constitutionnel, ' + c['decision'], 'url': c['cc'], 'exprimes': ex},
                'sondages': [{'fin': p['fin'], 'institut': p['institut'], 'echantillon': p['echantillon'], 'scores': p['scores'], 'url': p['url']} for p in polls]}
        l2, r2 = WP.main(tmp, c['annee'], 'second', 2)
        d2, e2 = duels(l2)
        t2 = D.date.fromisoformat(c['second_tour'])
        d2 = [p for p in d2 if (t2 - D.timedelta(days=int(MOIS_AVANT * 30.44))).isoformat() <= p['fin'] < c['second_tour']]
        res2, ex2 = resultats(c['cc2'], True)
        from collections import Counter
        print('   second tour : %d duels avec Le Pen (%s), %d vagues de rolling écartées ; résultat : Le Pen %.2f %%, Macron %.2f %%'
              % (len(d2), ', '.join('%s %d' % kv for kv in Counter(p['adversaire'] for p in d2).most_common()), e2, res2.get('Le Pen', 0), res2.get('Macron', 0)))
        camp['second_tour'] = c['second_tour']
        camp['duels'] = [{'fin': p['fin'], 'institut': p['institut'], 'echantillon': p['echantillon'], 'adversaire': p['adversaire'], 'score': p['score'], 'url': p['url']} for p in d2]
        camp['resultats_t2'] = res2
        camp['resultats_t2_source'] = {'titre': 'Conseil constitutionnel, ' + c['decision2'], 'url': c['cc2'], 'exprimes': ex2}
        if c['annee'] == 2022:
            ok, ko = controle_nsp(polls)
            part = ok / max(1, ok + ko)
            print('   contre-vérification NSPPolls : %d sondages concordants, %d différents (%.0f %%)' % (ok, ko, 100 * part))
            if part < 0.85: sys.exit('Contre-vérification insuffisante : rien n’est écrit.')
            camp['controle'] = {'source': 'NSPPolls', 'url': 'https://github.com/nsppolls/nsppolls', 'concordants': ok, 'differents': ko}
        out['campagnes'].append(camp)
    ancien = json.load(open(SORTIE, encoding='utf-8')) if os.path.exists(SORTIE) else None
    if ancien:
        for a, b in zip(ancien['campagnes'], out['campagnes']):
            if a['sondages'] != b['sondages'] or a['resultats'] != b['resultats']: print('%d : changé depuis le relevé du %s' % (b['annee'], ancien['releve']))
    if ecrire:
        json.dump(out, open(SORTIE, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        print('Écrit :', os.path.relpath(SORTIE, RACINE), os.path.getsize(SORTIE), 'octets')


if __name__ == '__main__':
    import urllib.parse  # noqa: E402
    main()
