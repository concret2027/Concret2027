#!/usr/bin/env python3
"""Prévisions du FMI pour comparer le budget du joueur (« Votre quinquennat ») à la France et à ses voisins.

Lit, dans la base du FMI (DataMapper, mêmes chiffres que le Fiscal Monitor et les Perspectives de l'économie mondiale),
le solde des administrations publiques (GGXCNL_NGDP, % du PIB) et leur dette (GGXWDG_NGDP, % du PIB) pour la France,
l'Allemagne, l'Espagne, l'Italie et la zone euro, de l'année en cours à 2031. Vérifie que la dette de la France est
celle de la projection du jeu (même édition) ; sinon, n'écrit rien et le dit.

  python3 outils/budget_fmi.py           compare avec donnees/budget_sources/fmi_pays.json
  python3 outils/budget_fmi.py --ecrire  écrit donnees/budget_sources/fmi_pays.json
Jamais de saisie à la main.
"""
import json, subprocess, sys
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SORTIE = RACINE / 'donnees' / 'budget_sources' / 'fmi_pays.json'
API = 'https://www.imf.org/external/datamapper/api/v1/'
PAYS = [('FRA', 'France'), ('DEU', 'Allemagne'), ('ESP', 'Espagne'), ('ITA', 'Italie'), ('EURO', 'Zone euro')]
IND = {'solde': 'GGXCNL_NGDP', 'dette': 'GGXWDG_NGDP'}


def lire(ind):
    # Par curl, comme les autres outils (il passe par le proxy de l'environnement).
    out = subprocess.run(['curl', '-sS', '-m', '90', API + ind], capture_output=True, text=True, check=True).stdout
    return json.loads(out)['values'][ind]


def main():
    an0 = date.today().year
    ans = [str(a) for a in range(an0, 2032)]
    V = {k: lire(i) for k, i in IND.items()}
    res = {'genere_le': date.today().isoformat(),
           'source': "FMI, base DataMapper (Fiscal Monitor et Perspectives de l'économie mondiale), solde (GGXCNL_NGDP) et dette brute (GGXWDG_NGDP) des administrations publiques, % du PIB",
           'url': 'https://www.imf.org/external/datamapper/GGXCNL_NGDP@FM/FRA/DEU/ESP/ITA/EURO',
           'pays': []}
    for code, nom in PAYS:
        p = {'code': code, 'nom': nom}
        for k in IND:
            s = V[k].get(code) or {}
            p[k] = {a: s.get(a) for a in ans if s.get(a) is not None}
        res['pays'].append(p)
    # Même édition que la projection du jeu : la dette de la France doit être la même, année par année.
    jeu = json.load(open(RACINE / 'donnees' / 'budget_jeu.json'))
    fr = res['pays'][0]['dette']
    ecarts = [(y['an'], y.get('dette_fmi'), fr.get(str(y['an']))) for y in jeu['projection']['ans'] if y.get('dette_fmi') is not None and fr.get(str(y['an'])) is not None and abs(y['dette_fmi'] - fr[str(y['an'])]) > 0.05]
    if ecarts:
        print('Édition différente de la projection du jeu (dette de la France) :', ecarts, '— rien écrit.')
        return 1
    for p in res['pays']:
        print('%-10s solde %s · dette %s' % (p['nom'], {a: p['solde'].get(a) for a in ('2027', '2031')}, {a: p['dette'].get(a) for a in ('2027', '2031')}))
    if '--ecrire' in sys.argv:
        json.dump(res, open(SORTIE, 'w'), ensure_ascii=False, indent=1)
        print('Écrit :', SORTIE)
    else:
        try:
            old = json.load(open(SORTIE))
            print('Inchangé' if old['pays'] == res['pays'] else 'Différent du fichier : relancer avec --ecrire')
        except FileNotFoundError:
            print('Pas encore de fichier : relancer avec --ecrire')
    return 0


if __name__ == '__main__':
    sys.exit(main())
