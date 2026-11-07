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
Bibliothèque standard seulement. Jamais de saisie à la main.
"""
import concurrent.futures as cf, datetime as dt, email.utils, html, json, os, re, sys, unicodedata, urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(RACINE, 'donnees', 'presse_sources.json')
NOMS = os.path.join(RACINE, 'donnees', 'presse_noms.json')
SORTIE = os.path.join(RACINE, 'donnees', 'presse.json')
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


def compile_noms(cfg):
    out = {}
    for c, r in cfg['candidats'].items():
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


def cle_lien(u):
    return re.sub(r'[?#].*$', '', (u or '').strip()).rstrip('/').replace('http://', 'https://')


def releve(archive, sources, noms, maintenant):
    actifs = [s for s in sources if s.get('active')]
    with cf.ThreadPoolExecutor(12) as ex:
        res = dict(zip([s['name'] for s in actifs], ex.map(lambda s: _essai(s), actifs)))
    vus_guid = {a['guid'] for a in archive['articles'] if a.get('guid')}
    vus_lien = {cle_lien(a['lien']) for a in archive['articles'] if a.get('lien')}
    jour_releve = maintenant.astimezone(PARIS).date().isoformat()
    nouveaux, erreurs = 0, []
    for s in actifs:
        r = res[s['name']]
        if isinstance(r, str):
            erreurs.append({'media': s['name'], 'erreur': r})
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
                               'noms_lus': sorted({x['name'] for x in actifs} - {e['media'] for e in erreurs})})
    archive['releves'] = archive['releves'][-GARDE_RELEVES:]
    return nouveaux, erreurs


def _essai(s):
    try:
        return lire(s)
    except Exception as e:
        return (type(e).__name__ + ': ' + str(e))[:160]


def agreger(archive, sources, noms_cfg):
    debut = archive['debut']
    cands = list(noms_cfg['candidats'])
    jours = {}
    exemples = {c: [] for c in cands}
    for a in sorted(archive['articles'], key=lambda a: (a['jour'], a.get('quand') or a['vu'])):
        if a['jour'] < debut:  # article publié avant le premier relevé : flux de profondeur inégale, pas compté
            continue
        j = jours.setdefault(a['jour'], {c: 0 for c in cands})
        for c in a['cites']:
            j[c] += 1
            exemples[c].append({'champ': a['cites'][c], 'titre': a['titre'], 'lien': a['lien'], 'media': a['media'], 'jour': a['jour']})
    # Par jour : un média est « lu » s'il a répondu à au moins un relevé ce jour-là ; sinon il est indisponible.
    statut = {}
    for r in archive['releves']:
        s = statut.setdefault(r['jour'], {'attendus': 0, 'releves': 0, '_att': set(), '_lus': set()})
        s['releves'] += 1
        err = {e['media'] for e in r['erreurs']}
        s['_att'] |= set(r['noms_lus']) | err
        s['_lus'] |= set(r['noms_lus'])
    for s in statut.values():
        att, lus = s.pop('_att'), s.pop('_lus')
        s['attendus'], s['lus'], s['erreurs'] = len(att), len(lus), sorted(att - lus)
    der = archive['releves'][-1]
    actifs = [s for s in sources if s.get('active')]
    return {
        'source': 'Flux RSS publics de %d médias français (titres et chapeaux), relevés toutes les 30 minutes par outils/presse.py' % len(actifs),
        'methode': noms_cfg['regle'] + ' Chaque jour (heure de Paris, date de publication du flux) : le nombre d\'articles distincts qui citent chaque candidat, tous médias ensemble ; un même article repris dans deux flux compte une fois. Les articles publiés avant le premier relevé ne comptent pas.',
        'noms': {c: r.get('note', '') for c, r in noms_cfg['candidats'].items()},
        'debut': debut,
        'mis_a_jour': der['t'],
        'panel': [{'name': s['name'], 'family': s['family'], 'active': bool(s.get('active')), **({'raison': s['raison']} if s.get('raison') else {})} for s in sources],
        'jours': {d: jours.get(d, {c: 0 for c in cands}) for d in sorted(set(jours) | set(statut)) if d >= debut},
        'statut': {d: statut[d] for d in sorted(statut)},
        'dernier_releve': {'t': der['t'], 'attendus': der['attendus'], 'lus': der['lus'], 'erreurs': [e['media'] for e in der['erreurs']]},
        # Exemples : les 3 derniers articles qui ont le nom dans le titre, complétés au besoin par ceux qui l'ont dans le chapeau.
        'exemples': {c: (list(reversed([x for x in v if x['champ'] == 'titre'][-3:])) + list(reversed([x for x in v if x['champ'] != 'titre'][-3:])))[:3] for c, v in exemples.items()},
    }


def main():
    a = sys.argv[1:]
    chemin = a[a.index('--archive') + 1] if '--archive' in a else None
    sources = json.load(open(SOURCES, encoding='utf-8'))['sources']
    noms_cfg = json.load(open(NOMS, encoding='utf-8'))
    noms = compile_noms(noms_cfg)
    archive = {'articles': [], 'releves': []}
    if chemin and os.path.exists(chemin):
        archive = json.load(open(chemin, encoding='utf-8'))
    maintenant = dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0)
    nouveaux, erreurs = releve(archive, sources, noms, maintenant)
    print('%d médias lus sur %d, %d articles nouveaux' % (archive['releves'][-1]['lus'], archive['releves'][-1]['attendus'], nouveaux))
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
    agg = agreger(archive, sources, noms_cfg)
    der = sorted(agg['jours'])[-7:]
    for c in noms_cfg['candidats']:
        print('  %-11s %s' % (c, sum(agg['jours'][d][c] for d in der)))
    if besoin and '--ecrire' in a:
        json.dump(agg, open(SORTIE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('écrit', SORTIE)


if __name__ == '__main__':
    main()
