#!/usr/bin/env python3
"""Jeu « Votre quinquennat » : les votes du Sénat sur les budgets 2027 (projet de loi de finances et projet de loi de
financement de la sécurité sociale), lus sur le site du Sénat.

Source : la liste des scrutins publics de la session (https://www.senat.fr/scrutin-public/scr<année>.html), puis la page
de chaque scrutin (résultat, décompte, position de chaque groupe). Seuls les scrutins dont l'intitulé porte sur l'un des
deux textes de 2027 sont gardés. Rien n'est saisi à la main : chaque chiffre est lu sur la page du scrutin.

Le rattachement à une mesure du jeu se fait dans outils/budget_jeu.py, par le numéro d'article écrit dans l'intitulé
(« l'article 16 », « de suppression de l'article 16 »), comme pour l'Assemblée.

  python3 outils/senat.py            compare avec donnees/budget_sources/senat_2027.json
  python3 outils/senat.py --ecrire   écrit donnees/budget_sources/senat_2027.json
"""
import html, json, os, re, sys, time, urllib.request
from datetime import date

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SORTIE = os.path.join(RACINE, 'donnees', 'budget_sources', 'senat_2027.json')
BASE = 'https://www.senat.fr/scrutin-public/'
UA = {'User-Agent': 'Concret/1.0 (https://concret2027.fr)'}
SESSION = 2026  # session 2026-2027 : liste scr2026.html
TEXTES = (('plfss', re.compile(r'financement de la s[ée]curit[ée] sociale pour 2027', re.I)),
          ('plf', re.compile(r'projet de loi de finances pour 2027', re.I)))
MOIS = {m: i + 1 for i, m in enumerate(['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'])}


def lire(url, essais=4):
    for k in range(essais):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception:  # noqa: BLE001
            if k == essais - 1: raise
            time.sleep(4 * (k + 1))


def texte(h):
    h = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', h, flags=re.S)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', h)).replace('\xa0', ' ')).strip()


def nb(s):
    return int(re.sub(r'\D', '', s) or 0)


def liste():
    """Les scrutins de la session : numéro, date, intitulé, lien."""
    h = lire(BASE + 'scr%d.html' % SESSION)
    out, jour = [], None
    # La page alterne des dates (« 4 novembre 2026 ») et des scrutins (« Scrutin N°49 : sur … »).
    for m in re.finditer(r'(\d{1,2}(?:er)? (?:%s) \d{4})|href="(\d{4}/scr\d{4}-(\d+)\.html)"[^>]*>\s*Scrutin N(?:&deg;|°)\s*\d+\s*</a>(.*?)(?=href="\d{4}/scr\d{4}-\d+\.html"|\d{1,2}(?:er)? (?:%s) \d{4}|$)' % ('|'.join(MOIS), '|'.join(MOIS)), h, re.S):
        if m.group(1):
            j, mo, a = m.group(1).replace('1er', '1').split(' ')
            jour = '%s-%02d-%02d' % (a, MOIS[mo], int(j))
            continue
        t = texte(m.group(4)).strip(' :-').strip()
        t = re.sub(r'\s*-\s*consulter le dossier législatif.*$', '', t).strip()
        out.append({'n': int(m.group(3)), 'd': jour, 't': t, 'url': BASE + m.group(2)})
    return out


def detail(s):
    x = texte(lire(s['url']))
    r = re.search(r"Le Sénat (a adopté|n'a pas adopté)\s+(\d[\d\s]*) votants\s+(\d[\d\s]*) suffrages exprimés\s+(\d[\d\s]*) pour\s+(\d[\d\s]*) contre\s+Abstention : (\d[\d\s]*)", x)
    if not r:
        raise ValueError('scrutin %d : décompte introuvable sur la page' % s['n'])
    s.update({'s': 'adopté' if r.group(1) == 'a adopté' else 'rejeté', 'votants': nb(r.group(2)), 'exprimes': nb(r.group(3)),
              'pour': nb(r.group(4)), 'contre': nb(r.group(5)), 'abst': nb(r.group(6)), 'g': {}})
    for g in re.finditer(r"Groupe ([^:]+?) : (\d+) sénateurs? Pour : (\d+) Contre : (\d+) Abstentions? : (\d+)", x):
        s['g'][g.group(1).strip()] = [int(g.group(3)), int(g.group(4)), int(g.group(5)), int(g.group(2))]
    return s


def main():
    ecrire = '--ecrire' in sys.argv
    L = [s for s in liste() if any(rx.search(s['t']) for _, rx in TEXTES)]
    for s in L:
        s['texte'] = next(k for k, rx in TEXTES if rx.search(s['t']))
        detail(s)
    L.sort(key=lambda s: s['n'])
    out = {'releve': date.today().isoformat(), 'source': {'titre': 'Sénat, scrutins publics de la session %d-%d' % (SESSION, SESSION + 1), 'url': BASE + 'scr%d.html' % SESSION},
           'scrutins': L}
    ancien = json.load(open(SORTIE, encoding='utf-8')) if os.path.exists(SORTIE) else {'scrutins': []}
    vus = {s['n'] for s in ancien['scrutins']}
    nouv = [s for s in L if s['n'] not in vus]
    print('%d scrutins du Sénat sur les budgets 2027 ; %d nouveaux' % (len(L), len(nouv)))
    for s in nouv: print('  n° %d (%s) %s : %s (%d pour, %d contre)' % (s['n'], s['d'], s['s'], s['t'][:150], s['pour'], s['contre']))
    if ecrire:
        json.dump(out, open(SORTIE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('Écrit :', os.path.relpath(SORTIE, RACINE))


if __name__ == '__main__':
    main()
