#!/usr/bin/env python3
"""Essai (rien publié) : les articles en français de GDELT (flux traduit du GKG 2.1, 24 dernières heures),
avec notre règle des noms appliquée aux titres (PAGE_TITLE). Compare au panel de donnees/presse_sources.json."""
import csv, datetime as dt, io, json, os, re, sys, urllib.request, zipfile, collections, html
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import presse as P
csv.field_size_limit(10**9)
cfg = json.load(open(os.path.join(P.RACINE, 'donnees', 'presse_noms.json'), encoding='utf-8'))
regs, sans = P.regles(cfg, P.candidats_sondages(dt.date.today()))
noms = P.compile_noms(regs, cfg.get('autorises', []))
src = json.load(open(os.path.join(P.RACINE, 'donnees', 'presse_sources.json'), encoding='utf-8'))['sources']
dom = lambda u: re.sub(r'^www\.', '', urllib.parse.urlparse(u).netloc.lower())
import urllib.parse
panel = {}
for s in src:
    d = dom(s['rss_url']); d = '.'.join(d.split('.')[-2:])
    panel.setdefault(d, (s['name'], s.get('active')))
fin = dt.datetime.utcnow().replace(second=0, microsecond=0); fin -= dt.timedelta(minutes=fin.minute % 15 + 30)
vus, par_dom, cite_dom, ex, accents, lus, err = set(), collections.Counter(), collections.defaultdict(collections.Counter), collections.defaultdict(list), [0, 0], 0, 0
for k in range(96):
    t = fin - dt.timedelta(minutes=15 * k)
    u = 'http://data.gdeltproject.org/gdeltv2/%s.translation.gkg.csv.zip' % t.strftime('%Y%m%d%H%M%S')
    try:
        z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(u, timeout=60).read()))
    except Exception as e:
        err += 1; continue
    lus += 1
    for row in csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding='utf-8', errors='replace'), delimiter='\t'):
        if len(row) < 27 or 'srclc:fra' not in row[25]: continue
        url = row[4]
        if url in vus: continue
        vus.add(url)
        d = '.'.join(row[3].lower().split('.')[-2:]); par_dom[d] += 1
        m = re.search(r'<PAGE_TITLE>(.*?)</PAGE_TITLE>', row[26])
        if not m: continue
        titre = html.unescape(m.group(1)).strip()
        if re.search(r'[éèàçêôû]', titre): accents[0] += 1
        accents[1] += 1
        t2 = P.norm_c(titre)
        for c, R in noms.items():
            if P.trouve(t2, R):
                cite_dom[d][c] += 1
                if len(ex[d]) < 2: ex[d].append(titre[:110])
actifs = {d for d, v in panel.items() if v[1]}
CLES = ['lemonde.fr','lepoint.fr','liberation.fr','lejdd.fr','cnews.fr','europe1.fr','marianne.net','mediapart.fr','lesechos.fr','letelegramme.fr','lamontagne.fr','rtl.fr','laprovence.com','corsematin.com','m6info.fr','franceantilles.fr','lesinrocks.com','lenouveleconomiste.fr','franceinter.fr','francetvinfo.fr','franceinfo.fr','ici.fr','bfmtv.com','lci.fr','tf1info.fr','arte.tv','courrier-picard.fr','lavoixdunord.fr','leprogres.fr','ouest-france.fr','actu.fr','lunion.fr','paris-normandie.fr','lyonne.fr','larep.fr','lepopulaire.fr','lejdc.fr','courrierdelouest.fr','lemainelibre.fr','presseocean.fr','nordeclair.fr','lequotidien.re','charliehebdo.fr','brut.media','i24news.tv','blast-info.fr']
print('\n=== MÉDIAS CLÉS : présence dans GDELT (24 h, articles en français) ===')
for d in CLES:
    etat = 'ACTIF dans nos 104' if d in actifs else ('EXCLU de nos 104' if d in panel else 'absent du panel')
    print('  %-22s %-20s articles %4d | citant un candidat : %3d %s' % (d, etat, par_dom.get(d, 0), sum(cite_dom[d].values()), dict(cite_dom[d].most_common(5))))
print('\n=== TOUS LES .fr HORS de nos médias ACTIFS, triés par articles (24 h) ===')
for d, n in par_dom.most_common():
    if d.endswith('.fr') and d not in actifs:
        print('  %-26s %-8s %4d articles | candidats %3d %s' % (d, 'EXCLU' if d in panel else '', n, sum(cite_dom[d].values()), dict(cite_dom[d].most_common(3))))
print('Fichiers lus : %d / 96 (erreurs %d) ; articles en français distincts : %d ; titres avec accents : %d / %d' % (lus, err, len(vus), accents[0], accents[1]))
fr = [d for d in par_dom if d.endswith('.fr')]
print('Domaines distincts : %d (dont .fr : %d)' % (len(par_dom), len(fr)))
dans = [d for d in par_dom if d in panel]
print('Déjà dans notre panel (même domaine) : %d : %s' % (len(dans), ', '.join(sorted(dans))))
print('\nDomaines HORS panel qui citent au moins un candidat dans un titre (24 h) :')
H = sorted([d for d in cite_dom if d not in panel], key=lambda d: -sum(cite_dom[d].values()))
for d in H[:60]:
    print('  %-28s articles %4d | citant : %3d %s | ex : %s' % (d, par_dom[d], sum(cite_dom[d].values()), dict(cite_dom[d].most_common(4)), ' // '.join(ex[d])))
tot_h = collections.Counter(); tot_p = collections.Counter()
for d, c in cite_dom.items(): (tot_p if d in panel else tot_h).update(c)
print('\nCitations par candidat (titres, 24 h) : panel via GDELT %s\n  hors panel %s' % (dict(tot_p.most_common()), dict(tot_h.most_common())))
print('\nPlus gros domaines hors panel (tous sujets) : ' + ', '.join('%s %d' % (d, n) for d, n in par_dom.most_common(200) if d not in panel)[:2500])
