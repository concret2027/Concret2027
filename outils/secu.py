#!/usr/bin/env python3
"""Déficit de la Sécurité sociale, lu à la source officielle : le dernier rapport de la Commission des comptes
de la Sécurité sociale (CCSS), publié sur securite-sociale.fr au printemps (comptes clos de l'année précédente)
et en septembre-octobre (avec le projet de budget de la Sécurité sociale).

  python3 outils/secu.py                 lit le dernier rapport et le compare à data.json, sans rien écrire
  python3 outils/secu.py --ecrire        ajoute les années closes absentes de data.json, recalcule le % du PIB
                                         (Eurostat) et met à jour l'entrée san_secu du calendrier
  python3 outils/secu.py --rapport URL   lit ce rapport-là au lieu du plus récent

Lignes lues, dans l'annexe « Tableaux des charges et produits », tableau « Charges nettes, produits nets et soldes
des régimes de base, par branche » (en M€) : bloc Maladie, ligne Solde (Assurance maladie) ; bloc ROBSS+FSV,
ligne Solde (toute la Sécurité sociale : régimes de base et Fonds de solidarité vieillesse).
Une année déjà en base n'est jamais réécrite : si le rapport l'a révisée, la révision est signalée.
Code de sortie 1 si le rapport est introuvable ou illisible (rien n'est écrit)."""
import json, os, re, subprocess, sys, tempfile, urllib.parse
from datetime import date

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
LISTE = 'https://www.securite-sociale.fr/home/la-secu-en-detail/comptes-statistiques-et-etudes-de-la-s%C3%A9curit%C3%A9-sociale/rapports-a-la-commission-des-comptes-de-la-securite-sociale.html'
SITE = 'https://www.securite-sociale.fr'
MOIS = ['janvier', 'fevrier', 'mars', 'avril', 'mai', 'juin', 'juillet', 'aout', 'septembre', 'octobre', 'novembre', 'decembre']
MOIS_FR = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
PIB = 'https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nama_10_gdp?geo=FR&na_item=B1GQ&unit=CP_MEUR&sinceTimePeriod=2000&format=JSON'


def get(url):
    # curl plutôt qu'urllib : il suit le proxy et les certificats de l'environnement de la tâche planifiée.
    r = subprocess.run(['curl', '-sSfL', '--retry', '3', '--max-time', '180', '-A', 'Mozilla/5.0 (concret2027.fr)', url], capture_output=True)
    if r.returncode:
        raise IOError('téléchargement impossible (%s) : %s' % (url, r.stderr.decode('utf-8', 'replace').strip()))
    return r.stdout


def sans_accent(s):
    return s.lower().translate(str.maketrans('éèêëàâäôöûüùîïç', 'eeeeaaaoouuuiic'))


def dernier_rapport():
    """Le rapport CCSS le plus récent de la page officielle : (année, mois, url)."""
    html = get(LISTE).decode('utf-8', 'replace')
    best = None
    for h in set(re.findall(r'href="([^"]+\.pdf)"', html)):
        nom = sans_accent(urllib.parse.unquote(h))
        m = re.search(r'/ccss/(20\d\d)/', nom)
        if not m or re.search(r'mensuel|point_d|brochure|chiffres', nom):
            continue
        fichier = nom.rsplit('/', 1)[-1]
        mois = max([i + 1 for i, x in enumerate(MOIS) if x in fichier or (x == 'septembre' and 'sept' in fichier)] or [0])
        cle = (int(m.group(1)), mois, urllib.parse.urljoin(SITE, h))
        if best is None or cle[:2] > best[:2]:
            best = cle
    return best


def lire(url):
    """Années closes du tableau des régimes de base : {année: (maladie M€, ROBSS+FSV M€)} et années prévues."""
    with tempfile.TemporaryDirectory() as t:
        pdf = os.path.join(t, 'r.pdf')
        open(pdf, 'wb').write(get(url))
        txt = subprocess.run(['pdftotext', '-layout', pdf, '-'], capture_output=True, text=True).stdout
    L = txt.split('\n')
    debut = next((i for i, l in enumerate(L) if re.search(r'soldes des r.gimes de base, par branche', l) and re.search(r'\(20\d\d-20\d\d', ' '.join(L[i:i + 2]))), None)
    if debut is None:
        raise ValueError('tableau « soldes des régimes de base, par branche » introuvable')
    entete = next((l for l in L[debut + 1:debut + 8] if len(re.findall(r'20\d\d', l)) >= 3), None)
    if entete is None:
        raise ValueError('ligne des années du tableau introuvable')
    ans = [(int(a), bool(p)) for a, p in re.findall(r'(20\d\d)\s*(\(\s*p\s*\))?', entete)]
    bloc = L[debut:debut + 90]
    serre = [re.sub(r'\s', '', l) for l in bloc]

    def solde(nom):
        i = next((i for i, s in enumerate(serre) if s == nom), None)
        j = next((j for j in range(i + 1, min(i + 20, len(serre))) if serre[j].startswith('Solde')), None) if i is not None else None
        if j is None:
            raise ValueError('bloc %s ou sa ligne Solde introuvable dans le tableau' % nom)
        champs = [re.sub(r'\s', '', x) for x in re.split(r'\s{2,}', re.sub(r'^\s*S\s*old\s*e', '', bloc[j]).strip())]
        v = [int(x.replace('−', '-')) for x in champs if re.fullmatch(r'[-−]?\d+', x.replace('−', '-'))]
        if len(v) != len(ans):
            raise ValueError('ligne Solde du bloc %s : %d valeurs pour %d années' % (nom, len(v), len(ans)))
        return v
    mal, tot = solde('Maladie'), solde('ROBSS+FSV')
    clos = {a: (mal[k], tot[k]) for k, (a, p) in enumerate(ans) if not p}
    return clos, [a for a, p in ans if p]


def pib():
    d = json.loads(get(PIB))
    t, v = d['dimension']['time']['category']['index'], d['value']
    return {int(y): v[str(i)] for y, i in t.items() if str(i) in v}


def main():
    a = sys.argv[1:]
    ecrire = '--ecrire' in a
    try:
        if '--rapport' in a:
            url = a[a.index('--rapport') + 1]
            nom = sans_accent(urllib.parse.unquote(url))
            an = int(re.search(r'/ccss/(20\d\d)/', nom).group(1))
            mois = max([i + 1 for i, x in enumerate(MOIS) if x in nom.rsplit('/', 1)[-1]] or [0])
        else:
            an, mois, url = dernier_rapport()
        clos, prev = lire(url)
    except Exception as e:
        print('Sécurité sociale ✗ rapport de la Commission des comptes illisible : %s. Rien écrit.' % e)
        sys.exit(1)
    lib = (MOIS_FR[mois - 1] + ' ' if mois else '') + str(an)
    print('Rapport de la Commission des comptes de la Sécurité sociale, %s : %s' % (lib, url))
    print('Années closes : %s ; prévisions (non retenues) : %s' % (', '.join(map(str, sorted(clos))), ', '.join(map(str, prev)) or 'aucune'))
    o = json.load(open(os.path.join(ROOT, 'data.json'), encoding='utf-8'))
    c = o['series']['sante']['C']['secu']
    nouveaux = []
    for y in sorted(clos):
        m, t = round(clos[y][0] / 1000, 1), round(clos[y][1] / 1000, 1)
        if y in c['y']:
            i = c['y'].index(y)
            if (c['md'][i], c['tot'][i]) != (m, t):
                print('- %d : révisé par ce rapport (maladie %s, total %s Md€) ; gardé tel que publié (maladie %s, total %s), lu dans le rapport de %s.' % (y, m, t, c['md'][i], c['tot'][i], c['rap'][str(y)][0]))
            else:
                print('- %d : identique (maladie %s, total %s Md€).' % (y, m, t))
        else:
            nouveaux.append((y, m, t))
            print('- %d : NOUVEAU, maladie %s Md€, toute la Sécurité sociale %s Md€.' % (y, m, t))
    if not ecrire:
        print('Rien écrit (relancer avec --ecrire pour ajouter les années nouvelles).' if nouveaux else 'data.json est à jour.')
        return
    g = pib()
    for y, m, t in nouveaux:
        if y != c['y'][-1] + 1:
            print('Sécurité sociale ✗ %d ne suit pas la dernière année en base (%d) : rien écrit.' % (y, c['y'][-1]))
            sys.exit(1)
        c['y'].append(y); c['md'].append(m); c['tot'].append(t); c['fr'].append(None)
        c['rap'][str(y)] = [lib, url]
    # % du PIB recalculé sur le PIB le plus récent d'Eurostat (les dernières années sont provisoires).
    c['fr'] = [round(m * 1000 / g[y] * 100, 2) if y in g and m is not None else f for y, m, f in zip(c['y'], c['md'], c['fr'])]
    open(os.path.join(ROOT, 'data.json'), 'w', encoding='utf-8').write(json.dumps(o, indent=0, ensure_ascii=False))
    cal = json.load(open(os.path.join(ROOT, 'donnees/calendrier.json'), encoding='utf-8'))
    e = next(x for x in cal['indicateurs'] if x['id'] == 'san_secu')
    auj = date.today()
    e['derniere_donnee'] = str(c['y'][-1])
    e['derniere_verification'] = auj.isoformat()
    # Le rapport de printemps (comptes clos) sort entre mai et juillet selon les années : tant qu'il n'est pas là,
    # on repasse tous les quinze jours ; une fois lu, on attend celui d'octobre (révisions), puis le printemps suivant.
    if nouveaux:
        e['prochaine_verification'] = ('%d-10-01' % auj.year) if auj.month < 10 else ('%d-05-15' % (auj.year + 1))
    elif 4 <= auj.month <= 9:
        e['prochaine_verification'] = date.fromordinal(auj.toordinal() + 14).isoformat()
    else:
        e['prochaine_verification'] = '%d-05-15' % (auj.year + (1 if auj.month >= 10 else 0))
    open(os.path.join(ROOT, 'donnees/calendrier.json'), 'w', encoding='utf-8').write(json.dumps(cal, indent=1, ensure_ascii=False))
    print('Écrit : %s ; %% du PIB recalculé (Eurostat) ; prochaine vérification le %s.' % (', '.join(str(n[0]) for n in nouveaux) or 'aucune année nouvelle', e['prochaine_verification']))


if __name__ == '__main__':
    main()
