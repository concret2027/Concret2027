"""Crédits du budget de l'État par mission et programme, lus dans le projet de loi de finances (tableau 1 des « Tableaux
d'évolution des dépenses » : crédits proposés pour l'année à venir, comparés à ceux votés pour l'année en cours).

  python3 outils/budget_missions.py   affiche les missions lues
"""
import json, os, re, subprocess, tempfile
PLF_URL = 'https://www.assemblee-nationale.fr/dyn/17/textes/l17b3210_projet-loi.pdf'
TITRE = "Projet de loi de finances pour 2027, tableau 1 « Tableau de comparaison, par mission et programme du budget général, des crédits proposés pour 2027 à ceux votés pour 2026 (hors fonds de concours) »"


def texte(url=PLF_URL):
    d = tempfile.mkdtemp()
    pdf = os.path.join(d, 'plf.pdf')
    subprocess.run(['curl', '-sSfL', '--retry', '4', '--max-time', '300', '-A', 'Mozilla/5.0 (concret2027.fr)', '-o', pdf, url], check=True)
    subprocess.run(['pdftotext', '-layout', pdf, pdf + '.txt'], check=True)
    return open(pdf + '.txt', encoding='utf-8').read()


NB = re.compile(r'\d{1,3}(?: \d{3})+|(?<![\d ])\d{1,3}(?![\d])')
def lire(txt):
    pages = txt.split('\f')
    deb = next(i for i, p in enumerate(pages) if 'Tableau de comparaison, par mission et programme du budget général, des crédits proposés pour' in p and 'Missions constituées de dotations' in p)
    rows, vus = [], 0
    for pi in range(deb, deb + 15):
        L = pages[pi].split('\n')
        # Fins de colonnes de la page : lues sur les lignes complètes (4 montants).
        fins = []
        for l in L:
            ms = [m for m in NB.finditer(l) if m.start() > 30]
            if len(ms) == 4: fins.append([m.end() for m in ms])
        if not fins: continue
        col = [sorted(f[k] for f in fins)[len(fins) // 2] for k in range(4)]
        cur = None
        for l in L:
            s = l.rstrip()
            if not s.strip(): cur = None; continue
            ms = [m for m in NB.finditer(s) if m.start() > 30]
            if ms and not re.match(r'^\s*(Projet de loi|LFI|Mission)', s):
                nom = s[:ms[0].start()].strip()
                if not nom: continue
                v = [None] * 4
                for m in ms:
                    k = min(range(4), key=lambda k: abs(col[k] - m.end()))
                    v[k] = int(m.group().replace(' ', ''))
                if nom.startswith('Pouvoirs publics'):
                    vus += 1
                    if vus > 1: return rows
                cur = {'nom': nom, 'ae26': v[0], 'ae27': v[1], 'cp26': v[2], 'cp27': v[3], 'page': pi + 1}
                rows.append(cur)
            elif cur is not None and not NB.search(s) and not s.strip().startswith('Missions') and not s.strip().startswith('(en euros)'):
                cur['nom'] += ' ' + s.strip()
            else:
                cur = None
    return rows
def grouper(R):
    cp = lambda r: r['cp27'] or 0
    i, M = 0, []
    while i < len(R):
        c, s, j = cp(R[i]), 0, i + 1
        while j < len(R) and s < c - 2: s += cp(R[j]); j += 1
        # les programmes « (ancien) » sans crédits 2027 suivent parfois
        while j < len(R) and cp(R[j]) == 0 and '(ancien)' in R[j]['nom']: j += 1
        if j > i + 1 and abs(s - c) <= 2: M.append(dict(R[i], programmes=R[i + 1:j])); i = j
        else: M.append(dict(R[i], programmes=[])); i += 1
    return M
def missions(url=PLF_URL):
    return grouper(lire(texte(url)))


if __name__ == '__main__':
    M = missions()
    for m in M: print(m['nom'][:60], m['cp27'], len(m['programmes']), m['page'])
