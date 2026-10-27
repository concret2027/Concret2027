#!/usr/bin/env python3
"""Page « La vie politique » : votes de l'Assemblée nationale, lois publiées au Journal officiel, agenda de la séance,
lus dans les données ouvertes de l'Assemblée nationale (data.assemblee-nationale.fr, 17e législature) ; frise depuis 1995.

  python3 outils/parlement.py                 lit les données ouvertes et compare à data.json, sans rien écrire
  python3 outils/parlement.py --ecrire        écrit series.politique dans data.json et met à jour le calendrier
  python3 outils/parlement.py --historique  (avec --ecrire) relit aussi les législatures closes (14e à 16e, depuis juin 2012)
                                              pour les grandes lois ; sinon elles sont gardées telles quelles dans data.json
  python3 outils/parlement.py --frise         relit chaque source de la frise et vérifie que ses chiffres et ses dates y figurent
Chaque passage affiche aussi les « actualités possibles » : votes et lois des trois derniers jours rattachés à une page de
mission, avec une phrase neutre et le lien de la source, que la tâche quotidienne reprend dans actu_<page> après vérification.

Ce qui est retenu, toujours de la même façon (règle affichée sur la page) :
  - votes : tout scrutin public solennel, toute motion (censure, rejet), toute déclaration du Gouvernement suivie d'un vote,
    tout vote sur l'ensemble d'un texte ou sur une partie d'un budget ; position de chaque groupe = position majoritaire
    publiée par l'Assemblée, avec le nombre de voix pour, contre et abstentions du groupe ;
  - lois : chaque loi promulguée (acte « PROM-PUB » du dossier législatif), avec son numéro et son Journal officiel ;
  - agenda : les points confirmés de l'ordre du jour de la séance publique pour les quatorze jours qui viennent ;
  - frise : élections présidentielles (second tour), référendums, dissolutions, nominations de Premier ministre, votes de
    l'Assemblée qui renversent le Gouvernement ou lui refusent la confiance, révisions de la Constitution.
Les événements de la frise antérieurs à la 17e législature sont écrits ci-dessous (FRISE), chacun avec sa source et les
chiffres ou dates à y retrouver (--frise les relit). Ceux de la 17e législature sont lus dans les scrutins.
Code de sortie 1 si une source est introuvable ou illisible (rien n'est écrit)."""
import io, json, os, re, subprocess, sys, zipfile
from datetime import date, datetime, timedelta

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OD = 'https://data.assemblee-nationale.fr/static/openData/repository/17/'
SRC = {
    'scrutins': OD + 'loi/scrutins/Scrutins.json.zip',
    'dossiers': OD + 'loi/dossiers_legislatifs/Dossiers_Legislatifs.json.zip',
    'agenda': OD + 'vp/reunions/Agenda.json.zip',
    'organes': OD + 'amo/deputes_actifs_mandats_actifs_organes/AMO10_deputes_actifs_mandats_actifs_organes.json.zip',
}
AN = 'PO838901'          # l'Assemblée nationale de la 17e législature (organe de la séance publique)
JOURS_VOTES = 120        # votes des quatre derniers mois
MAX_VOTES = 80
JOURS_LOIS = 365
MAX_LOIS = 200
JOURS_AGENDA = 14
JOURS_AVENIR = 30       # votes solennels déjà fixés, pour la page Votez les lois
# Page Votez les lois (donnees/votes.json) : tous les votes importants de la législature qui portent sur un choix à faire.
VOTEZ = ('texte', 'partie', 'rejet', 'censure', 'confiance', 'declaration')
MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']

# Rattachement prudent d'un texte à une page de mission, sur les mots de son intitulé (affiché comme un renvoi, sans plus).
PAGES = {
    'finances': r'loi de finances|finances publiques|programmation des finances|comptes publics|budg|fiscal|impôt|dette publique|résultats de la gestion|approbation des comptes|fin de gestion',
    'sante': r'sécurité sociale|santé|sanitaire|hôpita|hospital|médic|médecin|infirmi|soignant|orthophon|soins|maladie(?!s affectant les cultures)|mortalité|pharmac|fin de vie|aide à mourir|bioéthique|vaccin|vapotage|protoxyde|perte d.autonomie|grand âge|dépendance|handicap',
    'vie': r'logement|loyer|locati|sans-abri|pouvoir d.achat|vie chère|salaire|emploi|chômage|retraite|retraité|titre-restaurant|titres restaurant|travail|professionnalisation|revenu|pauvreté|pauvres|précarité',
    'education': r'école|enseignement|éducation|élèves|scolaire|université|étudiant|programmation de la recherche|recherche publique|apprentissage|formation professionnelle',
    'securite': r'sécurité intérieure|sécurité globale|ordre public|forces de l.ordre|police|gendarmerie|(?<!mesures de )justice|judiciaire|juridiction|pénal|peines|emprisonnement|détenu|privation de liberté|narcotrafic|criminalité|pédocriminalité|criminel|délinquance|violence|homicide|plainte|prison|pénitentiaire|terroris|attentat|renseignement|surveillance|procureur|douane|sûreté|état d.urgence',
    'defense': r'(?<!légitime )défense(?!\w)|militaire|armées',
    'demographie': r'immigration|asile|étrangers|nationalité|intégration|natalité|naissance|politique familiale|allocations familiales|congé parental|adoption d.enfant|adoption plénière|réforme de l.adoption|rétention administrative|titre de séjour|titres de séjour|droit du sol',
}
# Les mots affichés sur les pages, pour que la règle se lise (les mêmes que ci-dessus, sans les troncatures).
ENTIER = {'hôpita': 'hôpital', 'hospital': 'hospitalier', 'infirmi': 'infirmier', 'orthophon': 'orthophoniste', 'budg': 'budget', 'médic': 'médicament', 'pharmac': 'pharmacie', 'terroris': 'terrorisme', 'locati': 'locatif', 'sans-abri': 'sans-abrisme'}
MOTS = {k: [ENTIER.get(w, w) for w in (re.sub(r'\(\?<?[!=][^)]*\)', '', m).replace('.', '\'') for m in v.split('|'))] for k, v in PAGES.items()}

# Frise : événements avant la 17e législature, lus à leur source officielle ; v = textes à retrouver tels quels dans la source.
CC = 'https://www.conseil-constitutionnel.fr/decision/'
QE = 'https://questions.assemblee-nationale.fr/dyn/15/questions/QANR5L15QE19405.pdf'
QE_SRC = 'Assemblée nationale, réponse à la question écrite n° 19405 (JO du 25 juin 2019) : date de parution au Journal officiel du décret nommant le Premier ministre'
ELY = 'https://www.elysee.fr/emmanuel-macron/'
REV = 'https://www.conseil-constitutionnel.fr/la-constitution/les-revisions-constitutionnelles'
REV_SRC = 'Conseil constitutionnel, les révisions constitutionnelles'


def date_fr(d):
    a, m, j = d[:10].split('-')
    return '%s %s %s' % ('1er' if j == '01' else str(int(j)), MOIS[int(m) - 1], a)


def pres(d, decision, gagnant, g, perdant, p, exprimes, url, jo=None):
    return {'d': d, 'k': 'presidentielle', 't': '%s élu président de la République' % gagnant,
            'x': '%s %s voix, %s %s voix (second tour, %s suffrages exprimés).' % (gagnant, g, perdant, p, exprimes),
            'src': 'Conseil constitutionnel, décision n° %s (proclamation des résultats)' % decision, 'url': url, 'v': [g, p, exprimes]}


def pm(d, nom, rang, url, src, v):
    e = {'d': d, 'k': 'gouvernement', 't': '%s %s%s' % (nom, 'nommée Première ministre' if nom.startswith('Élisabeth') else 'nommé Premier ministre', rang),
         'src': src, 'url': url, 'v': v}
    if url == QE:
        e['x'] = 'Décret publié au Journal officiel du %s.' % date_fr(d)
    return e


def rev(d, num, objet):
    return {'d': d, 'k': 'constitution', 't': 'Révision de la Constitution : %s' % objet, 'x': 'Loi constitutionnelle n° %s.' % num,
            'src': REV_SRC, 'url': REV, 'v': ['n° %s' % num]}


FRISE = [
    pres('1995-05-07', '95-81 PDR du 12 mai 1995', 'Jacques Chirac', '15 763 027', 'Lionel Jospin', '14 180 644', '29 943 671', CC + '1995/9581PDR.htm'),
    pres('2002-05-05', '2002-111 PDR du 8 mai 2002', 'Jacques Chirac', '25 537 956', 'Jean-Marie Le Pen', '5 525 032', '31 062 988', CC + '2002/2002111PDR.htm'),
    pres('2007-05-06', '2007-141 PDR du 10 mai 2007', 'Nicolas Sarkozy', '18 983 138', 'Ségolène Royal', '16 790 440', '35 773 578', CC + '2007/2007141PDR.htm'),
    pres('2012-05-06', '2012-154 PDR du 10 mai 2012', 'François Hollande', '18 000 668', 'Nicolas Sarkozy', '16 860 685', '34 861 353', CC + '2012/2012154PDR.htm'),
    pres('2017-05-07', '2017-171 PDR du 10 mai 2017', 'Emmanuel Macron', '20 743 128', 'Marine Le Pen', '10 638 475', '31 381 603', CC + '2017/2017171PDR.htm'),
    pres('2022-04-24', '2022-197 PDR du 27 avril 2022', 'Emmanuel Macron', '18 768 639', 'Marine Le Pen', '13 288 686', '32 057 325', CC + '2022/2022197PDR.htm'),
    {'d': '2000-09-24', 'k': 'referendum', 't': 'Référendum : le mandat du président passe de sept à cinq ans (quinquennat)',
     'x': 'Oui 7 407 697, non 2 710 651 (10 118 348 suffrages exprimés, 39 941 192 inscrits).',
     'src': 'Conseil constitutionnel, décision n° 2000-29 REF du 28 septembre 2000 (proclamation des résultats)', 'url': CC + '2000/200029REF.htm',
     'v': ['7 407 697', '2 710 651', '10 118 348', '39 941 192']},
    {'d': '2005-05-29', 'k': 'referendum', 't': 'Référendum : le traité établissant une Constitution pour l\'Europe n\'est pas ratifié',
     'x': 'Non 15 449 508, oui 12 808 270 (28 257 778 suffrages exprimés, 41 789 202 inscrits).',
     'src': 'Conseil constitutionnel, décision n° 2005-38 REF du 1er juin 2005 (proclamation des résultats)', 'url': CC + '2005/200538REF.htm',
     'v': ['15 449 508', '12 808 270', '28 257 778', '41 789 202']},
    {'d': '1997-04-21', 'k': 'dissolution', 't': 'Dissolution de l\'Assemblée nationale',
     'x': 'Décret du 21 avril 1997, élections les 25 mai et 1er juin 1997.',
     'src': 'Sénat, compte rendu de la séance du 22 avril 1997 (lettre du président de la République du 21 avril 1997)',
     'url': 'https://www.senat.fr/seances/s199704/s19970422/s19970422_mono.html', 'v': ['21 avril 1997', 'dissolution']},
    {'d': '2024-06-09', 'k': 'dissolution', 't': 'Dissolution de l\'Assemblée nationale',
     'x': 'Décret du 9 juin 2024 (JO du 10 juin 2024), élections les 30 juin et 7 juillet 2024.',
     'src': 'Assemblée nationale, « Dissolution de l\'Assemblée nationale, en application de l\'article 12 de la Constitution »',
     'url': 'https://www.assemblee-nationale.fr/dyn/actualites-accueil-hub/dissolution-de-l-assemblee-nationale-en-application-de-l-article-12-de-la-constitution',
     'v': ['décret du 9 juin 2024 portant dissolution', 'Journal Officiel du 10 juin 2024']},
    pm('1995-05-18', 'Alain Juppé', '', QE, QE_SRC, ['18/5/1995']),
    pm('1995-11-08', 'Alain Juppé', ' (deuxième gouvernement)', QE, QE_SRC, ['8/11/1995']),
    pm('1997-06-03', 'Lionel Jospin', '', QE, QE_SRC, ['3/6/1997']),
    pm('2002-05-07', 'Jean-Pierre Raffarin', '', QE, QE_SRC, ['7/5/2002']),
    pm('2002-06-18', 'Jean-Pierre Raffarin', ' (deuxième gouvernement)', QE, QE_SRC, ['18/6/2002']),
    pm('2004-03-31', 'Jean-Pierre Raffarin', ' (troisième gouvernement)', QE, QE_SRC, ['31/3/2004']),
    pm('2005-06-01', 'Dominique de Villepin', '', QE, QE_SRC, ['1/6/2005']),
    pm('2007-05-19', 'François Fillon', '', QE, QE_SRC, ['19/5/2007']),
    pm('2007-06-19', 'François Fillon', ' (deuxième gouvernement)', QE, QE_SRC, ['19/6/2007']),
    pm('2010-11-16', 'François Fillon', ' (troisième gouvernement)', QE, QE_SRC, ['16/11/2010']),
    pm('2012-05-16', 'Jean-Marc Ayrault', '', QE, QE_SRC, ['16/5/2012']),
    pm('2012-06-19', 'Jean-Marc Ayrault', ' (deuxième gouvernement)', QE, QE_SRC, ['19/6/2012']),
    pm('2014-04-01', 'Manuel Valls', '', QE, QE_SRC, ['1/04/2014']),
    pm('2014-08-26', 'Manuel Valls', ' (deuxième gouvernement)', QE, QE_SRC, ['26/08/2014']),
    pm('2016-12-07', 'Bernard Cazeneuve', '', QE, QE_SRC, ['7/12/2016']),
    pm('2017-05-16', 'Édouard Philippe', '', QE, QE_SRC, ['16/05/2017']),
    pm('2017-06-22', 'Édouard Philippe', ' (deuxième gouvernement)', QE, QE_SRC, ['22/06/2017']),
    pm('2020-07-03', 'Jean Castex', '', ELY + '2020/07/03/jean-castex-nomme-premier-ministre', 'Élysée, communiqué du 3 juillet 2020', ['Jean CASTEX Premier ministre']),
    pm('2022-05-16', 'Élisabeth Borne', '', ELY + '2022/05/16/le-president-de-la-republique-a-nomme-mme-elisabeth-borne-premiere-ministre-et-la-chargee-de-former-un-gouvernement',
       'Élysée, communiqué du 16 mai 2022', ['Elisabeth BORNE, Première ministre']),
    pm('2024-01-09', 'Gabriel Attal', '', ELY + '2024/01/09/le-president-de-la-republique-a-nomme-m-gabriel-attal-premier-ministre-et-la-charge-de-former-un-gouvernement',
       'Élysée, communiqué du 9 janvier 2024', ['Gabriel Attal Premier ministre']),
    pm('2024-09-05', 'Michel Barnier', '', ELY + '2024/09/05/le-president-de-la-republique-a-nomme-monsieur-michel-barnier-premier-ministre',
       'Élysée, communiqué du 5 septembre 2024', ['Michel Barnier Premier ministre']),
    pm('2024-12-13', 'François Bayrou', '', ELY + '2024/12/13/le-president-de-la-republique-a-nomme-m-francois-bayrou-premier-ministre-et-la-charge-de-former-un-gouvernement',
       'Élysée, communiqué du 13 décembre 2024', ['François Bayrou Premier ministre']),
    pm('2025-09-09', 'Sébastien Lecornu', '', ELY + '2025/09/09/le-president-de-la-republique-a-nomme-sebastien-lecornu-premier-ministre',
       'Élysée, communiqué du 9 septembre 2025', ['Sébastien Lecornu Premier ministre']),
    pm('2025-10-10', 'Sébastien Lecornu', ' (deuxième gouvernement)',
       ELY + '2025/10/10/nomination-de-sebastien-lecornu-premier-ministre', 'Élysée, communiqué du 10 octobre 2025', ['Nomination de Sébastien Lecornu, Premier ministre']),
    rev('1995-08-04', '95-880 du 4 août 1995', 'session parlementaire unique, élargissement du référendum'),
    rev('1996-02-22', '96-138 du 22 février 1996', 'création des lois de financement de la sécurité sociale'),
    rev('1998-07-20', '98-610 du 20 juillet 1998', 'avenir de la Nouvelle-Calédonie'),
    rev('1999-01-25', '99-49 du 25 janvier 1999', 'traité d\'Amsterdam'),
    rev('1999-07-08', '99-568 du 8 juillet 1999', 'Cour pénale internationale'),
    rev('1999-07-08', '99-569 du 8 juillet 1999', 'égalité entre les femmes et les hommes'),
    rev('2000-10-02', '2000-964 du 2 octobre 2000', 'mandat du président de la République ramené à cinq ans'),
    rev('2003-03-25', '2003-267 du 25 mars 2003', 'mandat d\'arrêt européen'),
    rev('2003-03-28', '2003-276 du 28 mars 2003', 'organisation décentralisée de la République'),
    rev('2005-03-01', '2005-204 du 1', 'préalable à la ratification du traité établissant une Constitution pour l\'Europe'),
    rev('2005-03-01', '2005-205 du 1', 'Charte de l\'environnement'),
    rev('2007-02-23', '2007-237 du 23 février 2007', 'corps électoral de la Nouvelle-Calédonie'),
    rev('2007-02-23', '2007-238 du 23 février 2007', 'responsabilité du président de la République'),
    rev('2007-02-23', '2007-239 du 23 février 2007', 'interdiction de la peine de mort'),
    rev('2008-02-04', '2008-103 du 4 février 2008', 'traité de Lisbonne'),
    rev('2008-07-23', '2008-724 du 23 juillet 2008', 'modernisation des institutions, dont la question prioritaire de constitutionnalité'),
    rev('2024-03-08', '2024-200 du 8 mars 2024', 'liberté de recourir à l\'interruption volontaire de grossesse'),
]
# Les deux lois constitutionnelles du 1er mars 2005 : la source écrit « 1 er mars » ; le numéro suffit à les retrouver.
for e in FRISE:
    if e['k'] == 'constitution' and e['d'] == '2005-03-01':
        num = e['x'].split('n° ')[1].split(' du')[0]
        e['x'] = 'Loi constitutionnelle n° %s du 1er mars 2005.' % num
        e['v'] = ['n° %s du 1' % num]


def get(url):
    # curl plutôt qu'urllib : il suit le proxy et les certificats de l'environnement de la tâche planifiée.
    r = subprocess.run(['curl', '-sSfL', '--retry', '4', '--retry-all-errors', '--retry-delay', '3', '--max-time', '300', '-A', 'Mozilla/5.0 (concret2027.fr)', url], capture_output=True)
    if r.returncode:
        raise IOError('téléchargement impossible (%s) : %s' % (url, r.stderr.decode('utf-8', 'replace').strip()))
    return r.stdout


def lire_zip(url, filtre=None):
    """Chaque fichier JSON de l'archive (filtre : début du chemin)."""
    z = zipfile.ZipFile(io.BytesIO(get(url)))
    for n in z.namelist():
        if n.endswith('.json') and (filtre is None or n.startswith(filtre)):
            yield json.loads(z.read(n))


def liste(x):
    return [] if x is None else x if isinstance(x, list) else [x]


def jour(s):
    return (s or '')[:10]


def nb(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return 0


def groupes(organes):
    """Groupes politiques en cours : code (abréviation), nom complet."""
    g = {}
    for o in organes:
        o = o.get('organe') or {}
        if o.get('codeType') == 'GP' and not (o.get('viMoDe') or {}).get('dateFin'):
            g[o['uid']] = {'c': o.get('libelleAbrev') or o.get('libelleAbrege') or o['libelle'], 'n': o['libelle']}
    return g


def genre(titre):
    t = titre.lower()
    if t.startswith('la motion de censure'):
        return 'censure'
    if t.startswith('la motion de rejet'):
        return 'rejet'
    if 'déclaration de politique générale' in t or '49, alinéa premier' in t:
        return 'confiance'
    if t.startswith('la déclaration'):
        return 'declaration'
    if t.startswith('la première partie') or t.startswith('la deuxième partie') or t.startswith('la seconde partie'):
        return 'partie'
    if t.startswith("l'ensemble") or re.match(r"(le|la) (projet|proposition) de loi", t):
        return 'texte'
    return 'autre'


IMPORTANT = re.compile(r"^(l'ensemble|la motion|la première partie|la deuxième partie|la seconde partie|la déclaration)", re.I)


def rattacher(texte):
    t = (texte or '').lower()
    # Un mot compte s'il commence un mot du titre (« naissance » ne doit pas être trouvé dans « reconnaissance »).
    return [p for p, rx in PAGES.items() if re.search(r'(?<!\w)(?:' + rx + ')', t)]


def votes(scrutins, gp, depuis):
    out = []
    for s in scrutins:
        s = s['scrutin']
        if s.get('organeRef') != AN or s['dateScrutin'] < depuis:
            continue
        code = s['typeVote']['codeTypeVote']
        if not (code in ('SPS', 'MOC') or IMPORTANT.match(s['titre'])):
            continue
        dec = s['syntheseVote']['decompte']
        obj = s.get('objet') or {}
        dos = (obj.get('dossierLegislatif') or {})
        g = {}
        for x in liste(((s.get('ventilationVotes') or {}).get('organe') or {}).get('groupes', {}).get('groupe')):
            if x['organeRef'] not in gp:
                continue
            v = x['vote']; d = v.get('decompteVoix') or {}
            # Un groupe dont aucun membre n'a voté pour, contre ou ne s'est abstenu n'a pas de position : « nv » (n'a pas pris part au vote).
            pos = v.get('positionMajoritaire') if nb(d.get('pour')) + nb(d.get('contre')) + nb(d.get('abstentions')) else 'nv'
            g[gp[x['organeRef']]['c']] = [pos, nb(d.get('pour')), nb(d.get('contre')), nb(d.get('abstentions')), nb(x.get('nombreMembresGroupe'))]
        e = {'d': s['dateScrutin'], 'n': int(s['numero']), 'k': genre(s['titre']), 'sol': code == 'SPS', 'moc': code == 'MOC',
             's': s['sort']['code'], 't': s['titre'].rstrip('.'), 'v': nb(s['syntheseVote'].get('nombreVotants')),
             'req': nb(s['syntheseVote'].get('nbrSuffragesRequis')), 'p': nb(dec.get('pour')), 'c': nb(dec.get('contre')), 'a': nb(dec.get('abstentions')),
             'g': g}
        if dos.get('dossierRef'):
            e['dos'] = dos['dossierRef']
            e['dl'] = dos.get('libelle')
        pg = rattacher((dos.get('libelle') or '') + ' ' + s['titre'])
        if pg:
            e['pg'] = pg
        out.append(e)
    out.sort(key=lambda e: (e['d'], e['n']), reverse=True)
    return out


def evenements_17(scrutins):
    """Frise, 17e législature : censure adoptée, confiance refusée (lus dans les scrutins)."""
    out = []
    for s in scrutins:
        s = s['scrutin']
        k = genre(s['titre'])
        if s.get('organeRef') != AN or k not in ('censure', 'confiance'):
            continue
        dec = s['syntheseVote']['decompte']
        url = 'https://www.assemblee-nationale.fr/dyn/17/scrutins/%s' % s['numero']
        src = 'Assemblée nationale, scrutin n° %s du %s' % (s['numero'], date_fr(s['dateScrutin']))
        if k == 'censure' and s['sort']['code'] == 'adopté':
            out.append({'d': s['dateScrutin'], 'k': 'censure', 't': 'L\'Assemblée adopte une motion de censure : le Gouvernement est renversé',
                        'x': '%s voix pour la censure (majorité requise : %s).' % (dec['pour'], s['syntheseVote']['nbrSuffragesRequis']),
                        'src': src, 'url': url})
        if k == 'confiance' and s['sort']['code'] == 'rejeté':
            out.append({'d': s['dateScrutin'], 'k': 'censure', 't': 'L\'Assemblée refuse la confiance au Gouvernement',
                        'x': '%s voix contre, %s pour.' % (dec['contre'], dec['pour']), 'src': src, 'url': url})
    return out


def lois(dossiers, depuis, dernier_vote):
    out = []
    for j in dossiers:
        d = j.get('dossierParlementaire')
        if not d:
            continue
        pile = [d.get('actesLegislatifs')]
        while pile:
            a = pile.pop()
            if isinstance(a, list):
                pile.extend(a)
            elif isinstance(a, dict):
                if a.get('codeActe') == 'PROM-PUB' and jour(a.get('dateActe')) >= depuis:
                    jo = a.get('infoJO') or {}
                    e = {'d': jour(a['dateActe']), 'code': a.get('codeLoi'), 't': (a.get('titreLoi') or d['titreDossier']['titre']).strip(),
                         'jo': jour(jo.get('dateJO')), 'njo': jo.get('numJO'), 'nor': jo.get('referenceNOR'), 'dos': d['uid']}
                    if d['uid'] in dernier_vote:
                        e['sc'] = dernier_vote[d['uid']]
                    pg = rattacher(e['t'])
                    if pg:
                        e['pg'] = pg
                    out.append(e)
                pile.extend(v for v in a.values() if isinstance(v, (dict, list)))
    vus, uniques = set(), []
    for e in sorted(out, key=lambda e: (e['d'], e['code'] or ''), reverse=True):
        if e['code'] not in vus:
            vus.add(e['code']); uniques.append(e)
    return uniques


def agenda(reunions, de, a):
    jours = {}
    for r in reunions:
        r = r.get('reunion') or {}
        if r.get('organeReuniRef') != AN or (r.get('cycleDeVie') or {}).get('etat') != 'Confirmé':
            continue
        d = jour(r.get('timeStampDebut'))
        if not (de <= d <= a):
            continue
        for p in liste(((r.get('ODJ') or {}).get('pointsODJ') or {}).get('pointODJ')):
            if (p.get('cycleDeVie') or {}).get('etat') != 'Confirmé' or not p.get('objet'):
                continue
            o = re.sub(r'^(Suite de la discussion|Discussion|Explications de vote et vote par scrutin public|Vote solennel)( de| du| sur)? ', '', p['objet']).strip()
            o = re.sub(r"^(la |le |les |l'|l’)", '', o)
            o = o[:1].upper() + o[1:]
            jours.setdefault(d, [])
            if o not in jours[d]:
                jours[d].append(o)
    return [{'d': d, 'o': jours[d]} for d in sorted(jours)]


HEMICYCLE = 'https://www.assemblee-nationale.fr/dyn/vos-deputes/hemicycle'


def hemicycle(gp):
    """Plan officiel de l'hémicycle : pour chaque groupe, l'angle moyen de ses sièges (180 à gauche, 0 à droite, vu de la
    présidence) et sa couleur sur le plan de l'Assemblée. Siège → député lu sur la page du plan ; député → groupe lu dans les
    mandats en cours (données ouvertes)."""
    import html as H, math
    s = get(HEMICYCLE).decode('utf-8', 'replace')
    m = re.search(r'data-siegeData="([^"]+)"', s)
    if not m:
        raise ValueError('plan de l\'hémicycle introuvable')
    sieges = json.loads(H.unescape(m.group(1)))
    pos = {}
    for a in re.findall(r'<path([^>]*)>', s):
        i, d = re.search(r'id="p(\d+)"', a), re.search(r'd="M([\d.]+)[ ,]([\d.]+)', a)
        if i and d:
            pos[i.group(1)] = (float(d.group(1)), float(d.group(2)))
    xs, ys = [p[0] for p in pos.values()], [p[1] for p in pos.values()]
    cx, cy = (min(xs) + max(xs)) / 2, max(ys)
    dep = {}
    for a in lire_zip(SRC['organes'], 'json/acteur/'):
        a = a.get('acteur') or {}
        uid = a.get('uid')
        uid = uid.get('#text') if isinstance(uid, dict) else uid
        for md in liste((a.get('mandats') or {}).get('mandat')):
            ref = (md.get('organes') or {}).get('organeRef')
            if md.get('typeOrgane') == 'GP' and not md.get('dateFin') and ref in gp:
                dep[uid] = gp[ref]['c']
    ang, coul = {}, {}
    for siege, v in sieges.items():
        g = dep.get((v.get('tooltipUrl') or '').rsplit('/', 1)[-1])
        if g and siege in pos:
            x, y = pos[siege]
            ang.setdefault(g, []).append(math.degrees(math.atan2(cy - y, x - cx)))
            coul.setdefault(g, v.get('couleur'))
    return {g: {'a': round(sum(l) / len(l), 1), 'coul': coul[g]} for g, l in ang.items()}


def votes_a_venir(reunions, de, a, dossiers):
    """Votes solennels confirmés à l'ordre du jour de la séance (page Votez les lois) : date, objet, dossier, vote sur une partie
    ou sur l'ensemble. Le dossier manquant est retrouvé par l'intitulé du texte (dossiers : intitulé en minuscules → dossier)."""
    out = {}
    for r in reunions:
        r = r.get('reunion') or {}
        if r.get('organeReuniRef') != AN or (r.get('cycleDeVie') or {}).get('etat') != 'Confirmé':
            continue
        d = jour(r.get('timeStampDebut'))
        if not (de <= d <= a):
            continue
        for p in liste(((r.get('ODJ') or {}).get('pointsODJ') or {}).get('pointODJ')):
            if p.get('typePointODJ') != 'Vote solennel' or (p.get('cycleDeVie') or {}).get('etat') != 'Confirmé' or not p.get('objet'):
                continue
            o = re.sub(r"^Vote solennel (sur |de )?(l'ensemble (du |de la |de l')|le |la |l')?", '', p['objet']).strip()
            partie = re.search(r'\((première|deuxième|seconde) partie\)', o)
            sujet = re.sub(r'\s*\([^()]*\)\s*$', '', o).strip()
            dos = ((p.get('dossiersLegislatifsRefs') or {}).get('dossierRef')) or dossiers.get(sujet.lower())
            if isinstance(dos, list):
                dos = dos[0]
            if not dos:
                continue
            k = 'partie' if partie else 'texte'
            cle = dos + ':' + k + (':' + partie.group(1) if partie else '')
            if cle not in out or d < out[cle]['d']:
                out[cle] = {'d': d, 'cle': cle, 'dos': dos, 'k': k, 'o': o[:1].upper() + o[1:]}
    return sorted(out.values(), key=lambda e: e['d'])


# Grandes lois : chaque loi promulguée depuis juin 2012 (14e législature, début des données ouvertes de l'Assemblée)
# qui a eu un scrutin public solennel à l'Assemblée, ou a été adoptée par l'article 49, alinéa 3 (sans vote), ou a été
# soumise au Conseil constitutionnel par des parlementaires ou l'exécutif, ou est un budget (loi de finances de l'année ou rectificative, loi de financement de la sécurité sociale). Rattachée à une mission
# par la commission de l'Assemblée saisie au fond.
REPO = 'https://data.assemblee-nationale.fr/static/openData/repository/'
LEGIS = {
    14: (REPO + '14/loi/dossiers_legislatifs/Dossiers_Legislatifs_XIV.json.zip', REPO + '14/loi/scrutins/Scrutins_XIV.json.zip'),
    15: (REPO + '15/loi/dossiers_legislatifs/Dossiers_Legislatifs_XV.json.zip', REPO + '15/loi/scrutins/Scrutins_XV.json.zip'),
    16: (REPO + '16/loi/dossiers_legislatifs/Dossiers_Legislatifs.json.zip', REPO + '16/loi/scrutins/Scrutins.json.zip'),
    17: (SRC['dossiers'], SRC['scrutins']),
}
ORGANES_HIST = REPO + '17/amo/tous_acteurs_mandats_organes_xi_legislature/AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip'
COMMISSIONS = [  # (mots du nom de la commission, pages de mission)
    ('lois constitutionnelles', ['securite']), ('finances', ['finances']), ('affaires sociales', ['sante', 'vie']),
    ('défense', ['defense']), ('affaires culturelles', ['education']),
]
BUDGETS = {'3': 'loi de finances de l\'année', '21': 'loi de finances rectificative', '4': 'loi de financement de la sécurité sociale'}


def objets_zip(url):
    """Dossiers ou scrutins d'une archive, quel que soit son format (un fichier par objet, ou un seul fichier pour la 14e)."""
    for j in lire_zip(url):
        if 'export' in j:
            for d in liste(j['export']['dossiersLegislatifs']['dossier']):
                yield d
        elif 'scrutins' in j:
            for x in liste(j['scrutins']['scrutin']):
                yield {'scrutin': x}
        else:
            yield j


def commissions():
    """{organe: (nom court, pages)} pour les commissions permanentes de toutes les législatures."""
    out = {}
    for j in lire_zip(ORGANES_HIST, 'json/organe/'):
        o = j.get('organe') or {}
        if o.get('codeType') != 'COMPER':
            continue
        nom = o.get('libelle') or ''
        for mots, pages in COMMISSIONS:
            if mots in nom.lower():
                out[o['uid']] = (o.get('libelleAbrege') or nom, pages)
                break
        else:
            out[o['uid']] = (o.get('libelleAbrege') or nom, [])
    return out


def grandes_lois(legs, coms):
    out = []
    for leg in legs:
        url_dos, url_scr = LEGIS[leg]
        sps = {}
        for s in objets_zip(url_scr):
            s = s['scrutin']
            if s['typeVote']['codeTypeVote'] == 'SPS':
                d = s['syntheseVote']['decompte']
                sps[s['uid']] = {'n': int(s['numero']), 'd': s['dateScrutin'], 'p': nb(d.get('pour')), 'c': nb(d.get('contre')), 's': s['sort']['code']}
        for j in objets_zip(url_dos):
            d = j.get('dossierParlementaire')
            if not d:
                continue
            actes, pile = [], [d.get('actesLegislatifs')]
            while pile:
                a = pile.pop()
                if isinstance(a, list):
                    pile.extend(a)
                elif isinstance(a, dict):
                    actes.append(a); pile.extend(v for v in a.values() if isinstance(v, (dict, list)))
            prom = [a for a in actes if a.get('codeActe') == 'PROM-PUB' and a.get('codeLoi')]
            if not prom:
                continue
            code = (d.get('procedureParlementaire') or {}).get('code')
            votes = [sps[v] for a in actes if (a.get('codeActe') or '').startswith('AN') for v in [((a.get('voteRefs') or {}).get('voteRef'))] if isinstance(v, str) and v in sps]
            for a in actes:
                if (a.get('codeActe') or '').startswith('AN') and isinstance((a.get('voteRefs') or {}).get('voteRef'), list):
                    votes += [sps[v] for v in a['voteRefs']['voteRef'] if v in sps]
            b493 = any((a.get('codeActe') or '').startswith('AN') and '49' in ((a.get('statutConclusion') or {}).get('libelle') or '') for a in actes)
            # Saisine du Conseil constitutionnel par des députés, des sénateurs, le président de la République, le Premier ministre
            # ou un président d'assemblée (la saisine automatique des lois organiques, « de droit », ne compte pas).
            bcc = any((a.get('codeActe') or '').startswith('CC-SAISIE') and a.get('codeActe') != 'CC-SAISIE-DROIT' for a in actes)
            motif = 'budget' if code in BUDGETS else 'sol' if votes else '493' if b493 else 'cc' if bcc else None
            if not motif:
                continue
            fond = [a.get('organeRef') for a in actes if (a.get('codeActe') or '').startswith('AN') and a.get('codeActe', '').endswith('COM-FOND-SAISIE')]
            com = coms.get(fond[0]) if fond else None
            for pr in prom:
                jo = pr.get('infoJO') or {}
                e = {'d': jour(pr['dateActe']), 'code': pr['codeLoi'], 't': (pr.get('titreLoi') or d['titreDossier']['titre']).strip(),
                     'jo': jour(jo.get('dateJO')), 'dos': d['uid'], 'leg': leg, 'motif': motif, 'com': com[0] if com else ''}
                # Mission : les budgets selon leur nature, les autres lois selon les mots de leur titre (MOTS, affichés sur les pages).
                e['pg'] = ['finances'] if code in ('3', '21') else ['sante', 'vie'] if code == '4' else rattacher(e['t'])
                if b493:
                    e['a493'] = True
                if bcc:
                    e['cc'] = True
                if votes:
                    v = sorted(votes, key=lambda x: x['d'])[-1]
                    e['sc'] = v
                out.append(e)
    vus, res = set(), []
    for e in sorted(out, key=lambda e: e['d'], reverse=True):
        if e['code'] not in vus:
            vus.add(e['code']); res.append(e)
    return res


def construire(auj):
    scr = [s for s in lire_zip(SRC['scrutins'])]
    gp = groupes(lire_zip(SRC['organes'], 'json/organe/'))
    if len(scr) < 1000 or len(gp) < 5:
        raise IOError('données de l\'Assemblée incomplètes (%d scrutins, %d groupes)' % (len(scr), len(gp)))
    V = votes(scr, gp, (auj - timedelta(days=JOURS_VOTES)).isoformat())[:MAX_VOTES]
    # Pour chaque dossier, le dernier vote sur l'ensemble (ou solennel) de la législature : sert à montrer comment les groupes ont voté une loi.
    tous = votes(scr, gp, '2024-07-01')
    dernier = {}
    for e in tous:
        if e.get('dos') and e['k'] == 'texte' and e['dos'] not in dernier:
            dernier[e['dos']] = e['n']
    utiles = {n for n in dernier.values()}
    L = lois(lire_zip(SRC['dossiers'], 'json/dossierParlementaire/'), (auj - timedelta(days=JOURS_LOIS)).isoformat(), dernier)[:MAX_LOIS]
    # Les votes cités par une loi mais plus anciens que la fenêtre des votes sont ajoutés, marqués « loi » (non listés dans les votes de la semaine).
    deja = {e['n'] for e in V}
    VL = [dict(e, loi=True) for e in tous if e['n'] in utiles and e['n'] not in deja and any(l.get('sc') == e['n'] for l in L)]
    reunions = list(lire_zip(SRC['agenda'], 'json/reunion/'))
    A = agenda(reunions, auj.isoformat(), (auj + timedelta(days=JOURS_AGENDA)).isoformat())
    intitules = {}
    for e in tous:
        if e.get('dos'):
            intitules[re.sub(r'\s*\([^()]*\)\s*$', '', e['t'][e['t'].lower().find('projet') if 'projet' in e['t'].lower() else 0:]).strip().lower()] = e['dos']
            if e.get('dl'):
                intitules[e['dl'].lower()] = e['dos']
    AV = votes_a_venir(reunions, auj.isoformat(), (auj + timedelta(days=JOURS_AVENIR)).isoformat(), intitules)
    F = sorted(FRISE + evenements_17(scr), key=lambda e: e['d'])
    G = [dict(v, ref=k) for k, v in gp.items()]
    tailles = {}
    for e in tous[:1]:
        for c, x in e['g'].items():
            tailles[c] = x[4]
    for g in G:
        g['m'] = tailles.get(g['c'], 0)
    G.sort(key=lambda g: -g['m'])
    frise = [{k: v for k, v in e.items() if k != 'v'} for e in F]
    P = {
        'votes': {'source': 'Assemblée nationale, données ouvertes : scrutins de la 17e législature', 'url': SRC['scrutins'], 'date': auj.isoformat()},
        'lois': {'source': 'Assemblée nationale, données ouvertes : dossiers législatifs (actes de promulgation, références au Journal officiel)', 'url': SRC['dossiers'], 'date': auj.isoformat()},
        'agenda': {'source': 'Assemblée nationale, données ouvertes : agenda (ordre du jour de la séance publique)', 'url': SRC['agenda'], 'date': auj.isoformat()},
        'groupes': {'source': 'Assemblée nationale, données ouvertes : organes (groupes politiques)', 'url': SRC['organes'], 'date': auj.isoformat()},
    }
    # Grandes lois : la 17e législature à chaque passage ; les législatures closes avec --historique, sinon gardées.
    coms = commissions()
    legs = [14, 15, 16, 17] if '--historique' in sys.argv else [17]
    GL = grandes_lois(legs, coms)
    if legs == [17]:
        avant = ((json.load(open(os.path.join(ROOT, 'data.json'), encoding='utf-8')).get('series') or {}).get('politique') or {}).get('GRANDES') or []
        GL = sorted(GL + [e for e in avant if e.get('leg', 17) < 17], key=lambda e: e['d'], reverse=True)
    # Certains titres reprennent l'intitulé complet (« LOI n° 2021-160 du 15 février 2021 prorogeant… ») : on garde l'objet.
    for e in GL:
        e['t'] = re.sub(r'^LOI (organique )?n°\s*\S+ du \d{1,2}(er)? \S+ \d{4}\s*', '', e['t'], flags=re.I).strip()
    for e in GL:
        if e['motif'] != 'budget':
            e['pg'] = rattacher(e['t'])
    P['mots'] = MOTS
    P['grandes'] = {'source': 'Assemblée nationale, données ouvertes : dossiers législatifs et scrutins des 14e à 17e législatures (depuis juin 2012)', 'url': REPO, 'date': auj.isoformat()}
    try:
        HM = hemicycle(gp)
    except (IOError, ValueError, KeyError) as x:
        print('Plan de l\'hémicycle : lecture impossible :', x)
        HM = {}
    VZ = {'maj': auj.isoformat(), 'GROUPES': [dict({k: g[k] for k in ('c', 'n', 'm')}, **HM.get(g['c'], {})) for g in G],
          'VOTES': [{k: e[k] for k in ('d', 'n', 'k', 's', 't', 'v', 'req', 'p', 'c', 'a', 'g', 'dos', 'dl', 'pg') if k in e} for e in tous if e['k'] in VOTEZ],
          'P': {'votes': P['votes'], 'groupes': P['groupes'], 'agenda': P['agenda'],
                'hemicycle': {'source': 'Assemblée nationale, plan de l\'hémicycle (place et couleur de chaque groupe)', 'url': HEMICYCLE, 'date': auj.isoformat()}},
          'AVENIR': AV,
          # Le Premier ministre en fonction à chaque date (nominations de la frise, chacune avec sa source) : nomme le Gouvernement visé par une censure.
          'PM': [{'d': e['d'], 'n': re.match(r'^(.*?) nommée? Premi', e['t']).group(1), 'src': e['src'], 'url': e['url']}
                 for e in frise if e['k'] == 'gouvernement' and e['d'] >= '2024-01-01' and re.match(r'^(.*?) nommée? Premi', e['t'])]}
    return {'maj': auj.isoformat(), 'GROUPES': G, 'VOTES': V + VL, 'LOIS': L, 'AGENDA': A, 'FRISE': frise, 'GRANDES': GL, 'P': P, '_votez': VZ}


def verifier_frise():
    ko = 0
    cache = {}
    for e in FRISE:
        if e['url'] not in cache:
            try:
                b = get(e['url'])
            except IOError as x:
                print('  ✗', e['d'], e['t'], ':', x); ko += 1; cache[e['url']] = None; continue
            if e['url'].endswith('.pdf'):
                r = subprocess.run(['pdftotext', '-layout', '-', '-'], input=b, capture_output=True)
                t = r.stdout.decode('utf-8', 'replace')
            else:
                t = b.decode('utf-8', 'replace')
                if 'senat.fr/seances/s1997' in e['url']:
                    t = b.decode('iso-8859-1', 'replace')
                import html as H
                t = H.unescape(re.sub(r'<[^>]+>', ' ', t))
            cache[e['url']] = re.sub(r'\s+', ' ', t.replace('\xa0', ' '))
        t = cache[e['url']]
        if t is None:
            continue
        manque = [v for v in e['v'] if v not in t]
        if manque:
            ko += 1
            print('  ✗', e['d'], e['t'], ': introuvable dans la source :', manque)
        else:
            print('  ✓', e['d'], e['t'])
    print('Frise :', 'tout est retrouvé à la source' if not ko else '%d événement(s) à revoir' % ko)
    return ko


def actualites(S, auj):
    """Votes et lois des trois derniers jours rattachés à une page : (page, date, phrase, source, url)."""
    de = (auj - timedelta(days=3)).isoformat()
    out = []
    for v in S['VOTES']:
        if v.get('loi') or v['d'] < de or not v.get('pg'):
            continue
        t = v['t'][:1].lower() + v['t'][1:]
        verbe = 'adopte' if v['s'] == 'adopté' else 'rejette'
        if v['moc']:
            ch = '%d voix pour la censure, majorité requise : %d' % (v['p'], v['req'])
        else:
            ch = '%d voix pour, %d contre, %d abstentions' % (v['p'], v['c'], v['a'])
        for pg in v['pg']:
            out.append((pg, v['d'], 'L\'Assemblée nationale %s %s (%s).' % (verbe, t, ch), 'Assemblée nationale, scrutin n° %d' % v['n'],
                        'https://www.assemblee-nationale.fr/dyn/17/scrutins/%d' % v['n']))
    for l in S['LOIS']:
        if (l.get('jo') or l['d']) < de or not l.get('pg'):
            continue
        for pg in l['pg']:
            out.append((pg, l.get('jo') or l['d'], 'Publication au Journal officiel de la loi n° %s du %s %s.' % (l['code'], date_fr(l['d']), l['t']),
                        'Journal officiel%s, dossier législatif de l\'Assemblée nationale' % (' n° %s' % l['njo'] if l.get('njo') else ''),
                        'https://www.assemblee-nationale.fr/dyn/17/dossiers/%s' % l['dos']))
    return out


def main():
    if '--frise' in sys.argv:
        sys.exit(1 if verifier_frise() else 0)
    auj = date.today()
    try:
        S = construire(auj)
    except (IOError, zipfile.BadZipFile, KeyError, ValueError) as x:
        print('Assemblée nationale : lecture impossible :', x)
        sys.exit(1)
    VZ = S.pop('_votez')
    o = json.load(open(os.path.join(ROOT, 'data.json'), encoding='utf-8'))
    avant = o.get('series', {}).get('politique') or {}
    nv = {e['n'] for e in S['VOTES']} - {e['n'] for e in avant.get('VOTES', [])}
    nl = {e['code'] for e in S['LOIS']} - {e['code'] for e in avant.get('LOIS', [])}
    print('Votes retenus : %d (%d nouveaux) ; lois publiées : %d (%d nouvelles) ; jours d\'agenda : %d ; frise : %d événements ; groupes : %d'
          % (len(S['VOTES']), len(nv), len(S['LOIS']), len(nl), len(S['AGENDA']), len(S['FRISE']), len(S['GROUPES'])))
    for e in [e for e in S['VOTES'] if e['n'] in nv][:15]:
        print('  vote', e['d'], e['n'], e['s'], '%d-%d-%d' % (e['p'], e['c'], e['a']), e['t'][:110])
    for e in [e for e in S['LOIS'] if e['code'] in nl][:15]:
        print('  loi ', e['d'], e['code'], e['t'][:110])
    act = actualites(S, auj)
    print('Actualités possibles (à vérifier, puis à reprendre dans actu_<page> sans doublon) :' if act else 'Actualités possibles : aucune (rien de rattaché à une page ces trois derniers jours).')
    for a in act:
        print('  [%s] %s · %s · %s · %s' % a)
    if '--ecrire' in sys.argv:
        o.setdefault('series', {})['politique'] = S
        assert 'textes' in o and 'datasets' in o
        open(os.path.join(ROOT, 'data.json'), 'w', encoding='utf-8').write(json.dumps(o, indent=0, ensure_ascii=False))
        cp = os.path.join(ROOT, 'donnees/calendrier.json')
        cal = json.load(open(cp, encoding='utf-8'))
        for it in cal.get('indicateurs', []):
            if it.get('id') in ('pol_votes', 'pol_lois', 'pol_agenda'):
                it['derniere_verification'] = auj.isoformat()
                it['derniere_donnee'] = {'pol_votes': (S['VOTES'] or [{}])[0].get('d'), 'pol_lois': (S['LOIS'] or [{}])[0].get('d'),
                                         'pol_agenda': (S['AGENDA'] or [{}])[-1].get('d')}[it['id']] or it.get('derniere_donnee')
                it['prochaine_verification'] = (auj + timedelta(days=1)).isoformat()
        open(cp, 'w', encoding='utf-8').write(json.dumps(cal, indent=1, ensure_ascii=False) + '\n')
        open(os.path.join(ROOT, 'donnees/votes.json'), 'w', encoding='utf-8').write(json.dumps(VZ, separators=(',', ':'), ensure_ascii=False) + '\n')
        print('Écrit : series.politique et donnees/votes.json (%d votes pour la page Votez les lois).' % len(VZ['VOTES']))


if __name__ == '__main__':
    main()
