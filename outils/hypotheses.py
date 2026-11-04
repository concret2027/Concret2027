#!/usr/bin/env python3
"""Baromètre : les hypothèses de chaque sondage de premier tour de 2026-2027, pour « choisir une hypothèse ».

Les sondages du site (datasets.sondages_t1) donnent, pour chaque candidat, la moyenne des hypothèses où il figure,
lue dans la notice ou le rapport. Le détail hypothèse par hypothèse est lu dans la liste de sondages de Wikipédia en
français (« Liste de sondages sur l'élection présidentielle française de 2027 », wikitexte brut ; une case peut nommer un
autre candidat que sa colonne, par exemple Hollande dans la colonne de Glucksmann).

Un sondage n'est gardé que si ses hypothèses lues sur Wikipédia redonnent exactement les chiffres du site : pour chaque
candidat, la même moyenne (à 0,05 point près) sur le même nombre d'hypothèses. Sinon il est écarté, avec la raison, et la
page le dit sous le graphique.

Les choix proposés (GROUPES) : les candidats qui ne sont pas testés dans toutes les hypothèses.

python3 outils/hypotheses.py            compare avec donnees/hypotheses_t1.json
python3 outils/hypotheses.py --ecrire   écrit donnees/hypotheses_t1.json (chaque matin, après les sondages)
"""
import datetime as D, json, os, re, sys, urllib.parse
from collections import defaultdict

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import historique_wp as WP  # noqa: E402
from historique import lire, institut  # noqa: E402

RACINE = os.path.dirname(ICI)
SORTIE = os.path.join(RACINE, 'donnees', 'hypotheses_t1.json')
PAGE = "Liste_de_sondages_sur_l'élection_présidentielle_française_de_2027"
# Les choix : dans chaque groupe, les candidats dont la présence change d'une hypothèse à l'autre.
GROUPES = [
    {'id': 'centre', 'titre': 'Au centre', 'candidats': ['Philippe', 'Attal']},
    {'id': 'gauche', 'titre': 'Pour le PS et Place publique', 'candidats': ['Glucksmann', 'Hollande', 'Faure']},
]
PARTICULES = {'Marine Le Pen': 'Le Pen', 'Bruno Le Maire': 'Le Maire', 'Dominique de Villepin': 'Villepin'}


def court(n):
    n = re.sub(r'\s*\(.*?\)\s*$', '', n).strip()
    return PARTICULES.get(n, n.split()[-1])


def main():
    ecrire = '--ecrire' in sys.argv
    data = json.load(open(os.path.join(RACINE, 'data.json'), encoding='utf-8'))
    site = defaultdict(dict)
    for r in data['datasets']['sondages_t1']:
        site[(r['date'], institut(r['institut']))][r['candidat']] = (float(r['score']), int(r['hypotheses']))
    src = lire('https://fr.wikipedia.org/w/index.php?title=' + urllib.parse.quote(PAGE) + '&action=raw')
    tmp = os.path.join(os.environ.get('TMPDIR', '/tmp'), 'concret_wp_2027.wiki')
    open(tmp, 'w', encoding='utf-8').write(src)
    lignes, rejets = WP.main(tmp, 2026, nom_cellule=True)
    wp = defaultdict(list)
    for l in lignes:
        wp[(l['fin'], institut(l['institut']))].append({court(c): v for c, v in l['scores'].items()})
    garde, ecartes = [], []
    for k in sorted(site):
        hs = wp.get(k)
        if not hs:
            ecartes.append({'date': k[0], 'institut': k[1], 'raison': 'absent de la liste de Wikipédia'}); continue
        ko = []
        for c, (v, nh) in site[k].items():
            m = [h[c] for h in hs if c in h]
            if not m: ko.append('%s absent' % c)
            elif len(m) != nh: ko.append('%s : %d hypothèses sur Wikipédia, %d sur Concret' % (c, len(m), nh))
            elif abs(sum(m) / len(m) - v) > 0.051: ko.append('%s : %.2f sur Wikipédia, %.2f sur Concret' % (c, sum(m) / len(m), v))
        if ko:
            ecartes.append({'date': k[0], 'institut': k[1], 'raison': ' ; '.join(ko)}); continue
        garde.append({'date': k[0], 'institut': k[1], 'hyp': [{c: v for c, v in h.items() if c in site[k]} for h in hs]})
    out = {'releve': D.date.today().isoformat(),
           'source': {'titre': 'Wikipédia, ' + PAGE.replace('_', ' '), 'url': 'https://fr.wikipedia.org/wiki/' + urllib.parse.quote(PAGE)},
           'groupes': GROUPES, 'sondages': garde, 'ecartes': ecartes}
    print('%d sondages du site ; %d gardés avec leurs %d hypothèses ; %d écartés (hypothèses différentes de celles lues par Concret) :'
          % (len(site), len(garde), sum(len(p['hyp']) for p in garde), len(ecartes)))
    for e in ecartes: print('  ', e['date'], e['institut'], '·', e['raison'][:160])
    if os.path.exists(SORTIE):
        a = json.load(open(SORTIE, encoding='utf-8'))
        print('inchangé' if (a['sondages'], a['ecartes']) == (out['sondages'], out['ecartes']) else 'changé depuis le relevé du ' + a['releve'])
    if ecrire:
        json.dump(out, open(SORTIE, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        print('Écrit :', os.path.relpath(SORTIE, RACINE), os.path.getsize(SORTIE), 'octets')


if __name__ == '__main__':
    main()
