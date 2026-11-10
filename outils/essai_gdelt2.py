import datetime as dt, os, sys, traceback, re, io, zipfile, csv, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import presse as P
csv.field_size_limit(10 ** 9)
fin = dt.datetime(2026, 11, 10, 5, 0)
for k in range(8):
    t = fin - dt.timedelta(minutes=15 * k)
    u = P.GDELT + t.strftime('%Y%m%d%H%M%S') + '.translation.gkg.csv.zip'
    try:
        z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(u, timeout=60).read()))
        n = m = 0
        for row in csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding='utf-8', errors='replace'), delimiter='\t'):
            n += 1
            if len(row) < 27 or 'srclc:fra' not in row[25]: continue
            dom = '.'.join(row[3].lower().split('.')[-2:])
            if dom in ('rtl.fr', 'laprovence.com', 'corsematin.com', 'franceantilles.fr', 'lesinrocks.com'):
                m += 1
                mt = re.search(r'<PAGE_TITLE>(.*?)</PAGE_TITLE>', row[26])
                q = dt.datetime.strptime(row[1], '%Y%m%d%H%M%S').replace(tzinfo=dt.timezone.utc).astimezone(P.PARIS)
                if m < 3: print(dom, q, P.texte(mt.group(1)) if mt else None)
        print(u[-40:], 'lignes', n, 'nos médias', m)
    except Exception:
        print(u[-40:]); traceback.print_exc(limit=2)
