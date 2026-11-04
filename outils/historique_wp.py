"""Lit les tableaux « Sondages concernant le premier tour » d'une liste de sondages de Wikipédia (wikitexte brut).
Sortie JSON : une ligne par hypothèse {debut, fin, institut, echantillon, scores{candidat: score}, table, ligne}.
"""
import sys, re, json, datetime as D
import wikitextparser as wtp

MOIS = {'janv': 1, 'janvier': 1, 'jan': 1, 'févr': 2, 'fév': 2, 'février': 2, 'fevrier': 2, 'fev': 2, 'mars': 3, 'mar': 3,
        'avr': 4, 'avril': 4, 'mai': 5, 'juin': 6, 'juil': 7, 'juillet': 7, 'août': 8, 'aout': 8, 'sept': 9, 'sep': 9,
        'septembre': 9, 'oct': 10, 'octobre': 10, 'nov': 11, 'novembre': 11, 'déc': 12, 'dec': 12, 'décembre': 12, 'decembre': 12}
RM = r'(janvier|janv|jan|février|fevrier|févr|fév|fev|mars|mar|avril|avr|mai|juin|juillet|juil|août|aout|septembre|sept|sep|octobre|oct|novembre|nov|décembre|decembre|déc|dec)\.?'


def tpl_date(s):
    # {{date|23|Avril|2017}} → 23 Avril 2017 ; {{date|17 décembre 2015}} → 17 décembre 2015 ; {{date-|...}} pareil
    return re.sub(r'\{\{\s*date-?\s*\|([^{}]*)\}\}', lambda m: ' '.join(x for x in m.group(1).split('|') if '=' not in x), s, flags=re.I)


def nettoie(s):
    s = tpl_date(s or '')
    s = re.sub(r'<ref[^>]*/>', '', s); s = re.sub(r'<ref[^>]*>.*?</ref>', '', s, flags=re.S)
    s = re.sub(r'\{\{\s*formatnum\s*:\s*([^{}]*)\}\}', r'\1', s)
    s = re.sub(r'\{\{\s*(?:nobr|nowrap)\s*\|([^{}]*)\}\}', r'\1', s, flags=re.I)
    s = re.sub(r'\{\{\s*(?:1er|er)\s*\}\}', '1', s)
    s = re.sub(r'\{\{\s*(?:blanc|noir|gras|b)\s*\|([^{}]*)\}\}', r'\1', s, flags=re.I)
    s = re.sub(r'\{\{[^{}]*\}\}', ' ', s)
    s = re.sub(r'\{\{[^{}]*\}\}', ' ', s)
    s = s.replace('&nbsp;', ' ').replace(' ', ' ').replace('&#8209;', '-')
    s = re.sub(r'<[^>]+>', ' ', s)
    s = re.sub(r"'{2,}", '', s)
    s = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', s)
    s = re.sub(r'\[https?://\S+\s+([^\]]*)\]', r'\1', s)
    s = re.sub(r'\[https?://\S+\]', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def lien(s):
    m = re.search(r'\[(https?://\S+)', s or '')
    return m.group(1) if m else ''


def legende(t):
    """Mois et année de la légende du tableau (« Mars 2017 », « Sondages de 2015 », « Octobre-novembre 2021 »)."""
    c = nettoie(t.caption or '')
    ys = re.findall(r'(20\d\d)', c)
    ms = [MOIS[m.lower().rstrip('.')] for m in re.findall(RM, c, flags=re.I)]
    return (ms[-1] if len(ms) == 1 else None), (int(ys[-1]) if ys else None), c


def date_fin(txt, mois_leg, an_leg, an_def):
    t = txt.lower().replace('1er', '1')
    t = re.sub(r'\s*(?:-|–|—| au | et |/)\s*', ' | ', ' ' + t + ' ')
    parts = [p.strip() for p in t.split('|') if p.strip()]
    if not parts: return None, None
    def lit(p, m_def, y_def):
        md = re.search(r'(\d{1,2})', p)
        mm = re.search(RM, p, flags=re.I)
        my = re.search(r'(20\d\d)', p)
        if not md: return None
        return int(md.group(1)), (MOIS[mm.group(1)] if mm else m_def), (int(my.group(1)) if my else y_def)
    an = an_leg or an_def
    f = lit(parts[-1], mois_leg, an)
    if not f or not f[1] or not f[2]: return None, None
    try: fin = D.date(f[2], f[1], f[0])
    except ValueError: return None, None
    deb = fin
    if len(parts) > 1:
        s = lit(parts[0], f[1], f[2])
        if s:
            try:
                deb = D.date(s[2], s[1], s[0])
                if deb > fin:  # « 28 au 2 » : le début est le mois d'avant
                    deb = D.date(deb.year - (1 if deb.month == 1 else 0), 12 if deb.month == 1 else deb.month - 1, s[0]) if s[1] == f[1] else D.date(deb.year - 1, deb.month, deb.day)
            except ValueError: deb = fin
    return deb, fin


def score(c):
    t = nettoie(c)
    if re.search(r'\d', t) and '%' not in t and re.fullmatch(r'[<\s]*\d+(?:[.,]\d+)?\s*', t):
        t = t + ' %'
    m = re.findall(r'(\d+(?:[.,]\d+)?)\s*%', t)
    if not m: return None
    return float(m[-1].replace(',', '.'))


def nom(c):
    m = re.search(r'\[\[([^|\]]+)(?:\|[^\]]*)?\]\]', c or '')
    if m and not m.group(1).lower().startswith(('fichier:', 'file:', 'image:')): return m.group(1).strip()
    m = re.search(r'link=([^|\]]+)', c or '')
    if m: return m.group(1).strip()
    return None


def main(path, an_def, tour='premier', mini=3, nom_cellule=False):
    # nom_cellule : une case peut nommer un autre candidat que sa colonne (2027 : « 6,5 Hollande (PS) » dans la colonne de Glucksmann).
    src = open(path, encoding='utf-8').read()
    L = src.split('\n')
    # Section « Sondages concernant le premier tour » (2017, 2022) ou « Premier tour » (2012).
    a = next(i for i, l in enumerate(L) if re.match(r'^==\s*(Sondages concernant le )?' + tour + r' tour\s*==\s*$', l, re.I))
    b = next((i for i, l in enumerate(L) if i > a and re.match(r'^==[^=]', l)), len(L))
    sec = '\n'.join(L[a:b]); p = wtp.parse(sec)
    # Intertitres (« ==== Avril 2012 ==== », « === Année 2011 === ») : mois et année des tableaux sans légende.
    titres = [(m.start(), nettoie(m.group(1))) for m in re.finditer(r'^={3,5}\s*(.*?)\s*={3,5}\s*$', sec, re.M)]
    out, rejets = [], []
    an_courant = an_def
    for k, t in enumerate(p.tables):
        try: d = t.data(span=True)
        except Exception as e: rejets.append(('table', k, str(e))); continue
        ml, yl, cap = legende(t)
        if not yl:
            avant = [x for x in titres if x[0] < t.span[0]]
            if avant:
                c2 = avant[-1][1]; ys = re.findall(r'(20\d\d)', c2); ms = [MOIS[m.lower().rstrip('.')] for m in re.findall(RM, c2, flags=re.I)]
                if ys: yl = int(ys[-1]); ml = ms[-1] if len(ms) == 1 else None; cap = c2
        if yl: an_courant = yl
        # Ligne des noms : celle qui a le plus de liens [[Nom]] ; colonnes Sondeur / Date / Échantillon.
        hi = None; best = 0
        for i, r in enumerate(d[:4]):
            if len(set(c for c in r if (c or '').strip())) <= 1: continue  # ligne d'événement
            n = sum(1 for c in r if nom(c))
            if n > best: best, hi = n, i
        cols = {}
        for i, r in enumerate(d[:4]):
            for j, c in enumerate(r):
                x = nettoie(c).lower()
                if x.startswith('sondeur') or x.startswith('institut'): cols.setdefault('s', j)
                elif x.startswith('date'): cols.setdefault('d', j)
                elif x.startswith('échantillon') or x.startswith('echantillon'): cols.setdefault('e', j)
        if hi is None or 'd' not in cols or 's' not in cols:
            rejets.append(('table sans en-tête', k, cap)); continue
        noms = {j: nom(c) for j, c in enumerate(d[hi]) if nom(c) and j not in cols.values()}
        for i, r in enumerate(d[hi + 1:], hi + 1):
            if len(r) <= max(cols.values()): continue
            if len(set(c for c in r if (c or '').strip())) <= 1: continue  # ligne d'événement (colspan)
            st = nettoie(r[cols['s']])
            if not st or st.lower().startswith(('résultat', 'resultat', 'sondeur')): continue
            deb, fin = date_fin(nettoie(r[cols['d']]), ml, yl, an_courant)
            if not fin: rejets.append(('date', k, i, st, nettoie(r[cols['d']]))); continue
            ech = re.sub(r'\D', '', nettoie(r[cols['e']])) if 'e' in cols else ''
            sc = {}
            for j, n in noms.items():
                if j < len(r):
                    v = score(r[j]); nc = None
                    if nom_cellule:
                        cel = re.sub(r'<ref[^>]*/>|<ref[^>]*>.*?</ref>', '', r[j] or ''); nc = nom(cel)
                        if v is None and nc:  # « 6,5 Hollande (PS) » : le chiffre en tête de la case
                            m = re.match(r'\s*(\d+(?:[.,]\d+)?)\b', nettoie(cel)); v = float(m.group(1).replace(',', '.')) if m else None
                    if v is None: continue
                    sc[nc or n] = v
            if len(sc) < mini: rejets.append(('scores', k, i, st, len(sc))); continue
            out.append({'debut': deb.isoformat(), 'fin': fin.isoformat(), 'institut': st, 'echantillon': ech, 'scores': sc,
                        'url': lien(r[cols['s']]), 'table': k, 'legende': cap})
    return out, rejets


if __name__ == '__main__':
    o, r = main(sys.argv[1], int(sys.argv[2]))
    json.dump({'lignes': o, 'rejets': r}, open(sys.argv[3], 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(len(o), 'lignes', len(r), 'rejets')
    from collections import Counter
    print(Counter(x[0] for x in r))
    for x in r[:25]: print(' ', x)
