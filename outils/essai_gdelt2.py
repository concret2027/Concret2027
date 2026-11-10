import subprocess
for u in ['https://www.ideal-investisseur.fr/', 'https://www.ideal-investisseur.fr/en/markets/oat-bund-spread.html']:
    r = subprocess.run(['curl', '-s', '-m', '30', '-A', 'Concret2027/1.0 (https://concret2027.fr)', '-o', '/tmp/p.html', '-w', '%{http_code} %{size_download}', u], capture_output=True, text=True)
    print(u, r.stdout, r.stderr[:200])
print(open('/tmp/p.html', errors='replace').read()[:300] if __import__('os').path.exists('/tmp/p.html') else '')
import re
t = open('/tmp/p.html', errors='replace').read() if __import__('os').path.exists('/tmp/p.html') else ''
print(re.findall(r'\d{2}/\d{2}/\d{4}[^<]{0,80}', t)[:5])
