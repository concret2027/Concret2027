#!/usr/bin/env python3
"""Questions du jour fabriquées à partir des séries des pages (series.<page>.QUIZ, marquées "auto").

Les questions écrites à la main ne suffisent pas à éviter qu'une question revienne dans la semaine (cinq questions :
la même revient tous les cinq jours). Pour chaque courbe d'une page, trois questions sont calculées, jamais saisies :
  - le chiffre de la France la dernière année définitive (sans année estimée ni provisoire), les autres réponses étant
    la moyenne de l'UE, l'Allemagne et l'Espagne quand elles s'écartent assez, sinon des écarts fixes ;
  - le pays de l'UE qui a le chiffre le plus élevé, et celui qui a le plus bas, la même année (donnees/pays.json, lus aux
    mêmes sources par outils/pays.py ; au moins 20 pays de l'UE avec un chiffre).
Elles sont mêlées aux questions écrites à la main, qui restent telles quelles, de sorte que deux jours de suite ne portent
ni sur la même courbe ni sur la même forme de question. La question d'aujourd'hui ne change pas (le tirage du jour, sur la
page, dans le quiz et dans le compteur, reste le même), seules les suivantes sont rangées autrement.
Lancé par outils/controle.js verifier, avant la validation, pour suivre chaque nouveau chiffre.
  python3 outils/quiz_auto.py            compare
  python3 outils/quiz_auto.py --ecrire   écrit dans data.json
"""
import json, os, re, sys
from datetime import date, datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UE = ['BE', 'BG', 'CZ', 'DK', 'DE', 'EE', 'IE', 'EL', 'ES', 'FR', 'HR', 'IT', 'CY', 'LV', 'LT', 'LU', 'HU', 'MT', 'NL', 'AT', 'PL', 'PT', 'RO', 'SI', 'SK', 'FI', 'SE']
MIN = 20
PAGES = ['finances', 'education', 'sante', 'securite', 'defense', 'vie']
# Finances et Éducation : leurs séries n'ont ni intitulé ni années dans data.json (années fixes, comme sur leurs pages).
FIN = [('dette', 'Dette publique', '% du PIB', None), ('dep', 'Dépense publique', '% du PIB', 'dépense de toutes les administrations publiques (État, collectivités, Sécurité sociale)'),
       ('po', 'Impôts et cotisations', '% du PIB', 'impôts et cotisations sociales prélevés par les administrations publiques (prélèvements obligatoires)')]
EDU = [('el', 'Décrochage', '% des 18-24 ans', "jeunes de 18 à 24 ans qui ont quitté l'école sans diplôme du secondaire (ni bac, ni CAP, ni BEP) et ne suivent aucune formation"),
       ('ne', 'Ni emploi ni études', '% des 15-29 ans', "jeunes de 15 à 29 ans qui ne travaillent pas, n'étudient pas et ne suivent aucune formation"),
       ('te', 'Diplômés du supérieur', '% des 25-34 ans', None),
       ('yu', 'Chômage des 15-24 ans', '%', 'part des 15-24 ans sans emploi qui en cherchent un, parmi ceux qui travaillent ou cherchent un emploi')]
AFFN = {'depense': 'dep', 'detenus': 'det', 'juges': 'jug', 'police': 'pol', 'medic': 'med'}


def lire(f):
    with open(os.path.join(ROOT, f), encoding='utf-8') as h:
        return json.load(h)


def nf(v, d):
    s = ('{:,.' + str(d) + 'f}').format(abs(v)).replace(',', ' ').replace('.', ',')
    return ('−' if v < 0 and float(s.replace(' ', '').replace(',', '.')) != 0 else '') + s


def titre(x):
    # « 15-29 ans » ne se coupe pas en fin de ligne (trait d'union insécable).
    return re.sub(r'(\d)-(\d)', '\\1\u2011\\2', x['l'] + (' (%)' if x['u'] == '%' else ', ' + x['u']))


def unite(x):
    # Après un chiffre : « % » (et « du PIB ») ; les autres unités sont déjà dans la question.
    return (' % du PIB' if 'PIB' in x['u'] else ' %') if x['u'].startswith('%') else ''


def court(src):
    return re.split(r' \(|;|,', src or 'Eurostat')[0].strip() or 'Eurostat'


def indicateurs(S, P, pg, html):
    """Chaque courbe de la page : intitulé, unité, années, France, UE, Allemagne, Espagne, pays de l'UE, lien."""
    out = []
    ser = S.get(pg, {})
    if pg in ('finances', 'education'):
        D, y0, tab = (ser.get('D', {}), 1995, FIN) if pg == 'finances' else (ser.get('S', {}), 2002, EDU)
        for k, l, u, ex in tab:
            c = D.get(k)
            if not c or not c.get('fr'):
                continue
            n = len(c['fr'])
            out.append({'cle': pg + ('.D.' if pg == 'finances' else '.S.') + k, 'l': l, 'u': u, 'ex': ex, 'dec': 1, 'src': 'Eurostat',
                        'y': list(range(y0, y0 + n)), 'fr': c['fr'], 'ue': c.get('eu') or [], 'de': c.get('de') or [], 'es': c.get('es') or [],
                        'est': {}, 'prov': {}, 'v': 'ch-' + k})
        return out
    for k, c in (ser.get('C') or {}).items():
        if not c.get('y') or not c.get('fr') or c.get('regle') in ('composite', 'croissance', 'propre'):
            continue
        out.append({'cle': pg + '.' + k, 'l': c.get('l'), 'u': c.get('unite', ''), 'ex': c.get('ex'), 'dec': c.get('dec', 1), 'src': court(c.get('source')),
                    'y': c['y'], 'fr': c['fr'], 'ue': c.get('ue') or c.get('ue_calc') or [], 'de': c.get('de') or [], 'es': c.get('es') or [],
                    'est': c.get('est') or {}, 'prov': c.get('prov') or {}, 'v': 'ch-' + k})
    for k, c in (ser.get('AFF') or {}).items():
        if not c.get('y') or not c.get('fr') or c.get('regle') in ('composite', 'croissance'):
            continue
        a = AFFN.get(k, k)
        if "'ch-a-" + a + "'" not in html:
            continue
        out.append({'cle': pg + '.a-' + a, 'l': c.get('l'), 'u': c.get('unite', ''), 'ex': c.get('ex'), 'dec': c.get('dec', 1), 'src': court(c.get('source')),
                    'y': c['y'], 'fr': c['fr'], 'ue': c.get('ue') or c.get('ue_calc') or [], 'de': c.get('de') or [], 'es': c.get('es') or [],
                    'est': c.get('est') or {}, 'prov': c.get('prov') or {}, 'v': 'ch-a-' + a})
    return out


def val(L, i):
    return L[i] if i < len(L) else None


def derniere(x):
    for i in range(len(x['y']) - 1, -1, -1):
        y = x['y'][i]
        if val(x['fr'], i) is not None and str(y) not in x['est'] and str(y) not in x['prov']:
            return i
    return -1


def q_chiffre(x, i):
    """Le chiffre de la France : les trois autres réponses sont des chiffres réels (UE, Allemagne, Espagne) quand ils
    s'écartent assez, sinon des écarts fixes au chiffre de la France."""
    f = x['fr'][i]
    a = abs(f)
    if a == 0:
        return None
    d = 0 if a >= 10 else 1 if a >= 1 else 2
    unit = 10 ** -d
    r = lambda v: round(v, d)
    pct = x['u'].startswith('%') and 'PIB' not in x['u']
    ecart = max(0.12 * a, unit)
    pris = [r(f)]
    ok = lambda v: all(abs(v - p) >= ecart - 1e-9 for p in pris) and (not pct or 0 <= v <= 100) and (f < 0 or v > 0)
    for w in ('ue', 'de', 'es'):
        v = val(x[w], i)
        if v is not None and ok(r(v)) and len(pris) < 4:
            pris.append(r(v))
    for m in ((0.6, 1.4, 1.8, 0.4, 2.2) if f > 0 else (1.4, 0.6, 1.8, 0.4, 2.2)):
        if len(pris) >= 4:
            break
        v = r(f * m)
        if ok(v):
            pris.append(v)
    if len(pris) < 4:
        return None
    o = sorted(pris)
    suf = ' %' if pct else ''
    reste = [('Moyenne de l\'UE', val(x['ue'], i)), ('Allemagne', val(x['de'], i)), ('Espagne', val(x['es'], i))]
    e = nf(f, x['dec']) + unite(x) + ' en France en ' + str(x['y'][i]) + ' (' + x['src'] + ').'
    autres = ' ; '.join(n + ' : ' + nf(v, x['dec']) + unite(x) for n, v in reste if v is not None)
    return {'q': titre(x) + ' : quel était le chiffre de la France en ' + str(x['y'][i]) + ' ?',
            'o': [nf(v, d) + suf for v in o], 'a': o.index(r(f)), 'e': e + (' ' + autres + '.' if autres else '')}


def pays_annee(x, P, i):
    s = P['series'].get(x['cle'])
    y = x['y'][i]
    if not s or y not in s.get('y', []):
        return None
    j = s['y'].index(y)
    L = []
    for g in UE:
        v = x['fr'][i] if g == 'FR' else val(x['de'], i) if g == 'DE' else val(x['es'], i) if g == 'ES' else val(s.get(g) or [], j)
        if v is not None:
            L.append((g, v))
    return L if len(L) >= MIN else None


def q_rang(x, P, i, nom, haut):
    L = pays_annee(x, P, i)
    if not L:
        return None
    L.sort(key=lambda t: -t[1] if haut else t[1])
    if L[0][1] == L[1][1]:
        return None
    n, f = len(L), x['fr'][i]
    premier = L[0][0]
    # Les autres réponses : les deux pays qui suivent, et la France (ou le pays suivant si la France y est déjà).
    o = [premier]
    for g in [L[1][0], L[2][0], 'FR', L[3][0]]:
        if g not in o and len(o) < 4:
            o.append(g)
    o.sort(key=lambda g: nom[g])
    sens = 'élevé' if haut else 'bas'
    k = 1 + sum(1 for _, v in L if (v > f if haut else v < f))
    pf = 'le chiffre le plus ' + sens if k == 1 else 'le ' + str(k) + 'e chiffre le plus ' + sens
    v1 = L[0][1]
    e = nom[premier] + ' : ' + nf(v1, x['dec']) + unite(x) + ' (' + str(x['y'][i]) + ', ' + x['src'] + ').'
    if premier == 'FR':
        e += ' Ensuite : ' + nom[L[1][0]] + ', ' + nf(L[1][1], x['dec']) + unite(x) + ' ; ' + str(n) + ' pays de l\'UE ont un chiffre cette année-là.'
    else:
        e += ' France : ' + nf(f, x['dec']) + unite(x) + ', ' + pf + ' des ' + str(n) + ' pays de l\'UE' + (' qui le publient' if n < 27 else '') + '.'
    return {'q': titre(x) + ' : quel pays de l\'UE avait le chiffre le plus ' + sens + ' en ' + str(x['y'][i]) + ' ?',
            'o': [nom[g] for g in o], 'a': o.index(premier), 'e': e}


def fabriquer(S, P, pg, html, mains):
    nom = dict(P.get('noms') or {}, FR='France', DE='Allemagne', ES='Espagne')
    # Une courbe qui a déjà une question écrite à la main : pas de question sur le chiffre de la France en plus (ce serait
    # la même), et pas de question sur les pays si celle écrite à la main porte déjà sur eux.
    main_v = {q.get('v') for q in mains}
    deja = {q.get('v') for q in mains if re.search(r'quel pays', q.get('q', ''), re.I)}
    F = [[], [], []]
    for x in indicateurs(S, P, pg, html):
        i = derniere(x)
        if i < 0:
            continue
        ex = x['ex']
        # La définition n'est ajoutée que si elle apprend quelque chose de plus que l'intitulé.
        mots = lambda t: set(re.findall(r"[a-zà-ÿ]{4,}", (t or '').lower()))
        d = (ex[0].upper() + ex[1:] + '.') if ex and len(mots(ex) - mots(x['l'] + ' ' + x['u'])) >= 4 else None
        for t, q in enumerate([None if x['v'] in main_v else q_chiffre(x, i), None if x['v'] in deja else q_rang(x, P, i, nom, True), None if x['v'] in deja else q_rang(x, P, i, nom, False)]):
            if q:
                q.update({'v': x['v'], 'auto': True})
                if d:
                    q['d'] = d
                F[t].append(q)
    # Ordre des jours : jamais la même courbe moins de 6 jours après, et si possible pas deux fois de suite la même forme.
    reste = [q for t in range(3) for q in F[t]]
    pas = max(1, (len(reste) + len(mains)) // max(1, len(mains)))
    m = list(mains)
    out = []
    while reste or m:
        # Fenêtre plus courte quand la page a peu de courbes.
        nv = len({q.get('v') for q in reste + m + out})
        recent = [q.get('v') for q in out[-min(5, max(1, nv - 2)):]]
        libre = [q for q in m if q.get('v') not in recent]
        if m and (len(out) % pas == 0 or not reste) and (libre or not reste):
            pool = libre[:1] or m[:1]
        else:
            pool = reste or m
        forme = lambda q: q['q'].split(' : ')[-1][:20]
        choix = next((q for q in pool if q.get('v') not in recent and (not out or forme(q) != forme(out[-1]))), None) \
            or next((q for q in pool if q.get('v') not in recent), None) \
            or next((q for q in reste + m if q.get('v') not in recent), None) or pool[0]
        out.append(choix)
        (m if choix in m else reste).remove(choix)
    # La liste tourne en boucle : la fin est suivie du début. On échange les questions qui s'y retrouvent trop près.
    n = len(out)
    w = min(3, max(1, len({q.get('v') for q in out}) - 2))
    gene = lambda k: sum(1 for d in range(1, w + 1) for j in ((k - d) % n, (k + d) % n) if out[j].get('v') and out[j].get('v') == out[k].get('v'))
    for _ in range(3):
        for k in range(n):
            if gene(k):
                for j in range(n):
                    avant = gene(k) + gene(j)
                    out[k], out[j] = out[j], out[k]
                    if gene(k) + gene(j) < avant:
                        break
                    out[k], out[j] = out[j], out[k]
    return out


def jour_idx():
    d = datetime.now(ZoneInfo('Europe/Paris')).date() if ZoneInfo else date.today()
    return (d - date(2026, 1, 1)).days


def main():
    ecrire = '--ecrire' in sys.argv
    D = lire('data.json')
    P = lire('donnees/pays.json')
    S = D['series']
    idx = jour_idx()
    bilan = []
    for pg in PAGES:
        ser = S.get(pg)
        if not ser or not ser.get('QUIZ'):
            continue
        with open(os.path.join(ROOT, pg, 'index.html'), encoding='utf-8') as h:
            html = h.read()
        ancien = ser['QUIZ']
        aujourdhui = ancien[idx % len(ancien)]
        mains = [q for q in ancien if not q.get('auto')]
        neuf = fabriquer(S, P, pg, html, mains)
        # La question du jour reste la même : on fait tourner la liste pour qu'elle tombe aujourd'hui.
        if aujourdhui in neuf:
            j = neuf.index(aujourdhui)
            dec = (j - idx) % len(neuf)
            neuf = neuf[dec:] + neuf[:dec]
        n_auto = sum(1 for q in neuf if q.get('auto'))
        change = json.dumps(neuf, ensure_ascii=False, sort_keys=True) != json.dumps(ancien, ensure_ascii=False, sort_keys=True)
        bilan.append(pg + ' : ' + str(len(neuf)) + ' questions (' + str(len(mains)) + ' écrites, ' + str(n_auto) + ' calculées), une même question revient tous les ' + str(len(neuf)) + ' jours' + (' · changé' if change else ''))
        ser['QUIZ'] = neuf
    print('\n'.join(bilan))
    if ecrire:
        with open(os.path.join(ROOT, 'data.json'), 'w', encoding='utf-8') as h:
            h.write(json.dumps(D, indent=0, ensure_ascii=False))
        print('Écrit : data.json (series.<page>.QUIZ)')


if __name__ == '__main__':
    main()
