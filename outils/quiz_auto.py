#!/usr/bin/env python3
"""Questions du jour des pages (series.<page>.QUIZ), calculées à partir de leurs séries, sans qu'une question revienne.

Chaque page pose une question par jour (sur la page, dans le quiz et dans le compteur, le même tirage : QUIZ[jour % longueur]).
  - Les questions écrites à la main sont dans series.<page>.QUIZ_ECRITES (la tâche quotidienne y met à jour leurs chiffres).
  - Les questions calculées viennent des séries de la page et des 27 pays de l'UE (donnees/pays.json, lus aux mêmes sources
    par outils/pays.py), pour chaque courbe et chaque année définitive (sans année estimée ni provisoire) : le chiffre de la
    France ; le pays le plus haut, le plus bas, le plus proche de la France ; le nombre de pays au-dessus de la France ; la
    France face à un autre pays ; plus haut ou plus bas qu'il y a cinq ou dix ans ; l'année du plus haut et du plus bas (sans
    traverser un changement de méthode). Plusieurs milliers de questions, toutes différentes.
  - donnees/quiz_plan.json garde, pour chaque page, le jour où chaque question a été posée : une question déjà posée ne
    revient pas tant qu'il en reste une jamais posée. Les questions écrites à la main encore jamais posées passent en premier
    (une tous les trois jours au plus).
  - series.<page>.QUIZ est la fenêtre des 31 jours à venir : la question du jour d est en position d % 31. La question
    d'aujourd'hui ne change pas d'un passage à l'autre ; les sujets (courbes, ou courbes d'un même sujet comme les
    obligations de quitter le territoire) à tour de rôle, le moins récemment posé d'abord, jamais le même moins de six jours
    après, et si possible pas deux fois de suite la même forme de question.
Lancé par outils/controle.js verifier, avant la validation. Jamais de saisie à la main dans QUIZ.
  python3 outils/quiz_auto.py                                   compare
  python3 outils/quiz_auto.py --ecrire                          écrit data.json et donnees/quiz_plan.json
  python3 outils/quiz_auto.py --ecrire --changer securite,vie   remplace aussi la question d'aujourd'hui de ces pages
"""
import hashlib, json, os, re, sys
from datetime import date, datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UE = ['BE', 'BG', 'CZ', 'DK', 'DE', 'EE', 'IE', 'EL', 'ES', 'FR', 'HR', 'IT', 'CY', 'LV', 'LT', 'LU', 'HU', 'MT', 'NL', 'AT', 'PL', 'PT', 'RO', 'SI', 'SK', 'FI', 'SE']
MIN = 20          # pays de l'UE avec un chiffre, pour une question sur les pays
L = 31            # longueur de la fenêtre QUIZ
ECART_COURBE = 6  # jours avant de revenir sur la même courbe
ECART_FAMILLE = 120  # jours avant de reposer la même question pour une autre année avec la même réponse
ECART_FORME = 30  # jours avant de reposer la même forme de question sur la même courbe (autre année, autre réponse)
PAGES = ['finances', 'education', 'sante', 'securite', 'defense', 'vie', 'demographie']
# Courbes dont l'ancre sur la page n'est pas « ch-<clé> ».
ANCRE = {'demographie.nes_hue': 'ch-neshue', 'demographie.M.departs': 'ch-oq', 'demographie.M.oqtf': 'ch-oqtf'}
# Finances et Éducation : leurs séries n'ont ni intitulé ni années dans data.json (années fixes, comme sur leurs pages).
# Dette, dépense et prélèvements ; les autres courbes et repères de la page sont ajoutés dans indicateurs().
FIN = [('dette', 'Dette publique', '% du PIB', None), ('dep', 'Dépense publique', '% du PIB', 'dépense de toutes les administrations publiques (État, collectivités, Sécurité sociale)'),
       ('po', 'Impôts et cotisations', '% du PIB', 'impôts et cotisations sociales prélevés par les administrations publiques (prélèvements obligatoires)')]
EDU = [('el', 'Décrochage', '% des 18-24 ans', "jeunes de 18 à 24 ans qui ont quitté l'école sans diplôme du secondaire (ni bac, ni CAP, ni BEP) et ne suivent aucune formation"),
       ('ne', 'Ni emploi ni études', '% des 15-29 ans', "jeunes de 15 à 29 ans qui ne travaillent pas, n'étudient pas et ne suivent aucune formation"),
       ('te', 'Diplômés du supérieur', '% des 25-34 ans', None),
       ('yu', 'Chômage des 15-24 ans', '%', 'part des 15-24 ans sans emploi qui en cherchent un, parmi ceux qui travaillent ou cherchent un emploi')]
PISA = [('m', 'PISA, mathématiques', 'score moyen des élèves de 15 ans', 'ch-pisa-m'), ('r', 'PISA, compréhension de l\'écrit', 'score moyen des élèves de 15 ans', 'ch-pisa-r'),
        ('s', 'PISA, sciences', 'score moyen des élèves de 15 ans', 'ch-pisa-s')]
AFFN = {'depense': 'dep', 'detenus': 'det', 'juges': 'jug', 'police': 'pol', 'medic': 'med'}


def lire(f):
    with open(os.path.join(ROOT, f), encoding='utf-8') as fh:
        return json.load(fh)


def nf(v, d):
    s = ('{:,.' + str(d) + 'f}').format(abs(v)).replace(',', '\u202f').replace('.', ',')
    return ('−' if v < 0 and float(s.replace('\u202f', '').replace(',', '.')) != 0 else '') + s


def h(t):
    return hashlib.md5(t.encode('utf-8')).hexdigest()


# Intitulés réécrits pour une question, quand « intitulé, unité » ne se lit pas (l'unité est une phrase entière).
TITRE_QUIZ = {'vie.s80': 'Écart de revenu entre les plus aisés et les plus modestes',
              'sante.secu': "Solde de l'Assurance maladie (négatif : déficit), % du PIB",
              'vie.rev': 'Revenu des ménages par habitant, hors inflation (100 en 2008)'}
# Et l'explication de son chiffre, affichée sous la question.
D_QUIZ = {'vie.rev': "Un indice : 100 = le niveau de 2008 dans chaque pays ; 110 = 10 % de plus qu'en 2008, hors inflation.",
          'vie.s80': 'Le chiffre dit combien de fois plus de revenu ont les 20 % les plus aisés que les 20 % les plus modestes (4 = quatre fois plus).'}


def titre(x):
    if x.get('cle') in TITRE_QUIZ:
        return re.sub(r'(\d)-(\d)', '\\1\u2011\\2', TITRE_QUIZ[x['cle']])
    # « 15-29 ans » ne se coupe pas en fin de ligne (trait d'union insécable).
    # Pas d'unité répétée quand elle redit l'intitulé (« Enfants par femme »).
    u = '' if not x['u'] or x['u'].lower() == x['l'].lower() else (' (%)' if x['u'] == '%' else ', ' + x['u'])
    return re.sub(r'(\d)-(\d)', '\\1\u2011\\2', x['l'] + u)


def unite(x):
    # Après un chiffre : « % » (et « du PIB ») ; les autres unités sont déjà dans la question.
    return (' % du PIB' if 'PIB' in x['u'] else ' %') if x['u'].startswith('%') else ''


def court(src):
    return re.split(r' \(|;|,', src or 'Eurostat')[0].strip() or 'Eurostat'


def val(T, i):
    return T[i] if T is not None and 0 <= i < len(T) else None


def indicateurs(S, pg, html):
    """Chaque courbe de la page : intitulé, unité, années, France, UE, Allemagne, Espagne, changements de méthode, lien."""
    out = []
    ser = S.get(pg, {})
    base = lambda **k: dict({'est': {}, 'prov': {}, 'br': {}, 'dec': 1, 'src': 'Eurostat', 'ex': None, 'ue': [], 'de': [], 'es': []}, **k)
    if pg in ('finances', 'education'):
        D, y0, tab = (ser.get('D', {}), 1995, FIN) if pg == 'finances' else (ser.get('S', {}), 2002, EDU)
        for k, l, u, ex in tab:
            c = D.get(k)
            if not c or not c.get('fr'):
                continue
            out.append(base(cle=pg + ('.D.' if pg == 'finances' else '.S.') + k, l=l, u=u, ex=ex, y=list(range(y0, y0 + len(c['fr']))), fr=c['fr'],
                            ue=c.get('eu') or [], de=c.get('de') or [], es=c.get('es') or [], br={str(b): 1 for b in (c.get('br') or [])}, v='ch-' + k))
        if pg == 'finances':
            # Les autres courbes et repères de la page (toile « La France et ses voisins », retraites, taux à 10 ans) : mêmes
            # chiffres que la page, mêmes séries des autres pays (donnees/pays.json) quand elles existent.
            an = lambda y0, n: list(range(y0, y0 + n))
            Dd = ser.get('D', {}).get('deficit') or {}
            if Dd.get('fr'):
                out.append(base(cle='finances.D.deficit', l='Solde public (négatif : déficit)', u='% du PIB', y=an(1995, len(Dd['fr'])), fr=Dd['fr'], ue=Dd.get('eu') or [],
                                de=Dd.get('de') or [], es=Dd.get('es') or [], v='ch-deficit',
                                ex="recettes moins dépenses de toutes les administrations publiques ; un chiffre négatif est un déficit"))
            PI = ser.get('PIB') or {}
            if PI.get('fr'):
                out.append(base(cle='finances.PIB', l='Richesse par habitant', u='en dollars', dec=0, src='Banque mondiale', y=an(1990, len(PI['fr'])), fr=PI['fr'],
                                ue=PI.get('eu') or [], de=PI.get('de') or [], es=PI.get('es') or [], v='pib-chart',
                                ex="PIB par habitant, en dollars de 2021, hors inflation et corrigé des écarts de prix entre pays (parité de pouvoir d'achat)"))
            X94, X95 = ser.get('X94') or {}, ser.get('X95') or {}
            if X94.get('uFr'):
                out.append(base(cle='finances.X94.u', l='Chômage, moyenne de l\'année', u='%', src='Banque mondiale', y=an(1994, len(X94['uFr'])), fr=X94['uFr'],
                                ue=X94.get('uEu') or [], es=X94.get('uEs') or [], v='toile'))
            if X95.get('iFr'):
                out.append(base(cle='finances.X95.i', l='Intérêts de la dette', u='% du PIB', y=an(1995, len(X95['iFr'])), fr=X95['iFr'], ue=X95.get('iEu') or [],
                                es=X95.get('iEs') or [], v='toile', ex="intérêts payés chaque année par toutes les administrations publiques sur leur dette"))
            R = ser.get('retraites') or {}
            if R.get('fr') and R.get('annees'):
                out.append(base(cle='finances.retraites', l='Dépenses publiques de retraite', u='% du PIB', y=R['annees'], fr=R['fr'], ue=R.get('eu') or [],
                                de=R.get('de') or [], v='ch-retraites', ex="pensions de vieillesse versées par les administrations publiques"))
            Y = ser.get('Y10') or {}
            if Y.get('fr'):
                out.append(base(cle='finances.Y10', l='Taux d\'emprunt de l\'État à 10 ans, moyenne de l\'année', u='%', dec=2, src='Eurostat', y=an(1994, len(Y['fr'])),
                                fr=Y['fr'], de=Y.get('de') or [], es=Y.get('es') or [], v='rate-num'))
        if pg == 'education':
            SP, AR, EQ = ser.get('SP') or {}, ser.get('ARWU') or {}, ser.get('EQ') or {}
            if SP.get('fr'):
                out.append(base(cle='education.dep', l="Dépense d'éducation", u='% du PIB', y=list(range(2002, 2002 + len(SP['fr']))), fr=SP['fr'], ue=SP.get('eu') or [],
                                de=SP.get('de') or [], es=SP.get('es') or [], v='ch-dep', ex="dépense publique pour l'éducation, de l'école maternelle à l'université"))
            if AR.get('fr') and AR.get('y'):
                out.append(base(cle='education.arwu', l='Universités dans le top 100 mondial (classement de Shanghai)', u='', dec=0, src='Classement de Shanghai',
                                y=AR['y'], fr=AR['fr'], de=AR.get('de') or [], es=AR.get('es') or [], v='ch-arwu'))
            if EQ.get('fr') and EQ.get('y'):
                out.append(base(cle='education.eq', l="Écart de score PISA entre élèves favorisés et défavorisés", u='points', dec=0, src='OCDE', y=EQ['y'], fr=EQ['fr'],
                                v='ch-eq', ex="écart de score en mathématiques entre les élèves du quart le plus favorisé et ceux du quart le plus défavorisé"))
            for k, l, u, v in PISA:
                c = (ser.get('PI') or {}).get(k)
                if c and c.get('y') and c.get('fr'):
                    out.append(base(cle='education.PI.' + k, l=l, u=u, y=c['y'], fr=c['fr'], ue=c.get('ue_calc') or [], de=c.get('de') or [], es=c.get('es') or [],
                                    dec=0, src='OCDE', v=v))
        return out
    for groupe, pre in (('C', ''), ('AFF', 'a-'), ('M', 'M.')):
        for k, c in (ser.get(groupe) or {}).items():
            if c.get('regle') == 'composite':
                # Un programme (vaccins, dépistages) : une courbe par vaccin ou dépistage, lien vers la courbe du programme.
                for sk, sc in (c.get('sous') or {}).items():
                    if sc.get('y') and sc.get('fr'):
                        out.append(base(cle=pg + '.' + k + '-' + sk, l=sc.get('l'), u=sc.get('unite', ''), ex=sc.get('ex'), dec=int(sc.get('dec', 1)), src=court(sc.get('sc') or sc.get('source')),
                                        y=sc['y'], fr=sc['fr'], ue=sc.get('ue') or sc.get('ue_calc') or [], de=sc.get('de') or [], es=sc.get('es') or [], v='ch-' + k))
                continue
            if not c.get('y') or not c.get('fr'):
                continue
            if pre == 'a-':
                k = AFFN.get(k, k)
                if "'ch-a-" + k + "'" not in html:
                    continue
            br = c.get('br') or {}
            out.append(base(cle=pg + '.' + pre + k, l=c.get('l'), u=c.get('unite', ''), ex=c.get('ex'), dec=int(c.get('dec', 1)), src=court(c.get('source')),
                            y=c['y'], fr=c['fr'], ue=c.get('ue') or c.get('ue_calc') or [], de=c.get('de') or [], es=c.get('es') or [],
                            est=c.get('est') or {}, prov=c.get('prov') or {}, br=br if isinstance(br, dict) else {str(b): 1 for b in br}, v=ANCRE.get(pg + '.' + pre + k, 'ch-' + ('' if pre == 'M.' else pre) + k)))
    return out


def annees(x):
    """Les années définitives de la France (indices)."""
    return [i for i, y in enumerate(x['y']) if val(x['fr'], i) is not None and str(y) not in x['est'] and str(y) not in x['prov']]


def segment(x, i, j):
    """Vrai si aucun changement de méthode n'a lieu entre les années i et j."""
    a, b = sorted((x['y'][i], x['y'][j]))
    return not any(a < int(k) <= b for k in x['br'].keys() if str(k).isdigit())


def pays_annee(x, P, i):
    s = P['series'].get(x['cle'])
    y = x['y'][i]
    if not s or y not in s.get('y', []):
        return None
    j = s['y'].index(y)
    T = []
    for g in UE:
        v = x['fr'][i] if g == 'FR' else val(x['de'], i) if g == 'DE' else val(x['es'], i) if g == 'ES' else val(s.get(g) or [], j)
        if v is not None:
            T.append((g, v))
    return T if len(T) >= MIN else None


def fabriquer(x, P, nom):
    """Toutes les questions d'une courbe."""
    Q = []
    src, T, dec, U = x['src'], titre(x), x['dec'], unite(x)
    fmt = lambda v: nf(v, dec) + U
    idxs = annees(x)

    def add(k, forme, q, o, a, e):
        Q.append({'k': x['cle'] + '|' + k, 'forme': forme, 'q': q, 'o': o, 'a': a, 'e': e, 'v': x['v']})

    for i in idxs:
        y, f = x['y'][i], x['fr'][i]
        Y = str(y)
        # 1. Le chiffre de la France : les autres réponses sont la moyenne de l'UE, l'Allemagne, l'Espagne quand elles s'écartent
        #    assez, sinon des écarts fixes.
        a = abs(f)
        if a:
            d = 0 if a >= 10 or x['dec'] == 0 else 1 if a >= 1 else 2  # un nombre entier (universités, points) reste entier
            r = lambda v: round(v, d)
            pct = x['u'].startswith('%') and 'PIB' not in x['u']
            ecart = max(0.12 * a, 10 ** -d)
            pris = [r(f)]
            ok = lambda v: all(abs(v - p) >= ecart - 1e-9 for p in pris) and (not pct or 0 <= v <= 100) and (f < 0 or v > 0)
            for w in ('ue', 'de', 'es'):
                v = val(x[w], i)
                if v is not None and len(pris) < 4 and ok(r(v)):
                    pris.append(r(v))
            for m in ((0.6, 1.4, 1.8, 0.4, 2.2) if f > 0 else (1.4, 0.6, 1.8, 0.4, 2.2)):
                if len(pris) < 4 and ok(r(f * m)):
                    pris.append(r(f * m))
            if len(pris) == 4:
                o = sorted(pris)
                reste = [('Moyenne de l\'UE', val(x['ue'], i)), ('Allemagne', val(x['de'], i)), ('Espagne', val(x['es'], i))]
                autres = ' ; '.join(n + ' : ' + fmt(v) for n, v in reste if v is not None)
                add('chiffre|' + Y, 'chiffre', T + ' : quel était le chiffre de la France en ' + Y + ' ?', [nf(v, d) + (' %' if pct else '') for v in o],
                    o.index(r(f)), fmt(f) + ' en France en ' + Y + ' (' + src + ').' + (' ' + autres + '.' if autres else ''))
        Lp = pays_annee(x, P, i)
        if not Lp:
            continue
        n = len(Lp)
        qui = ' des ' + str(n) + ' pays de l\'UE' + (' qui le publient' if n < 27 else '')
        for haut in (True, False):
            Ls = sorted(Lp, key=lambda t: -t[1] if haut else t[1])
            if Ls[0][1] == Ls[1][1]:
                continue
            sens = 'élevé' if haut else 'bas'
            k_ = 1 + sum(1 for _, v in Lp if (v > f if haut else v < f))
            pf = 'le chiffre le plus ' + sens if k_ == 1 else 'le ' + str(k_) + 'e chiffre le plus ' + sens
            p1 = Ls[0][0]
            # 2-3. Le pays le plus haut, le plus bas : les autres réponses sont les deux pays qui suivent et la France.
            o = [p1]
            for g in [Ls[1][0], Ls[2][0], 'FR', Ls[3][0]]:
                if g not in o and len(o) < 4:
                    o.append(g)
            o = sorted((nom[g] for g in o), key=lambda t: h(x['cle'] + t))
            e = nom[p1] + ' : ' + fmt(Ls[0][1]) + ' (' + Y + ', ' + src + ').'
            e += (' Ensuite : ' + nom[Ls[1][0]] + ', ' + fmt(Ls[1][1]) + '.') if p1 == 'FR' else (' France : ' + fmt(f) + ', ' + pf + qui + '.')
            add(('haut|' if haut else 'bas|') + Y, 'haut' if haut else 'bas', T + ' : quel pays de l\'UE avait le chiffre le plus ' + sens + ' en ' + Y + ' ?',
                o, o.index(nom[p1]), e)
        # 4. Combien de pays au-dessus de la France ?
        dessus = sum(1 for _, v in Lp if v > f)
        if not any(v == f for g, v in Lp if g != 'FR'):
            B = ['Aucun', 'De 1 à 5', 'De 6 à 12', '13 ou plus']
            a_ = 0 if dessus == 0 else 1 if dessus <= 5 else 2 if dessus <= 12 else 3
            top = max(Lp, key=lambda t: t[1])
            add('dessus|' + Y, 'dessus', T + ' : en ' + Y + ', combien de pays de l\'UE avaient un chiffre plus élevé que la France ?', B, a_,
                ('Aucun' if dessus == 0 else str(dessus)) + ' sur les ' + str(n) + ' pays de l\'UE' + (' qui le publient' if n < 27 else '') + ' (' + Y + ', ' + src + '). France : ' + fmt(f)
                + ('' if top[0] == 'FR' else ' ; le plus élevé : ' + nom[top[0]] + ', ' + fmt(top[1])) + '.')
        # 5. Le pays le plus proche de la France.
        dist = sorted(((abs(v - f), g, v) for g, v in Lp if g != 'FR'))
        if dist[0][0] < dist[1][0] - 1e-9 and nf(dist[0][2], dec) != nf(dist[1][2], dec):
            p1 = dist[0][1]
            autres = [dist[len(dist) // 3][1], dist[(2 * len(dist)) // 3][1], dist[-1][1]]
            o = sorted([nom[p1]] + [nom[g] for g in autres], key=lambda t: h(x['cle'] + 'p' + t))
            add('proche|' + Y, 'proche', T + ' : en ' + Y + ', quel pays de l\'UE avait le chiffre le plus proche de celui de la France ?', o, o.index(nom[p1]),
                nom[p1] + ' : ' + fmt(dist[0][2]) + ', contre ' + fmt(f) + ' en France (' + Y + ', ' + src + ').')
        # 6. La France et trois autres pays : lequel avait le chiffre le plus élevé ? (quatre réponses ; le plus élevé dépasse
        #    le deuxième d'au moins 5 %, pour que la question ne se joue pas à une décimale près).
        loin = [(g, v) for g, v in Lp if g != 'FR' and abs(v - f) >= 0.05 * max(abs(f), abs(v))]
        tires = sorted(loin, key=lambda t: h(x['cle'] + Y + t[0]))
        for n0 in range(0, min(len(tires), 9), 3):
            trio = tires[n0:n0 + 3]
            if len(trio) < 3:
                break
            groupe = [('FR', f)] + trio
            tri = sorted(groupe, key=lambda t: -t[1])
            if tri[0][1] - tri[1][1] < 0.05 * max(abs(tri[0][1]), abs(tri[1][1])):
                continue
            o = sorted([nom[g] for g, _ in groupe], key=lambda t: h(x['cle'] + Y + str(n0) + t))
            add('duel|' + Y + '|' + trio[0][0], 'duel', T + ' : en ' + Y + ', lequel de ces quatre pays avait le chiffre le plus élevé ?', o, o.index(nom[tri[0][0]]),
                ' ; '.join(nom[g] + ' : ' + fmt(v) for g, v in tri) + ' (' + Y + ', ' + src + ').')
    # 7. Plus haut ou plus bas qu'il y a cinq ou dix ans (sans traverser un changement de méthode).
    for i in idxs:
        y, f = x['y'][i], x['fr'][i]
        for recul in (5, 10):
            j = next((j for j in idxs if x['y'][j] == y - recul), None)
            if j is None or not segment(x, j, i):
                continue
            f0 = x['fr'][j]
            if abs(f - f0) < 0.03 * max(abs(f), abs(f0)) or nf(f, dec) == nf(f0, dec):
                continue
            # Quatre réponses : baisse ou hausse, de plus ou de moins de 10 % (chiffres positifs seulement ; pas trop près du seuil).
            if f <= 0 or f0 <= 0:
                continue
            pc = 100 * (f - f0) / f0
            if 7 <= abs(pc) <= 13:
                continue
            o = ['Baisse de plus de 10 %', 'Baisse de moins de 10 %', 'Hausse de moins de 10 %', 'Hausse de plus de 10 %']
            a = 0 if pc <= -10 else 1 if pc < 0 else 2 if pc < 10 else 3
            add('evol|' + str(y) + '|' + str(recul), 'evol', T + ' : entre ' + str(y - recul) + ' et ' + str(y) + ', comment le chiffre de la France a-t-il évolué ?', o, a,
                str(y - recul) + ' : ' + fmt(f0) + ' ; ' + str(y) + ' : ' + fmt(f) + ', soit ' + ('+' if pc > 0 else '−') + nf(abs(pc), 0) + ' % (France, ' + src + ').')
    # 8. L'année du plus haut et du plus bas, sur la dernière période sans changement de méthode (au moins huit années).
    if idxs:
        der = idxs[-1]
        per = [i for i in idxs if segment(x, i, der)]
        if len(per) >= 8:
            for haut in (True, False):
                vs = sorted(per, key=lambda i: -x['fr'][i] if haut else x['fr'][i])
                if nf(x['fr'][vs[0]], dec) == nf(x['fr'][vs[1]], dec):
                    continue
                ys = []
                for i in [vs[0], vs[len(vs) // 2], vs[-1], vs[(3 * len(vs)) // 4], vs[len(vs) // 4]]:
                    if str(x['y'][i]) not in ys and len(ys) < 4:
                        ys.append(str(x['y'][i]))
                if len(ys) < 4:
                    continue
                o = sorted(ys)
                y0, y1 = x['y'][per[0]], x['y'][der]
                add(('anmax|' if haut else 'anmin|') + str(y0) + '|' + str(y1), 'annee',
                    T + ' : en quelle année la France a-t-elle eu son chiffre le plus ' + ('élevé' if haut else 'bas') + ' entre ' + str(y0) + ' et ' + str(y1) + ' ?',
                    o, o.index(str(x['y'][vs[0]])), 'En ' + str(x['y'][vs[0]]) + ' : ' + fmt(x['fr'][vs[0]]) + ' (France, ' + src + ').' + ('' if vs[0] == der else ' En ' + str(y1) + ' : ' + fmt(x['fr'][der]) + '.'))
    ex = x['ex']
    mots = lambda t: set(re.findall(r"[a-zà-ÿ]{4,}", (t or '').lower()))
    d = (ex[0].upper() + ex[1:] + '.') if ex and len(mots(ex) - mots(x['l'] + ' ' + x['u'])) >= 4 else None
    d = D_QUIZ.get(x.get('cle'), d)
    if d:
        for q in Q:
            q['d'] = d
    return Q


# Un sujet = une courbe ; les courbes d'un même sujet comptent ensemble (les obligations de quitter le territoire : celles
# délivrées et les départs ; la population née à l'étranger et les étrangers), pour ne pas revenir trop souvent sur le même sujet.
SUJETS = [(re.compile(r'quitter le territoire', re.I), 'oqtf'),
          # Démographie : les personnes nées à l'étranger, nées hors de l'UE et les étrangers, un seul sujet.
          (re.compile(r"^(Personnes nées|Étrangers)", re.I), 'origine')]


def sujet(q):
    if q.get('forme') == 'main': return 'main|' + q.get('k', q['q'])
    if str(q.get('k', '')).startswith('demographie.M.'): return 'migrations'
    for rx, nom in SUJETS:
        if rx.search(q['q'].split(':')[0]): return nom
    return q.get('v') or q['q']


def famille(q):
    """La même question pour le joueur : même courbe, même forme, même bonne réponse (l'année change seule)."""
    if q.get('forme') == 'main': return 'main|' + q.get('k', q['q'])
    return '|'.join([str(q.get('v')), str(q.get('forme')), str(q['o'][q['a']]) if q.get('o') else ''])


def forme_courbe(q):
    return 'forme|' + (('main|' + q.get('k', q['q'])) if q.get('forme') == 'main' else str(q.get('v')) + '|' + str(q.get('forme')))


def jour_idx():
    d = datetime.now(ZoneInfo('Europe/Paris')).date() if ZoneInfo else date.today()
    return (d - date(2026, 1, 1)).days


def nettoie(q):
    """La question telle qu'elle va dans data.json."""
    o = {k: q[k] for k in ('q', 'o', 'a', 'e', 'v', 'd') if q.get(k) is not None}
    if q.get('auto'):
        o['auto'] = True
    return o


def main():
    ecrire = '--ecrire' in sys.argv
    changer = set(sys.argv[sys.argv.index('--changer') + 1].split(',')) if '--changer' in sys.argv else set()
    D = lire('data.json')
    P = lire('donnees/pays.json')
    S = D['series']
    fplan = os.path.join(ROOT, 'donnees', 'quiz_plan.json')
    plan = lire('donnees/quiz_plan.json') if os.path.exists(fplan) else {}
    nom = dict(P.get('noms') or {}, FR='France', DE='Allemagne', ES='Espagne')
    idx = jour_idx()
    bilan = []
    for pg in PAGES:
        ser = S.get(pg)
        if not ser:
            continue
        if pg == 'demographie':
            ser.setdefault('QUIZ_ECRITES', [])  # page sans calcul : seulement des questions sur les chiffres, aucune écrite à la main
        if not (ser.get('QUIZ') or 'QUIZ_ECRITES' in ser):
            continue
        with open(os.path.join(ROOT, pg, 'index.html'), encoding='utf-8') as fh:
            html = fh.read()
        ancien = ser.get('QUIZ') or []
        # Premier passage : les questions écrites à la main étaient dans QUIZ ; elles passent dans QUIZ_ECRITES, et comme elles
        # ont déjà toutes été posées, elles comptent comme posées.
        premier = 'QUIZ_ECRITES' not in ser
        if premier:
            ser['QUIZ_ECRITES'] = [{k: v for k, v in q.items() if k != 'auto'} for q in ancien if not q.get('auto')]
        mains = {}
        for q in ser['QUIZ_ECRITES']:
            k = 'main|' + h(q['q'])[:12]
            if len(q.get('o') or []) < 4:
                continue  # toujours quatre réponses : une question écrite à deux réponses n'est plus posée
            mains[k] = dict(q, k=k, forme='main', auto=False)
        pool = dict(mains)
        for x in indicateurs(S, pg, html):
            for q in fabriquer(x, P, nom):
                q['auto'] = True
                pool.setdefault(q['k'], q)
        etat = plan.setdefault(pg, {'poses': {}, 'jours': {}})
        poses, jours = etat['poses'], etat['jours']
        if premier:
            for k in mains:
                poses.setdefault(k, idx - 1)
        # Les questions des jours passés comptent comme posées (on garde le premier jour où elles l'ont été).
        for j, k in jours.items():
            if int(j) < idx:
                poses.setdefault(k, int(j))
        # La question d'aujourd'hui : celle déjà prévue, sinon celle en ligne (retrouvée par son texte), sauf si on la change.
        auj = jours.get(str(idx))
        if auj not in pool:
            vu = ancien[idx % len(ancien)]['q'] if ancien else None
            auj = next((k for k, q in pool.items() if q['q'] == vu), None)
        if pg in changer:
            if auj:
                poses[auj] = min(poses.get(auj, idx - 1), idx - 1)
            auj = None
        choisis = [auj] if auj else []
        # Les années récentes d'abord (par tranches de cinq ans), puis au hasard fixe de la question.
        an = lambda k: max([int(t) for t in re.findall(r'\|(\d{4})(?=\||$)', k)] or [9999])
        dern = max([an(k) for k in pool if an(k) != 9999] or [0])
        ordre = sorted(pool, key=lambda k: (0 if k in mains else max(0, dern - an(k)) // 5 + 1, h(pg + k)))
        # Les formes de question à tour de rôle.
        CYCLE = ['chiffre', 'haut', 'duel', 'evol', 'bas', 'dessus', 'proche', 'annee']
        # Les sujets à tour de rôle : le sujet posé il y a le plus longtemps passe en premier, pour qu'une courbe riche en
        # questions (beaucoup de pays, beaucoup d'années) ne revienne pas plus souvent que les autres.
        dernier = {}
        for k, j in poses.items():
            if k in pool: dernier[sujet(pool[k])] = max(dernier.get(sujet(pool[k]), -10**6), j)
        for n, k in enumerate(choisis): dernier[sujet(pool[k])] = idx + n
        fam_vue = {}
        for k, j in poses.items():
            if k in pool:
                for f in (famille(pool[k]), forme_courbe(pool[k])): fam_vue[f] = max(fam_vue.get(f, -10**6), j)
        for n, k in enumerate(choisis):
            for f in (famille(pool[k]), forme_courbe(pool[k])): fam_vue[f] = idx + n
        while len(choisis) < L:
            prec = [pool[k] for k in choisis[-(ECART_COURBE - 1):]]
            vs = {sujet(q) for q in prec}
            forme0 = prec[-1]['forme'] if prec else None
            libre = lambda k: k not in poses and k not in choisis
            # Même courbe, même forme, même bonne réponse (« le plus élevé en 2024 » puis « en 2025 », toujours le même pays) :
            # c'est la même question pour le joueur ; elle attend ECART_FAMILLE jours.
            jour = idx + len(choisis)
            neuve = lambda k: jour - fam_vue.get(famille(pool[k]), -10**6) >= ECART_FAMILLE
            # Et la même forme sur la même courbe (« le chiffre de la France en 2023 », puis « en 2024 ») attend ECART_FORME jours.
            fraiche = lambda k: neuve(k) and jour - fam_vue.get(forme_courbe(pool[k]), -10**6) >= ECART_FORME
            cand = None
            if not any(pool[k]['forme'] == 'main' for k in choisis[-2:]):
                cand = next((k for k in ordre if k in mains and libre(k) and sujet(pool[k]) not in vs), None)
            # Décalé d'une page à l'autre : le même jour, les pages ne posent pas toutes la même forme de question.
            # La forme du jour suit la date (et non la place dans la fenêtre, qui repart chaque jour) : deux jours de suite,
            # jamais la même forme de question sur une page.
            voulue = CYCLE[(jour + 3 * PAGES.index(pg)) % len(CYCLE)]
            if not prec and str(idx - 1) in jours and jours[str(idx - 1)] in pool: forme0 = pool[jours[str(idx - 1)]]['forme']
            if not cand:
                # D'abord un sujet pas posé ces derniers jours avec une question vraiment nouvelle ; une page qui a peu de sujets
                # (Finances : trois courbes) revient plus vite sur un sujet, mais jamais sur la même question.
                tri = lambda f: sorted({sujet(pool[k]) for k in ordre if libre(k) and f(k)}, key=lambda x: (dernier.get(x, -10**6), h(pg + x)))
                sujets = tri(lambda k: fraiche(k) and sujet(pool[k]) not in vs) or tri(fraiche) or tri(lambda k: neuve(k) and sujet(pool[k]) not in vs) \
                    or tri(neuve) or tri(lambda k: sujet(pool[k]) not in vs) or tri(lambda k: True)
                for sj in sujets[:1]:
                    du = [k for k in ordre if libre(k) and fraiche(k) and sujet(pool[k]) == sj] or [k for k in ordre if libre(k) and neuve(k) and sujet(pool[k]) == sj] \
                        or [k for k in ordre if libre(k) and sujet(pool[k]) == sj]
                    cand = next((k for k in du if pool[k]['forme'] == voulue), None) or next((k for k in du if pool[k]['forme'] != forme0), None) or du[0]
            cand = cand or next((k for k in ordre if libre(k)), None)
            if not cand:
                # Tout a été posé : la question posée il y a le plus longtemps.
                cand = min((k for k in pool if k not in choisis), key=lambda k: poses.get(k, -1))
            choisis.append(cand)
            dernier[sujet(pool[cand])] = idx + len(choisis) - 1
            for f in (famille(pool[cand]), forme_courbe(pool[cand])): fam_vue[f] = idx + len(choisis) - 1
        etat['jours'] = {str(idx + n): k for n, k in enumerate(choisis)}
        poses.setdefault(choisis[0], idx)
        fen = [None] * L
        for n, k in enumerate(choisis):
            fen[(idx + n) % L] = nettoie(pool[k])
        # La question d'aujourd'hui garde le texte déjà en ligne (même question) : les réponses déjà données restent comptées.
        if ancien and auj and choisis[0] == auj and pg not in changer and ancien[idx % len(ancien)].get('a') == fen[idx % L].get('a') \
                and ancien[idx % len(ancien)].get('o') == fen[idx % L].get('o'):
            fen[idx % L] = ancien[idx % len(ancien)]
        change = json.dumps(fen, ensure_ascii=False) != json.dumps(ancien, ensure_ascii=False)
        jamais = sum(1 for k in pool if k not in poses)
        bilan.append(pg + ' : ' + str(len(pool)) + ' questions (' + str(len(mains)) + ' écrites), ' + str(jamais) + ' jamais posées' + (' · changé' if change else '')
                     + "\n   aujourd'hui : " + pool[choisis[0]]['q'])
        ser['QUIZ'] = fen
    print('\n'.join(bilan))
    if ecrire:
        with open(os.path.join(ROOT, 'data.json'), 'w', encoding='utf-8') as fh:
            fh.write(json.dumps(D, indent=0, ensure_ascii=False))
        with open(fplan, 'w', encoding='utf-8') as fh:
            fh.write(json.dumps(plan, ensure_ascii=False, separators=(',', ':'), sort_keys=True))
        print('Écrit : data.json (series.<page>.QUIZ, QUIZ_ECRITES) et donnees/quiz_plan.json')


if __name__ == '__main__':
    main()
