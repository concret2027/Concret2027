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
Candidats suivis : tous ceux testés dans les sondages de premier tour des 60 derniers jours (data.json,
datasets.sondages_t1), plus Jordan Bardella, testé à la place de Marine Le Pen. Chacun est compté à partir
du relevé où il entre dans la liste (archive['suivis']) : l'archive ne garde pas les chapeaux, on ne recompte pas le passé.
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
JOURS_SONDAGES = 60
PREMIERS = ['Le Pen', 'Mélenchon', 'Philippe', 'Glucksmann', 'Attal', 'Retailleau', 'Lisnard', 'Zemmour']
TOUJOURS = ['Bardella']  # testé à la place de Marine Le Pen
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
    """Tous les candidats testés dans les sondages de premier tour des 60 derniers jours, plus Bardella."""
    rows = json.load(open(DATA, encoding='utf-8'))['datasets'].get('sondages_t1', [])
    debut = (aujourdhui - dt.timedelta(days=JOURS_SONDAGES)).isoformat()
    L = []
    for r in sorted(rows, key=lambda r: r['date']):
        if r['date'] >= debut and r['candidat'] not in L:
            L.append(r['candidat'])
    return L + [c for c in TOUJOURS if c not in L]


def regles(cfg, cands):
    """La règle de chaque candidat suivi ; un nom sans règle écrite est cherché sous son nom complet (page Wikipédia)."""
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
            out[c] = {'motifs': [norm(PAGES[c])], 'note': 'Compté seulement sous son nom complet « %s » (règle par défaut, à revoir).' % PAGES[c]}
        else:
            sans.append(c)
    return out, sans


def compile_noms(cfg):
    out = {}
    for c, r in cfg.items():
        out[c] = ([re.compile(r'(?<![\w-])' + re.escape(m) + r'(?![\w])') for m in r['motifs']],
                  r.get('exclure_avant', []), r.get('exclure_apres', []))
    return out


def trouve(t, regle):
    motifs, avant, apres = regle
    for rx in motifs:
        for m in rx.finditer(t):
            if any(t[:m.start()].endswith(a) for a in avant) or any(t[m.end():].startswith(a) for a in apres):
                continue
            return True
    return False


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
    req = urllib.request.Request(src['rss_url'], headers={'User-Agent': UA, 'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml'})
    with urllib.request.urlopen(req, timeout=15) as r:
        b = r.read(8_000_000)
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
    with cf.ThreadPoolExecutor(24) as ex:
        res = dict(zip([fid(s) for s in actifs], ex.map(lambda s: _essai(s), actifs)))
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
            titre_n, desc_n = norm(it['titre']), norm(it['desc'])
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


def agreger(archive, sources, noms_cfg, regs, sans):
    debut = archive['debut']
    cands = list(regs)
    suivis = archive.get('suivis', {})
    depuis = {c: max(debut, suivis.get(c, debut)[:10]) for c in cands}  # jour du premier relevé qui le compte
    jours = {}
    exemples = {c: [] for c in cands}
    for a in sorted(archive['articles'], key=lambda a: (a['jour'], a.get('quand') or a['vu'])):
        if a['jour'] < debut:  # article publié avant le premier relevé : flux de profondeur inégale, pas compté
            continue
        if a['jour'] > dt.datetime.fromisoformat(a['vu']).astimezone(PARIS).date().isoformat():  # daté après le jour où il a été vu (agenda) : pas compté
            continue
        j = jours.setdefault(a['jour'], {c: 0 for c in cands})
        for c in a['cites']:
            if c not in j:
                continue
            j[c] += 1
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
        'source': 'Flux RSS publics de %d médias français (%d flux ; titres et chapeaux), relevés toutes les 30 minutes par outils/presse.py' % (len(med_act), len(actifs)),
        'methode': noms_cfg['regle'] + ' Chaque jour (heure de Paris, date de publication du flux) : le nombre d\'articles distincts qui citent chaque candidat, tous médias ensemble ; un même article repris dans deux flux compte une fois. Les articles publiés avant le premier relevé ne comptent pas.',
        'noms': {c: r.get('note', '') for c, r in regs.items()},
        'candidats': 'Tous les candidats testés dans les sondages de premier tour des %d derniers jours, plus Jordan Bardella, testé à la place de Marine Le Pen.' % JOURS_SONDAGES,
        'suivis': {c: suivis.get(c, debut) for c in cands},
        'sans_regle': sans,
        'debut': debut,
        'mis_a_jour': der['t'],
        # Un média par ligne (ses flux comptés dans « flux »).
        'panel': [{'name': s['name'], 'family': s['family'], 'active': bool(s.get('active')), 'flux': sum(1 for x in actifs if x['name'] == s['name']), **({'raison': s['raison']} if s.get('raison') else {})} for s in premiers(sources)],
        # Un candidat pas encore suivi ce jour-là n'a pas de chiffre (null), ce n'est pas zéro.
        'jours': {d: {c: (jours.get(d, {}).get(c, 0) if d >= depuis[c] else None) for c in cands} for d in sorted(set(jours) | set(statut)) if d >= debut},
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
    noms = compile_noms(regs)
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
    agg = agreger(archive, sources, noms_cfg, regs, sans)
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
