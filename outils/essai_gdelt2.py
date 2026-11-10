import datetime as dt, os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import presse as P, urllib.request, io, zipfile, csv, re
der = urllib.request.urlopen(P.GDELT + 'lastupdate-translation.txt', timeout=30).read().decode()
print(der)
t = re.search(r'/(\d{14})\.translation\.gkg', der).group(1); print('t', t)
u = P.GDELT + t + '.translation.gkg.csv.zip'
try:
    z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(u, timeout=60).read()))
    n = 0
    for row in csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding='utf-8', errors='replace'), delimiter='\t'):
        n += 1
        if n < 2: print(len(row), row[1], row[3], row[25][:40])
    print('lignes', n)
except Exception:
    traceback.print_exc()
a = {}
G, err = P.lire_gdelt(a, dt.datetime.now(dt.timezone.utc), {'rtl.fr', 'laprovence.com', 'franceantilles.fr', 'corsematin.com', 'lesinrocks.com'})
print('err', err, a)
if G: print({k: len(v) for k, v in G.items()}); print([x['titre'] for v in G.values() for x in v][:5])
