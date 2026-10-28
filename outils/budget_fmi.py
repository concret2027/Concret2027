#!/usr/bin/env python3
"""Prévisions du FMI pour comparer le budget du joueur (« Votre quinquennat ») à la France et à ses voisins.

Lit, dans la base du FMI (DataMapper, mêmes chiffres que le Fiscal Monitor et les Perspectives de l'économie mondiale),
le solde des administrations publiques (GGXCNL_NGDP, % du PIB) et leur dette (GGXWDG_NGDP, % du PIB) pour la France,
l'Allemagne, l'Espagne, l'Italie et la zone euro (tableau « Se comparer »), puis les autres pays d'Europe, le Royaume-Uni, les États-Unis,
le Japon et le Canada, de l'année en cours à 2031. Vérifie que la dette de la France est
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
# Les pays du tableau « Se comparer » (tableau: True), puis les autres pays d'Europe et quatre grands pays, pour dire de quel pays
# le déficit du joueur est le plus proche, la même année.
PAYS = [('FRA', 'France', True), ('DEU', 'Allemagne', True), ('ESP', 'Espagne', True), ('ITA', 'Italie', True), ('EURO', 'Zone euro', True),
        ('BEL', 'Belgique', False), ('BGR', 'Bulgarie', False), ('CZE', 'Tchéquie', False), ('DNK', 'Danemark', False), ('EST', 'Estonie', False),
        ('IRL', 'Irlande', False), ('GRC', 'Grèce', False), ('HRV', 'Croatie', False), ('CYP', 'Chypre', False), ('LVA', 'Lettonie', False),
        ('LTU', 'Lituanie', False), ('LUX', 'Luxembourg', False), ('HUN', 'Hongrie', False), ('MLT', 'Malte', False), ('NLD', 'Pays-Bas', False),
        ('AUT', 'Autriche', False), ('POL', 'Pologne', False), ('PRT', 'Portugal', False), ('ROU', 'Roumanie', False), ('SVN', 'Slovénie', False),
        ('SVK', 'Slovaquie', False), ('FIN', 'Finlande', False), ('SWE', 'Suède', False), ('NOR', 'Norvège', False), ('ISL', 'Islande', False),
        ('CHE', 'Suisse', False), ('GBR', 'Royaume-Uni', False), ('USA', 'États-Unis', False), ('JPN', 'Japon', False), ('CAN', 'Canada', False)]
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
    for code, nom, tab in PAYS:
        p = {'code': code, 'nom': nom, 'tableau': tab}
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
    sans = [p['nom'] for p in res['pays'] if p['solde'].get(str(an0 + 1)) is None]
    if sans: print('Sans prévision de solde pour', an0 + 1, ':', ', '.join(sans))
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
