#!/usr/bin/env python3
"""Baromètre : consultations de la page Wikipédia (en français) des candidats, chiffres publics de Wikimedia.

Une mesure de l'intérêt du public, pas un sondage ni un soutien : le nombre de fois où la page de chaque candidat a été
lue (personnes seulement, robots exclus par Wikimedia), additionné par semaine complète, du lundi au dimanche.
Les candidats : les 8 premiers des sondages de premier tour des 30 derniers jours, parmi ceux testés dans au moins la moitié
de ces sondages (
Marine Le Pen et Jordan Bardella comptent comme un seul candidat du RN, Marine Le Pen).
Source : API Wikimedia (https://wikimedia.org/api/rest_v1/), données ouvertes. L'outil respecte le délai demandé par
Wikimedia quand il répond « trop de requêtes » (en-tête Retry-After) ; un candidat qu'il n'a pas pu lire garde ses
chiffres précédents, et c'est dit.

  python3 outils/wikipedia.py            compare à data.json, sans rien écrire
  python3 outils/wikipedia.py --ecrire   écrit datasets.wikipedia_vues et datasets.wikipedia_info
"""
import json, os, subprocess, sys, time, urllib.parse
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = 'https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/fr.wikipedia/all-access/user/'
UA = 'Concret2027/1.0 (https://concret2027.fr; contact@concret2027.fr)'
DEBUT = date(2025, 11, 3)  # un lundi : un an de semaines complètes
# Nom court du Baromètre → titre de la page Wikipédia en français.
PAGES = {'Le Pen': 'Marine Le Pen', 'Bardella': 'Jordan Bardella', 'Mélenchon': 'Jean-Luc Mélenchon', 'Philippe': 'Édouard Philippe',
         'Glucksmann': 'Raphaël Glucksmann', 'Attal': 'Gabriel Attal', 'Retailleau': 'Bruno Retailleau', 'Lisnard': 'David Lisnard',
         'Zemmour': 'Éric Zemmour', 'Hollande': 'François Hollande', 'Roussel': 'Fabien Roussel', 'Tondelier': 'Marine Tondelier',
         'Dupont-Aignan': 'Nicolas Dupont-Aignan', 'Arthaud': 'Nathalie Arthaud', 'Knafo': 'Sarah Knafo', 'Ruffin': 'François Ruffin',
         'Villepin': 'Dominique de Villepin', 'Faure': 'Olivier Faure', 'Bertrand': 'Xavier Bertrand', 'Royal': 'Ségolène Royal'}


def candidats(D):
    """Les 8 premiers des sondages de premier tour des 30 derniers jours (moyenne des scores), parmi les candidats testés dans
    au moins la moitié de ces sondages ; Bardella compté avec Le Pen."""
    rows = D.get('sondages_t1', [])
    if not rows: return []
    fin = max(r['date'] for r in rows); debut = (date.fromisoformat(fin) - timedelta(days=30)).isoformat()
    s, ou, tous = {}, {}, set()
    for r in rows:
        if r['date'] < debut: continue
        c = 'Le Pen' if r['candidat'] == 'Bardella' else r['candidat']; k = (r['date'], r['institut']); tous.add(k); ou.setdefault(c, set()).add(k)
        try: s.setdefault(c, []).append(float(r['score']))
        except (TypeError, ValueError): pass
    L = [(c, sum(v) / len(v)) for c, v in s.items() if 2 * len(ou[c]) >= len(tous)]
    return [c for c, _ in sorted(L, key=lambda x: -x[1])][:8]


def lire(titre, d0, d1):
    """Consultations par jour ; None si Wikimedia refuse encore après trois essais (délai Retry-After respecté)."""
    u = API + urllib.parse.quote(titre.replace(' ', '_')) + '/daily/' + d0.strftime('%Y%m%d') + '/' + d1.strftime('%Y%m%d')
    for essai in range(4):
        # Corps et en-têtes séparés (le proxy de l'environnement ajoute son propre bloc d'en-têtes).
        r = subprocess.run(['curl', '-sS', '-m', '60', '-A', UA, '-D', '/dev/stderr', '-o', '-', '-w', '\n%{http_code}', u], capture_output=True, text=True)
        corps, _, code = r.stdout.rpartition('\n'); tete = r.stderr
        if code == '200':
            return {it['timestamp'][:8]: it['views'] for it in json.loads(corps).get('items', [])}
        if code == '404':
            return {}
        att = 30
        for l in tete.splitlines():
            if l.lower().startswith('retry-after:'):
                try: att = min(90, int(l.split(':')[1]))
                except ValueError: pass
        if essai < 3: time.sleep(att + 2)
    return None


def main():
    ecrire = '--ecrire' in sys.argv
    o = json.load(open(os.path.join(ROOT, 'data.json'), encoding='utf-8'))
    D = o['datasets']
    C = candidats(D)
    auj = date.today(); dim = auj - timedelta(days=auj.weekday() + 1)  # dernier dimanche passé : semaines complètes seulement
    avant = {}
    for r in D.get('wikipedia_vues', []): avant.setdefault(r['candidat'], []).append(r)
    out, manque = [], []
    for i, c in enumerate(C):
        if i: time.sleep(8)
        t = PAGES.get(c)
        v = lire(t, DEBUT, dim) if t else None
        if not v:
            manque.append(c); out += avant.get(c, []); print('%-12s pas lu (%s) : chiffres précédents gardés' % (c, 'page inconnue' if not t else 'Wikimedia refuse')); continue
        sem = {}
        for j, n in v.items():
            d = date(int(j[:4]), int(j[4:6]), int(j[6:]))
            lundi = d - timedelta(days=d.weekday()); sem[lundi] = sem.get(lundi, 0) + n
        L = [{'candidat': c, 'semaine': k.isoformat(), 'vues': str(sem[k])} for k in sorted(sem)]
        out += L
        print('%-12s %s : %s semaines, dernière (%s) : %s consultations' % (c, t, len(L), L[-1]['semaine'], L[-1]['vues']))
    info = [{'releve': auj.isoformat(), 'jusqu_au': dim.isoformat(), 'candidats': ', '.join(C), 'source': 'Wikimedia, consultations des pages Wikipédia en français (personnes, robots exclus)',
             'url': 'https://pageviews.wmcloud.org/?project=fr.wikipedia.org&platform=all-access&agent=user&pages=' + '|'.join(urllib.parse.quote(PAGES[c].replace(' ', '_')) for c in C if c in PAGES),
             'manque': ', '.join(manque)}]
    if ecrire and out:
        D['wikipedia_vues'] = out; D['wikipedia_info'] = info
        open(os.path.join(ROOT, 'data.json'), 'w', encoding='utf-8').write(json.dumps(o, indent=0, ensure_ascii=False))
        print('Écrit : datasets.wikipedia_vues (%d lignes) et wikipedia_info.' % len(out))
    elif not out:
        print('Wikipédia ✗ aucun chiffre lu. Rien écrit.'); sys.exit(1)


if __name__ == '__main__':
    main()
