"""Séries lues dans les rapports PDF de l'EFPIA, pour tous les pays d'Europe qu'ils couvrent (menu « + Ajouter un pays »).

  wait_dispo()     part des nouveaux médicaments disponibles (Patients W.A.I.T. Indicator, graphique « Rate of availability »)
  wait_delai()     délai moyen d'accès, en jours (même étude, graphique « Time to availability »)
  medicaments()    ventes de médicaments en % du PIB (« The Pharmaceutical Industry in Figures », tableau « Pharmaceutical
                   market value (at ex-factory prices) ») ; medicaments_meur() donne les millions d'euros lus

Chaque fonction rend {pays: {année: valeur}} avec les codes de outils/ue_calc.py (EL pour la Grèce, UK pour le Royaume-Uni) ;
pour l'étude W.A.I.T., la clé 'ue' porte la moyenne de l'UE imprimée par le rapport.
Les chiffres des graphiques sont du texte dans le PDF, mais les noms de pays sont écrits à la verticale : chaque chiffre est
rattaché à sa barre par sa position, et chaque barre au nom écrit dessous. Une édition n'est gardée que si chaque barre a son
pays et sa valeur, si les barres sont dans l'ordre du graphique, et si « produits disponibles / médicaments autorisés » redonne
le pourcentage imprimé ; sinon elle est écartée et signalée (ECARTEES). Rien n'est saisi à la main.

  python3 outils/pays_pdf.py      relit les éditions, compte les pays par année et compare la France, l'Allemagne, l'Espagne
                                  et la moyenne de l'UE aux chiffres publiés dans data.json (rien n'est écrit)
"""
import io, json, os, re, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ue_calc as U
import pdfplumber

ROOT = U.ROOT

# Patients W.A.I.T. Indicator (IQVIA pour l'EFPIA) : y = année de l'étude (« 2025 Survey »), publiée l'année suivante.
WAIT = {
    2020: 'https://www.efpia.eu/media/602652/efpia-patient-wait-indicator-final-250521.pdf',
    2021: 'https://www.efpia.eu/media/676539/efpia-patient-wait-indicator_update-july-2022_final.pdf',
    2022: 'https://www.efpia.eu/media/s4qf1eqo/efpia_patient_wait_indicator_final_report.pdf',
    2023: 'https://efpia.eu/media/vtapbere/efpia-patient-wait-indicator-2024.pdf',
    2024: 'https://efpia.eu/media/oeganukm/efpia-patients-wait-indicator-2024-final-110425.pdf',
    2025: 'https://www.efpia.eu/media/mnfdwzax/efpia-patients-wait-indicator-2025.pdf',
}
# « The Pharmaceutical Industry in Figures » : chaque édition donne une année (édition 2026 : 2024). L'édition 2025 (année 2023,
# https://www.efpia.eu/media/uj0popel/the-pharmaceutical-industry-in-figures-2025.pdf) n'est plus en ligne (erreur 404).
FIGURES = {
    2022: 'https://www.efpia.eu/media/637143/the-pharmaceutical-industry-in-figures-2022.pdf',
    2023: 'https://www.efpia.eu/media/rm4kzdlx/the-pharmaceutical-industry-in-figures-2023.pdf',
    2024: 'https://www.efpia.eu/media/2rxdkn43/the-pharmaceutical-industry-in-figures-2024.pdf',
    2026: 'https://www.efpia.eu/media/owqczcqz/the-pharmaceutical-industry-in-figures-2026.pdf',
}

# Pays hors UE couverts par ces rapports et qui ont un code dans outils/pays.py (HORS).
HORS = {'NO': 'Norway', 'CH': 'Switzerland', 'IS': 'Iceland', 'UK': 'United Kingdom', 'TR': 'Turkey'}
NOMS = {n.lower(): g for g, n in list(U.NOM_EN.items()) + list(HORS.items())}
NOMS.update({'czech': 'CZ', 'czech rep.': 'CZ', 'czech republic': 'CZ', 'luxemburg': 'LU', 'türkiye': 'TR', 'turkiye': 'TR',
             'u.k.': 'UK', 'uk': 'UK'})
# Noms imprimés sans code chez Concret : laissés de côté. Tout autre nom inconnu fait écarter l'édition (pour le voir).
SANS_CODE = {'england', 'scotland', 'wales', 'northern ireland', 'serbia', 'north macedonia', 'n. macedonia', 'macedonia',
             'bosnia', 'bosnia and herzegovina', 'albania', 'montenegro', 'kosovo', 'kazakhstan', 'russia', 'ukraine'}
MOYENNE = {'eu average', 'eu27 average', 'eu 27 average'}
TOTAL = {'eu approvals', 'ema approvals'}

ECARTEES = []   # (série, édition, raison) : éditions laissées de côté
PARTIELS = {}   # (série, année) -> pays marqués d'une seule astérisque (« did not complete a full dataset »)
_pdf = {}


def pdf(url):
    if url not in _pdf:
        _pdf[url] = U.get(url)
    return pdfplumber.open(io.BytesIO(_pdf[url]))


def nombre(t):
    return float(t.replace(',', ''))


def code(nom):
    """Code du pays imprimé, None s'il n'en a pas chez Concret ; KeyError pour un nom jamais vu."""
    n = nom.strip().lower()
    if n in NOMS:
        return NOMS[n]
    if n in SANS_CODE:
        return None
    raise KeyError(nom)


def page_titre(doc, motif):
    """Première page dont le grand titre (police de plus de 20 points) commence par motif."""
    for i, pg in enumerate(doc.pages):
        t = ' '.join(w['text'] for w in pg.extract_words(extra_attrs=['size']) if w['size'] > 20 and w['top'] < 120)
        if re.match(motif, t):
            return i
    raise ValueError('page introuvable : ' + motif)


def lignes_horizontales(pg):
    """Nombres écrits à l'horizontale : {texte, x, top}. Les caractères sont regroupés par ligne puis coupés dès qu'un écart
    dépasse 1,5 point (deux étiquettes voisines se touchent presque)."""
    cs = sorted((c for c in pg.chars if abs(c['matrix'][1]) < 0.5 and c['text'].strip()), key=lambda c: c['top'])
    lignes = []
    for c in cs:
        if lignes and c['top'] - lignes[-1][0]['top'] <= 1:
            lignes[-1].append(c)
        else:
            lignes.append([c])
    mots = []
    for l in lignes:
        l.sort(key=lambda c: c['x0'])
        cur = [l[0]]
        for c in l[1:]:
            if c['x0'] - cur[-1]['x1'] > 1.5:
                mots.append(cur); cur = []
            cur.append(c)
        mots.append(cur)
    out = []
    for m in mots:
        t = ''.join(c['text'] for c in m)
        if re.fullmatch(r'\d[\d,]*%?', t):
            out.append(dict(texte=t, x=(m[0]['x0'] + m[-1]['x1']) / 2, x0=m[0]['x0'], top=m[0]['top']))
    return out


def etiquettes(pg):
    """Noms écrits à la verticale, par colonne : [(x du centre, texte, haut)]."""
    rot = sorted((c for c in pg.chars if abs(c['matrix'][1]) > 0.5), key=lambda c: (c['x0'] + c['x1']) / 2)
    cols = []
    for c in rot:
        x = (c['x0'] + c['x1']) / 2
        if cols and abs(x - cols[-1][0][0]) <= 2:
            cols[-1][1].append(c)
        else:
            cols.append([(x,), [c]])
    out = []
    for (x,), cs in cols:
        cs.sort(key=lambda c: c['matrix'][5], reverse=cs[0]['matrix'][1] < 0)
        out.append((sum((c['x0'] + c['x1']) / 2 for c in cs) / len(cs), ''.join(c['text'] for c in cs), min(c['top'] for c in cs)))
    return out


def graphique(pg):
    """Barres d'un graphique de l'étude W.A.I.T., de gauche à droite : [{nom, valeurs}] où valeurs = nombres écrits au-dessus."""
    labs = etiquettes(pg)
    haut = Counter(round(t) for _, _, t in labs).most_common(1)[0][0]
    labs = [l for l in labs if haut - 6 <= l[2] <= haut + 40]          # les noms sous l'axe (pas le titre de l'axe)
    bas = haut - 2
    # Barres (ou boîtes) : rectangles pleins, ni blancs ni gris de fond, de la largeur d'une barre, au-dessus des noms.
    rs = [r for r in pg.rects if r['fill'] and 5 < r['width'] < 14 and r['x1'] < pg.width and r['bottom'] <= bas
          and r['height'] > 0.5 and r['non_stroking_color'] not in ((1,), (1.0,), 1, 1.0, (1, 1, 1), (1.0, 1.0, 1.0))]
    rs.sort(key=lambda r: r['x0'])
    barres = []
    for r in rs:
        x = (r['x0'] + r['x1']) / 2
        if barres and abs(x - barres[-1]['x']) <= 3:
            continue
        barres.append(dict(x=x, x0=r['x0'], noms=[], valeurs=[]))
    if len(barres) < 10:
        raise ValueError('barres introuvables (%d)' % len(barres))
    pas = sorted(b['x'] - a['x'] for a, b in zip(barres, barres[1:]))[len(barres) // 2]
    for x, t, _ in labs:
        b = min(barres, key=lambda b: abs(b['x'] - x))
        if abs(b['x'] - x) <= 0.5 * pas:
            b['noms'].append(t)
        elif t.strip():
            barres.append(dict(x=x, x0=x, noms=[t], valeurs=[], sans_barre=True))
    barres.sort(key=lambda b: b['x'])
    # Graduations de l'axe : à gauche de la première barre ; elles bornent le haut du graphique.
    nums = lignes_horizontales(pg)
    gauche = barres[0]['x0'] - 3
    grad = [n for n in nums if n['x'] < gauche and n['top'] < bas]
    if not grad:
        raise ValueError("graduations de l'axe introuvables")
    plafond = min(n['top'] for n in grad) - 15
    droite = barres[-1]['x'] + pas
    vals = [n for n in nums if gauche <= n['x'] <= droite and plafond < n['top'] < bas]
    # Chaque nombre va à la barre la plus proche ; une barre reçoit au plus un nombre de chaque sorte (nombre, pourcentage).
    cand = sorted(((abs(b['x'] - n['x']), i, j) for i, n in enumerate(vals) for j, b in enumerate(barres)
                   if abs(b['x'] - n['x']) <= 0.75 * pas), key=lambda c: c[0])
    pris, orph = set(), []
    for d, i, j in cand:
        if i in pris:
            continue
        sorte = vals[i]['texte'].endswith('%')
        if any(v.endswith('%') == sorte for v in barres[j]['valeurs']):
            continue
        barres[j]['valeurs'].append(vals[i]['texte']); pris.add(i)
    orph = [vals[i]['texte'] for i in range(len(vals)) if i not in pris]
    if orph:
        raise ValueError('nombres sans barre : %s' % orph)
    for b in barres:
        b['nom'] = ' '.join(b['noms']).replace('  ', ' ').strip()
    return barres, pg.extract_text() or ''


def lire_wait(serie):
    """Lit une série W.A.I.T. dans chaque édition ; serie = 'dispo' ou 'delai'."""
    out = {}
    for y, url in sorted(WAIT.items()):
        try:
            with pdf(url) as doc:
                couv = doc.pages[0].extract_text() or ''
                m = re.search(r'Indicator\s+(\d{4})\s+Survey', couv)
                if not m or int(m.group(1)) != y:
                    raise ValueError("la couverture n'annonce pas l'étude %d" % y)
                motif = r'Rate of availability \(\d{4}' if serie == 'dispo' else r'Time to availability \(\d{4}'
                barres, texte = graphique(doc.pages[page_titre(doc, motif)])
            lu, partiels = (dispo if serie == 'dispo' else delai)(barres, texte)
        except Exception as e:
            ECARTEES.append((serie, y, str(e)))
            continue
        for g, v in lu.items():
            out.setdefault(g, {})[y] = v
        PARTIELS[(serie, y)] = partiels
    return out


def pays_des_barres(barres):
    """[(code ou 'ue' ou 'total' ou None, nom, astérisques, barre)] ; KeyError si un nom est inconnu."""
    out = []
    for b in barres:
        nom = b['nom'].lstrip('*').strip()
        n = nom.lower()
        g = 'ue' if n in MOYENNE else 'total' if n in TOTAL else code(nom)
        out.append((g, nom, len(b['nom']) - len(b['nom'].lstrip('*')), b))
    return out


def dispo(barres, texte):
    """« Rate of availability » : sous chaque barre, le nombre de médicaments disponibles et le pourcentage ; contrôles."""
    lst = pays_des_barres(barres)
    tot = [b for g, _, _, b in lst if g == 'total']
    if len(tot) != 1 or len(tot[0]['valeurs']) != 1:
        raise ValueError('nombre de médicaments autorisés introuvable')
    total = nombre(tot[0]['valeurs'][0])
    out, partiels, suite, manque = {}, set(), [], []
    for g, nom, ast, b in lst:
        if g == 'total':
            continue
        pc = [nombre(v[:-1]) for v in b['valeurs'] if v.endswith('%')]
        nb = [nombre(v) for v in b['valeurs'] if not v.endswith('%')]
        if b.get('sans_barre') or len(pc) != 1:
            manque.append(nom)
            continue
        if nb and abs(nb[0] / total * 100 - pc[0]) > 0.5 + 1e-9:
            raise ValueError('%s : %d / %d ne redonne pas %d %%' % (nom, nb[0], total, pc[0]))
        suite.append(pc[0])
        if g:
            out[g] = pc[0]
            if ast == 1:
                partiels.add(g)
    if manque:
        raise ValueError('barres sans pourcentage : %s' % manque)
    if any(a < b for a, b in zip(suite, suite[1:])):
        raise ValueError("les barres ne sont pas dans l'ordre décroissant")
    m = re.search(r'European Union average:\s*(\d+) products available \((\d+)%\)', texte)
    if not m or 'ue' not in out or int(m.group(2)) != out['ue'] or abs(int(m.group(1)) / total * 100 - out['ue']) > 0.5 + 1e-9:
        raise ValueError("moyenne de l'UE : la barre et la note ne concordent pas")
    return out, partiels


def delai(barres, texte):
    """« Time to availability » : délai moyen écrit au-dessus de chaque boîte ; moyenne de l'UE lue dans la note du graphique."""
    lst = pays_des_barres(barres)
    out, partiels, suite, manque = {}, set(), [], []
    for g, nom, ast, b in lst:
        if len(b['valeurs']) > 1:
            raise ValueError('%s : plusieurs nombres %s' % (nom, b['valeurs']))
        if not b['valeurs']:
            # Un pays nommé sans boîte ni chiffre (trop peu de dates déclarées) : pas de valeur, rien à rattacher.
            if not b.get('sans_barre'):
                manque.append(nom)
            continue
        if b.get('sans_barre'):
            raise ValueError('%s : un chiffre sans boîte' % nom)
        v = nombre(b['valeurs'][0])
        suite.append(v)
        if g:
            out[g] = v
            if ast == 1:
                partiels.add(g)
    if manque:
        raise ValueError('boîtes sans chiffre : %s' % manque)
    if any(a > b for a, b in zip(suite, suite[1:])):
        raise ValueError("les boîtes ne sont pas dans l'ordre croissant")
    m = re.search(r'European Union average:\s*([\d,]+) days', texte)
    if not m:
        raise ValueError("moyenne de l'UE introuvable dans la note")
    out['ue'] = nombre(m.group(1))
    return out, partiels


def wait_dispo():
    """Part (%) des nouveaux médicaments autorisés en Europe qui sont disponibles pour les patients, par année d'étude."""
    return lire_wait('dispo')


def wait_delai():
    """Délai moyen (jours) entre l'autorisation européenne et la disponibilité pour les patients, par année d'étude."""
    return lire_wait('delai')


_meur = {}
def medicaments_meur():
    """Ventes de médicaments à prix fabricant, tous canaux (M€), par année ; contrôle : la somme des pays redonne le TOTAL."""
    if _meur:
        return _meur
    for ed, url in sorted(FIGURES.items()):
        try:
            with pdf(url) as doc:
                pg = next(p for p in doc.pages if 'PHARMACEUTICAL MARKET VALUE' in (p.extract_text() or ''))
                ws = pg.extract_words(extra_attrs=['size', 'fontname'])
            ent = next(w for w in ws if w['text'] == 'EFPIA' and w['size'] > 9)
            an = next(w for w in ws if abs(w['top'] - ent['top']) < 1 and re.fullmatch(r'\d{4}', w['text']))
            y = int(an['text'])
            fin = next(w for w in ws if w['text'] == 'TOTAL')
            tot = next(w for w in ws if abs(w['top'] - fin['top']) < 1 and re.fullmatch(r'[\d,]+', w['text']))
            # Lignes du tableau : texte en 8 points, maigre, entre l'en-tête et le total (pas le titre du graphique voisin).
            corps = [w for w in ws if ent['top'] + 5 < w['top'] < fin['top'] - 1 and 7.5 < w['size'] < 8.5 and 'Bold' not in w['fontname']]
            corps.sort(key=lambda w: (round(w['top']), w['x0']))
            lus, nom, somme = {}, [], 0
            for w in corps:
                if re.fullmatch(r'\d[\d,]*', w['text']):
                    if not nom:
                        raise ValueError('nombre sans pays : ' + w['text'])
                    v = nombre(w['text'])
                    somme += v
                    g = code(' '.join(nom))
                    if g:
                        if g in lus:
                            raise ValueError('pays en double : ' + ' '.join(nom))
                        lus[g] = v
                    nom = []
                else:
                    nom.append(w['text'])
            if nom:
                raise ValueError('pays sans nombre : ' + ' '.join(nom))
            if abs(somme - nombre(tot['text'])) > 0.5:
                raise ValueError('la somme des pays (%d) ne redonne pas le total (%s)' % (somme, tot['text']))
            if y != ed - 2:
                raise ValueError("l'édition %d donne l'année %d" % (ed, y))
        except Exception as e:
            ECARTEES.append(('medicaments', ed, str(e)))
            continue
        for g, v in lus.items():
            _meur.setdefault(g, {})[y] = v
    return _meur


def medicaments():
    """Ventes de médicaments rapportées au PIB (Eurostat nama_10_gdp, B1GQ, CP_MEUR), en %."""
    md = medicaments_meur()
    garde = U.UE[:]
    U.UE[:] = garde + [g for g in HORS if g not in garde]
    try:
        pib = U.pib_euros()
    finally:
        U.UE[:] = garde
    return {g: {y: 100 * v / pib[g][y] for y, v in a.items() if pib.get(g, {}).get(y)} for g, a in md.items()}


def comparer(nom, lu, ref, pays, dec, cle=None):
    """Tableau : valeur lue / valeur publiée dans data.json, pour chaque pays et chaque année ; rend (accords, écarts)."""
    ok, ko = 0, []
    print('\n%s' % nom)
    print('  %-5s' % 'année' + ''.join('%14s' % g for g in pays))
    for i, y in enumerate(ref['y']):
        cases = []
        for g in pays:
            pub = (ref[cle][g.lower()] if cle else ref.get(g.lower()))
            p = pub[i] if pub and i < len(pub) else None
            w = lu.get('ue' if g == 'UE' else g, {}).get(y)
            if p is None and w is None:
                cases.append('%14s' % '-')
                continue
            wr = None if w is None else round(w, dec)
            egal = p is not None and wr is not None and abs(wr - p) < 1e-9
            ok += egal
            if not egal:
                ko.append((g, y, wr, p))
            cases.append('%14s' % ('%s/%s %s' % (wr, p, '=' if egal else '≠')))
        print('  %-5d' % y + ''.join(cases))
    return ok, ko


def main():
    o = json.load(open(os.path.join(ROOT, 'data.json'), encoding='utf-8'))['series']['sante']
    res = {}
    for nom, f in (('wait_dispo', wait_dispo), ('wait_delai', wait_delai), ('medicaments', medicaments)):
        r = f()
        ans = sorted({y for a in r.values() for y in a})
        print('%s : %s' % (nom, ', '.join('%d : %d pays' % (y, sum(1 for g, a in r.items() if g != 'ue' and y in a)) for y in ans)))
        res[nom] = r
    print('\nÉditions écartées : ' + ('aucune' if not ECARTEES else ''))
    for s, ed, raison in ECARTEES:
        print('  %s, édition %d : %s' % (s, ed, raison))
    bilan = []
    bilan.append(comparer('Nouveaux médicaments disponibles (%) : lu / data.json', res['wait_dispo'], o['C']['wd'], ['FR', 'DE', 'UE'], 0))
    bilan.append(comparer("Délai d'accès (jours) : lu / data.json", res['wait_delai'], o['C']['wt'], ['FR', 'DE', 'UE'], 0))
    md = o['AFF']['medic']
    bilan.append(comparer('Ventes de médicaments (M€) : lu / data.json', medicaments_meur(), md, ['FR', 'DE', 'ES'], 0, cle='md'))
    bilan.append(comparer('Ventes de médicaments (% du PIB) : lu / data.json', res['medicaments'], md, ['FR', 'DE', 'ES'], md.get('dec', 2)))
    ok = sum(b[0] for b in bilan)
    ko = [x for b in bilan for x in b[1]]
    print('\n%d chiffres identiques, %d différents ou absents' % (ok, len(ko)))
    for g, y, w, p in ko:
        print('  %s %d : lu %s, publié %s' % (g, y, w, p))
    return 1 if ko or ECARTEES else 0


if __name__ == '__main__':
    sys.exit(main())
