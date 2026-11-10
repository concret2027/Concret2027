#!/usr/bin/env python3
"""Articles de presse qui citent les candidats (Baromètre, bloc « Par ailleurs »).

Lit les flux RSS/Atom publics du panel (donnees/presse_sources.json), garde une archive
des articles vus (titre, lien, date, candidats trouvés et où ; jamais le texte entier),
et fait le compte par jour (heure de Paris) des articles distincts qui citent chaque
candidat (donnees/presse_noms.json). Un flux en erreur est « indisponible », jamais zéro.

  python3 outils/presse.py                       relève et affiche, n'écrit rien
  python3 outils/presse.py --archive A --ecrire  relève et écrit l'archive A
  ... --agreger                                  écrit aussi donnees/presse.json
  ... --agreger-si-besoin                        seulement après 23 h 30 UTC, ou si hier manque
  ... --live L                                   écrit aussi, à chaque relevé, le compte du moment dans L
Candidats suivis : tous ceux testés dans les sondages de premier tour des 30 derniers jours (data.json,
datasets.sondages_t1), et seulement eux (règle de l'éditeur, 8 novembre 2026, ramenée de 60 à 30 jours le même jour). Chacun est compté à partir
du relevé où il entre dans la liste (archive['suivis']) : l'archive ne garde pas les chapeaux, on ne recompte pas le passé.
Chaque candidat est cherché par son nom de famille (règle dans presse_noms.json) ; à chaque compte, les titres archivés
sont relus avec la règle en vigueur (les chapeaux, non gardés, gardent ce qui y a été trouvé au relevé).
Bibliothèque standard seulement. Jamais de saisie à la main.
"""
import concurrent.futures as cf, datetime as dt, email.utils, html, json, os, re, sys, unicodedata, urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(RACINE, 'donnees', 'presse_sources.json')
NOMS = os.path.join(RACINE, 'donnees', 'presse_noms.json')
SORTIE = os.path.join(RACINE, 'donnees', 'presse.json')
DATA = os.path.join(RACINE, 'data.json')
JOURS_SONDAGES = 30
PREMIERS = ['Le Pen', 'Mélenchon', 'Philippe', 'Glucksmann', 'Attal', 'Retailleau', 'Lisnard', 'Zemmour']
TOUJOURS = []  # aucune exception : seulement les personnes testées dans les sondages (règle du 8 novembre 2026)
UA = 'Mozilla/5.0 (compatible; Concret/1.0; +https://concret2027.fr)'
PARIS = ZoneInfo('Europe/Paris')
GARDE_RELEVES = 2000  # relevés gardés dans l'archive (environ 40 jours)


def norm(s):
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r'[’‘`]', "'", re.sub(r'[‐-–­]', '-', re.sub(r'\s+', ' ', s)))


def texte(s):
    s = re.sub(r'<[^>]+>', ' ', html.unescape(s or ''))
    return re.sub(r'\s+', ' ', html.unescape(s)).strip()


def candidats_sondages(aujourdhui):
    """Toutes les personnes testées dans au moins un sondage de premier tour des 30 derniers jours."""
    rows = json.load(open(DATA, encoding='utf-8'))['datasets'].get('sondages_t1', [])
    debut = (aujourdhui - dt.timedelta(days=JOURS_SONDAGES)).isoformat()
    L = []
    for r in sorted(rows, key=lambda r: r['date']):
        if r['date'] >= debut and r['candidat'] not in L:
            L.append(r['candidat'])
    return L + [c for c in TOUJOURS if c not in L]


def regles(cfg, cands):
    """La règle de chaque candidat suivi ; un nom sans règle écrite est cherché par son nom de famille, son prénom lu dans sa page Wikipédia."""
    out, sans = {}, []
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from wikipedia import PAGES
    except Exception:
        PAGES = {}
    for c in cands:
        if c in cfg['candidats']:
            out[c] = cfg['candidats'][c]
        elif c in PAGES:
            out[c] = {'nom': c, 'prenoms': [PAGES[c].replace('_', ' ').split(' ')[0]], 'note': 'Cherché par son nom de famille, comme les autres (règle par défaut, sans exclusion propre, à revoir).'}
        else:
            sans.append(c)
    return out, sans


def norm_c(s):
    """Comme norm, mais garde les majuscules : le nom est cherché avec sa majuscule."""
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[’‘`]', "'", re.sub(r'[‐-–­]', '-', re.sub(r'\s+', ' ', s)))


def compile_noms(cfg, autorises=()):
    """Règle commune (presse_noms.json) : le nom de famille, mot entier, avec sa majuscule (ou tout en capitales)."""
    aut = {norm(w) for w in autorises}
    out = {}
    for c, r in cfg.items():
        nom = norm_c(r.get('nom') or c)
        rx = re.compile(r"(?<![\w-])(?:" + re.escape(nom) + '|' + re.escape(nom.upper()) + r")(?![\w])")
        out[c] = {'rx': rx, 'prenoms': {norm(x) for x in r.get('prenoms', [])}, 'aut': aut,
                  'avant': {norm(x) for x in r.get('exclure_avant', [])}, 'apres': [norm_c(x) for x in r.get('exclure_apres', [])],
                  'apres_rx': [re.compile(x) for x in r.get('exclure_apres_rx', [])], 'contient': [norm_c(x) for x in r.get('exclure_si_contient', [])],
                  'prenom_si_suivi': r.get('prenom_si_suivi', False), 'particule': r.get('particule', False)}
    return out


MOT_AVANT = re.compile(r"([\w'.-]+) $")


def _prenom(tok, R):
    """Un mot à majuscule juste avant le nom, qui n'est ni le prénom du candidat, ni un titre, ni un mot courant : un autre prénom."""
    tok = re.sub(r"^[dlDL]'", '', tok)
    if not tok or not tok[0].isupper() or tok.isupper() or any(ch.isdigit() for ch in tok):
        return False
    return norm(tok) not in R['prenoms'] and norm(tok) not in R['aut']


def pourquoi_pas(t, m, R):
    """None si l'occurrence compte, sinon la raison de l'écarter."""
    av = MOT_AVANT.search(t[:m.start()])
    tok = av.group(1) if av else ''
    if tok and norm(re.sub(r"^[dlDL]'", '', tok)) in R['prenoms']:
        return None  # « Édouard Philippe », « François Hollande »
    if tok and norm(tok) in R['avant']:
        return 'avant'
    suite = t[m.end():]
    if any(suite.startswith(a) for a in R['apres']) or any(x.search(suite) for x in R['apres_rx']):
        return 'apres'
    if any(x in t for x in R['contient']):
        return 'contient'
    if R['prenom_si_suivi'] and re.match(r" (?:(?:de|du|d') ?)?[A-Z][a-z]", suite):
        return 'prenom'  # « Philippe Martinez », « Philippe de Villiers »
    if tok and _prenom(tok, R):
        return 'autre prenom'
    if R['particule'] and tok in ('de', 'du'):
        av2 = MOT_AVANT.search(t[:av.start()])
        if av2 and norm(av2.group(1)) not in R['prenoms'] and _prenom(av2.group(1), R):
            return 'autre prenom'
    return None


def trouve(t, R):
    """t : texte passé par norm_c (accents retirés, majuscules gardées)."""
    return any(pourquoi_pas(t, m, R) is None for m in R['rx'].finditer(t))


def local(tag):
    return tag.rsplit('}', 1)[-1]


def enfant(el, *noms):
    for x in el:
        if local(x.tag) in noms:
            if local(x.tag) == 'link' and x.get('href'):
                if x.get('rel', 'alternate') == 'alternate':
                    return x.get('href')
                continue
            return ''.join(x.itertext())
    return ''


def date_de(s, lien):
    s = (s or '').strip()
    d = None
    if s:
        try:
            d = email.utils.parsedate_to_datetime(s)
        except Exception:
            try:
                d = dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
            except Exception:
                d = None
        if d is not None and d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        if d is not None and d.year < 100:  # « 07 Nov 26 »
            d = d.replace(year=d.year + 2000)
    if d is None:  # Le Parisien : pas de date dans le flux, la date est dans l'adresse (-07-11-2026-)
        m = re.search(r'-(\d\d)-(\d\d)-(20\d\d)-', lien or '')
        if m:
            return '%s-%s-%s' % (m.group(3), m.group(2), m.group(1)), None
        return None, None
    p = d.astimezone(PARIS)
    return p.date().isoformat(), p.isoformat(timespec='minutes')


def lire(src):
    req = urllib.request.Request(src['rss_url'], headers={'User-Agent': UA, 'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml', 'Accept-Encoding': 'identity'})
    with urllib.request.urlopen(req, timeout=15) as r:
        b = r.read(8_000_000)
    if b[:2] == b'\x1f\x8b':  # certains serveurs compressent sans qu'on l'ait demandé
        import gzip
        b = gzip.decompress(b)
    racine = ET.fromstring(b)
    items = []
    for el in racine.iter():
        if local(el.tag) not in ('item', 'entry'):
            continue
        lien = (enfant(el, 'link') or '').strip()
        guid = (enfant(el, 'guid', 'id') or '').strip()
        titre = texte(enfant(el, 'title'))
        desc = texte(enfant(el, 'description', 'summary'))[:1200]
        jour, quand = date_de(enfant(el, 'pubDate', 'published', 'updated', 'date'), lien)
        if titre and (lien or guid):
            items.append({'guid': guid, 'lien': lien, 'titre': titre, 'desc': desc, 'jour': jour, 'quand': quand})
    if not items:
        raise ValueError('aucun article dans le flux')
    return items


GDELT = 'http://data.gdeltproject.org/gdeltv2/'


def lire_gdelt(archive, maintenant, domaines):
    """Pour les médias sans flux public utilisable : leurs articles en français dans les fichiers publics GKG de GDELT
    (flux « translation », un fichier toutes les 15 minutes), depuis le dernier fichier lu (archive['gdelt_t']).
    Renvoie ({domaine: [articles]}, None) ou (None, erreur). Titre seulement (PAGE_TITLE), pas de chapeau."""
    import csv, io, zipfile
    csv.field_size_limit(10 ** 9)
    try:
        der = urllib.request.urlopen(GDELT + 'lastupdate-translation.txt', timeout=30).read().decode()
        t_fin = dt.datetime.strptime(re.search(r'/(\d{14})\.translation\.gkg', der).group(1), '%Y%m%d%H%M%S').replace(tzinfo=dt.timezone.utc)
    except Exception as e:
        return None, ('GDELT : ' + type(e).__name__ + ': ' + str(e))[:160]
    t0 = archive.get('gdelt_t')
    t = dt.datetime.fromisoformat(t0) + dt.timedelta(minutes=15) if t0 else t_fin - dt.timedelta(hours=3)
    t = max(t, t_fin - dt.timedelta(hours=12))
    out, lus = {d: [] for d in domaines}, 0
    while t <= t_fin:
        u = GDELT + t.strftime('%Y%m%d%H%M%S') + '.translation.gkg.csv.zip'
        try:
            z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(u, timeout=60).read()))
            for row in csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding='utf-8', errors='replace'), delimiter='\t'):
                if len(row) < 27 or 'srclc:fra' not in row[25]:
                    continue
                dom = '.'.join(row[3].lower().split('.')[-2:])
                if dom not in out:
                    continue
                m = re.search(r'<PAGE_TITLE>(.*?)</PAGE_TITLE>', row[26])
                if not m:
                    continue
                q = dt.datetime.strptime(row[1], '%Y%m%d%H%M%S').replace(tzinfo=dt.timezone.utc).astimezone(PARIS)
                out[dom].append({'guid': '', 'lien': row[4], 'titre': texte(m.group(1)), 'desc': '', 'jour': q.date().isoformat(), 'quand': q.isoformat(timespec='minutes')})
            lus += 1
        except Exception:
            pass  # fichier absent (GDELT en saute parfois un) : on passe au suivant
        archive['gdelt_t'] = t.isoformat()
        t += dt.timedelta(minutes=15)
    if not lus:
        return None, 'GDELT : aucun fichier lu'
    return out, None


def fid(s):
    """Identifiant d'un flux : le nom du média, suivi du nom du flux quand le média en a plusieurs."""
    return s['name'] + (' · ' + s['flux'] if s.get('flux') else '')


def premiers(sources):
    """Une ligne par média : son premier flux actif, sinon sa première ligne."""
    vus = {}
    for s in sorted(sources, key=lambda s: not s.get('active')):
        vus.setdefault(s['name'], s)
    return [s for s in sources if vus.get(s['name']) is s]


def cle_lien(u):
    return re.sub(r'[?#].*$', '', (u or '').strip()).rstrip('/').replace('http://', 'https://')


def releve(archive, sources, noms, maintenant):
    actifs = [s for s in sources if s.get('active')]
    rss = [s for s in actifs if not s.get('gdelt')]
    with cf.ThreadPoolExecutor(24) as ex:
        res = dict(zip([fid(s) for s in rss], ex.map(lambda s: _essai(s), rss)))
    gd = [s for s in actifs if s.get('gdelt')]
    if gd:
        G, err = lire_gdelt(archive, maintenant, {s['gdelt'] for s in gd})
        for s in gd:
            res[fid(s)] = err if err else G.get(s['gdelt'], [])
    vus_guid = {a['guid'] for a in archive['articles'] if a.get('guid')}
    vus_lien = {cle_lien(a['lien']) for a in archive['articles'] if a.get('lien')}
    jour_releve = maintenant.astimezone(PARIS).date().isoformat()
    nouveaux, erreurs = 0, []
    for s in actifs:
        r = res[fid(s)]
        if isinstance(r, str):
            erreurs.append({'media': fid(s), 'erreur': r})
            continue
        for it in r:
            k = cle_lien(it['lien'])
            if (it['guid'] and it['guid'] in vus_guid) or (k and k in vus_lien):
                continue
            titre_n, desc_n = norm_c(it['titre']), norm_c(it['desc'])
            cites = {}
            for c, regle in noms.items():
                if trouve(titre_n, regle):
                    cites[c] = 'titre'
                elif trouve(desc_n, regle):
                    cites[c] = 'chapeau'
            archive['articles'].append({'guid': it['guid'], 'lien': it['lien'], 'titre': it['titre'][:300], 'media': s['name'],
                                        'jour': it['jour'] or jour_releve, 'date_lue': bool(it['jour']), 'quand': it['quand'],
                                        'vu': maintenant.isoformat(timespec='minutes'), 'cites': cites})
            if it['guid']:
                vus_guid.add(it['guid'])
            if k:
                vus_lien.add(k)
            nouveaux += 1
    archive.setdefault('debut', jour_releve)
    archive['releves'].append({'t': maintenant.isoformat(timespec='minutes'), 'jour': jour_releve, 'attendus': len(actifs),
                               'lus': len(actifs) - len(erreurs), 'erreurs': erreurs,
                               'noms_lus': sorted({fid(x) for x in actifs} - {e['media'] for e in erreurs})})
    archive['releves'] = archive['releves'][-GARDE_RELEVES:]
    return nouveaux, erreurs


def _essai(s):
    try:
        return lire(s)
    except Exception as e:
        return (type(e).__name__ + ': ' + str(e))[:160]


def recompte(a, noms):
    """Les candidats cités, selon la règle en vigueur : le titre est relu (il est gardé dans l'archive) ; le chapeau ne l'est pas
    (il n'est pas gardé) : un candidat trouvé dans le chapeau lors du relevé reste compté."""
    t = norm_c(a['titre'])
    cites = {c: 'titre' for c, R in noms.items() if trouve(t, R)}
    for c, ou in a.get('cites', {}).items():
        if ou == 'chapeau' and c not in cites:
            cites[c] = 'chapeau'
    return cites


VIDES = set(norm(w) for w in '''a à au aux avec ce ces cet cette dans de des du elle en et est être il ils je la le les leur leurs lui mais me même ne ni nos notre nous on ou où par pas pour qu que qui sa se ses si son sont sur ta te tes toi ton tous tout tu un une vos votre vous y c d j l m n s t qu' ça dont été fait faire fut plus moins très après avant contre entre sans sous chez depuis vers face selon comme aussi alors encore déjà bien quand ans an jour jours hier demain soir matin semaine mois
dit dire déclare estime assure affirme lance juge appelle annonce veut va peut doit faut ont avait avoir sera serait était
direct vidéo video live info infos actu actualité politique présidentielle presidentielle 2027 2026 élection election candidat candidate candidats campagne france français française français pourquoi comment quoi ce qu'il qu'elle selon après face nouveau nouvelle premier première tour'''.split())


def mots(titres24, regs):
    """Pour chaque candidat cité dans au moins 5 titres de 3 médias en 24 heures : les 3 mots repris par le plus de médias
    (au moins 3 médias chacun : un média qui publie beaucoup ne pèse pas plus), sans les mots courants ni les noms et prénoms des candidats."""
    noms = set()
    for c, r in regs.items():
        for x in [c] + list((r.get('prenoms') if isinstance(r, dict) else None) or []):
            n = norm(x if isinstance(x, str) else ' '.join(x)); noms |= set(n.split()) | set(n.replace('-', ' ').split())
    sortie = {}
    for c, L in titres24.items():
        if len(L) < 5 or len({m for m, _ in L}) < 3:
            continue
        compte, forme = {}, {}
        for m, t in L:
            vus = set()
            for w in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'-]+", t):
                w = re.sub(r"^[a-zA-Z]'", '', w).strip("'-")
                k = norm(w)
                if len(k) < 4 or k in VIDES or k in noms or k in vus:
                    continue
                vus.add(k); compte.setdefault(k, set()).add(m); forme.setdefault(k, {}); forme[k][w] = forme[k].get(w, 0) + 1
        top = [k for k, n in sorted(compte.items(), key=lambda x: (-len(x[1]), x[0])) if len(n) >= 3][:3]
        if top:
            sortie[c] = {'mots': [max(forme[k], key=lambda w: (forme[k][w], w.islower())) for k in top], 'titres': len(L)}
    return sortie


def agreger(archive, sources, noms_cfg, regs, sans, noms=None):
    debut = archive['debut']
    cands = list(regs)
    suivis = archive.get('suivis', {})
    # Titres relus avec la règle en vigueur (noms) : chaque candidat est compté depuis le début du relevé ;
    # ses chapeaux, eux, ne sont lus que depuis le relevé où il est entré dans la liste (chapeaux_depuis).
    depuis = {c: debut if noms is not None else max(debut, suivis.get(c, debut)[:10]) for c in cands}
    jours, medias = {}, {}
    exemples = {c: [] for c in cands}
    titres24 = {c: [] for c in cands}
    fin24 = dt.datetime.fromisoformat(archive['releves'][-1]['t']) - dt.timedelta(hours=24) if archive['releves'] else None
    for a in sorted(archive['articles'], key=lambda a: (a['jour'], a.get('quand') or a['vu'])):
        if a['jour'] < debut:  # article publié avant le premier relevé : flux de profondeur inégale, pas compté
            continue
        if a['jour'] > dt.datetime.fromisoformat(a['vu']).astimezone(PARIS).date().isoformat():  # daté après le jour où il a été vu (agenda) : pas compté
            continue
        j = jours.setdefault(a['jour'], {c: 0 for c in cands})
        if noms is not None:
            a['cites'] = recompte(a, noms)
        for c in a['cites']:
            if c not in j:
                continue
            j[c] += 1
            medias.setdefault(a['jour'], {}).setdefault(c, set()).add(a['media'])
            if fin24 and dt.datetime.fromisoformat(a['vu']) >= fin24 and a['cites'][c] == 'titre':
                titres24[c].append((a['media'], a['titre']))
            exemples[c].append({'champ': a['cites'][c], 'titre': a['titre'], 'lien': a['lien'], 'media': a['media'], 'jour': a['jour']})
    # Par jour : un média est « lu » s'il a répondu à au moins un relevé ce jour-là ; sinon il est indisponible.
    media = lambda f: f.split(' · ')[0]
    statut = {}
    for r in archive['releves']:
        s = statut.setdefault(r['jour'], {'attendus': 0, 'releves': 0, '_att': set(), '_lus': set()})
        s['releves'] += 1
        err = {e['media'] for e in r['erreurs']}
        s['_att'] |= set(r['noms_lus']) | err
        s['_lus'] |= set(r['noms_lus'])
    for s in statut.values():
        att, lus = s.pop('_att'), s.pop('_lus')
        att_m, lus_m = {media(f) for f in att}, {media(f) for f in lus}
        s['attendus'], s['lus'], s['erreurs'] = len(att_m), len(lus_m), sorted(att_m - lus_m)
        s['flux_attendus'], s['flux_lus'], s['flux_erreurs'] = len(att), len(lus), sorted(att - lus)
    der = archive['releves'][-1]
    actifs = [s for s in sources if s.get('active')]
    med_act = sorted({s['name'] for s in actifs})
    der_lus = {media(f) for f in der['noms_lus']}
    der_err = [e['media'] for e in der['erreurs']]
    return {
        'source': 'Flux RSS publics de %d médias français (%d flux ; titres et chapeaux), et titres de %d médias sans flux utilisable relevés via GDELT, toutes les 30 minutes par outils/presse.py' % (len(med_act) - len({s['name'] for s in actifs if s.get('gdelt')}), len([s for s in actifs if not s.get('gdelt')]), len({s['name'] for s in actifs if s.get('gdelt')})),
        'methode': noms_cfg['regle'] + ' Chaque jour (heure de Paris, date de publication du flux) : le nombre d\'articles distincts qui citent chaque candidat, tous médias ensemble ; un même article repris dans deux flux compte une fois. Les articles publiés avant le premier relevé ne comptent pas.',
        'noms': {c: r.get('note', '') for c, r in regs.items()},
        'candidats': 'Suivies : toutes les personnes testées dans au moins un sondage de premier tour publié ces %d derniers jours (on entre quand un institut teste la personne, on sort quand plus aucun ne l\'a testée depuis %d jours). À la publication de la liste officielle des candidats par le Conseil constitutionnel, seuls ceux-là seront suivis.' % (JOURS_SONDAGES, JOURS_SONDAGES),
        'suivis': {c: (debut if noms is not None else suivis.get(c, debut)) for c in cands},
        'chapeaux_depuis': {c: suivis[c] for c in cands if noms is not None and len(suivis.get(c, '')) > 10},
        'sans_regle': sans,
        'debut': debut,
        'mis_a_jour': der['t'],
        # Un média par ligne (ses flux comptés dans « flux »).
        'panel': [{'name': s['name'], 'family': s['family'], 'active': bool(s.get('active')), 'flux': sum(1 for x in actifs if x['name'] == s['name']), **({'raison': s['raison']} if s.get('raison') else {}), **({'via': 'GDELT'} if s.get('gdelt') else {})} for s in premiers(sources)],
        # Un candidat pas encore suivi ce jour-là n'a pas de chiffre (null), ce n'est pas zéro.
        'jours': {d: {c: (jours.get(d, {}).get(c, 0) if d >= depuis[c] else None) for c in cands} for d in sorted(set(jours) | set(statut)) if d >= debut},
        # Par jour : les médias (pas les articles) qui citent chaque candidat ; un média compte une fois, quel que soit son nombre d'articles.
        'medias_jours': {d: {c: sorted(v) for c, v in medias[d].items()} for d in sorted(medias) if d >= debut},
        # Les mots les plus fréquents dans les titres des 24 dernières heures (candidats cités dans au moins 5 titres de 3 médias).
        'mots_24h': mots(titres24, regs),
        'statut': {d: statut[d] for d in sorted(statut)},
        # Un média est lu si au moins un de ses flux a répondu ; les flux en erreur d'un média lu sont listés à part.
        'dernier_releve': {'t': der['t'], 'attendus': len({media(f) for f in der['noms_lus']} | {media(f) for f in der_err}), 'lus': len(der_lus),
                           'erreurs': sorted({media(f) for f in der_err} - der_lus), 'flux_attendus': der['attendus'], 'flux_lus': der['lus'],
                           'flux_erreurs': [f for f in der_err if media(f) in der_lus]},
        # Exemples : les 3 derniers articles qui ont le nom dans le titre, complétés au besoin par ceux qui l'ont dans le chapeau.
        'exemples': {c: (list(reversed([x for x in v if x['champ'] == 'titre'][-3:])) + list(reversed([x for x in v if x['champ'] != 'titre'][-3:])))[:3] for c, v in exemples.items()},
    }


def main():
    a = sys.argv[1:]
    chemin = a[a.index('--archive') + 1] if '--archive' in a else None
    sources = json.load(open(SOURCES, encoding='utf-8'))['sources']
    noms_cfg = json.load(open(NOMS, encoding='utf-8'))
    archive = {'articles': [], 'releves': []}
    if chemin and os.path.exists(chemin):
        archive = json.load(open(chemin, encoding='utf-8'))
    maintenant = dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0)
    regs, sans = regles(noms_cfg, candidats_sondages(maintenant.astimezone(PARIS).date()))
    noms = compile_noms(regs, noms_cfg.get('autorises', []))
    if 'suivis' not in archive:  # les 8 premiers candidats sont suivis depuis le début du relevé
        archive['suivis'] = {c: archive['debut'] for c in PREMIERS} if archive.get('debut') else {}
    for c in regs:  # un nouveau nom : depuis ce relevé
        archive['suivis'].setdefault(c, maintenant.astimezone(PARIS).isoformat(timespec='minutes'))
    for c in sans:
        print('  sans règle, pas compté :', c)
    nouveaux, erreurs = releve(archive, sources, noms, maintenant)
    print('%d flux lus sur %d, %d articles nouveaux' % (archive['releves'][-1]['lus'], archive['releves'][-1]['attendus'], nouveaux))
    for e in erreurs:
        print('  indisponible :', e['media'], '·', e['erreur'])
    if '--ecrire' in a and chemin:
        tmp = chemin + '.tmp'
        json.dump(archive, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        os.replace(tmp, chemin)
    besoin = '--agreger' in a
    if '--agreger-si-besoin' in a:
        hier = (maintenant.astimezone(PARIS).date() - dt.timedelta(days=1)).isoformat()
        try:
            ancien = json.load(open(SORTIE, encoding='utf-8'))
        except Exception:
            ancien = {}
        besoin = (maintenant.hour, maintenant.minute) >= (23, 30) or (hier >= archive['debut'] and hier not in ancien.get('jours', {}))
    agg = agreger(archive, sources, noms_cfg, regs, sans, noms)
    der = sorted(agg['jours'])[-7:]
    for c in regs:
        print('  %-13s %s' % (c, sum(agg['jours'][d][c] or 0 for d in der)))
    if '--live' in a and '--ecrire' in a:
        live = a[a.index('--live') + 1]
        json.dump(agg, open(live + '.tmp', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        os.replace(live + '.tmp', live)
    if besoin and '--ecrire' in a:
        json.dump(agg, open(SORTIE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('écrit', SORTIE)


if __name__ == '__main__':
    main()
