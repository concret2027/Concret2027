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
    d'aujourd'hui ne change pas d'un passage à l'autre ; jamais la même courbe moins de six jours après, et si possible pas
    deux fois de suite la même forme de question.
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
PAGES = ['finances', 'education', 'sante', 'securite', 'defense', 'vie']
# Finances et Éducation : leurs séries n'ont ni intitulé ni années dans data.json (années fixes, comme sur leurs pages).
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


def titre(x):
    # « 15-29 ans » ne se coupe pas en fin de ligne (trait d'union insécable).
    return re.sub(r'(\d)-(\d)', '\\1\u2011\\2', x['l'] + (' (%)' if x['u'] == '%' else ', ' + x['u']))


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
    base = lambda **k: dict({'est': {}, 'prov': {}, 'br': {}, 'dec': 1, 'src': 'Eurostat', 'ex': None}, **k)
    if pg in ('finances', 'education'):
        D, y0, tab = (ser.get('D', {}), 1995, FIN) if pg == 'finances' else (ser.get('S', {}), 2002, EDU)
        for k, l, u, ex in tab:
            c = D.get(k)
            if not c or not c.get('fr'):
                continue
            out.append(base(cle=pg + ('.D.' if pg == 'finances' else '.S.') + k, l=l, u=u, ex=ex, y=list(range(y0, y0 + len(c['fr']))), fr=c['fr'],
                            ue=c.get('eu') or [], de=c.get('de') or [], es=c.get('es') or [], br={str(b): 1 for b in (c.get('br') or [])}, v='ch-' + k))
        if pg == 'education':
            for k, l, u, v in PISA:
                c = (ser.get('PI') or {}).get(k)
                if c and c.get('y') and c.get('fr'):
                    out.append(base(cle='education.PI.' + k, l=l, u=u, y=c['y'], fr=c['fr'], ue=c.get('ue_calc') or [], de=c.get('de') or [], es=c.get('es') or [],
                                    dec=0, src='OCDE', v=v))
        return out
    for groupe, pre in (('C', ''), ('AFF', 'a-')):
        for k, c in (ser.get(groupe) or {}).items():
            if not c.get('y') or not c.get('fr') or c.get('regle') in ('composite', 'croissance', 'propre'):
                continue
            if pre:
                k = AFFN.get(k, k)
                if "'ch-a-" + k + "'" not in html:
                    continue
            br = c.get('br') or {}
            out.append(base(cle=pg + '.' + pre + k, l=c.get('l'), u=c.get('unite', ''), ex=c.get('ex'), dec=c.get('dec', 1), src=court(c.get('source')),
                            y=c['y'], fr=c['fr'], ue=c.get('ue') or c.get('ue_calc') or [], de=c.get('de') or [], es=c.get('es') or [],
                            est=c.get('est') or {}, prov=c.get('prov') or {}, br=br if isinstance(br, dict) else {str(b): 1 for b in br}, v='ch-' + pre + k))
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
            d = 0 if a >= 10 else 1 if a >= 1 else 2
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
        # 6. La France face à un autre pays (trois pays par année, tirés de la question, écart d'au moins 5 %).
        loin = [(g, v) for g, v in Lp if g != 'FR' and abs(v - f) >= 0.05 * max(abs(f), abs(v))]
        for g, v in sorted(loin, key=lambda t: h(x['cle'] + Y + t[0]))[:3]:
            o = sorted(['France', nom[g]], key=lambda t: h(x['cle'] + Y + g + t))
            add('duel|' + Y + '|' + g, 'duel', T + ' : en ' + Y + ', lequel de ces deux pays avait le chiffre le plus élevé ?', o, o.index('France' if f > v else nom[g]),
                'France : ' + fmt(f) + ' ; ' + nom[g] + ' : ' + fmt(v) + ' (' + Y + ', ' + src + ').')
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
            add('evol|' + str(y) + '|' + str(recul), 'evol', T + ' : le chiffre de la France était-il plus élevé en ' + str(y) + ' qu\'en ' + str(y - recul) + ' ?',
                ['Plus élevé en ' + str(y), 'Plus bas en ' + str(y)], 0 if f > f0 else 1,
                str(y - recul) + ' : ' + fmt(f0) + ' ; ' + str(y) + ' : ' + fmt(f) + ' (France, ' + src + ').')
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
                    o, o.index(str(x['y'][vs[0]])), 'En ' + str(x['y'][vs[0]]) + ' : ' + fmt(x['fr'][vs[0]]) + ' (France, ' + src + '). En ' + str(y1) + ' : ' + fmt(x['fr'][der]) + '.')
    ex = x['ex']
    mots = lambda t: set(re.findall(r"[a-zà-ÿ]{4,}", (t or '').lower()))
    d = (ex[0].upper() + ex[1:] + '.') if ex and len(mots(ex) - mots(x['l'] + ' ' + x['u'])) >= 4 else None
    if d:
        for q in Q:
            q['d'] = d
    return Q


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
        if not ser or not (ser.get('QUIZ') or ser.get('QUIZ_ECRITES')):
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
        while len(choisis) < L:
            prec = [pool[k] for k in choisis[-(ECART_COURBE - 1):]]
            vs = {q['v'] for q in prec}
            forme0 = prec[-1]['forme'] if prec else None
            libre = lambda k: k not in poses and k not in choisis
            cand = None
            if not any(pool[k]['forme'] == 'main' for k in choisis[-2:]):
                cand = next((k for k in ordre if k in mains and libre(k) and pool[k].get('v') not in vs), None)
            # Décalé d'une page à l'autre : le même jour, les pages ne posent pas toutes la même forme de question.
            voulue = CYCLE[(len(choisis) + 3 * PAGES.index(pg)) % len(CYCLE)]
            cand = cand or next((k for k in ordre if libre(k) and pool[k]['v'] not in vs and pool[k]['forme'] == voulue), None) \
                or next((k for k in ordre if libre(k) and pool[k]['v'] not in vs and pool[k]['forme'] != forme0), None) \
                or next((k for k in ordre if libre(k) and pool[k]['v'] not in vs), None) \
                or next((k for k in ordre if libre(k)), None)
            if not cand:
                # Tout a été posé : la question posée il y a le plus longtemps.
                cand = min((k for k in pool if k not in choisis), key=lambda k: poses.get(k, -1))
            choisis.append(cand)
        etat['jours'] = {str(idx + n): k for n, k in enumerate(choisis)}
        poses.setdefault(choisis[0], idx)
        fen = [None] * L
        for n, k in enumerate(choisis):
            fen[(idx + n) % L] = nettoie(pool[k])
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
