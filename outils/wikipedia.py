#!/usr/bin/env python3
"""Baromètre : consultations de la page Wikipédia (en français) des candidats, chiffres publics de Wikimedia.

Une mesure de l'intérêt du public, pas un sondage ni un soutien : le nombre de fois où la page de chaque candidat a été
lue (personnes seulement, robots exclus par Wikimedia), en lectures par semaine, en moyenne sur les 28 jours qui finissent
la veille du relevé (le dernier jour publié par Wikimedia), puis tous les 7 jours en remontant : la courbe va jusqu'à hier.
Les candidats : les 8 premiers des sondages de premier tour des 30 derniers jours, parmi ceux testés dans au moins la moitié
de ces sondages (
Marine Le Pen et Jordan Bardella comptent comme un seul candidat du RN, Marine Le Pen).
Source : API Wikimedia (https://wikimedia.org/api/rest_v1/), données ouvertes. L'outil respecte le délai demandé par
Wikimedia quand il répond « trop de requêtes » (en-tête Retry-After) ; un candidat qu'il n'a pas pu lire garde ses
chiffres précédents, et c'est dit.

  python3 outils/wikipedia.py            compare à data.json, sans rien écrire
  python3 outils/wikipedia.py --ecrire   écrit datasets.wikipedia_vues ({candidat, jusqu_au, vues}) et datasets.wikipedia_info ; chaque matin
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
    auj = date.today(); hier = auj - timedelta(days=1)
    avant = {}
    for r in D.get('wikipedia_vues', []): avant.setdefault(r['candidat'], []).append(r)
    lus, manque = {}, []
    for i, c in enumerate(C):
        if i: time.sleep(8)
        t = PAGES.get(c)
        v = lire(t, DEBUT - timedelta(days=27), hier) if t else None
        if not v:
            manque.append(c); print('%-12s pas lu (%s) : chiffres précédents gardés' % (c, 'page inconnue' if not t else 'Wikimedia refuse')); continue
        lus[c] = {date(int(j[:4]), int(j[4:6]), int(j[6:])): n for j, n in v.items()}
    if not lus:
        print('Wikipédia ✗ aucun chiffre lu. Rien écrit.'); sys.exit(1)
    # Dernier jour publié par Wikimedia pour tous les candidats lus (le chiffre d'hier peut arriver dans la matinée).
    fin = min(max(v) for v in lus.values())
    out = []
    for c in C:
        if c not in lus: out += avant.get(c, []); continue
        v, L, J = lus[c], [], fin
        # Un point tous les 7 jours, en remontant depuis le dernier jour : la moyenne par semaine des 28 jours qui finissent ce jour-là.
        while J - timedelta(days=27) >= DEBUT - timedelta(days=27) and J >= DEBUT:
            jours = [v.get(J - timedelta(days=k)) for k in range(28)]
            if all(x is not None for x in jours): L.append({'candidat': c, 'jusqu_au': J.isoformat(), 'vues': str(round(sum(jours) / 4))})
            J -= timedelta(days=7)
        L.reverse(); out += L
        print('%-12s %s : %s points, dernier (28 jours jusqu\'au %s) : %s lectures par semaine' % (c, PAGES[c], len(L), L[-1]['jusqu_au'], L[-1]['vues']))
    info = [{'releve': auj.isoformat(), 'jusqu_au': fin.isoformat(), 'candidats': ', '.join(C), 'source': 'Wikimedia, consultations des pages Wikipédia en français (personnes, robots exclus)',
             'url': 'https://pageviews.wmcloud.org/?project=fr.wikipedia.org&platform=all-access&agent=user&range=latest-90&pages=' + '|'.join(urllib.parse.quote(PAGES[c].replace(' ', '_')) for c in C if c in PAGES),
             'manque': ', '.join(manque)}]
    if ecrire:
        D['wikipedia_vues'] = out; D['wikipedia_info'] = info
        open(os.path.join(ROOT, 'data.json'), 'w', encoding='utf-8').write(json.dumps(o, indent=0, ensure_ascii=False))
        print('Écrit : datasets.wikipedia_vues (%d lignes) et wikipedia_info.' % len(out))


if __name__ == '__main__':
    main()
