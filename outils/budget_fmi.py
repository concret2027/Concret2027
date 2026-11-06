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
# Les grands pays hors d'Europe placés sur le nuage « À quel pays ressemble votre budget » (dépenses et recettes des administrations
# publiques, Fiscal Monitor, % du PIB, la même année que les pays d'Europe d'Eurostat), et ceux du graphe de la richesse par habitant.
MONDE = [('USA', 'États-Unis', 'US'), ('CHN', 'Chine', 'CN'), ('JPN', 'Japon', 'JP'), ('GBR', 'Royaume-Uni', 'UK'), ('CAN', 'Canada', 'CA'),
         ('KOR', 'Corée du Sud', 'KR'), ('IND', 'Inde', 'IN'), ('RUS', 'Russie', 'RU'), ('BRA', 'Brésil', 'BR'), ('AUS', 'Australie', 'AU'),
         ('TUR', 'Turquie', 'TR')]
IND_MONDE = {'dep': 'G_X_G01_GDP_PT', 'rec': 'GGR_G01_GDP_PT'}
# PIB par habitant en parité de pouvoir d'achat (dollars internationaux), Perspectives de l'économie mondiale : l'UE et les grands pays.
UE27 = [('AUT', 'Autriche', 'AT'), ('BEL', 'Belgique', 'BE'), ('BGR', 'Bulgarie', 'BG'), ('HRV', 'Croatie', 'HR'), ('CYP', 'Chypre', 'CY'),
        ('CZE', 'Tchéquie', 'CZ'), ('DNK', 'Danemark', 'DK'), ('EST', 'Estonie', 'EE'), ('FIN', 'Finlande', 'FI'), ('FRA', 'France', 'FR'),
        ('DEU', 'Allemagne', 'DE'), ('GRC', 'Grèce', 'EL'), ('HUN', 'Hongrie', 'HU'), ('IRL', 'Irlande', 'IE'), ('ITA', 'Italie', 'IT'),
        ('LVA', 'Lettonie', 'LV'), ('LTU', 'Lituanie', 'LT'), ('LUX', 'Luxembourg', 'LU'), ('MLT', 'Malte', 'MT'), ('NLD', 'Pays-Bas', 'NL'),
        ('POL', 'Pologne', 'PL'), ('PRT', 'Portugal', 'PT'), ('ROU', 'Roumanie', 'RO'), ('SVK', 'Slovaquie', 'SK'), ('SVN', 'Slovénie', 'SI'),
        ('ESP', 'Espagne', 'ES'), ('SWE', 'Suède', 'SE')]


def lire(ind):
    # Par curl, comme les autres outils (il passe par le proxy de l'environnement).
    out = subprocess.run(['curl', '-sS', '-m', '90', API + ind], capture_output=True, text=True, check=True).stdout
    return json.loads(out)['values'][ind]


def meta(ind):
    """L'édition de la base (« Fiscal Monitor (October 2026) ») et la date de mise à jour, lues dans la liste des indicateurs."""
    out = subprocess.run(['curl', '-sS', '-m', '90', API + 'indicators'], capture_output=True, text=True, check=True).stdout
    m = json.loads(out)['indicators'][ind]
    return {'edition': m.get('source'), 'maj': m.get('last-modified'), 'unite': m.get('unit')}


def monde(an):
    """Dépenses et recettes des administrations publiques (% du PIB) des grands pays hors d'Europe, l'année an."""
    V = {k: lire(i) for k, i in IND_MONDE.items()}
    out, sans = [], []
    for code, nom, c2 in MONDE:
        d, r = (V['dep'].get(code) or {}).get(str(an)), (V['rec'].get(code) or {}).get(str(an))
        if d is None or r is None: sans.append(nom); continue
        out.append({'code': c2, 'imf': code, 'nom': nom, 'an': an, 'dep': round(d, 1), 'rec': round(r, 1)})
    return {'an': an, 'source': 'FMI, base DataMapper, Fiscal Monitor : dépenses (G_X_G01_GDP_PT) et recettes (GGR_G01_GDP_PT) des administrations publiques, % du PIB',
            'url': 'https://www.imf.org/external/datamapper/G_X_G01_GDP_PT@FM', 'edition': meta('G_X_G01_GDP_PT'), 'lu': date.today().isoformat(), 'pays': out, 'sans': sans}


def pib_hab():
    """PIB par habitant en parité de pouvoir d'achat (PPPPC), dernière année projetée commune à tous les pays retenus."""
    V = lire('PPPPC')
    L = UE27 + [(c, n, c2) for c, n, c2 in MONDE]
    dispo = [max([int(a) for a, v in (V.get(c) or {}).items() if v is not None] or [0]) for c, n, c2 in L]
    an = min([a for a in dispo if a > 0])
    out, sans = [], []
    for c, n, c2 in L:
        v = (V.get(c) or {}).get(str(an))
        if v is None: sans.append(n)
        else: out.append({'code': c2, 'imf': c, 'nom': n, 'v': round(v)})
    return {'an': an, 'source': "FMI, base DataMapper, Perspectives de l'économie mondiale : PIB par habitant en parité de pouvoir d'achat (PPPPC), dollars internationaux courants, projection",
            'url': 'https://www.imf.org/external/datamapper/PPPPC@WEO', 'edition': meta('PPPPC'), 'lu': date.today().isoformat(), 'pays': out, 'sans': sans}


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
    res['monde'] = monde(an0 - 1)
    res['pib_hab'] = pib_hab()
    print('Hors d\'Europe,', res['monde']['an'], ':', ', '.join('%s %s/%s' % (p['nom'], p['dep'], p['rec']) for p in res['monde']['pays']), '· sans chiffre :', res['monde']['sans'])
    print('PIB par habitant (PPA),', res['pib_hab']['an'], ':', ', '.join('%s %s' % (p['nom'], p['v']) for p in res['pib_hab']['pays'] if p['code'] in ('FR', 'DE', 'US', 'CN')), '· sans chiffre :', res['pib_hab']['sans'], '·', res['pib_hab']['edition'])
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
            memes = old['pays'] == res['pays'] and (old.get('monde') or {}).get('pays') == res['monde']['pays'] and (old.get('pib_hab') or {}).get('pays') == res['pib_hab']['pays']
            print('Inchangé' if memes else 'Différent du fichier : relancer avec --ecrire')
        except FileNotFoundError:
            print('Pas encore de fichier : relancer avec --ecrire')
    return 0


if __name__ == '__main__':
    sys.exit(main())
