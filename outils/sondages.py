#!/usr/bin/env python3
"""Mentions légales des sondages du Baromètre, lues dans les notices de la Commission des sondages.

La loi du 19 juillet 1977 (modifiée en 2016) impose, avec tout sondage publié : l'organisme, le commanditaire, le nombre
de personnes interrogées, les dates du terrain, la marge d'erreur, et le droit de consulter la notice à la Commission
des sondages. Pour chaque sondage de datasets.sondages_t1 et sondages_t2, l'outil cherche sa notice dans la liste
officielle « 2027 - Présidentielle » (même institut, publiée dans les jours qui suivent le terrain, même nombre de
personnes interrogées), la lit (PDF) et en tire le commanditaire et la phrase sur la marge d'erreur.

  python3 outils/sondages.py            affiche ce qui est trouvé, sans rien écrire
  python3 outils/sondages.py --ecrire   écrit datasets.sondages_notices dans data.json

Un sondage dont la notice n'est pas encore en ligne peut être publié avec ses mentions lues dans le rapport complet de
l'institut ou du média (datasets.sondages_rapports, rempli par la tâche quotidienne : date, institut, terrain, echantillon,
commanditaire, marge, url du rapport) : il reçoit alors une ligne « statut : rapport », affichée avec la mention « notice
pas encore publiée par la Commission des sondages ». À chaque passage, l'outil recherche sa notice ; dès qu'elle est en
ligne, elle devient la référence, la ligne du rapport est retirée et tout écart (commanditaire, échantillon, marge) est
affiché. Sans notice ni rapport, un sondage n'a pas de ligne : la page ne l'affiche pas.
Code de sortie 1 si le site de la Commission est injoignable (rien n'est écrit)."""
import html, json, os, re, subprocess, sys, tempfile
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ue_calc as U

ROOT = U.ROOT
CDS = 'https://www.commission-des-sondages.fr'
LISTE = CDS + '/notices/medias/fichiers/bytag/14/2027-Presidentielle'
CACHE = os.path.join(tempfile.gettempdir(), 'concret-notices')
MOIS = {'janvier': 1, 'fevrier': 2, 'février': 2, 'mars': 3, 'avril': 4, 'mai': 5, 'juin': 6, 'juillet': 7, 'aout': 8, 'août': 8,
        'septembre': 9, 'octobre': 10, 'novembre': 11, 'decembre': 12, 'décembre': 12}
# Nom de l'institut dans data.json → mots qui le désignent dans le titre des notices.
INSTITUT = {'harris': r'harris|\bthi\b', 'harris interactive': r'harris|\bthi\b', 'ipsos': r'ipsos', 'cluster17': r'cluster ?17',
            'opinionway': r'opinion ?way', 'ifop': r'ifop', 'elabe': r'elabe', 'odoxa': r'odoxa', 'verian': r'verian', 'yougov': r'yougov'}


def get_bin(url):
    r = subprocess.run(['curl', '-sSf', '--max-time', '120', '-A', 'Mozilla/5.0 (concret2027.fr)', url], capture_output=True)
    if r.returncode:
        raise IOError('téléchargement impossible : ' + url)
    return r.stdout


def redirection(url):
    """Adresse du PDF : le site renvoie vers http://…, on la reprend en https."""
    r = subprocess.run(['curl', '-sSI', '--max-time', '60', url], capture_output=True, text=True)
    m = re.search(r'^location:\s*(\S+)', r.stdout, re.I | re.M)
    return m.group(1).replace('http://', 'https://') if m else None


def liste():
    # La liste « 2027 - Présidentielle », et la page générale des notices (certaines n'ont pas l'étiquette).
    s = get_bin(LISTE).decode('utf-8', 'replace') + get_bin(CDS + '/notices/').decode('utf-8', 'replace')
    out, vus = [], set()
    for h, t in re.findall(r'href="(/notices/medias/fichiers/add/\d+)"[^>]*>(.*?)</a>', s, re.S):
        t = html.unescape(re.sub(r'<[^>]+>|\s+', ' ', t)).strip()
        m = re.search(r'(\d{1,2})(?:er)?\s+([a-zéû]+)\s*$', t, re.I)
        if m and m.group(2).lower() in MOIS and h not in vus:
            vus.add(h)
            out.append({'add': CDS + h, 'titre': t, 'jour': int(m.group(1)), 'mois': MOIS[m.group(2).lower()]})
    return out


def texte(n):
    """Texte des premières pages de la notice (méthode, échantillon, marge), mis en cache le temps de la session."""
    os.makedirs(CACHE, exist_ok=True)
    f = os.path.join(CACHE, re.sub(r'\W', '_', n['add'].split('/')[-1]) + '.txt')
    if os.path.exists(f):
        return open(f, encoding='utf-8').read(), open(f + '.url', encoding='utf-8').read()
    url = redirection(n['add'])
    if not url:
        return '', ''
    pdf = os.path.join(CACHE, 'n.pdf')
    open(pdf, 'wb').write(get_bin(url))
    t = subprocess.run(['pdftotext', '-layout', '-l', '12', pdf, '-'], capture_output=True, text=True).stdout
    open(f, 'w', encoding='utf-8').write(t); open(f + '.url', 'w', encoding='utf-8').write(url)
    return t, url


def fin_terrain(p):
    """Dernier jour du terrain (date ISO du sondage dans data.json)."""
    return date.fromisoformat(p['date'])


def fin_interviews(t):
    """Derniers jours des interviews que la notice écrit (« Les interviews ont été réalisées du 9 au 10 septembre 2026 ») :
    liste de (jour, mois). Vide si la notice ne le dit pas sous cette forme (rien n'est alors écarté sur la date)."""
    noms = '|'.join(MOIS)
    rx = r'réalisée?s?\s+du\s+\d{1,2}(?:er)?(?:\s+(?:%s))?\s+au\s+(\d{1,2})(?:er)?\s+(%s)' % (noms, noms)
    return [(int(j), MOIS[m.lower()]) for j, m in re.findall(rx, re.sub(r'\s+', ' ', t), re.I) if m.lower() in MOIS]


def chiffre(n):
    return re.compile(r'(?<!\d)' + r'[\s  .]?'.join(str(n)) + r'(?!\d)')


def commanditaire(t, titre):
    """Le commanditaire, tel que la notice l'écrit (chaque institut a sa formule), ligne par ligne."""
    lignes = [re.sub(r'\s+', ' ', l).strip() for l in t.split('\n')]
    coupe = lambda c: re.split(r'\s+[–—|-]\s+|\s{2,}| Nombre de | Première publication| Pour les rem|\s+\d{1,2}(?:er)? \w+ 20\d\d', c)[0].strip(' ,;:.✓')
    regles = [r"acheteur du sondage\s*:\s*(.+)", r"commanditaire\(?s?\)?\s*(?:du sondage)?\s*:\s*(.+)", r"Commanditaires? du sondage\s+(.+)",
              r"NOTICE TECHNIQUE\s*:\s*\S+(?:-\S+)?\s+pour\s+(.+?)(?:\s+\d+)?$", r"[ÉE]tude (?:r[ée]alis[ée]e )?(?:par \S+ )?\S* ?r[ée]alis[ée]e pour\s+(.+?)\s+aupr[eè]s",
              r"[ÉE]tude r[ée]alis[ée]e (?:par \S+ )?pour\s+(.+)", r"Enqu[êe]te r[ée]alis[ée]e pour\s+(?:le journal\s+)?(.+?)(?:\s+et publi[ée]e.*)?$",
              r"Notice \S+ pour\s+(.+?)\s+[–—-]"]
    # Tableau à deux colonnes (Ipsos) dont la valeur est coupée autour de l'intitulé « Commanditaires du sondage » :
    # la fin de la ligne d'avant et le début de celle d'après.
    for k, l in enumerate(lignes):
        if re.fullmatch(r"\W*Commanditaires? du sondage", l, re.I):
            av = next((x for x in reversed(lignes[:k]) if x), ''); ap = next((x for x in lignes[k + 1:] if x), '')
            if av and ap and not re.search(r'\d', ap) and not av.startswith('▪'):
                return (av + ' ' + ap).replace(' – ', ', ')
    trouves = []
    for rx in regles:
        for k, l in enumerate(lignes):
            m = re.search(rx, l, re.I)
            if m:
                c = coupe(m.group(1))
                # Phrase coupée en fin de ligne (« pour LCI, le Figaro et Sud ») : on recolle la ligne suivante si elle la complète.
                # Fin en capitales coupée (« … ET LE NOUVEL » / « OBS ») : on recolle le mot de la ligne suivante.
                if c.isupper() and k + 1 < len(lignes) and re.fullmatch(r"[A-ZÉÈ'’ ]{2,12}", lignes[k + 1]):
                    c = c + ' ' + lignes[k + 1]
                if re.search(r"\b(?:et|de|du|la|le)$", c, re.I) and k + 1 < len(lignes):
                    c = (c + ' ' + coupe(lignes[k + 1]).split('  ')[0]).strip()
                if 1 < len(c) < 80 and not re.match(r"(?i)(?:la commission|les sondages|une valeur|les remercier|d['’]un)", c):
                    trouves.append(c)
    if not trouves:
        return None
    # Deux formules pour le même commanditaire (en-tête abrégé « Ifop pour le vote blanc », phrase complète « Ifop pour
    # le Parti du vote blanc ») : on garde la plus complète, celle qui contient les mots de l'autre.
    mots = lambda c: set(re.findall(r"\w+", c.lower()))
    c = trouves[0]
    for d in trouves[1:]:
        if len(d) > len(c) and mots(c) <= mots(d):
            c = d
    return c


def _f(x):
    return float(x.replace(',', '.'))


def marge(t, echantillon):
    """Marge d'erreur des intentions de vote, telle que la notice la donne : (plus petite, plus grande) en points.
    1. La phrase de la notice (« entre plus ou moins 1,4 et 3,1 points ») ;
    2. sinon la ligne du tableau des marges qui correspond à la base des intentions de vote (ou au premier
       échantillon cité), dont on prend la plus petite et la plus grande valeur ;
    3. sinon, pour un tableau générique (taille d'échantillon × score), la ligne de la base des intentions de vote
       citée par la notice. Rien trouvé : None (la page renvoie à la notice, le contrôle le signale)."""
    plat = re.sub(r'\s+', ' ', t)
    m = re.search(r"marges? d.(?:erreur|incertitude)[^.]{0,200}?entre (?:plus ou moins |± ?)?(\d+,\d+) et (?:plus ou moins |± ?)?(\d+,\d+) ?(?:points|pts|point)", plat, re.I)
    if m:
        return _f(m.group(1)), _f(m.group(2)), 'phrase'
    lignes = [re.sub(r'[ \t]+', ' ', l).strip() for l in t.split('\n')]
    row = lambda l: [_f(x) for x in re.findall(r'(?<![\d,])(\d{1,2},\d{1,2}|\d)(?![\d,])', l)]
    # Ligne étiquetée « intention(s) de vote » (Verian) : la base des intentions de vote.
    for k, l in enumerate(lignes):
        if re.search(r'intention', l, re.I):
            for l2 in (l, lignes[k + 1] if k + 1 < len(lignes) else ''):
                m2 = re.match(r'(?:.*?\b)?(\d{3,5}) ((?:\d{1,2},\d ?){5,})$', l2)
                if m2:
                    v = row(m2.group(2)); return min(v), max(v), 'tableau (intentions de vote)'
    # « La marge d'erreur est de : 1,4 1,9 … » (OpinionWay, YouGov) : la première ligne est le premier échantillon cité.
    for l in lignes:
        m2 = re.search(r"marge d.erreur est de\s*:?\s*((?:\d{1,2},\d{1,2}\s*){5,})", l, re.I)
        if m2:
            v = row(m2.group(1)); return min(v), max(v), 'tableau'
    # Lignes « 1943 personnes 1 1,3 … » (Cluster17) : celle de l'échantillon publié, sinon la première.
    rows = [(int(m2.group(1)), row(m2.group(2))) for m2 in (re.match(r'(\d{3,5}) personnes ((?:[\d,]+ ?){6,})$', l) for l in lignes) if m2]
    if rows:
        e = int(echantillon or 0); r = [x for x in rows if x[0] == e] or rows
        return min(r[0][1]), max(r[0][1]), 'tableau'
    # Tableau générique (Ifop, Ipsos) : base des intentions de vote citée, ligne de la taille la plus proche.
    mb = re.search(r"certaine?s? d.aller voter interrog[ée]es?, (\d[\d  ]*\d) personnes ont exprim", plat, re.I) or re.search(r"(?:base|parmi|dont)[^.]{0,80}?(\d[\d  ]{2,6}\d) (?:personnes )?(?:inscrites? )?(?:sur les listes )?[^.]{0,40}?(?:certaine?s? d.aller voter|intentions de vote|exprim)", plat, re.I) \
        or re.search(r"[ée]chantillon de (\d[\d  ]{2,6}\d) personnes \(Base intentions de vote", plat, re.I)
    tab = [(int(re.sub(r'\D', '', m2.group(1))), row(m2.group(2))) for m2 in (re.match(r'(\d[\d ]{1,5}\d) ((?:\d{1,2},\d ?){5,})', l) for l in lignes) if m2]
    if mb and tab:
        n = int(re.sub(r'\D', '', mb.group(1)))
        # La ligne du tableau la plus proche sans dépasser la base (marge un peu plus large, jamais plus étroite).
        sous = [x for x in tab if x[0] <= n] or tab
        r = max(sous, key=lambda x: x[0])
        return min(r[1]), max(r[1]), 'tableau (base %d, ligne %d)' % (n, r[0])
    # Tableau illisible dans le PDF mais échantillon cité (« Pour un échantillon de 901 et 683 personnes ») : les
    # valeurs du tableau sont celles de la formule standard à 95 %, de 5 % à 50 % ; on la reprend pour le premier cité.
    me = re.search(r"Pour un [ée]chantillon de (\d[\d  ]*\d)(?: et| ,|,| personnes)", plat)
    if me and re.search(r"marge d.erreur est de", plat, re.I):
        n = int(re.sub(r'\D', '', me.group(1)))
        f = lambda p: round(196 * (p * (1 - p) / n) ** .5, 1)
        return f(.05), f(.5), 'formule du tableau (échantillon de %d)' % n
    return None


def main():
    ecrire = '--ecrire' in sys.argv
    o = json.load(open(os.path.join(ROOT, 'data.json'), encoding='utf-8'))
    D = o['datasets']
    polls = {}
    for r in D.get('sondages_t1', []):
        polls.setdefault((r['date'], r['institut']), {'date': r['date'], 'institut': r['institut'], 'terrain': r.get('terrain', ''), 'echantillon': r.get('echantillon', '')})
    for r in D.get('sondages_t2', []):
        polls.setdefault((r['date'], r['institut'].replace(' Interactive', '')), {'date': r['date'], 'institut': r['institut'].replace(' Interactive', ''), 'terrain': '', 'echantillon': ''})
    try:
        N = liste()
    except Exception as e:
        print('Sondages ✗ site de la Commission des sondages injoignable (%s). Rien écrit.' % e); sys.exit(1)
    out, manque, remplaces, prises = [], [], [], set()
    R = {(r['date'], r['institut'].replace(' Interactive', '')): r for r in D.get('sondages_rapports', [])}
    for k in sorted(polls):
        p = polls[k]
        fin = fin_terrain(p)
        rx = INSTITUT.get(p['institut'].lower(), re.escape(p['institut']))
        cands = []
        for n in N:
            if not re.search(rx, n['titre'], re.I):
                continue
            for an in (fin.year, fin.year + 1):
                try:
                    d = date(an, n['mois'], n['jour'])
                except ValueError:
                    continue
                if fin - timedelta(days=1) <= d <= fin + timedelta(days=45):
                    cands.append((abs((d - fin).days), n))
        cands.sort(key=lambda x: x[0])
        trouve = None
        for _, n in cands:
            t, url = texte(n)
            if not t:
                continue
            # La notice doit porter le même nombre de personnes interrogées (quand on le connaît).
            if p['echantillon'] and not chiffre(p['echantillon']).search(t):
                continue
            # Une notice ne vaut que pour un sondage ; et ses interviews doivent finir le dernier jour du terrain
            # (l'institut publie parfois deux sondages de suite, avec le même nombre de personnes interrogées).
            if n['titre'].split()[0] in prises:
                continue
            fi = fin_interviews(t)
            if fi and (fin.day, fin.month) not in fi:
                continue
            trouve = (n, t, url); break
        rap = R.get(k)
        if not trouve:
            if rap:
                # Notice pas encore en ligne : les mentions lues dans le rapport de l'institut, en attendant.
                out.append({'date': p['date'], 'institut': p['institut'], 'terrain': rap.get('terrain') or p['terrain'], 'echantillon': rap.get('echantillon') or p['echantillon'],
                            'commanditaire': rap.get('commanditaire', ''), 'marge': rap.get('marge', ''), 'notice': '', 'url': rap.get('url', ''), 'statut': 'rapport'})
                print('%s %-11s notice pas encore en ligne : mentions du rapport (%s)' % (p['date'], p['institut'], rap.get('url', '')))
                continue
            manque.append(p); continue
        n, t, url = trouve
        c = commanditaire(t, n['titre'])
        mg = marge(t, p['echantillon'])
        num = n['titre'].split()[0]; prises.add(num)
        ligne = {'date': p['date'], 'institut': p['institut'], 'terrain': p['terrain'], 'echantillon': p['echantillon'],
                 'commanditaire': c or '', 'marge': ('%s à %s' % (('%.1f' % mg[0]).replace('.', ','), ('%.1f' % mg[1]).replace('.', ','))) if mg else '', 'notice': num, 'url': url}
        out.append(ligne)
        if rap:
            # La notice est arrivée : elle remplace le rapport ; on signale ce qui diffère.
            ecarts = [ch for ch in ('commanditaire', 'echantillon', 'marge') if rap.get(ch) and ligne[ch] and str(rap[ch]).strip().lower() != str(ligne[ch]).strip().lower()]
            print('%s %-11s notice %s en ligne : elle remplace le rapport%s' % (p['date'], p['institut'], num, (' ; ÉCART ' + ', '.join('%s : rapport « %s », notice « %s »' % (ch, rap[ch], ligne[ch]) for ch in ecarts)) if ecarts else ', mentions identiques'))
            remplaces.append(k)
        print('%s %-11s notice %-6s commanditaire : %-30s marge : %s' % (p['date'], p['institut'], num, c or '(non lu)', ('%s-%s (%s)' % mg if mg else '(non lue)')))
    print('\n%d sondages avec notice, %d sans notice retrouvée :' % (len(out), len(manque)))
    for p in manque:
        print('   %s %s %s (%s personnes)' % (p['date'], p['institut'], p['terrain'], p['echantillon'] or '?'))
    if ecrire:
        D['sondages_notices'] = out
        if 'sondages_rapports' in D:
            D['sondages_rapports'] = [r for r in D['sondages_rapports'] if (r['date'], r['institut'].replace(' Interactive', '')) not in remplaces]
        open(os.path.join(ROOT, 'data.json'), 'w', encoding='utf-8').write(json.dumps(o, indent=0, ensure_ascii=False))
        print('Écrit : datasets.sondages_notices (%d lignes).' % len(out))


if __name__ == '__main__':
    main()
